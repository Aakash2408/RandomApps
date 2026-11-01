"""In-memory public chat rooms for Lifetimes.

Anyone on the site can read and post, so the design limits what a stranger can do:
- a fixed set of rooms (nobody can create one), and only the newest MAX_PER_ROOM
  messages are kept, each for at most TTL seconds; nothing touches disk;
- nickname + short text only. Links, emails and phone-number-like digit runs are
  refused, which also stops players (often teens) sharing contact details;
- per-IP posting limits, plus a global cap so a flood cannot grow memory;
- three distinct reporters hide a message for everyone.
Clients render every field as text (never HTML), and the server re-validates the
optional "life" share card field by field.
"""
from __future__ import annotations

import re
import threading
import time
from collections import deque

ROOMS = {
    "general": ("💬", "General", "Talk about anything (game-related, ideally)."),
    "stories": ("📖", "Life stories", "Share how your last life went."),
    "rich": ("💰", "Billionaires club", "Flex your net worth and swap money tips."),
    "hardcore": ("💀", "Hardcore", "For Hardcore and Challenge mode survivors."),
    "help": ("🛟", "Help & tips", "How do I become a surgeon? Ask here."),
}
MAX_PER_ROOM = 100
TTL = 24 * 3600
MAX_TEXT = 240
NICK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.\-]{1,15}$")
RESERVED = ("admin", "moderator", "mod", "system", "lifetimes", "staff", "official")
LINK_RE = re.compile(
    r"(https?://|www\.|\b[a-z0-9-]+\.(com|net|org|io|gg|app|xyz|me|co|ly|ru|tk|link|site|online|info|biz|in|uk)\b"
    r"|\b[\w.+-]+@[\w-]+\.\w+|discord\.gg|t\.me/|wa\.me/)", re.I)
DIGITS_RE = re.compile(r"(?:\d[\s\-().]*){7,}")  # phone numbers and the like
MONEY_RE = re.compile(r"[$€£₹¥]\s?\d[\d,.]*\s?(k|m|b|bn|million|billion|trillion)?\b", re.I)
CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")
# A short list of slurs and the worst insults gets the message refused outright.
BLOCKED_WORDS = re.compile(r"\b(n[i1]gg(a|er)s?|f[a@]gg?(ot)?s?|retards?|k[i1]ke|ch[i1]nk|tr[a@]nny|kys)\b", re.I)
# Milder swearing is masked, not refused.
MASK_WORDS = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt\w*|dick\w*|asshole\w*)\b", re.I)

POST_GAP = 3.0           # seconds between posts from one IP
POSTS_PER_10MIN = 30
GLOBAL_PER_MIN = 300
REPORTS_TO_HIDE = 3
REPORTS_PER_HOUR = 30


class Rejected(Exception):
    def __init__(self, msg: str, status: int = 400):
        super().__init__(msg)
        self.status = status


def _clean_text(raw) -> str:
    if not isinstance(raw, str):
        raise Rejected("write a message")
    t = CONTROL_RE.sub("", raw).strip()
    t = re.sub(r"\s+", " ", t)
    if not t:
        raise Rejected("write a message")
    if len(t) > MAX_TEXT:
        raise Rejected(f"keep it under {MAX_TEXT} characters")
    if LINK_RE.search(t):
        raise Rejected("links and emails aren't allowed in chat")
    if DIGITS_RE.search(MONEY_RE.sub(" ", t)):
        raise Rejected("phone numbers aren't allowed in chat")
    if BLOCKED_WORDS.search(t):
        raise Rejected("that message breaks the chat rules")
    return MASK_WORDS.sub(lambda m: m.group(0)[0] + "*" * (len(m.group(0)) - 1), t)


def _clean_nick(raw) -> str:
    if not isinstance(raw, str):
        raise Rejected("pick a nickname")
    n = re.sub(r"\s+", " ", raw.strip())
    if not NICK_RE.fullmatch(n):
        raise Rejected("nicknames are 2-16 letters, numbers, spaces, _ . -")
    low = n.lower().replace(" ", "")
    if any(low.startswith(r) for r in RESERVED) or BLOCKED_WORDS.search(n) or MASK_WORDS.search(n) or DIGITS_RE.search(n):
        raise Rejected("pick a different nickname")
    return n


def _short(v, n: int) -> str:
    if not isinstance(v, str):
        raise Rejected("bad life card")
    v = CONTROL_RE.sub("", v).strip()[:n]
    if LINK_RE.search(v) or DIGITS_RE.search(v) or BLOCKED_WORDS.search(v):
        raise Rejected("bad life card")
    return v


def _clean_life(raw):
    """Optional summary of a finished life, shown as a card. Every field is checked."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise Rejected("bad life card")
    age, worth = raw.get("age"), raw.get("worth")
    if not isinstance(age, int) or isinstance(age, bool) or not 0 <= age <= 130:
        raise Rejected("bad life card")
    if not isinstance(worth, (int, float)) or isinstance(worth, bool) or not -1e12 <= worth <= 1e13:
        raise Rejected("bad life card")
    ach = raw.get("achievements", 0)
    if not isinstance(ach, int) or isinstance(ach, bool) or not 0 <= ach <= 99:
        raise Rejected("bad life card")
    mode = raw.get("mode", "classic")
    if mode not in ("classic", "hardcore", "challenge"):
        raise Rejected("bad life card")
    return {
        "name": _short(raw.get("name"), 40), "age": age, "country": _short(raw.get("country"), 30),
        "career": _short(raw.get("career", ""), 40), "cause": _short(raw.get("cause", ""), 60),
        "worth": round(worth), "achievements": ach, "mode": mode,
    }


class Board:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        self._rooms = {r: deque(maxlen=MAX_PER_ROOM) for r in ROOMS}
        self._next_id = 1
        self._posts: dict[str, deque] = {}
        self._global: deque = deque()
        self._reports: dict[str, deque] = {}

    def _expire(self, now: float):
        for q in self._rooms.values():
            while q and q[0]["ts"] < now - TTL:
                q.popleft()

    @staticmethod
    def _public(m: dict) -> dict:
        return {"id": m["id"], "nick": m["nick"], "text": m["text"], "ts": m["ts"], "life": m["life"]}

    def room_list(self):
        now = time.time()
        with self._lock:
            self._expire(now)
            out = []
            for key, (icon, name, blurb) in ROOMS.items():
                q = self._rooms[key]
                active = len({m["nick"] for m in q if m["ts"] > now - 900 and not m["hidden"]})
                out.append({"id": key, "icon": icon, "name": name, "blurb": blurb, "active": active})
            return out

    def messages(self, room: str, after: int = 0):
        now = time.time()
        with self._lock:
            self._expire(now)
            return [self._public(m) for m in self._rooms[room] if m["id"] > after and not m["hidden"]]

    def _limit(self, book: dict, ip: str, window: float, cap: int, now: float, gap: float = 0.0):
        q = book.setdefault(ip, deque())
        while q and q[0] < now - window:
            q.popleft()
        if gap and q and now - q[-1] < gap:
            raise Rejected("slow down a little", 429)
        if len(q) >= cap:
            raise Rejected("you're posting too fast, take a break", 429)
        q.append(now)
        if len(book) > 20000:  # drop idle IPs so the books can't grow forever
            for k in [k for k, v in book.items() if not v or v[-1] < now - window]:
                del book[k]

    def post(self, room: str, ip: str, nick, text, life=None):
        nick, text, life = _clean_nick(nick), _clean_text(text), _clean_life(life)
        now = time.time()
        with self._lock:
            while self._global and self._global[0] < now - 60:
                self._global.popleft()
            if len(self._global) >= GLOBAL_PER_MIN:
                raise Rejected("chat is very busy, try again in a minute", 429)
            self._limit(self._posts, ip, 600, POSTS_PER_10MIN, now, POST_GAP)
            self._global.append(now)
            m = {"id": self._next_id, "nick": nick, "text": text, "ts": int(now), "life": life,
                 "ip": ip, "reporters": set(), "hidden": False}
            self._next_id += 1
            self._rooms[room].append(m)
            return self._public(m)

    def report(self, room: str, msg_id: int, ip: str):
        now = time.time()
        with self._lock:
            m = next((m for m in self._rooms[room] if m["id"] == msg_id), None)
            if not m:
                raise Rejected("message not found", 404)
            if m["ip"] == ip or ip in m["reporters"]:
                return
            self._limit(self._reports, ip, 3600, REPORTS_PER_HOUR, now)
            m["reporters"].add(ip)
            if len(m["reporters"]) >= REPORTS_TO_HIDE:
                m["hidden"] = True


board = Board()
