import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { TestimonialReel, TestimonialReelProps } from "./TestimonialReel";
import { Captions, Caption, CaptionStyle } from "./Captions";
import { Hook, HookTitle, Insert, InsertView } from "./PineQuestLook";

// PineQuest S5 participant / judge reel: speaker answers, typed grid cards, framed project inserts,
// captions over everything, supplied PineQuest S5 end card (last item, bare). No name title on screen.
export type PineQuestReelProps = TestimonialReelProps & { inserts: Insert[]; hook?: Hook; captions?: Caption[]; captionStyle?: CaptionStyle };

export const PineQuestReel: React.FC<PineQuestReelProps> = ({ inserts, hook, captions, captionStyle, ...rest }) => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      <TestimonialReel {...rest} look="pinequest" />
      {inserts.map((ins, i) => (
        <Sequence key={i} from={Math.round(ins.from * fps)} durationInFrames={Math.round(ins.seconds * fps)} name={`insert ${ins.src}`}>
          <InsertView ins={ins} />
        </Sequence>
      ))}
      {hook ? (
        <Sequence from={Math.round(hook.from * fps)} durationInFrames={Math.round(hook.seconds * fps)} name="hook title">
          <HookTitle hook={hook} />
        </Sequence>
      ) : null}
      {captions && captionStyle ? <Captions captions={captions} style={captionStyle} /> : null}
    </AbsoluteFill>
  );
};
