// Minimal entry: only the per-student reel (rest of the old Root depends on files purged from /tmp).
import React from "react";
import { Composition, registerRoot } from "remotion";
import { reelFrames } from "./reel/TestimonialReel";
import { StudentReel, StudentReelProps } from "./reel/StudentReel";
import { PineQuestReel, PineQuestReelProps } from "./reel/PineQuestReel";
import { EngIntro } from "./eng/EngIntro";
import { EngEpisode, EngEpisodeProps, engFrames } from "./eng/EngEpisode";
import timing from "./eng/intro_timing.json";

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
  <Composition id="EngIntro" component={EngIntro} fps={30} width={1080} height={1920} durationInFrames={timing.standaloneFrames} defaultProps={{ mark: undefined as string | undefined }} />
  <Composition
    id="EngEpisode"
    component={EngEpisode}
    fps={30}
    width={1080}
    height={1920}
    durationInFrames={600}
    defaultProps={{ presenter: "presenter.mp4", presenterSeconds: 10, cam: [], stacks: [], captions: [], chapters: [], outroSeconds: 3, nextLabel: "EP 02 · soon" } as EngEpisodeProps}
    calculateMetadata={({ props }) => ({ durationInFrames: engFrames(props as any) })}
  />
  </>
);
registerRoot(Root);
