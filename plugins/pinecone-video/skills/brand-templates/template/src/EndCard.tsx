import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "./brand";

// Programme end card: partner names orbit in, programme name lands, CTA fades up
// (pattern of the Morphosis end card).
export type EndCardProps = {
  eyebrow: string;
  programme: string;
  line: string;
  cta: string;
  partners: string[];
};

export const EndCard: React.FC<EndCardProps> = ({
  eyebrow,
  programme,
  line,
  cta,
  partners,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const land = spring({ frame: frame - 15, fps, config: { damping: 16 } });
  const ctaIn = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ backgroundColor: brand.ink }}>
      {partners.map((p, i) => {
        // Upper arc only, so partner names never cross the programme title.
        const angle = Math.PI + ((i + 0.5) / Math.max(1, partners.length)) * Math.PI;
        const r = interpolate(frame, [0, 30], [700, 340], {
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={p}
            style={{
              position: "absolute",
              left: 540 + Math.cos(angle) * r - 140,
              top: 760 + Math.sin(angle) * r * 0.6,
              width: 280,
              textAlign: "center",
              fontFamily: brand.font,
              fontSize: 40,
              color: brand.muted,
              opacity: interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" }),
            }}
          >
            {p}
          </div>
        );
      })}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 18, top: 260 }}>
        <div style={{ fontFamily: brand.font, fontSize: 28, letterSpacing: 8, color: brand.blueSoft }}>
          {eyebrow.toUpperCase()}
        </div>
        <div
          style={{
            fontFamily: brand.font,
            fontSize: 150,
            fontWeight: 700,
            color: brand.paper,
            transform: `scale(${land})`,
          }}
        >
          {programme}
        </div>
        <div style={{ fontFamily: brand.font, fontSize: 36, color: brand.muted, maxWidth: 820, textAlign: "center" }}>
          {line}
        </div>
        <div
          style={{
            opacity: ctaIn,
            marginTop: 40,
            padding: "18px 40px",
            borderRadius: 999,
            background: brand.blue,
            fontFamily: brand.font,
            fontSize: 40,
            fontWeight: 600,
            color: brand.paper,
          }}
        >
          {cta}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
