// Lifetimes on phones: offline install, home-screen prompt, haptics, swipe-to-close.
// Loaded after game.js; everything here is progressive (a browser without a feature
// simply plays the game without it).
'use strict';

// ---------- offline + install ----------
if ('serviceWorker' in navigator && (location.protocol === 'https:' || ['localhost', '127.0.0.1'].includes(location.hostname))) {
  window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => { /* offline mode is optional */ }));
}

const Install = (() => {
  let deferred = null;
  const standalone = () => window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  window.addEventListener('beforeinstallprompt', (e) => { e.preventDefault(); deferred = e; refresh(); });
  window.addEventListener('appinstalled', () => { deferred = null; refresh(); toast('Lifetimes is on your home screen. Enjoy!'); });

  function canOffer() { return !standalone() && (deferred || ios) && localStorage.getItem('lt_install_dismissed') !== '1'; }
  function refresh() {
    // The start sheet renders a placeholder; fill it whenever install becomes possible.
    const slot = document.getElementById('install-slot');
    if (slot) slot.innerHTML = canOffer() ? '<div class="install"><span aria-hidden="true">📲</span><div><b>Play it like an app</b><div class="note">Full screen, works offline, one tap from your home screen.</div></div><button type="button" class="opt primary" data-act="install">Install</button><button type="button" class="close" data-act="install-x" aria-label="Not now">✕</button></div>' : '';
  }
  async function prompt() {
    if (deferred) { deferred.prompt(); const { outcome } = await deferred.userChoice; deferred = null; if (outcome !== 'accepted') dismiss(); refresh(); return; }
    if (ios) sheet('install', 'Add to Home Screen', '<div class="hero"><div class="big" aria-hidden="true">📲</div></div><ol class="steps"><li>Tap the <b>Share</b> button <span aria-hidden="true">(□↑)</span> in Safari.</li><li>Scroll and tap <b>Add to Home Screen</b>.</li><li>Tap <b>Add</b>. Lifetimes now opens full screen, even offline.</li></ol>');
  }
  function dismiss() { localStorage.setItem('lt_install_dismissed', '1'); refresh(); }
  return { refresh, prompt, dismiss, standalone };
})();

// ---------- haptics ----------
// Vibration follows the sound toggle, so one "quiet" switch silences both.
const HAPTIC = { tap: 8, age: 12, good: [10, 40, 10], bad: [40, 30, 60], choice: 15, achievement: [15, 40, 15, 40, 30], money: [8, 30, 8], love: [10, 60, 10, 60, 10], death: [80, 60, 120], birth: [10, 40, 20], chat: 10, error: [30, 30, 30] };
if (navigator.vibrate) {
  const play = SFX.play.bind(SFX);
  SFX.play = (name) => { play(name); if (!SFX.muted && HAPTIC[name] && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) { try { navigator.vibrate(HAPTIC[name]); } catch (e) { /* ignore */ } } };
}

// ---------- swipe down to close a sheet ----------
(() => {
  const s = document.getElementById('sheet');
  let y0 = null, dy = 0, dragging = false;
  const closable = () => !document.getElementById('sheet-close').hidden;
  s.addEventListener('touchstart', (e) => {
    // Only start a drag from the grip/header, or anywhere when the sheet is scrolled to the top.
    const fromHandle = e.target.closest('.grip, .sheet-head');
    if (!closable() || (!fromHandle && s.scrollTop > 0) || e.target.closest('input, select, textarea, .chat-list, .rooms')) return;
    y0 = e.touches[0].clientY; dy = 0; dragging = false;
  }, { passive: true });
  s.addEventListener('touchmove', (e) => {
    if (y0 === null) return;
    dy = Math.max(0, e.touches[0].clientY - y0);
    if (dy > 8) dragging = true;
    if (dragging) { s.style.transition = 'none'; s.style.transform = `translate(-50%, ${dy}px)`; }
  }, { passive: true });
  s.addEventListener('touchend', () => {
    if (y0 === null) return;
    s.style.transition = ''; s.style.transform = '';
    if (dragging && dy > 110) closeSheet();
    y0 = null; dragging = false;
  });
})();

// ---------- deep links from home-screen shortcuts ----------
(() => {
  const q = new URLSearchParams(location.search);
  if (q.get('open') === 'rooms') setTimeout(() => openRooms(), 300);
  // window.history explicitly: game.js has its own global `history` (rewind snapshots).
  if (q.has('open') || q.has('source')) { q.delete('open'); q.delete('source'); window.history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : '')); }
})();

// The start screen is drawn before this file loads; fill its install slot now.
Install.refresh();
