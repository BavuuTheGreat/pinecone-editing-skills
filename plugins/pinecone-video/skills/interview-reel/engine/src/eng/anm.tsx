import React from "react";
import { Easing, interpolate } from "remotion";
import { ACCENT, clamp, SANS } from "./tokens";

// Remotion ports of motion from the "Annnimate starter pack" (https://annnimate.com, free to use in any project, no attribution).
// The originals are GSAP + scroll components for web pages; a render needs a pure function of the frame, so these re-implement the
// same motion (durations, staggers, easing curves and layering read from the pack's source) as time -> pixels:
//   DualScramble  <- dual-scramble      text dissolves into brand-coloured noise and resolves back into the text
//   SplitFlap     <- split-flap-board   a mechanical flap that riffles through its drum and lands with a small rebound
//   CurtainOut    <- curtain-slider     twelve columns wipe away one after another, the next image settles in beneath
//   TextReveal    <- text-reveal        words rise out of a mask, staggered, expo.out
//   ChapterRail   <- process-rail       a bead travels along a line and each step lights as it arrives
// All `t` values are seconds since the animation started (negative = not started).
export const ANM = Easing.bezier(0.3, 0.9, 0.1, 1); // the pack's 'annnimate' ease
export const ANM_IO = Easing.bezier(0.7, 0, 0.16, 1); // 'annnimateInOut'
const EXPO_OUT = Easing.bezier(0.16, 1, 0.3, 1);
const rnd = (n: number) => { const s = Math.sin(n * 127.1 + 311.7) * 43758.5453; return s - Math.floor(s); };
const NOISE = "!<>-_\\/[]{}=+*^?#abcdefghijklmnopqrstuvwxyz0123456789";

// ---- dual-scramble: original (colour2) -> noise (colour1) -> final text (colour2), sweeping left to right, no layout shift ----
export const DualScramble: React.FC<{ text: string; t: number; duration?: number; color1?: string; color2: string; style?: React.CSSProperties }> = ({
  text, t, duration = 0.6, color1 = ACCENT, color2, style,
}) => {
  const chars = text.split("");
  const cnt = Math.max(1, text.replace(/\s/g, "").length);
  let k = 0;
  return (
    <span style={{ position: "relative", display: "inline-block", whiteSpace: "pre", ...style }}>
      <span style={{ visibility: "hidden" }}>{text}</span>
      <span style={{ position: "absolute", left: 0, top: 0, whiteSpace: "pre" }}>
        {chars.map((ch, i) => {
          if (/\s/.test(ch)) return <span key={i}>{ch}</span>;
          const f = k++ / cnt;
          const s0 = f * 0.6 * duration, e0 = s0 + 0.4 * duration; // this character's noise window
          if (t < 0 || t >= e0) return <span key={i} style={{ color: color2 }}>{ch}</span>;
          if (t < s0) return <span key={i} style={{ color: color2 }}>{ch}</span>;
          const tick = Math.floor(t * 18);
          return <span key={i} style={{ color: color1 }}>{NOISE[Math.floor(rnd(i * 7.3 + tick * 13.1) * NOISE.length)]}</span>;
        })}
      </span>
    </span>
  );
};

// ---- text-reveal: words rise out of a mask, 0.06 s stagger, 0.6 s, expo.out ----
export const TextReveal: React.FC<{ text: string; t: number; stagger?: number; duration?: number; style?: React.CSSProperties }> = ({ text, t, stagger = 0.06, duration = 0.6, style }) => (
  <span style={{ display: "inline-flex", flexWrap: "wrap", gap: "0 0.28em", ...style }}>
    {text.split(" ").map((w, i) => {
      const p = interpolate(t - i * stagger, [0, duration], [0, 1], { ...clamp, easing: EXPO_OUT });
      return (
        <span key={i} style={{ display: "inline-block", overflow: "hidden", verticalAlign: "bottom" }}>
          <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * 110}%)` }}>{w}</span>
        </span>
      );
    })}
  </span>
);

// ---- split-flap: one tile. A flap falls (power2.in), the next flap lands (power1.in), a small rebound, rest. ----
const FALL = 0.4, LAND = 0.18, UP = 0.16, DOWN = 0.2, BOUNCE_DEG = 32;
export const SplitFlapTile: React.FC<{ from: string; to: string; t: number; drum?: string; duration?: number; cycles?: number; w?: number; h?: number; color?: string; bg?: string }> = ({
  from, to, t, drum = "0123456789", duration = 0.36, cycles = 2, w = 28, h = 40, color = "#fff", bg = "#1c1c1c",
}) => {
  // the characters it riffles through: forward along the drum from `from` to `to`
  const a = Math.max(0, drum.indexOf(from)), b = Math.max(0, drum.indexOf(to));
  const steps = ((b - a + drum.length) % drum.length) || drum.length;
  const seq: string[] = [];
  const n = Math.min(steps, cycles + 4);
  for (let i = 1; i <= n; i++) seq.push(drum[(a + Math.round((i * steps) / n)) % drum.length]);
  const fast = duration / (1 + cycles * 0.35);
  const periods = seq.map((_, i) => (seq.length <= 1 ? duration : fast + (duration - fast) * (i / (seq.length - 1))));
  let at = 0, idx = -1, u = 0;
  for (let i = 0; i < seq.length; i++) {
    if (t >= at && t < at + periods[i]) { idx = i; u = (t - at) / periods[i]; break; }
    at += periods[i];
  }
  const done = t >= at;
  const cur = t < 0 ? from : done ? to : idx > 0 ? seq[idx - 1] : from;
  const next = done || t < 0 ? cur : seq[idx];
  let topRot = 0, botRot = 90, shade = 0;
  if (idx >= 0 && !done && t >= 0) {
    if (u < FALL) { const x = u / FALL; topRot = -90 * x * x; shade = 0.55 * x * x; }
    else {
      topRot = -90;
      const l = (u - FALL) / LAND;
      if (u < FALL + LAND) botRot = 90 * (1 - l);
      else if (u < FALL + LAND + UP) { botRot = BOUNCE_DEG * Math.sin(((u - FALL - LAND) / UP) * (Math.PI / 2)); }
      else if (u < FALL + LAND + UP + DOWN) { const d = (u - FALL - LAND - UP) / DOWN; botRot = BOUNCE_DEG * (1 - d * d * 0); botRot = BOUNCE_DEG * (1 - d); }
      else botRot = 0;
    }
  }
  const settled = done || t < 0 || (idx >= 0 && u >= FALL);
  const showNewTop = idx >= 0 && !done && t >= 0;
  const half: React.CSSProperties = { position: "absolute", left: 0, width: w, height: h / 2, overflow: "hidden", background: bg, backfaceVisibility: "hidden" };
  const glyph = (c: string, top: number): React.CSSProperties & { children?: never } => ({ position: "absolute", left: 0, top, width: w, height: h, lineHeight: `${h}px`, textAlign: "center", fontFamily: SANS, fontWeight: 700, fontSize: h * 0.68, color });
  return (
    <div style={{ position: "relative", width: w, height: h, perspective: 320, margin: "0 2px" }}>
      {/* behind: the top half already carries the incoming glyph, the bottom half the outgoing one until the flap lands */}
      <div style={{ ...half, top: 0, borderRadius: "5px 5px 0 0" }}><div style={glyph(next, 0)}>{showNewTop ? next : cur}</div></div>
      <div style={{ ...half, top: h / 2, borderRadius: "0 0 5px 5px" }}><div style={glyph(cur, -h / 2)}>{settled && showNewTop ? next : cur}</div></div>
      {/* the falling top flap (outgoing glyph) */}
      {showNewTop && topRot > -90 ? (
        <div style={{ ...half, top: 0, borderRadius: "5px 5px 0 0", transformOrigin: "50% 100%", transform: `rotateX(${topRot}deg)`, filter: `brightness(${1 - shade})` }}><div style={glyph(cur, 0)}>{cur}</div></div>
      ) : null}
      {/* the landing bottom flap (incoming glyph) */}
      {showNewTop && botRot < 90 ? (
        <div style={{ ...half, top: h / 2, borderRadius: "0 0 5px 5px", transformOrigin: "50% 0%", transform: `rotateX(${botRot}deg)` }}><div style={glyph(next, -h / 2)}>{next}</div></div>
      ) : null}
    </div>
  );
};

// ---- curtain-slider: the outgoing picture is 12 columns; each column's clip edge wipes sideways, staggered; the one beneath settles in ----
export const curtainPath = (p: number, w: number, h: number, cols = 12): string => {
  const stripDur = 0.62, stagger = (1 - stripDur) / Math.max(1, cols - 1);
  const cw = w / cols;
  const parts: string[] = [];
  for (let c = 0; c < cols; c++) {
    const local = Math.min(1, Math.max(0, (p - c * stagger) / stripDur));
    const e = ANM_IO(local);
    const vis = cw * (1 - e);
    if (vis > 0.5) parts.push(`M${(c * cw + (cw - vis)).toFixed(1)} 0H${((c + 1) * cw).toFixed(1)}V${h}H${(c * cw + (cw - vis)).toFixed(1)}Z`); // the left edge advances: left-to-right curtain
  }
  return parts.length ? `path('${parts.join("")}')` : "path('M0 0H0V0Z')";
};
export const CurtainOut: React.FC<{ p: number; w: number; h: number; children: React.ReactNode }> = ({ p, w, h, children }) => {
  if (p >= 1) return null;
  if (p <= 0) return <div style={{ position: "absolute", inset: 0 }}>{children}</div>;
  return (
    <div style={{ position: "absolute", inset: 0, clipPath: curtainPath(p, w, h) }}>
      {children}
      <div style={{ position: "absolute", inset: 0, background: "#000", opacity: 0.3 * Math.min(1, p * 1.6) }} />
    </div>
  );
};
// the layer revealed beneath: zoom-settles from 1.12 and clears from a light shade
export const curtainIncoming = (p: number): { scale: number; shade: number } => ({ scale: 1 + 0.12 * (1 - ANM(Math.min(1, p))), shade: 0.18 * (1 - ANM(Math.min(1, p))) });

// ---- process-rail: a bead draws the line and each step lights up as it arrives ----
export const ChapterRail: React.FC<{ n: number; index: number; t: number; step?: number; color: string; dim: string }> = ({ n, index, t, step = 64, color, dim }) => {
  const prev = Math.max(0, index - 1);
  const pos = prev + (index - prev) * ANM_IO(Math.min(1, Math.max(0, t / 0.7)));
  return (
    <div style={{ position: "relative", width: step * (n - 1) + 14, height: 14 }}>
      <div style={{ position: "absolute", left: 7, right: 7, top: 6, height: 2, background: dim }} />
      <div style={{ position: "absolute", left: 7, top: 6, height: 2, width: pos * step, background: color }} />
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} style={{ position: "absolute", left: i * step, top: 0, width: 14, height: 14, borderRadius: 7, background: i <= pos + 0.01 ? color : "#0C0D0B", border: `2px solid ${i <= pos + 0.01 ? color : dim}` }} />
      ))}
    </div>
  );
};
