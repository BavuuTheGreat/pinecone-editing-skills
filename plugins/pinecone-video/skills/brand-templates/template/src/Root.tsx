import React from "react";
import { Composition } from "remotion";
import { video, seconds } from "./brand";
import { Counter10K, Counter10KProps, OUTRO_SECONDS, STEP_SECONDS } from "./Counter10K";
import { ListCard, ListCardProps, HEADING_SECONDS, ITEM_SECONDS } from "./ListCard";
import { KineticTitle, KineticTitleProps } from "./KineticTitle";
import { WordCaptions, WordCaptionsProps, captionsDurationMs } from "./WordCaptions";
import { EndCard, EndCardProps } from "./EndCard";

const counterDefaults: Counter10KProps = {
  steps: [
    { year: "2017", count: 1 },
    { year: "2021", count: 26 },
    { year: "2025", count: 604 },
    { year: "2026", count: 1331 },
  ],
  goal: "BE 1 OF 10K",
  tagline: "Дэлхийд үнэлэгдэх нэг түмэн инженерийг бид бэлтгэнэ.",
};

const listDefaults: ListCardProps = {
  heading: "most in-demand tech jobs",
  items: [
    { rank: 5, title: "Cloud and Platform Engineer", note: "infrastructure" },
    { rank: 4, title: "Data Engineer" },
    { rank: 3, title: "Cybersecurity Specialist" },
    { rank: 2, title: "AI and Systems Engineering", note: "production" },
    { rank: 1, title: "???????" },
  ],
};

const titleDefaults: KineticTitleProps = {
  kicker: "THE WORLD IS WAITING FOR YOU.",
  title: "26",
  name: "hello_world",
  place: "CHOIJIN LAMA TEMPLE MUSEUM",
  date: "AUGUST 14TH",
};

const captionDefaults: WordCaptionsProps = {
  wordsPerLine: 3,
  words: [
    { text: "Сайн", startMs: 0, endMs: 400 },
    { text: "багшийг", startMs: 400, endMs: 900 },
    { text: "урт", startMs: 900, endMs: 1200 },
    { text: "хугацаанд", startMs: 1200, endMs: 1800 },
    { text: "ажиллуулах", startMs: 1800, endMs: 2500 },
  ],
};

const endCardDefaults: EndCardProps = {
  eyebrow: "Introducing",
  programme: "Morphosis",
  line: "Туршлагатай инженерүүдийг олон улсад гаргах хөтөлбөр",
  cta: "Бүртгүүлэх · Link in bio",
  partners: ["Google", "Microsoft", "Amazon", "Meta"],
};

const base = { fps: video.fps, width: video.width, height: video.height };

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="Counter10K"
      component={Counter10K}
      {...base}
      durationInFrames={seconds(STEP_SECONDS * 4 + OUTRO_SECONDS)}
      defaultProps={counterDefaults}
      calculateMetadata={({ props }) => ({
        durationInFrames: seconds(STEP_SECONDS * props.steps.length + OUTRO_SECONDS),
      })}
    />
    <Composition
      id="ListCard"
      component={ListCard}
      {...base}
      durationInFrames={seconds(HEADING_SECONDS + ITEM_SECONDS * 5)}
      defaultProps={listDefaults}
      calculateMetadata={({ props }) => ({
        durationInFrames: seconds(HEADING_SECONDS + ITEM_SECONDS * props.items.length),
      })}
    />
    <Composition
      id="KineticTitle"
      component={KineticTitle}
      {...base}
      durationInFrames={seconds(10)}
      defaultProps={titleDefaults}
    />
    <Composition
      id="WordCaptions"
      component={WordCaptions}
      {...base}
      durationInFrames={seconds(3)}
      defaultProps={captionDefaults}
      calculateMetadata={({ props }) => ({
        durationInFrames: Math.ceil((captionsDurationMs(props.words) / 1000) * video.fps),
      })}
    />
    <Composition
      id="EndCard"
      component={EndCard}
      {...base}
      durationInFrames={seconds(4)}
      defaultProps={endCardDefaults}
    />
  </>
);
