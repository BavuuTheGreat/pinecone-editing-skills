import React from "react";
import { AbsoluteFill, Img, interpolate, OffthreadVideo, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { MARK, ROUND } from "./fonts";
import { CHARS_PER_SECOND } from "./QuestionTypeCard";

// PineQuest S5 reel look, measured from DfqgqzBE85z / DfmXpIijZkS / Dfg2YWhAtbO (Nov 2026):
// grey chevron mark top-centre, #181818 card with a fine 67 px grid, question typed in at 53 % height,
// project/team media framed 1004 px wide on the same card while the speaker's voice runs on.
export const PQ_BG = "#181818";
const GRID: React.CSSProperties = {
  backgroundColor: PQ_BG,
  backgroundImage:
    "linear-gradient(rgba(255,255,255,0.06) 1.5px, transparent 1.5px), linear-gradient(90deg, rgba(255,255,255,0.06) 1.5px, transparent 1.5px)",
  backgroundSize: "67px 67px",
  backgroundPosition: "6px 22px",
};

export const ChevronLogo: React.FC = () => {
  const url = `url(${staticFile(MARK)})`;
  return (
    <div
      style={{
        position: "absolute", top: 86, left: 540 - 30, width: 60, height: 50, backgroundColor: "#BDBDBD", opacity: 0.55,
        WebkitMaskImage: url, maskImage: url, WebkitMaskSize: "contain", maskSize: "contain",
        WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", WebkitMaskPosition: "center", maskPosition: "center",
        filter: "blur(0.6px)",
      }}
    />
  );
};

// Fixed line breaks, decided once per question (CSS text-wrap: balance re-wrapped on every typed frame, so the
// text jumped sideways mid-typing: review 2026-11-14). Each line is centred at its FINAL width (the untyped rest is
// laid out invisibly), so nothing moves while it types. The cursor is zero-width and glued to the last typed letter.
const MAX_LINE = 30; // chars per line at 47 px Manrope inside 900 px
export const splitLines = (q: string): string[] => {
  const words = q.split(" ");
  if (q.length <= MAX_LINE || words.length < 2) return [q];
  let best: string[] = [q];
  let bestScore = Infinity;
  for (let i = 1; i < words.length; i++) {
    const l1 = words.slice(0, i).join(" ");
    const l2 = words.slice(i).join(" ");
    const score = Math.max(l1.length, l2.length) + (l1.length < l2.length ? 0.5 : 0); // balanced, top line not shorter
    if (score < bestScore) { bestScore = score; best = [l1, l2]; }
  }
  return best;
};

export const PQCard: React.FC<{ question: string; typing?: boolean }> = ({ question, typing = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // typing=false (default since review 2026-11-16 "show the question at once"): whole question with a gentle fade/scale-in
  const typed = typing ? Math.max(0, Math.floor(((frame - 3) * CHARS_PER_SECOND) / fps)) : question.length + 1;
  const appear = typing ? 1 : easeOut(Math.min(1, frame / 8));
  const lines = splitLines(question);
  let offset = 0;
  return (
    <AbsoluteFill style={{ ...GRID, backgroundPosition: `6px ${22 - frame * 0.6}px` }}>
      <ChevronLogo />
      <div
        style={{
          position: "absolute", top: "53%", left: 0, right: 0, transform: "translateY(-50%)", textAlign: "center",
          fontFamily: ROUND, fontWeight: 500, fontSize: 47, lineHeight: 1.3, color: "#F2F2F2",
          ...(typing ? {} : { opacity: appear, transform: `translateY(-50%) scale(${0.96 + 0.04 * appear})` }),
        }}
      >
        {lines.map((ln, li) => {
          const start = offset;
          offset += ln.length + 1; // + the space that became the line break
          const n = Math.max(0, Math.min(ln.length, typed - start));
          const shown = ln.slice(0, n).replace(/\s+$/, "");
          const cursorHere = typed >= start && (typed < start + ln.length + 1 || li === lines.length - 1) && shown.length > 0;
          return (
            <div key={li} style={{ whiteSpace: "pre" }}>
              <span>{shown}</span>
              {typing && cursorHere ? <Cursor visible /> : null}
              <span style={{ opacity: 0 }}>{ln.slice(shown.length)}</span>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

export type Insert = {
  from: number; // seconds on the reel timeline
  seconds: number;
  src: string; // in public/
  media: "image" | "video";
  layout: "framed" | "full";
  videoStart?: number; // seconds into a video src
};

// Speaker audio keeps playing underneath (inserts are picture only).
export const InsertView: React.FC<{ ins: Insert }> = ({ ins }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, ins.seconds * fps], [1, 1.06], { extrapolateRight: "clamp" });
  const pop = easeOut(Math.min(1, frame / 8));
  const popStyle: React.CSSProperties = {
    transform: `scale(${0.82 + 0.18 * pop}) rotate(${(1 - pop) * -2.5}deg)`, opacity: Math.min(1, frame / 3),
    filter: pop < 1 ? `blur(${(1 - pop) * 14}px)` : undefined,
  };
  const media =
    ins.media === "image" ? (
      <Img src={staticFile(ins.src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${zoom})` }} />
    ) : (
      <OffthreadVideo src={staticFile(ins.src)} muted startFrom={Math.round((ins.videoStart ?? 0) * fps)}
        style={{ width: "100%", height: "100%", objectFit: "cover" }} />
    );
  if (ins.layout === "full") {
    return (
      <AbsoluteFill style={{ backgroundColor: "#000" }}>
        <AbsoluteFill style={{ transform: `scale(${1.25 - 0.25 * pop})`, filter: pop < 1 ? `blur(${(1 - pop) * 20}px)` : undefined }}>{media}</AbsoluteFill>
        <ChevronLogo />
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={GRID}>
      <ChevronLogo />
      <div style={{ position: "absolute", left: 38, top: 640, width: 1004, height: 564, overflow: "hidden", borderRadius: 6,
        boxShadow: "0 24px 60px rgba(0,0,0,0.55)", ...popStyle }}>{media}</div>
    </AbsoluteFill>
  );
};

// ---------- PineQuest motion (v2: "more exciting" pass) ----------
export type PQEdgeKind = "whip" | "fade" | "glitch" | "impact" | "none";
export type ZoomKey = { t: number; scale: number; y?: number; still?: boolean }; // seconds inside the clip; snaps over 5 frames; still: applies at once (a fixed framing, no snap)

const easeOut = (x: number) => 1 - Math.pow(1 - x, 3);
const easeIn = (x: number) => x * x * x;

// deterministic per-frame noise
const hash = (n: number) => {
  const s = Math.sin(n * 12.9898) * 43758.5453;
  return s - Math.floor(s);
};

export const PQEdge: React.FC<{ len: number; inEdge: PQEdgeKind; outEdge: PQEdgeKind; zoom?: ZoomKey[]; children: React.ReactNode }> = ({
  len, inEdge, outEdge, zoom, children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  let scale = 1, blur = 0, bright = 1, ty = 0, tx = 0;
  // punch-in zoom keys (snap with ease-out over 5 frames)
  if (zoom && zoom.length) {
    let cur = { scale: 1, y: 0 }, prev = { scale: 1, y: 0 }, since = 999;
    for (const k of zoom) {
      const kf = Math.round(k.t * fps);
      if (frame >= kf) { prev = cur; cur = { scale: k.scale, y: k.y ?? 0 }; since = k.still ? 999 : frame - kf; }
    }
    const p = Math.min(1, since / 5);
    scale *= prev.scale + (cur.scale - prev.scale) * easeOut(p);
    ty += prev.y + (cur.y - prev.y) * easeOut(p);
  }
  const IN = 7, OUT = 5;
  if (inEdge === "whip" && frame < IN) {
    const k = 1 - easeOut(frame / IN);
    scale *= 1 + 0.22 * k; blur += 26 * k; bright += 0.35 * k; ty += -60 * k;
  }
  if (inEdge === "impact" && frame < 10) {
    const k = 1 - easeOut(frame / 10);
    scale *= 1 + 0.14 * k; bright += 0.5 * k;
  }
  const left = len - 1 - frame;
  if (outEdge === "whip" && left < OUT) {
    const k = easeIn(1 - left / OUT);
    scale *= 1 + 0.2 * k; blur += 26 * k; bright += 0.3 * k; ty += 60 * k;
  }
  // fade: calm dip to dark around question cards (whip blur on card text read as a glitch, review 2026-11-14)
  let dim = 1;
  if (inEdge === "fade" && frame < 6) dim = Math.min(dim, 0.15 + 0.85 * easeOut(frame / 6));
  if (outEdge === "fade" && left < 6) dim = Math.min(dim, 0.15 + 0.85 * easeOut(left / 6));
  if (dim < 1) bright *= dim;
  let glitch = 0;
  if (inEdge === "glitch" && frame < 9) glitch = 1 - frame / 9;
  if (outEdge === "glitch" && left < 5) glitch = Math.max(glitch, 1 - left / 5);
  if (glitch > 0) { tx += (hash(frame) - 0.5) * 70 * glitch; scale *= 1 + 0.05 * glitch; }
  const style: React.CSSProperties = {
    transform: `translate(${tx}px, ${ty}px) scale(${scale})`,
    filter: blur || bright !== 1 ? `blur(${blur.toFixed(1)}px) brightness(${bright.toFixed(2)})` : undefined,
  };
  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#000" }}>
      <AbsoluteFill style={style}>{children}</AbsoluteFill>
      {glitch > 0 ? <GlitchBars amount={glitch} frame={frame} /> : null}
    </AbsoluteFill>
  );
};

const GlitchBars: React.FC<{ amount: number; frame: number }> = ({ amount, frame }) => (
  <AbsoluteFill style={{ mixBlendMode: "screen" }}>
    {Array.from({ length: 9 }).map((_, i) => {
      const r = hash(frame * 31 + i * 7);
      if (r > 0.25 + 0.6 * amount) return null;
      const top = hash(frame * 13 + i) * 1920;
      const h = 8 + hash(i * 3 + frame) * 90;
      const col = i % 3 === 0 ? "rgba(255,40,80,0.55)" : i % 3 === 1 ? "rgba(40,220,255,0.5)" : "rgba(255,255,255,0.35)";
      return <div key={i} style={{ position: "absolute", left: (hash(i + frame * 5) - 0.5) * 200, top, width: 1280, height: h, background: col, opacity: amount }} />;
    })}
  </AbsoluteFill>
);

export const Cursor: React.FC<{ visible: boolean }> = ({ visible }) => {
  const frame = useCurrentFrame();
  const on = visible && Math.floor(frame / 8) % 2 === 0;
  // zero-width anchor: the bar never takes layout space, so the text never re-wraps or shifts while typing
  return (
    <span style={{ position: "relative" }}>{/* inline (not inline-block): adds no line-break opportunity mid-word */}
      <span style={{ position: "absolute", left: 6, top: 9, width: 3, height: 38, borderRadius: 1.5, background: "#F2F2F2", opacity: on ? 0.85 : 0 }} />
    </span>
  );
};

// Cold-open headline (top reels on the account open with a bold headline from frame 0).
export type HookLine = { text: string; highlight?: string };
export type Hook = { from: number; seconds: number; lines: HookLine[]; top?: number; motion?: "calm" | "punchy" }; // calm (default): headline fades in whole; punchy: word-by-word pop

// Auto-fit (review 2026-11-16, "текст жижиг болгох"): the longest line may take at most 80 % of the 1080 width. Shrink only, never grow:
// a short two-line headline keeps the approved 80 px. Width is estimated from the character count (Manrope ExtraBold Cyrillic ~0.6 em/char).
const HOOK_MAX = 80, HOOK_MAX_W = 0.8 * 1080, EM_PER_CHAR = 0.66; // 0.66: measured on a still of "нэг компанийн захирал" (real ~0.60) plus margin
export const hookFontSize = (lines: HookLine[]): number => {
  if (!lines.length) return HOOK_MAX;
  const widest = Math.max(1, ...lines.map((l) => l.text.length * EM_PER_CHAR + (l.highlight ? 0.5 : 0))); // 0.5 em: the highlight pill's padding
  return Math.min(HOOK_MAX, Math.floor(HOOK_MAX_W / widest));
};

export const HookTitle: React.FC<{ hook: Hook }> = ({ hook }) => {
  const size = hookFontSize(hook.lines);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = Math.round(hook.seconds * fps);
  const calm = hook.motion !== "punchy";
  const outK = Math.max(0, (frame - (total - 5)) / 5);
  const fadeIn = calm ? easeOut(Math.min(1, frame / 12)) : 1;
  let w = 0;
  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <AbsoluteFill style={{ background: "linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.25) 32%, transparent 50%)", opacity: 1 - outK }} />
      <div style={{ position: "absolute", top: hook.top ?? 250, left: 0, right: 0, textAlign: "center", opacity: (1 - outK) * fadeIn,
        transform: calm ? undefined : `scale(${1 + outK * 0.15})`, filter: !calm && outK ? `blur(${outK * 10}px)` : undefined }}>
        {hook.lines.map((ln, li) => (
          <div key={li} style={{ display: "flex", flexWrap: "nowrap", justifyContent: "center", gap: `0 ${Math.round(size * 0.225)}px`, marginBottom: 14 }}>
            {(ln.highlight && ln.text.includes(ln.highlight)
              ? [...ln.text.split(ln.highlight)[0].trim().split(" "), ln.highlight, ...ln.text.split(ln.highlight)[1].trim().split(" ")].filter(Boolean)
              : ln.text.split(" ")
            ).map((word, wi) => {
              const idx = w++;
              const p = calm ? 1 : easeOut(Math.min(1, Math.max(0, (frame - 2 - idx * 3) / 6)));
              const hl = ln.highlight === word;
              return (
                <span key={wi} style={{
                  fontFamily: ROUND, fontWeight: 800, fontSize: size, lineHeight: 1.12, color: hl ? "#111" : "#fff",
                  background: hl ? "#F2F2F2" : "transparent", padding: hl ? `0 ${Math.round(size * 0.175)}px` : 0, borderRadius: hl ? Math.round(size * 0.125) : 0,
                  textShadow: hl ? "none" : "0 4px 24px rgba(0,0,0,0.55)", display: "inline-block", opacity: p,
                  transform: calm ? undefined : `translateY(${(1 - p) * 40}px) scale(${0.7 + 0.3 * p})`, letterSpacing: -1,
                }}>{word}</span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
