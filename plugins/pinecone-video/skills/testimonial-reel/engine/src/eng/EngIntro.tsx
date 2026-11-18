import React from "react";
import { AbsoluteFill, interpolate, staticFile, useCurrentFrame } from "remotion";
import T from "./intro_timing.json";
import { ACCENT, clamp, CREAM, GHOST, hash, INK, MONO, SANS, SERIF, SERIF_I, SETTLE, SMOOTH } from "./tokens";

// Series intro "Engineers matter more with AI" (about 3.9 s, then it opens onto the first shot).
// An engineer types "Engineers matter"; the AI suggests "more with AI" as grey ghost text (one shimmer);
// a Tab keycap is pressed, the ghost turns solid left to right, "<more/>" with "more" in Pinecone green italic and the brackets in white. The caret leaves; the block lifts away.
export const FONT = 176;
export const LINE = 182;
export const LEFT = 96;
export const TOP = 560;

// The caret spans cap height to baseline (measured on a still: cap top = baseline - 0.72 em). `before`: it sits left of the next glyph, not on it.
const Caret: React.FC<{ frame: number; solid: boolean; size?: number; before?: boolean }> = ({ frame, solid, size = FONT, before = false }) => {
  const on = solid || Math.floor(frame / 15) % 2 === 0;
  return (
    <span style={{ position: "relative" }}>
      <span style={{ position: "absolute", left: before ? -size * 0.085 : size * 0.05, top: size * 0.27, width: Math.max(4, size * 0.04), height: size * 0.72, background: ACCENT, opacity: on ? 1 : 0, borderRadius: 2 }} />
    </span>
  );
};

export const Mark: React.FC<{ src?: string; style?: React.CSSProperties }> = ({ src, style }) => {
  if (!src) return null;
  const url = `url(${staticFile(src)})`;
  return (
    <div style={{ width: 58, height: 48, backgroundColor: CREAM, opacity: 0.8, WebkitMaskImage: url, maskImage: url, WebkitMaskSize: "contain", maskSize: "contain",
      WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", ...style }} />
  );
};

// Pinecone mention: the mark plus a small "pinecone <academy/>" wordmark (text-only when the brand-pack mark is missing).
export const Lockup: React.FC<{ src?: string; text?: boolean }> = ({ src, text = true }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
    {text ? (
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, fontFamily: SANS, fontWeight: 800, fontSize: 38, letterSpacing: -1, color: CREAM, opacity: 0.92 }}>
        pinecone<span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 21, letterSpacing: 0.5, color: ACCENT }}>academy</span>
      </div>
    ) : null}
    <Mark src={src} />
  </div>
);

// The title block, drawn for intro frame `f` (also used by the outro with the final state: f >= 120, small = true).
export const TitleBlock: React.FC<{ f: number; size?: number; showCaret?: boolean }> = ({ f, size = FONT, showCaret = true }) => {
  const k1 = T.line1Keys.filter((k) => f >= k).length;
  const k2 = T.line2Keys.filter((k) => f >= k).length;
  const typing1 = f >= T.line1Keys[0] && k1 < T.line1.length;
  const typing2 = f >= T.line2Keys[0] && k2 < T.line2.length;
  const recent = (arr: number[]) => arr.some((k) => f >= k && f < k + 3);
  const ghostA = interpolate(f, [T.ghostIn, T.ghostIn + 8], [0, 1], { ...clamp, easing: SETTLE });
  const [s0, s1] = T.shimmer;
  const GL = T.ghost.length + T.ghost2.length;
  const shimmerPos = interpolate(f, [s0, s1], [-3, GL + 3], { ...clamp, easing: SMOOTH });
  const shimmerOn = f >= s0 && f <= s1;
  const accepted = (i: number) => interpolate(f, [T.acceptStart + i * T.acceptPerChar, T.acceptStart + i * T.acceptPerChar + 7], [0, 1], { ...clamp, easing: SETTLE });
  const acceptedAll = f > T.acceptStart + GL * T.acceptPerChar + 7;
  const line3Caret = f >= T.line2Keys[T.line2Keys.length - 1] + 6 && f < T.caretOff;
  const solidCaret = typing1 || typing2 || recent(T.line1Keys) || recent(T.line2Keys);
  const base: React.CSSProperties = { fontFamily: SERIF, fontSize: size, lineHeight: `${size * (LINE / FONT)}px`, color: CREAM, letterSpacing: -size * 0.012, whiteSpace: "pre" };
  // ghost line "<more/> with AI": index 0 "<", 1-4 "more" (green italic), 5-6 "/>" (white like the rest)
  return (
    <div>
      <div style={base}>
        {T.line1.slice(0, k1)}
        {showCaret && f < T.line2Keys[0] - 2 && f >= 2 ? <Caret frame={f} solid={solidCaret} size={size} /> : null}
        {k1 === 0 ? "​" : ""}
      </div>
      <div style={base}>
        {T.line2.slice(0, k2)}
        {showCaret && f >= T.line2Keys[0] - 2 && f < T.line2Keys[T.line2Keys.length - 1] + 6 ? <Caret frame={f} solid={solidCaret} size={size} /> : null}
        {k2 === 0 ? "​" : ""}
      </div>
      {[T.ghost, T.ghost2].map((line, li) => {
        const off = li === 0 ? 0 : T.ghost.length; // global char index for the accept stagger and the shimmer
        return (
          <div key={li} style={{ ...base, position: "relative" }}>
            {li === 0 && showCaret && line3Caret && f < T.acceptStart ? <Caret frame={f} solid={false} size={size} before /> : null}
            {line.split("").map((ch, ci) => {
              const i = off + ci;
              const a = accepted(i);
              const sh = shimmerOn ? 0.42 * Math.exp(-Math.pow((i - shimmerPos) / 1.9, 2)) : 0;
              const inMore = li === 0 && ci >= 1 && ci <= 4; // "more" inside "<more/>": Pinecone green italic; brackets white
              const ghostAlpha = 0.28 + sh;
              const col = inMore ? ACCENT : li === 0 ? "#FFFFFF" : CREAM; // "more" Pinecone green, the brackets white, "with AI" like the lines above
              // ghost -> solid: blend alpha, never swap font (no layout shift)
              const alpha = ghostAlpha + (1 - ghostAlpha) * a;
              return (
                <span key={ci} style={{ fontFamily: inMore ? SERIF_I : SERIF, color: a > 0 ? col : CREAM, opacity: ghostA * (a > 0 ? alpha : ghostAlpha + sh) }}>
                  {ch === " " ? " " : ch}
                </span>
              );
            })}
            {li === 1 && showCaret && acceptedAll && f < T.caretOff ? <Caret frame={f} solid={false} size={size} /> : null}
          </div>
        );
      })}
    </div>
  );
};

export const TabKey: React.FC<{ f: number }> = ({ f }) => {
  const inP = interpolate(f, [T.tabIn, T.tabIn + 9], [0, 1], { ...clamp, easing: SETTLE });
  const press = interpolate(f, [T.tabPress, T.tabPress + 3, T.tabPress + 9], [0, 1, 0], clamp);
  const gone = interpolate(f, [T.caretOff, T.caretOff + 8], [1, 0], { ...clamp, easing: SMOOTH });
  const lit = interpolate(f, [T.tabPress, T.tabPress + 3], [0, 1], clamp);
  return (
    <div style={{ position: "absolute", left: LEFT, top: TOP + 4 * LINE + 40, opacity: inP * gone, transform: `translateY(${(1 - inP) * 22 + press * 5}px)` }}>
      <div style={{ display: "inline-flex", alignItems: "center", gap: 14, padding: "14px 26px", borderRadius: 16, fontFamily: SANS, fontSize: 30, fontWeight: 700, letterSpacing: 1,
        color: lit > 0.5 ? INK : CREAM, background: lit > 0.5 ? ACCENT : "rgba(242,235,220,0.08)", border: `1.5px solid ${lit > 0.5 ? ACCENT : "rgba(242,235,220,0.28)"}`,
        boxShadow: press > 0.5 ? "0 1px 0 rgba(0,0,0,0.5)" : "0 6px 0 rgba(242,235,220,0.14)" }}>
        <span>tab</span>
        <span style={{ fontSize: 28 }}>⇥</span>
      </div>
    </div>
  );
};

// Everything the intro draws, for frame f. `exit` 0..1 lifts the block away (used while the first shot opens).
export const IntroScene: React.FC<{ f: number; mark?: string; exit?: number; standalone?: boolean; meta?: boolean; signature?: string; ep?: string }> = ({ f, mark, exit = 0, standalone = false, meta = false, signature, ep }) => {
  const metaA = interpolate(f, [4, 16], [0, 1], { ...clamp, easing: SETTLE });
  const lift = exit * -36;
  const slate = standalone ? interpolate(f, [T.caretOff + 6, T.caretOff + 22], [0, 1], { ...clamp, easing: SETTLE }) : 0;
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {meta ? <div style={{ position: "absolute", left: LEFT, top: 238, right: LEFT, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: metaA * (1 - exit) }}>
        <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, letterSpacing: 5, color: ACCENT }}>EP 01</div>
        <Lockup src={mark} text />
      </div> : null}
      <div style={{ position: "absolute", left: LEFT, top: TOP, opacity: 1 - exit, transform: `translateY(${lift}px)` }}>
        <TitleBlock f={f} />
      </div>
      <TabKey f={f} />
      {ep ? (
        <div style={{ position: "absolute", left: LEFT, top: TOP + 4 * LINE + 70, opacity: interpolate(f, [T.caretOff + 6, T.caretOff + 18], [0, 1], { ...clamp, easing: SETTLE }),
          transform: `translateY(${(1 - interpolate(f, [T.caretOff + 6, T.caretOff + 18], [0, 1], clamp)) * 12}px)`, fontFamily: SANS, fontWeight: 700, fontSize: 48, letterSpacing: 9, color: ACCENT }}>{ep}</div>
      ) : null}
      {signature ? (
        // the presenter's name and role sign the closer once the suggestion has been accepted
        <div style={{ position: "absolute", left: LEFT, top: TOP + 4 * LINE + 70, opacity: interpolate(f, [T.caretOff + 6, T.caretOff + 18], [0, 1], { ...clamp, easing: SETTLE }),
          transform: `translateY(${(1 - interpolate(f, [T.caretOff + 6, T.caretOff + 18], [0, 1], clamp)) * 12}px)`, fontFamily: SANS, fontWeight: 500, fontSize: 36, letterSpacing: 0.3, color: "rgba(242,235,220,0.9)" }}>{signature}</div>
      ) : null}
    </AbsoluteFill>
  );
};

export const EngIntro: React.FC<{ mark?: string; meta?: boolean }> = ({ mark, meta }) => {
  const frame = useCurrentFrame();
  return <IntroScene f={frame} mark={mark} standalone meta={meta} />;
};
