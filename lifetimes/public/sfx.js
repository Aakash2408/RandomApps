// Lifetimes sound effects: synthesized with the Web Audio API, so there are no audio
// files to load or license. Browsers only allow audio after a user gesture, so the
// context is created lazily on the first sound (which always follows a click).
'use strict';

const SFX = (() => {
  let ctx = null, master = null;
  let muted = localStorage.getItem('lt_muted') === '1';

  function ac() {
    if (muted) return null;
    if (!ctx) {
      const C = window.AudioContext || window.webkitAudioContext;
      if (!C) return null;
      ctx = new C();
      master = ctx.createGain(); master.gain.value = 0.22; master.connect(ctx.destination);
    }
    if (ctx.state === 'suspended') ctx.resume();
    return ctx;
  }

  // One enveloped oscillator note.
  function tone(freq, start, dur, type = 'sine', vol = 1, slideTo = 0) {
    const c = ac(); if (!c) return;
    const t = c.currentTime + start;
    const o = c.createOscillator(), g = c.createGain();
    o.type = type; o.frequency.setValueAtTime(freq, t);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(master);
    o.start(t); o.stop(t + dur + 0.02);
  }

  function noise(start, dur, vol = 0.4, freq = 900) {
    const c = ac(); if (!c) return;
    const t = c.currentTime + start;
    const buf = c.createBuffer(1, Math.ceil(c.sampleRate * dur), c.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / d.length);
    const src = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
    src.buffer = buf; f.type = 'bandpass'; f.frequency.value = freq; g.gain.value = vol;
    src.connect(f); f.connect(g); g.connect(master); src.start(t);
  }

  const play = {
    tap: () => tone(660, 0, 0.06, 'triangle', 0.5),
    age: () => { tone(392, 0, 0.09, 'triangle', 0.6); tone(523, 0.07, 0.12, 'triangle', 0.6); },
    good: () => { tone(659, 0, 0.12, 'sine', 0.7); tone(988, 0.09, 0.22, 'sine', 0.6); },
    bad: () => { tone(220, 0, 0.28, 'sawtooth', 0.35, 140); noise(0, 0.12, 0.25, 300); },
    choice: () => { tone(523, 0, 0.08, 'sine', 0.5); tone(784, 0.06, 0.12, 'sine', 0.5); },
    achievement: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, i * 0.08, 0.28, 'triangle', 0.6)),
    money: () => { tone(1319, 0, 0.07, 'square', 0.25); tone(1760, 0.06, 0.16, 'square', 0.25); },
    love: () => { tone(587, 0, 0.18, 'sine', 0.55); tone(740, 0.12, 0.18, 'sine', 0.55); tone(880, 0.24, 0.3, 'sine', 0.55); },
    death: () => [392, 330, 262, 196].forEach((f, i) => tone(f, i * 0.22, 0.5, 'sine', 0.55)),
    birth: () => [784, 988, 1175].forEach((f, i) => tone(f, i * 0.07, 0.25, 'sine', 0.5)),
    chat: () => tone(880, 0, 0.08, 'sine', 0.35, 1100),
    error: () => tone(180, 0, 0.18, 'square', 0.25),
  };

  return {
    play(name) { try { if (!muted && play[name]) play[name](); } catch (e) { /* audio is optional */ } },
    get muted() { return muted; },
    toggle() { muted = !muted; localStorage.setItem('lt_muted', muted ? '1' : '0'); if (!muted) play.tap(); return muted; },
  };
})();
