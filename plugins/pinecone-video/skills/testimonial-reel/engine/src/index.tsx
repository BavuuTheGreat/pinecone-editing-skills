// Minimal entry: only the per-student reel (rest of the old Root depends on files purged from /tmp).
import React from "react";
import { Composition, registerRoot } from "remotion";
import { reelFrames } from "./reel/TestimonialReel";
import { StudentReel, StudentReelProps } from "./reel/StudentReel";
import { PineQuestReel, PineQuestReelProps } from "./reel/PineQuestReel";

const Root: React.FC = () => (
  <>
  <Composition
    id="StudentReel"
    component={StudentReel}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={300}
    defaultProps={{ items: [{ kind: "question", text: "Сурах?", seconds: 2.4 }], titles: [], shrinkSeconds: 1.1, holdSeconds: 3.4, nameTitle: { kicker: "Pinecone Bootcamp", words: ["Нэр"], wordSeconds: 2.7, top: 1240, from: 0.45, seconds: 3 } } as StudentReelProps}
    calculateMetadata={({ props }) => ({ durationInFrames: reelFrames(props as any, 30) })}
  />
  <Composition
    id="PineQuestReel"
    component={PineQuestReel}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={300}
    defaultProps={{ items: [{ kind: "question", text: "PineQuest-д орсон сэтгэгдэл", seconds: 2.4 }], titles: [], shrinkSeconds: 1.1, holdSeconds: 0, builtInOutro: false, inserts: [] } as PineQuestReelProps}
    calculateMetadata={({ props }) => ({ durationInFrames: reelFrames(props as any, 30) })}
  />
  </>
);
registerRoot(Root);
