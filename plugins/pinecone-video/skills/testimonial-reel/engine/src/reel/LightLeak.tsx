import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

// Pink/magenta light-leak flash, as on the cuts in DfEm-d-iLUz (5.9-6.7 s, 11.9-12.5 s):
// two soft colour blobs sweep left to right and peak on the cut, with a light screen wash.
const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const LightLeak: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const mid = durationInFrames / 2;
  const glow = interpolate(frame, [0, mid, durationInFrames], [0, 1, 0], {
    ...clamp,
    easing: Easing.inOut(Easing.sin),
  });
  const sweep = interpolate(frame, [0, durationInFrames], [-520, 520], clamp);
  return (
    <AbsoluteFill style={{ pointerEvents: "none", overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          opacity: glow,
          mixBlendMode: "screen",
          transform: `translateX(${sweep}px)`,
          background:
            "radial-gradient(ellipse 75% 90% at 35% 45%, #FF2E7E 0%, rgba(255,46,126,0) 70%), radial-gradient(ellipse 70% 85% at 70% 60%, #B23CFF 0%, rgba(178,60,255,0) 70%)",
          filter: "blur(40px)",
        }}
      />
      <AbsoluteFill style={{ opacity: glow * 0.3, mixBlendMode: "screen", backgroundColor: "#FFE7F3" }} />
    </AbsoluteFill>
  );
};
