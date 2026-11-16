// Time-pure motion helpers. Every function maps (t, ...) -> value with no hidden
// state, so any frame can be painted in any order and renders are reproducible.

export const clamp = (x, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, x));
export const lerp = (a, b, p) => a + (b - a) * p;
export const progress = (t, start, end) => clamp((t - start) / (end - start));

// Spring presets: stiffness k, damping c (mass 1).
export const SNAPPY = { k: 320, c: 30 }; // buttons, toggles, cursor
export const UI = { k: 180, c: 22 }; // containers, cards: a hair of overshoot
export const HEAVY = { k: 90, c: 19 }; // big type, logos: no overshoot

// Damped spring settling from 0 to 1, closed form, t in seconds since start.
export function spring(t, { k, c } = UI) {
  if (t <= 0) return 0;
  const w = Math.sqrt(k);
  const zeta = c / (2 * w);
  if (zeta < 1) {
    const wd = w * Math.sqrt(1 - zeta * zeta);
    const decay = Math.exp(-zeta * w * t);
    return 1 - decay * (Math.cos(wd * t) + ((zeta * w) / wd) * Math.sin(wd * t));
  }
  if (zeta === 1) return 1 - Math.exp(-w * t) * (1 + w * t);
  const r1 = -w * (zeta - Math.sqrt(zeta * zeta - 1));
  const r2 = -w * (zeta + Math.sqrt(zeta * zeta - 1));
  return 1 + (r2 * Math.exp(r1 * t) - r1 * Math.exp(r2 * t)) / (r1 - r2);
}

// A value that changes target several times: keys = [[time, value], ...] sorted
// by time. Each change adds its own spring from its own start, so retargeting
// mid-flight stays smooth and frame t never depends on frame t-1.
export function track(t, keys, cfg = UI) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], cfg);
  }
  return v;
}

// Same as track() for [x, y] or any numeric tuple.
export function trackVec(t, keys, cfg = UI) {
  return keys[0][1].map((_, d) =>
    track(t, keys.map(([time, vec]) => [time, vec[d]]), cfg),
  );
}

// Seeded PRNG (mulberry32). Use instead of Math.random.
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let r = Math.imul(a ^ (a >>> 15), 1 | a);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

// Smooth 1D value noise in [-1, 1], deterministic for a given seed.
export function noise(x, seed = 1) {
  const hash = (n) => rng(seed * 7919 + n)() * 2 - 1;
  const i = Math.floor(x);
  const f = x - i;
  const s = f * f * (3 - 2 * f);
  return lerp(hash(i), hash(i + 1), s);
}

// Beat helpers: read beats.json once, then ask where t sits on the grid.
export function beatIndex(t, beats) {
  let lo = 0;
  let hi = beats.length - 1;
  if (t < beats[0]) return -1;
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1;
    if (beats[mid] <= t) lo = mid;
    else hi = mid - 1;
  }
  return lo;
}

// Seconds since the most recent beat (Infinity before the first one).
export const sinceBeat = (t, beats) => {
  const i = beatIndex(t, beats);
  return i < 0 ? Infinity : t - beats[i];
};
