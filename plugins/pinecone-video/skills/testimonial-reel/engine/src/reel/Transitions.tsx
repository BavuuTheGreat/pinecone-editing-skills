import React from "react";
import { Easing, interpolate, staticFile } from "remotion";
import { MARK } from "./fonts";

// v8 transitions, all inside each item's own frames (no overlap, so audio timing is untouched):
//   card  — shot blurs + dims into a question card, and resolves from blur out of one
//   bloom — between two students: soft brighten + blur out, settle back in
//   (jump cuts inside one answer keep the light leak, see LightLeak.tsx)
export type Edge = "card" | "bloom" | "none";

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const OUT = Easing.bezier(0.5, 0, 0.75, 0); // accelerate into the cut
const IN = Easing.bezier(0.25, 1, 0.5, 1); // decelerate out of the cut
export const EDGE_FRAMES = { card: { out: 12, in: 16 }, bloom: { out: 9, in: 14 }, none: { out: 0, in: 0 } };

type Look = { blur: number; bright: number; scale: number };
const LOOK: Record<Exclude<Edge, "none">, Look> = {
  card: { blur: 22, bright: 0.2, scale: 1.07 },
  bloom: { blur: 16, bright: 1.55, scale: 1.06 },
};

// frame = frame inside the clip, len = clip length in frames.
export const clipEdgeStyle = (frame: number, len: number, inEdge: Edge, outEdge: Edge): React.CSSProperties => {
  let k = 0;
  let look: Look | null = null;
  if (inEdge !== "none" && frame < EDGE_FRAMES[inEdge].in) {
    look = LOOK[inEdge];
    k = interpolate(frame, [0, EDGE_FRAMES[inEdge].in], [1, 0], { ...clamp, easing: IN });
  }
  const left = len - frame;
  if (outEdge !== "none" && left <= EDGE_FRAMES[outEdge].out) {
    const o = interpolate(frame, [len - EDGE_FRAMES[outEdge].out, len - 1], [0, 1], { ...clamp, easing: OUT });
    if (o > k) {
      k = o;
      look = LOOK[outEdge];
    }
  }
  if (!look || k <= 0) return {};
  return {
    filter: `blur(${look.blur * k}px) brightness(${1 + (look.bright - 1) * k})`,
    transform: `scale(${1 + (look.scale - 1) * k})`,
  };
};

// Card fade: rises from black at the start, text softens away at the end.
export const cardEdge = (frame: number, len: number): { bg: number; text: React.CSSProperties } => ({
  bg: interpolate(frame, [0, 8], [0, 1], { ...clamp, easing: IN }),
  text: {
    opacity: interpolate(frame, [len - 9, len - 1], [1, 0], { ...clamp, easing: OUT }),
    filter: `blur(${interpolate(frame, [len - 9, len - 1], [0, 10], { ...clamp, easing: OUT })}px)`,
  },
});

// Logo as in the reference reels: warm tan, translucent, soft-edged (sampled ~rgb(157,129,98) over the set).
export const SoftLogo: React.FC<{ opacity?: number }> = ({ opacity = 0.72 }) => {
  const url = `url(${staticFile(MARK)})`;
  return (
    <div
      style={{
        position: "absolute",
        top: 76,
        left: 540 - 27,
        width: 54,
        height: 47,
        backgroundColor: "#C4A27A",
        WebkitMaskImage: url,
        maskImage: url,
        WebkitMaskSize: "contain",
        maskSize: "contain",
        WebkitMaskRepeat: "no-repeat",
        maskRepeat: "no-repeat",
        opacity,
        filter: "blur(1.8px)",
      }}
    />
  );
};
