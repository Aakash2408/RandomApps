import pytest
from fastapi.testclient import TestClient

from server import chat, main


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    chat.board.reset()
    monkeypatch.setattr(chat, "POST_GAP", 0.0)
    monkeypatch.setenv("CLIENT_IP_HEADER", "X-Test-IP")


@pytest.fixture
def client():
    return TestClient(main.app)


def post(client, text="hello", nick="Ava", room="general", ip="1.1.1.1", **kw):
    return client.post(f"/api/rooms/{room}/messages", json={"nick": nick, "text": text, **kw}, headers={"X-Test-IP": ip})


def test_rooms_are_listed(client):
    j = client.get("/api/rooms").json()["rooms"]
    assert [r["id"] for r in j] == list(chat.ROOMS)
    assert all(r["active"] == 0 for r in j)


def test_post_and_read_back(client):
    r = post(client, "first!")
    assert r.status_code == 200
    m = r.json()["message"]
    assert m["nick"] == "Ava" and m["text"] == "first!" and "ip" not in m
    post(client, "second", nick="Leo", ip="2.2.2.2")
    msgs = client.get("/api/rooms/general/messages").json()["messages"]
    assert [x["text"] for x in msgs] == ["first!", "second"]
    after = client.get(f"/api/rooms/general/messages?after={m['id']}").json()["messages"]
    assert [x["text"] for x in after] == ["second"]
    assert client.get("/api/rooms/stories/messages").json()["messages"] == []
    assert client.get("/api/rooms")


def test_unknown_room_404(client):
    assert client.get("/api/rooms/secret/messages").status_code == 404
    assert post(client, room="secret").status_code == 404


@pytest.mark.parametrize("text", [
    "join https://evil.example", "go to www.site.org", "my insta is cool.gg", "mail me a@b.co",
    "call 98765 43210", "text +1 (555) 123-4567", "discord.gg/abc", "", "   ", "x" * 241,
])
def test_links_contacts_and_bad_lengths_are_refused(client, text):
    assert post(client, text).status_code == 400


def test_money_is_not_mistaken_for_a_phone_number(client):
    assert post(client, "just hit $2500000 net worth").status_code == 200
    assert post(client, "and $1,250,000,000 later", ip="9.9.9.9").status_code == 200


def test_slurs_refused_and_swears_masked(client):
    assert post(client, "you are a retard").status_code == 400
    m = post(client, "holy shit I won the lottery").json()["message"]
    assert m["text"] == "holy s*** I won the lottery"


def test_control_and_bidi_chars_stripped(client):
    m = post(client, "hi\u202ethere\x00").json()["message"]
    assert m["text"] == "hithere"


@pytest.mark.parametrize("nick", ["A", "x" * 17, "<b>", "Admin", "mod_team", "Moderator1", "shithead", "call5551234567", None, 5])
def test_bad_nicks(client, nick):
    assert post(client, nick=nick).status_code == 400


def test_html_is_stored_as_plain_text(client):
    m = post(client, "<img src=x onerror=alert(1)>").json()["message"]
    assert m["text"] == "<img src=x onerror=alert(1)>"  # the client renders it as text, never HTML


def test_life_card_validated(client):
    life = {"name": "Mia Silva", "age": 88, "country": "Brazil", "career": "Surgeon", "cause": "old age", "worth": 4200000, "achievements": 5, "mode": "hardcore"}
    m = post(client, "my best life", room="stories", life=life).json()["message"]
    assert m["life"]["worth"] == 4200000 and m["life"]["mode"] == "hardcore"
    for bad in ({**life, "age": 500}, {**life, "age": True}, {**life, "worth": "lots"}, {**life, "name": 7},
                {**life, "career": "see www.x.com"}, {**life, "mode": "god"}, "nope"):
        assert post(client, "x", room="stories", ip="3.3.3.3", life=bad).status_code == 400


def test_per_ip_flood_limit(client):
    codes = [post(client, f"m{i}").status_code for i in range(chat.POSTS_PER_10MIN + 1)]
    assert codes[:-1] == [200] * chat.POSTS_PER_10MIN and codes[-1] == 429
    assert post(client, "other ip", ip="4.4.4.4").status_code == 200


def test_post_gap(client, monkeypatch):
    monkeypatch.setattr(chat, "POST_GAP", 60.0)
    assert post(client, "one").status_code == 200
    assert post(client, "two").status_code == 429


def test_global_cap(client, monkeypatch):
    monkeypatch.setattr(chat, "GLOBAL_PER_MIN", 3)
    codes = [post(client, "hi", ip=f"5.5.5.{i}").status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]


def test_room_keeps_only_newest(client, monkeypatch):
    for i in range(chat.MAX_PER_ROOM + 5):
        post(client, f"m{i}", ip=f"6.6.{i // 200}.{i % 200}")
    msgs = client.get("/api/rooms/general/messages").json()["messages"]
    assert len(msgs) == chat.MAX_PER_ROOM and msgs[-1]["text"] == f"m{chat.MAX_PER_ROOM + 4}"


def test_messages_expire(client, monkeypatch):
    post(client, "old")
    t = chat.time.time()
    monkeypatch.setattr(chat.time, "time", lambda: t + chat.TTL + 1)
    assert client.get("/api/rooms/general/messages").json()["messages"] == []


def test_three_distinct_reports_hide_a_message(client):
    mid = post(client, "spam spam").json()["message"]["id"]
    url = f"/api/rooms/general/messages/{mid}/report"
    client.post(url, headers={"X-Test-IP": "1.1.1.1"})  # author can't report themselves
    for _ in range(3):
        client.post(url, headers={"X-Test-IP": "7.7.7.7"})  # same reporter counts once
    client.post(url, headers={"X-Test-IP": "8.8.8.8"})
    assert len(client.get("/api/rooms/general/messages").json()["messages"]) == 1
    client.post(url, headers={"X-Test-IP": "9.9.9.9"})
    assert client.get("/api/rooms/general/messages").json()["messages"] == []
    assert client.post("/api/rooms/general/messages/9999/report").status_code == 404


def test_api_is_not_cached(client):
    assert client.get("/api/rooms").headers["cache-control"] == "no-store"
