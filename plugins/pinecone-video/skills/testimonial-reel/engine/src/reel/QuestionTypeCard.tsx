import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";
import { CARD_BG, ROUND } from "./fonts";
import { SoftLogo } from "./Transitions";

// Question card as in DfEm-d-iLUz: charcoal with a faint square grid, soft tan logo on top (same as on clips),
// question typed on letter by letter in its final centred position. Hard cut in and out.
export const CHARS_PER_SECOND = 22;

export const QuestionTypeCard: React.FC<{ question: string }> = ({ question }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typed = Math.max(0, Math.floor(((frame - 3) * CHARS_PER_SECOND) / fps));
  const shown = question.slice(0, typed);
  const rest = question.slice(typed);
  return (
    <AbsoluteFill
      style={{
        backgroundColor: CARD_BG,
        backgroundImage:
          "linear-gradient(rgba(255,255,255,0.035) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.035) 2px, transparent 2px)",
        backgroundSize: "180px 180px",
        backgroundPosition: "0px 0px",
      }}
    >
      <SoftLogo />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div
          style={{
            fontFamily: ROUND,
            fontWeight: 500,
            fontSize: 42,
            lineHeight: 1.35,
            color: "#F2F2F2",
            textAlign: "center",
            maxWidth: 900,
            ...({ textWrap: "balance" } as React.CSSProperties), // even two-line questions, no orphan "вэ?"
          }}
        >
          <span>{shown}</span>
          <span style={{ opacity: 0 }}>{rest}</span>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
