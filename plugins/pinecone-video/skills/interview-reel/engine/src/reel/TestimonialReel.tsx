import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { KineticWords, KineticWordsProps } from "./KineticWords";
import { LightLeak } from "./LightLeak";
import { QuestionTypeCard } from "./QuestionTypeCard";
import { OutroBackdrop, OutroLockup, outroClipStyle } from "./Outro";
import { SoftLogo } from "./Transitions";
import { ChevronLogo, PQCard, PQEdge, PQEdgeKind, ZoomKey } from "./PineQuestLook";

// Seated-testimonial reel, rebuilt from DfEm-d-iLUz: hard cuts, typed question cards,
// kinetic keyword titles; v5 outro; soft reference-style logo. Cuts are hard, as in the Pinecone reels
// (light leak only between intro speakers).
export type ReelItem =
  | { kind: "clip"; src: string; seconds: number; answer?: string; student?: string; leakBefore?: boolean; bare?: boolean; zoom?: ZoomKey[]; hook?: boolean; join?: boolean }  // bare: no corner logo (supplied end card); zoom: pinequest punch-ins
  | { kind: "question"; text: string; seconds: number; sfx?: string };

export type ReelTitle = KineticWordsProps & { item: number; from: number; seconds: number };

export type TestimonialReelProps = {
  items: ReelItem[];
  titles: ReelTitle[];
  shrinkSeconds: number;
  holdSeconds: number;
  builtInOutro?: boolean; // false: no shrink/lockup; the last item (e.g. a supplied end card) plays as is
  look?: "bootcamp" | "pinequest"; // pinequest: grey chevron logo + PineQuest S5 grid card (default bootcamp, approved)
  cardTyping?: boolean; // pinequest: type the question letter by letter (default false: the whole question at once)
  hookMotion?: "calm" | "punchy"; // pinequest: calm (default) = no impact zoom, hard cut into answer 1; punchy = impact + whip
};

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const LEAK_HALF = 7; // 14-frame flash centred on the cut

export const reelFrames = (p: TestimonialReelProps, fps: number): number =>
  p.items.reduce((s, it) => s + Math.round(it.seconds * fps), 0) + Math.round(p.holdSeconds * fps);

type ClipProps = { src: string; outroFrom: number | null; outroLen: number; bare?: boolean; pq?: boolean };

const Clip: React.FC<ClipProps> = ({ src, outroFrom, outroLen, bare, pq }) => {
  const frame = useCurrentFrame();
  const t = outroFrom === null ? -1 : frame - outroFrom;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={outroClipStyle(t, outroLen)}>
        <OffthreadVideo src={staticFile(src)} />
      </AbsoluteFill>
      {bare ? null : (
        <AbsoluteFill style={{ opacity: t < 0 ? 1 : interpolate(t, [0, 8], [1, 0], clamp) }}>
          {pq ? <ChevronLogo /> : <SoftLogo />}
        </AbsoluteFill>
      )}
    </AbsoluteFill>
  );
};

export const TestimonialReel: React.FC<TestimonialReelProps> = ({ items, titles, shrinkSeconds, holdSeconds, builtInOutro = true, look = "bootcamp", cardTyping = false, hookMotion = "calm" }) => {
  const pq = look === "pinequest";
  const { fps } = useVideoConfig();
  const starts: number[] = [];
  let acc = 0;
  for (const it of items) {
    starts.push(acc);
    acc += Math.round(it.seconds * fps);
  }
  const last = items.length - 1;
  const lastLen = Math.round(items[last].seconds * fps);
  const shrink = Math.round(shrinkSeconds * fps);
  const outroStart = acc - shrink;
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      {builtInOutro ? (
        <Sequence from={outroStart} durationInFrames={shrink + Math.round(holdSeconds * fps)} name="outro backdrop">
          <OutroBackdrop />
        </Sequence>
      ) : null}
      {items.map((it, i) => (
        <Sequence key={i} from={starts[i]} durationInFrames={Math.round(it.seconds * fps)} name={`${it.kind} ${i + 1}`}>
          {(() => {
            const body =
              it.kind === "clip" ? (
                <Clip src={it.src} outroFrom={builtInOutro && i === last ? lastLen - shrink : null} outroLen={shrink} bare={it.bare} pq={pq} />
              ) : (
                <>
                  {pq ? <PQCard question={it.text} typing={cardTyping} /> : <QuestionTypeCard question={it.text} />}
                  {it.sfx ? <Audio src={staticFile(it.sfx)} /> : null}
                </>
              );
            if (!pq) return body;
            // boundary j (between item j-1 and j): glitch into the end card, calm fade at any question card, whip clip->clip
            const edge = (j: number): PQEdgeKind =>
              j === last ? "glitch" : items[j].kind === "question" || items[j - 1].kind === "question" ? "fade"
                : (items[j] as { join?: boolean }).join ? "none" : "whip"; // join: jump cut inside one answer (pause removed)
            const isHook = (j: number) => { const x = items[j]; return x.kind === "clip" && !!x.hook; };
            const calmHook = hookMotion !== "punchy";
            const inEdge: PQEdgeKind = i === 0 ? (calmHook ? "none" : "impact") : calmHook && i === 1 && isHook(0) && it.kind === "clip" ? "none" : edge(i);
            const outEdge: PQEdgeKind = i === last ? "none" : calmHook && i === 0 && isHook(0) && items[1].kind === "clip" ? "none" : edge(i + 1);
            return (
              <PQEdge len={Math.round(it.seconds * fps)} inEdge={inEdge} outEdge={outEdge} zoom={it.kind === "clip" ? it.zoom : undefined}
                drift={it.kind === "clip" && !it.bare ? items.slice(0, i).filter((x) => x.kind === "clip" && !(x as { join?: boolean }).join).length : undefined}>
                {body}
              </PQEdge>
            );
          })()}
        </Sequence>
      ))}
      {titles.map((t, i) => (
        <Sequence
          key={`t${i}`}
          from={starts[t.item] + Math.round(t.from * fps)}
          durationInFrames={Math.round(t.seconds * fps)}
          name={`title ${t.words.join(" ")}`}
        >
          <KineticWords kicker={t.kicker} words={t.words} wordSeconds={t.wordSeconds} top={t.top} />
        </Sequence>
      ))}
      {items.map((it, i) =>
        it.kind === "clip" && it.leakBefore ? (
          <Sequence key={`leak${i}`} from={starts[i] - LEAK_HALF} durationInFrames={LEAK_HALF * 2} name={`leak ${i + 1}`}>
            <LightLeak />
          </Sequence>
        ) : null,
      )}
      {builtInOutro ? (
        <Sequence from={outroStart} durationInFrames={shrink + Math.round(holdSeconds * fps)} name="outro">
          <OutroLockup enter={shrink} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
