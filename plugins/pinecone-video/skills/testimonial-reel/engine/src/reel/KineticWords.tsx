import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CONDENSED, ROUND } from "./fonts";

// Kinetic keyword title as in DeLat1wjdqL: small caps kicker fades up first,
// then big condensed words resolve from a blurred ghost to solid white, one after another.
export type KineticWordsProps = {
  kicker: string;
  words: string[];
  wordSeconds: number;
  top: number;
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const ease = Easing.bezier(0.16, 1, 0.3, 1);

const Word: React.FC<{ text: string; local: number; length: number }> = ({ text, local, length }) => (
  <div
    style={{
      fontFamily: CONDENSED,
      fontWeight: 700,
      fontSize: 200,
      lineHeight: 0.95,
      letterSpacing: -2,
      color: "#fff",
      textTransform: "uppercase",
      whiteSpace: "nowrap", // hyphenated names (Бат-Эрдэнэ) stay on one line
      textShadow: "0 6px 30px rgba(0,0,0,0.45)",
      opacity: interpolate(local, [0, 5, length - 4, length], [0.25, 1, 1, 0], clamp),
      filter: `blur(${interpolate(local, [0, 6], [14, 0], { ...clamp, easing: ease })}px)`,
      transform: `scale(${interpolate(local, [0, 8], [1.06, 1], { ...clamp, easing: ease })})`,
    }}
  >
    {text}
  </div>
);

export const KineticWords: React.FC<KineticWordsProps> = ({ kicker, words, wordSeconds, top }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const lead = Math.round(0.25 * fps);
  const per = Math.round(wordSeconds * fps);
  const idx = Math.min(words.length - 1, Math.max(0, Math.floor((frame - lead) / per)));
  const local = frame - lead - idx * per;
  const isLast = idx >= words.length - 1;
  const length = isLast ? durationInFrames - lead - idx * per : per;
  return (
    <AbsoluteFill style={{ alignItems: "center" }}>
      <div style={{ position: "absolute", top, display: "flex", flexDirection: "column", alignItems: "center", gap: 42 }}>
        <div
          style={{
            fontFamily: ROUND,
            fontWeight: 800,
            fontSize: 30,
            letterSpacing: 4,
            color: "#fff",
            textTransform: "uppercase",
            textShadow: "0 2px 14px rgba(0,0,0,0.5)",
            opacity: interpolate(frame, [0, 8, durationInFrames - 6, durationInFrames], [0, 1, 1, 0], clamp),
            transform: `translateY(${interpolate(frame, [0, 10], [16, 0], { ...clamp, easing: ease })}px)`,
          }}
        >
          {kicker}
        </div>
        {frame >= lead && words.length > 0 ? <Word key={idx} text={words[idx]} local={local} length={length} /> : null}
      </div>
    </AbsoluteFill>
  );
};
