import React from "react";
import { interpolate } from "remotion";
import { clamp, SANS, SETTLE, SMOOTH } from "./tokens";
import { DualScramble, SplitFlapTile } from "./anm";

// Black-and-white isometric "map model": a small procedural city (blocks, avenues, buildings with heights and windows, parks with trees,
// moving cars), seen from above at 30 degrees. A (start) -> the route draws along the streets -> "you have arrived" at the north-west
// corner of the Pinecone block (the map's pin lands on the wrong side) -> the last 50 m dashed round the block to the door on the east
// side -> B = Pinecone Academy. The camera starts wide on the whole route and pushes in on the building. Greys and white only; not a real
// city (nothing to misread). Size 1008 x 537 (the demo region scaled by 1.0714).
// t = seconds since the layer began; cues (same clock): arrive, last50, solved.
export type MapCues = { arrive: number; last50: number; solved: number; start?: number; legDur?: number }; // start: when the route starts (default 1.0 s); legDur: how long the dashed leg takes to draw (default 2.0 s). Short layers (a 3 s hook) pass small values.
const W = 1008, H = 537;
const WHITE = "#FFFFFF";

// ---------- the world ----------
const BS = 90; // block size
const NB = 11; // blocks per side
const SWID = (k: number) => (k % 4 === 2 ? 58 : 38); // street k runs just before block k; every 4th street is an avenue
const xs: number[] = [], sc: number[] = [];
{
  let pos = 0;
  for (let k = 0; k <= NB; k++) {
    const sw = SWID(k);
    sc[k] = pos + sw / 2; // street centre line
    pos += sw;
    if (k < NB) { xs[k] = pos; pos += BS; }
  }
}
const WORLD = sc[NB] + SWID(NB) / 2;
const PB = { i: 8, j: 3 }; // the Pinecone block
const mulberry = (a: number) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

type Bld = { u0: number; v0: number; u1: number; v1: number; h: number; kind: "b" | "pine" | "tree" | "park" };
const BUILDINGS: Bld[] = [];
{
  for (let i = 0; i < NB; i++) for (let j = 0; j < NB; j++) {
    const u0 = xs[i], v0 = xs[j];
    if (i === PB.i && j === PB.j) {
      BUILDINGS.push({ u0: u0 + 6, v0: v0 + 6, u1: u0 + BS - 6, v1: v0 + BS - 6, h: 58, kind: "pine" });
      continue;
    }
    const r = mulberry(i * 131 + j * 17 + 7);
    const t = r();
    if (t < 0.11) { // park: lawn + trees
      BUILDINGS.push({ u0: u0 + 4, v0: v0 + 4, u1: u0 + BS - 4, v1: v0 + BS - 4, h: 0, kind: "park" });
      for (let k = 0; k < 9; k++) BUILDINGS.push({ u0: u0 + 14 + r() * (BS - 28), v0: v0 + 14 + r() * (BS - 28), u1: 0, v1: 0, h: 9 + r() * 6, kind: "tree" });
      continue;
    }
    const split = t < 0.3 ? 1 : t < 0.6 ? 2 : 4;
    const inset = 5, gap = 4, inner = BS - 2 * inset;
    const cells = split === 1 ? [[0, 0, 1, 1]] : split === 2 ? (r() < 0.5 ? [[0, 0, 1, 0.5], [0, 0.5, 1, 1]] : [[0, 0, 0.5, 1], [0.5, 0, 1, 1]]) : [[0, 0, 0.5, 0.5], [0.5, 0, 1, 0.5], [0, 0.5, 0.5, 1], [0.5, 0.5, 1, 1]];
    for (const [a, b, c, d] of cells) {
      const near = Math.abs(i - PB.i) <= 1 && Math.abs(j - PB.j) <= 1; // keep the blocks around the Pinecone building low so it is never hidden
      const tall = r() < 0.12 && !near;
      const h = near ? 6 + r() * 8 : tall ? 46 + r() * 34 : 9 + r() * 24;
      BUILDINGS.push({ u0: u0 + inset + a * inner + (a > 0 ? gap / 2 : 0), v0: v0 + inset + b * inner + (b > 0 ? gap / 2 : 0), u1: u0 + inset + c * inner - (c < 1 ? gap / 2 : 0), v1: v0 + inset + d * inner - (d < 1 ? gap / 2 : 0), h, kind: "b" });
    }
  }
}
BUILDINGS.sort((p, q) => (p.u0 + p.u1 + p.v0 + p.v1) - (q.u0 + q.u1 + q.v0 + q.v1)); // back to front

// route in world coordinates (street centre lines), A -> arrival at the NW corner of the Pinecone block
const A = { u: sc[1], v: sc[9] };
const ROUTE: [number, number][] = [[sc[1], sc[9]], [sc[1], sc[6]], [sc[5], sc[6]], [sc[5], sc[4]], [sc[PB.i], sc[4]], [sc[PB.i], sc[PB.j]]];
const ARRIVE = { u: sc[PB.i], v: sc[PB.j] };
const DOOR = { u: sc[PB.i + 1], v: xs[PB.j] + BS / 2 }; // east side, mid
const LAST: [number, number][] = [[sc[PB.i], sc[PB.j]], [sc[PB.i + 1], sc[PB.j]], [DOOR.u, DOOR.v]]; // along the top, down the east side to the door
const PINE_C = { u: xs[PB.i] + BS / 2, v: xs[PB.j] + BS / 2 };

// isometric projection with a camera: centre (cu, cv) at the middle of the frame, scale s
type Cam = { cu: number; cv: number; s: number };
const proj = (u: number, v: number, z: number, c: Cam): [number, number] => [W / 2 + ((u - c.cu) - (v - c.cv)) * 0.866 * c.s, H / 2 + 30 + ((u - c.cu) + (v - c.cv)) * 0.5 * c.s - z * c.s * 0.8];
const pts = (a: [number, number][]) => a.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ");
const shade = (g: number, f: number) => { const v = Math.max(0, Math.min(255, Math.round(g * f))); return `rgb(${v},${v},${v})`; };

const polyLen = (p: [number, number][]) => p.reduce((s, q, i) => (i ? s + Math.hypot(q[0] - p[i - 1][0], q[1] - p[i - 1][1]) : 0), 0);
// dash string revealed up to len px (14 on, 12 off)
const dashTo = (len: number) => {
  const parts: number[] = [];
  let left = len, on = true;
  while (left > 0.1) { const seg = on ? 14 : 12; parts.push(Math.min(seg, left)); left -= seg; on = !on; }
  if (parts.length % 2 === 1) parts.push(0);
  parts.push(4000);
  return parts.join(" ");
};
const partial = (p: [number, number][], f: number): [number, number][] => {
  // the first fraction f of a polyline
  const L = polyLen(p); let left = L * f; const out: [number, number][] = [p[0]];
  for (let i = 1; i < p.length; i++) {
    const d = Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1]);
    if (left >= d) { out.push(p[i]); left -= d; } else { const k = left / d; out.push([p[i - 1][0] + (p[i][0] - p[i - 1][0]) * k, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k]); break; }
  }
  return out;
};
const wproj = (route: [number, number][], c: Cam, z = 1): [number, number][] => route.map(([u, v]) => proj(u, v, z, c));

// cars: small boxes driving along the avenues (positions are a function of t)
const CARS: { axis: "u" | "v"; line: number; phase: number; dir: number }[] = [];
{ const r = mulberry(99); for (const k of [2, 6, 10]) for (let n = 0; n < 4; n++) { CARS.push({ axis: "u", line: sc[k] + (r() < 0.5 ? -8 : 8), phase: r() * WORLD, dir: r() < 0.5 ? 1 : -1 }); CARS.push({ axis: "v", line: sc[k] + (r() < 0.5 ? -8 : 8), phase: r() * WORLD, dir: r() < 0.5 ? 1 : -1 }); } }

export const MapCard: React.FC<{ t: number; cues: MapCues }> = ({ t, cues }) => {
  const t0 = cues.start ?? 1.0, ld = cues.legDur ?? 2.0;
  const fade = interpolate(t, [0.1 * t0, 0.8 * t0], [0, 1], { ...clamp, easing: SMOOTH });
  const aIn = interpolate(t, [0.5 * t0, 0.9 * t0], [0, 1], { ...clamp, easing: SETTLE });
  const route = interpolate(t, [t0, Math.max(t0 + 0.6, cues.arrive)], [0, 1], { ...clamp, easing: SMOOTH });
  const arrived = interpolate(t, [cues.arrive, cues.arrive + 0.4 * (ld / 2)], [0, 1], { ...clamp, easing: SETTLE });
  const last = interpolate(t, [cues.last50, cues.last50 + ld], [0, 1], { ...clamp, easing: SMOOTH });
  const tag = interpolate(t, [cues.last50 + 0.15 * ld, cues.last50 + 0.4 * ld], [0, 1], { ...clamp, easing: SETTLE });
  const bIn = interpolate(t, [cues.last50 + 0.85 * ld, cues.last50 + 1.1 * ld], [0, 1], { ...clamp, easing: SETTLE });
  const glow = interpolate(t, [cues.solved, cues.solved + 0.6 * ld], [0, 1], clamp);
  const ring = glow > 0 && glow < 1 ? glow : 0;
  // camera: wide on the whole route, then it glides in on the Pinecone block
  const k = interpolate(t, [t0 + 0.5 * t0, cues.last50 + 0.75 * ld], [0, 1], { ...clamp, easing: SMOOTH });
  const c0 = { u: (A.u + ARRIVE.u) / 2, v: (A.v + ARRIVE.v) / 2 };
  const cam: Cam = { cu: c0.u + (PINE_C.u + 40 - c0.u) * k, cv: c0.v + (PINE_C.v + 20 - c0.v) * k, s: 0.54 + 0.34 * k };
  const P = (u: number, v: number, z = 0) => proj(u, v, z, cam);
  const onScreen = (u: number, v: number) => { const [x, y] = P(u, v); return x > -140 && x < W + 140 && y > -160 && y < H + 200; };

  const streets: React.ReactNode[] = [];
  // ground plane
  streets.push(<polygon key="g" points={pts([P(0, 0), P(WORLD, 0), P(WORLD, WORLD), P(0, WORLD)])} fill="#0c0c0c" />);
  for (let k2 = 0; k2 <= NB; k2++) {
    const w = SWID(k2), a = sc[k2];
    const av = w > 30;
    streets.push(<polygon key={`su${k2}`} points={pts([P(a - w / 2, 0), P(a + w / 2, 0), P(a + w / 2, WORLD), P(a - w / 2, WORLD)])} fill={av ? "#242424" : "#1a1a1a"} />);
    streets.push(<polygon key={`sv${k2}`} points={pts([P(0, a - w / 2), P(WORLD, a - w / 2), P(WORLD, a + w / 2), P(0, a + w / 2)])} fill={av ? "#242424" : "#1a1a1a"} />);
    if (av) { // lane dashes
      streets.push(<polyline key={`du${k2}`} points={pts([P(a, 0), P(a, WORLD)])} stroke="#555" strokeWidth={1.4} strokeDasharray="10 12" fill="none" />);
      streets.push(<polyline key={`dv${k2}`} points={pts([P(0, a), P(WORLD, a)])} stroke="#555" strokeWidth={1.4} strokeDasharray="10 12" fill="none" />);
    }
  }
  // block bases (pavement) + crosswalk stripes at the busy intersections around the route
  const bases: React.ReactNode[] = [];
  for (let i = 0; i < NB; i++) for (let j = 0; j < NB; j++) {
    if (!onScreen(xs[i] + BS / 2, xs[j] + BS / 2)) continue;
    const u0 = xs[i], v0 = xs[j];
    const park = BUILDINGS.some((b) => b.kind === "park" && b.u0 === u0 + 4 && b.v0 === v0 + 4);
    bases.push(<polygon key={`b${i}-${j}`} points={pts([P(u0, v0), P(u0 + BS, v0), P(u0 + BS, v0 + BS), P(u0, v0 + BS)])} fill={park ? "#303030" : "#2b2b2b"} stroke="#3c3c3c" strokeWidth={0.8} />);
  }
  // buildings, back to front
  const items: React.ReactNode[] = [];
  BUILDINGS.forEach((b, idx) => {
    const cu = (b.u0 + b.u1) / 2, cv = (b.v0 + b.v1) / 2;
    if (!onScreen(cu, cv)) return;
    if (b.kind === "park") { items.push(<polygon key={idx} points={pts([P(b.u0, b.v0), P(b.u1, b.v0), P(b.u1, b.v1), P(b.u0, b.v1)])} fill="#3d3d3d" />); return; }
    if (b.kind === "tree") { const [x, y] = P(b.u0, b.v0, 0); items.push(<g key={idx}><ellipse cx={x} cy={y + 2} rx={b.h * cam.s * 0.55} ry={b.h * cam.s * 0.25} fill="#000" opacity={0.35} /><circle cx={x} cy={y - b.h * cam.s * 0.7} r={b.h * cam.s * 0.5} fill="#cfcfcf" opacity={0.55} /></g>); return; }
    const pine = b.kind === "pine";
    const g = pine ? 255 : 110 + 110 * Math.min(1, b.h / 80);
    const top = shade(g, 1), east = shade(g, pine ? 0.86 : 0.66), south = shade(g, pine ? 0.66 : 0.42);
    const T = [P(b.u0, b.v0, b.h), P(b.u1, b.v0, b.h), P(b.u1, b.v1, b.h), P(b.u0, b.v1, b.h)];
    const E = [P(b.u1, b.v0, 0), P(b.u1, b.v1, 0), P(b.u1, b.v1, b.h), P(b.u1, b.v0, b.h)];
    const S = [P(b.u0, b.v1, 0), P(b.u1, b.v1, 0), P(b.u1, b.v1, b.h), P(b.u0, b.v1, b.h)];
    const lines: React.ReactNode[] = [];
    if (b.h >= 40 || pine) { // floors as faint horizontal bands on the two visible faces
      for (let z = 8; z < b.h - 2; z += 8) {
        const [e0, e1] = [P(b.u1, b.v0, z), P(b.u1, b.v1, z)], [s0, s1] = [P(b.u0, b.v1, z), P(b.u1, b.v1, z)];
        lines.push(<line key={`e${z}`} x1={e0[0]} y1={e0[1]} x2={e1[0]} y2={e1[1]} stroke="#000" strokeOpacity={0.22} strokeWidth={0.8} />);
        lines.push(<line key={`s${z}`} x1={s0[0]} y1={s0[1]} x2={s1[0]} y2={s1[1]} stroke="#000" strokeOpacity={0.28} strokeWidth={0.8} />);
      }
    }
    items.push(
      <g key={idx}>
        <polygon points={pts(E)} fill={east} stroke="#0c0c0c" strokeWidth={0.6} />
        <polygon points={pts(S)} fill={south} stroke="#0c0c0c" strokeWidth={0.6} />
        {lines}
        {pine ? <polygon points={pts([P(b.u1, DOOR.v - 6, 0), P(b.u1, DOOR.v + 6, 0), P(b.u1, DOOR.v + 6, 11), P(b.u1, DOOR.v - 6, 11)])} fill="#2a2a2a" stroke="#000" strokeWidth={0.8} /> : null}
        <polygon points={pts(T)} fill={top} stroke="#0c0c0c" strokeWidth={0.6} />
        {pine ? <polygon points={pts([P(b.u0 + 14, b.v0 + 14, b.h), P(b.u1 - 14, b.v0 + 14, b.h), P(b.u1 - 14, b.v1 - 14, b.h), P(b.u0 + 14, b.v1 - 14, b.h)])} fill="#e4e4e4" stroke="#bdbdbd" strokeWidth={0.8} /> : null}
      </g>
    );
  });
  // cars
  const cars = CARS.map((c, i) => {
    const pos = ((c.phase + t * 42 * c.dir) % WORLD + WORLD) % WORLD;
    const u = c.axis === "u" ? c.line : pos, v = c.axis === "u" ? pos : c.line;
    if (!onScreen(u, v)) return null;
    const du = c.axis === "v" ? 7 : 3.5, dv = c.axis === "u" ? 7 : 3.5;
    const x0 = u - du / 2, x1 = u + du / 2, y0 = v - dv / 2, y1 = v + dv / 2, h = 3.2;
    return (
      <g key={`c${i}`}>
        <polygon points={pts([P(x1, y0, 0), P(x1, y1, 0), P(x1, y1, h), P(x1, y0, h)])} fill="#8a8a8a" />
        <polygon points={pts([P(x0, y1, 0), P(x1, y1, 0), P(x1, y1, h), P(x0, y1, h)])} fill="#5a5a5a" />
        <polygon points={pts([P(x0, y0, h), P(x1, y0, h), P(x1, y1, h), P(x0, y1, h)])} fill="#f2f2f2" />
      </g>
    );
  });
  // route
  const rp = partial(wproj(ROUTE, cam, 0.6), route);
  const lastFull = wproj(LAST, cam, 0.6);
  const lastLen = polyLen(lastFull);
  const seg1Len = polyLen(lastFull.slice(0, 2));
  const aP = P(A.u, A.v, 0), arP = P(ARRIVE.u, ARRIVE.v, 0), doorP = P(DOOR.u, DOOR.v, 0), tagP = P(LAST[1][0], LAST[1][1], 0);
  const pinP = P(PINE_C.u, PINE_C.v, 58);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", overflow: "hidden", background: "#0c0c0c", filter: "grayscale(1)" }}>
      <svg width="100%" height="100%" viewBox={`0 0 ${W} ${H}`} style={{ position: "absolute", inset: 0, display: "block" }}>
        <g opacity={fade}>
          {streets}
          {bases}
          {cars}
          {last > 0 ? <polyline points={pts(lastFull)} fill="none" stroke="#fff" strokeWidth={5.5} strokeLinejoin="round" strokeDasharray={dashTo(last * lastLen)} /> : null}
          {items}
        </g>
        {/* route A -> "arrived" (a dark casing under a white line) */}
        {rp.length > 1 ? <><polyline points={pts(rp)} fill="none" stroke="#000" strokeWidth={13} strokeLinecap="round" strokeLinejoin="round" opacity={0.7 * fade} /><polyline points={pts(rp)} fill="none" stroke={WHITE} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" opacity={fade} /></> : null}
        {/* the last 50 m: dashed, round the block to the door */}
        {/* the east side of the last leg again, on top: it runs in front of the block, the north side runs behind it */}
        {last > 0 && last * lastLen > seg1Len ? <polyline points={pts(lastFull.slice(1))} fill="none" stroke={WHITE} strokeWidth={5.5} strokeLinejoin="round" strokeDasharray={dashTo(last * lastLen - seg1Len)} /> : null}
        {/* A */}
        <g transform={`translate(${aP[0]} ${aP[1]}) scale(${aIn})`} opacity={aIn}>
          <line x1={0} y1={0} x2={0} y2={-30} stroke={WHITE} strokeWidth={3} />
          <circle cy={-46} r={20} fill={WHITE} />
          <text textAnchor="middle" y={-37} fontFamily={SANS} fontWeight={700} fontSize={24} fill="#0B0B0B">A</text>
          <ellipse rx={13} ry={6} fill="#000" opacity={0.5} />
        </g>
        {/* "arrived" */}
        <g transform={`translate(${arP[0]} ${arP[1]})`} opacity={arrived}>
          <circle r={11 + 10 * (1 - arrived)} fill="#0B0B0B" stroke={WHITE} strokeWidth={4.5} />
          <text x={-18} y={-22} textAnchor="end" fontFamily={SANS} fontWeight={600} fontSize={19} fill="#E6E6E6" stroke="#000" strokeWidth={4} paintOrder="stroke">you have arrived</text>
        </g>
        {/* B: a pin standing at the door */}
        <g transform={`translate(${doorP[0]} ${doorP[1] - 14 * (1 - bIn)})`} opacity={bIn}>
          {ring > 0 ? <ellipse rx={26 + 60 * ring} ry={13 + 30 * ring} fill="none" stroke={WHITE} strokeWidth={2} opacity={0.75 * (1 - ring)} /> : null}
          <ellipse rx={11} ry={5} fill="#000" opacity={0.55} />
          <g transform="translate(0 -6) scale(1.25)"><path d="M0 0 L-9 -16 A19 19 0 1 1 9 -16 Z" fill={WHITE} stroke="#000" strokeWidth={1.5} /></g>
          <text textAnchor="middle" y={-26} fontFamily={SANS} fontWeight={700} fontSize={19} fill="#0B0B0B">B</text>
        </g>
        {tag > 0 ? <line x1={tagP[0]} y1={tagP[1]} x2={tagP[0] + 24} y2={tagP[1] - 36} stroke={WHITE} strokeWidth={1.6} opacity={tag} /> : null}
        {/* scale bar */}
        <g transform="translate(34 500)" opacity={0.9 * fade}>
          <line x1={0} y1={0} x2={86} y2={0} stroke={WHITE} strokeWidth={3} />
          <line x1={0} y1={-6} x2={0} y2={6} stroke={WHITE} strokeWidth={3} /><line x1={86} y1={-6} x2={86} y2={6} stroke={WHITE} strokeWidth={3} />
          <text x={43} y={-11} textAnchor="middle" fontFamily={SANS} fontWeight={600} fontSize={16} fill="#d8d8d8">50 m</text>
        </g>
        {/* north arrow */}
        <g transform="translate(972 46)" opacity={0.9 * fade}>
          <circle r={19} fill="none" stroke="#bdbdbd" strokeWidth={1.8} />
          <path d="M0 -13 L6 7 L0 3 L-6 7 Z" fill={WHITE} transform="rotate(-30)" />
        </g>
        <defs><radialGradient id="vg" cx="50%" cy="52%" r="75%"><stop offset="60%" stopColor="#000" stopOpacity={0} /><stop offset="100%" stopColor="#000" stopOpacity={0.62} /></radialGradient></defs>
        <rect width={W} height={H} fill="url(#vg)" />
      </svg>
      {/* the "50 m" tag: two split-flap tiles riffle up from 00, then a static "m" */}
      <div style={{ position: "absolute", left: tagP[0] + 22, top: tagP[1] - 74, opacity: tag, display: "flex", alignItems: "center", padding: "6px 12px 6px 8px", borderRadius: 14, background: "#000", border: "2px solid #fff" }}>
        <SplitFlapTile from="0" to="5" t={t - (cues.last50 + 0.17 * ld)} w={26} h={40} duration={0.22} color="#fff" bg="#1c1c1c" />
        <SplitFlapTile from="0" to="0" t={t - (cues.last50 + 0.25 * ld)} w={26} h={40} duration={0.22} cycles={3} color="#fff" bg="#1c1c1c" />
        <span style={{ fontFamily: SANS, fontWeight: 600, fontSize: 24, color: WHITE, marginLeft: 6 }}>m</span>
      </div>
      {/* B's name resolves out of noise */}
      <div style={{ position: "absolute", left: doorP[0] - 150, width: 300, top: doorP[1] + 12, textAlign: "center", opacity: bIn > 0 ? 1 : 0, fontFamily: SANS, fontWeight: 600, fontSize: 26, letterSpacing: 0 }}>
        <span style={{ display: "inline-block", padding: "5px 14px 6px", borderRadius: 8, background: "#000" }}><DualScramble text="Pinecone Academy" t={t - (cues.last50 + 0.85 * ld)} duration={0.7} color1="#8d8d8d" color2={WHITE} /></span>
      </div>
    </div>
  );
};
