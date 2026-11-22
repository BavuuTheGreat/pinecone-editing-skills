import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand } from "./brand";

// Event teaser: typewriter kicker -> big 3D-ish title -> place/date, as in the Hello World '26 teaser.
export type KineticTitleProps = {
  kicker: string;
  title: string;
  name: string;
  place: string;
  date: string;
};

const TYPE_FRAMES_PER_CHAR = 2;

const Starfield: React.FC = () => {
  const stars = Array.from({ length: 80 }, (_, i) => ({
    x: (i * 137.5) % 100,
    y: (i * 61.8) % 100,
    size: (i % 3) + 1,
  }));
  return (
    <AbsoluteFill>
      {stars.map((s, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: `${s.x}%`,
            top: `${s.y}%`,
            width: s.size,
            height: s.size,
            borderRadius: s.size,
            background: brand.muted,
            opacity: 0.6,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

export const KineticTitle: React.FC<KineticTitleProps> = ({
  kicker,
  title,
  name,
  place,
  date,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const typed = kicker.slice(0, Math.floor(frame / TYPE_FRAMES_PER_CHAR));
  const titleStart = kicker.length * TYPE_FRAMES_PER_CHAR + 10;
  const pop = spring({ frame: frame - titleStart, fps, config: { damping: 14 } });
  const details = interpolate(frame, [titleStart + 20, titleStart + 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shadow = [1, 2, 3, 4, 5, 6]
    .map((d) => `${d * 3}px ${d * 3}px 0 #1B2E8C`)
    .join(", ");
  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(180deg, #05070F 0%, ${brand.ink} 55%, #23356F 100%)`,
      }}
    >
      <Starfield />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", gap: 40 }}>
        <div style={{ fontFamily: brand.mono, fontSize: 36, color: brand.paper, minHeight: 44 }}>
          {typed}
        </div>
        <div
          style={{
            fontFamily: brand.font,
            fontSize: 420,
            fontWeight: 700,
            color: brand.blueSoft,
            textShadow: shadow,
            transform: `scale(${pop})`,
            lineHeight: 1,
          }}
        >
          {title}
        </div>
        <div style={{ opacity: details, display: "flex", flexDirection: "column", alignItems: "center", gap: 20 }}>
          <div style={{ fontFamily: brand.font, fontSize: 88, fontWeight: 600, color: brand.paper }}>
            {name}
          </div>
          <div style={{ display: "flex", gap: 48, fontFamily: brand.mono, fontSize: 32, color: brand.muted }}>
            <span>{place}</span>
            <span>{date}</span>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
