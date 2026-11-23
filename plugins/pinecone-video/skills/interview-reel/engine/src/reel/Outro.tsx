import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CARD_BG, GREEN, MARK, MONO, ROUND } from "./fonts";

// v5 outro: the last shot eases back into a rounded frame over the question-card grid,
// softens out, then the pinecone lockup assembles piece by piece (mark, wordmark,
// typed <academy/>, accent rule), holds, and the whole frame fades to black.
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const SMOOTH = Easing.bezier(0.65, 0, 0.35, 1);
const SETTLE = Easing.bezier(0.16, 1, 0.3, 1);

// Transform for the final clip; t = frames since the outro began, len = frames it lasts.
export const outroClipStyle = (t: number, len: number): React.CSSProperties => {
  if (t < 0) return {};
  const s = interpolate(t, [0, len], [1, 0.8], { ...clamp, easing: SMOOTH });
  return {
    transform: `scale(${s}) translateY(${interpolate(t, [0, len], [0, -40], { ...clamp, easing: SMOOTH })}px)`,
    borderRadius: interpolate(t, [0, len * 0.6], [0, 56], { ...clamp, easing: SMOOTH }),
    overflow: "hidden",
    boxShadow: `0 30px 90px rgba(0,0,0,${interpolate(t, [0, len], [0, 0.6], clamp)})`,
    filter: `brightness(${interpolate(t, [len * 0.4, len], [1, 0.75], clamp)}) blur(${interpolate(t, [len * 0.55, len], [0, 14], clamp)}px)`,
    opacity: interpolate(t, [len * 0.6, len], [1, 0], { ...clamp, easing: SMOOTH }),
  };
};

export const OutroBackdrop: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        backgroundColor: CARD_BG,
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.035) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.035) 2px, transparent 2px)",
        backgroundSize: "180px 180px",
        opacity: interpolate(frame, [0, 10, durationInFrames - 15, durationInFrames - 1], [0, 1, 1, 0], clamp),
      }}
    >
      <AbsoluteFill
        style={{ background: "radial-gradient(ellipse 60% 40% at 50% 50%, rgba(0,211,127,0.07) 0%, rgba(0,0,0,0) 70%)" }}
      />
    </AbsoluteFill>
  );
};

const rise = (t: number) => ({
  opacity: interpolate(t, [0, 12], [0, 1], { ...clamp, easing: SETTLE }),
  transform: `translateY(${interpolate(t, [0, 18], [28, 0], { ...clamp, easing: SETTLE })}px)`,
  filter: `blur(${interpolate(t, [0, 14], [10, 0], { ...clamp, easing: SETTLE })}px)`,
});

// enter = frame (inside this sequence) where the lockup starts to build.
export const OutroLockup: React.FC<{ enter: number }> = ({ enter }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame - enter;
  const tag = "<academy/>";
  const typed = Math.max(0, Math.floor(((t - 16) * 18) / fps));
  const out = interpolate(frame, [durationInFrames - 15, durationInFrames - 1], [1, 0], { ...clamp, easing: SMOOTH });
  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", opacity: out }}>
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
        <Img src={staticFile(MARK)} style={{ width: 120, height: 104, ...rise(t) }} />
        <span
          style={{
            fontFamily: ROUND,
            fontWeight: 700,
            fontSize: 112,
            color: "#fff",
            letterSpacing: -3,
            lineHeight: 1,
            ...rise(t - 6),
          }}
        >
          pinecone
        </span>
        <span style={{ fontFamily: MONO, fontWeight: 500, fontSize: 44, color: GREEN, opacity: t >= 16 ? 1 : 0 }}>
          <span>{tag.slice(0, typed)}</span>
          <span style={{ opacity: 0 }}>{tag.slice(typed)}</span>
        </span>
        <div
          style={{
            width: interpolate(t, [24, 46], [0, 240], { ...clamp, easing: SMOOTH }),
            height: 3,
            borderRadius: 2,
            backgroundColor: GREEN,
            opacity: 0.85,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
