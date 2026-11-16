import React from "react";
import {
  AbsoluteFill,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand, seconds } from "./brand";

// Numbered list overlay ("5. Cloud and Platform Engineer"), as in the top-5-jobs reel.
export type ListItem = {
  rank: number;
  title: string;
  note?: string;
};

export type ListCardProps = {
  heading: string;
  items: ListItem[];
  backgroundVideo?: string;
};

export const ITEM_SECONDS = 3;
export const HEADING_SECONDS = 2;

const Item: React.FC<{ item: ListItem }> = ({ item }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 18 } });
  const x = interpolate(enter, [0, 1], [-60, 0]);
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 80 }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 28,
          opacity: enter,
          transform: `translateX(${x}px)`,
        }}
      >
        <div style={{ fontFamily: brand.font, fontSize: 140, fontWeight: 600, color: brand.paper }}>
          {item.rank}.
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div
            style={{
              fontFamily: brand.font,
              fontSize: 64,
              fontWeight: 600,
              color: brand.paper,
              textTransform: "uppercase",
              lineHeight: 1.05,
            }}
          >
            {item.title}
          </div>
          {item.note ? (
            <div style={{ fontFamily: brand.font, fontSize: 36, color: brand.muted }}>
              {item.note}
            </div>
          ) : null}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Heading: React.FC<{ text: string; count: number }> = ({ text, count }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 12 } });
  return (
    <AbsoluteFill style={{ justifyContent: "center", padding: 80 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <div
          style={{
            fontFamily: brand.font,
            fontSize: 260,
            fontWeight: 700,
            color: brand.blue,
            transform: `scale(${pop})`,
          }}
        >
          {count}
        </div>
        <div style={{ fontFamily: brand.font, fontSize: 72, fontWeight: 600, color: brand.paper }}>
          {text}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const ListCard: React.FC<ListCardProps> = ({
  heading,
  items,
  backgroundVideo,
}) => {
  const headingFrames = seconds(HEADING_SECONDS);
  const itemFrames = seconds(ITEM_SECONDS);
  return (
    <AbsoluteFill style={{ backgroundColor: brand.ink }}>
      {backgroundVideo ? (
        <OffthreadVideo src={backgroundVideo} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : null}
      <AbsoluteFill
        style={{ background: "linear-gradient(180deg, rgba(14,18,32,0) 40%, rgba(14,18,32,0.85) 100%)" }}
      />
      <Sequence durationInFrames={headingFrames}>
        <Heading text={heading} count={items.length} />
      </Sequence>
      {items.map((item, i) => (
        <Sequence
          key={item.rank}
          from={headingFrames + i * itemFrames}
          durationInFrames={itemFrames}
        >
          <Item item={item} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
