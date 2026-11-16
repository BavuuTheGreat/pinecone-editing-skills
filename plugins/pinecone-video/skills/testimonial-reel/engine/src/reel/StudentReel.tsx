import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import { TestimonialReel, TestimonialReelProps } from "./TestimonialReel";
import { Captions, Caption, CaptionStyle } from "./Captions";
import { KineticWords, KineticWordsProps } from "./KineticWords";

// One-student cut of the reel: same reel plus the v4/v5 kinetic name title during the intro (below the face).
// nameTitle.scale shrinks one name's font only when it would overflow the 1080 frame.
export type NameTitle = KineticWordsProps & { from: number; seconds: number; scale?: number };
export type StudentReelProps = TestimonialReelProps & { nameTitle: NameTitle; captions?: Caption[]; captionStyle?: CaptionStyle };

export const StudentReel: React.FC<StudentReelProps> = ({ nameTitle, captions, captionStyle, ...rest }) => {
  const { fps } = useVideoConfig();
  const { from, seconds, scale, ...kw } = nameTitle;
  return (
    <AbsoluteFill>
      <TestimonialReel {...rest} />
      <Sequence from={Math.round(from * fps)} durationInFrames={Math.round(seconds * fps)} name="name title">
        {scale && scale !== 1 ? (
          <AbsoluteFill style={{ transform: `scale(${scale})`, transformOrigin: `50% ${kw.top + 120}px` }}>
            <KineticWords {...kw} />
          </AbsoluteFill>
        ) : (
          <KineticWords {...kw} />
        )}
      </Sequence>
      {captions && captionStyle ? <Captions captions={captions} style={captionStyle} /> : null}
    </AbsoluteFill>
  );
};
