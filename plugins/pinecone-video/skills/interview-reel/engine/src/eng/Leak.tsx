import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Soft colour light leak (the colourful smooth transition of the testimonial reels, LightLeak.tsx), with two palettes so the
// two chapter changes of an episode do not look the same: "pink" (the original) and "green" (Pinecone green).
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const TONES = {
  pink: ["#FF2E7E", "#B23CFF", "#FFE7F3"],
  green: ["#00D37F", "#0A9B8E", "#E4FFF3"],
};

export const Leak: React.FC<{ tone?: keyof typeof TONES; dir?: number }> = ({ tone = "pink", dir = 1 }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const [a, b, wash] = TONES[tone];
  const glow = interpolate(frame, [0, durationInFrames / 2, durationInFrames], [0, 1, 0], { ...clamp, easing: Easing.inOut(Easing.sin) });
  const sweep = interpolate(frame, [0, durationInFrames], [-520, 520], clamp) * dir;
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      <AbsoluteFill style={{ opacity: glow, mixBlendMode: "screen", transform: `translateX(${sweep}px)`, filter: "blur(40px)",
        background: `radial-gradient(ellipse 75% 90% at 35% 45%, ${a} 0%, rgba(0,0,0,0) 70%), radial-gradient(ellipse 70% 85% at 70% 60%, ${b} 0%, rgba(0,0,0,0) 70%)` }} />
      <AbsoluteFill style={{ opacity: glow * 0.3, mixBlendMode: "screen", backgroundColor: wash }} />
    </AbsoluteFill>
  );
};
