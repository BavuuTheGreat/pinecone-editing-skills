import React from "react";
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  useCurrentFrame,
} from "remotion";
import { brand, seconds } from "./brand";

// "N / 10K" milestone counter over photos, as in the "Be 1 of 10K" film.
export type CounterStep = {
  year: string;
  count: number;
  image?: string;
};

export type Counter10KProps = {
  steps: CounterStep[];
  goal: string;
  tagline: string;
};

export const STEP_SECONDS = 2.4;
export const OUTRO_SECONDS = 3;

const StepCard: React.FC<{ step: CounterStep; from: number }> = ({
  step,
  from,
}) => {
  const frame = useCurrentFrame();
  const dur = seconds(STEP_SECONDS);
  const value = Math.round(
    interpolate(frame, [0, dur * 0.5], [from, step.count], {
      extrapolateRight: "clamp",
    }),
  );
  const fade = interpolate(frame, [0, 6, dur - 6, dur], [0, 1, 1, 0]);
  return (
    <AbsoluteFill style={{ opacity: fade }}>
      {step.image ? (
        <Img
          src={step.image}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            filter: "grayscale(1) brightness(0.7)",
          }}
        />
      ) : null}
      <AbsoluteFill
        style={{ justifyContent: "center", alignItems: "center", gap: 12 }}
      >
        <div style={{ fontFamily: brand.font, fontSize: 44, color: brand.muted }}>
          {step.year}
        </div>
        <div
          style={{
            fontFamily: brand.font,
            fontSize: 120,
            fontWeight: 600,
            color: brand.paper,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {value.toLocaleString("en-US")}/10K
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Outro: React.FC<{ goal: string; tagline: string }> = ({
  goal,
  tagline,
}) => {
  const frame = useCurrentFrame();
  const rise = interpolate(frame, [0, 20], [40, 0], {
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        padding: 120,
        background: `radial-gradient(circle at 50% 120%, ${brand.blue} 0%, ${brand.ink} 60%)`,
      }}
    >
      <div style={{ transform: `translateY(${rise}px)`, display: "flex", gap: 48 }}>
        <div style={{ fontFamily: brand.font, fontSize: 40, color: brand.paper }}>
          {goal}
        </div>
        <div style={{ fontFamily: brand.font, fontSize: 40, color: brand.muted }}>
          {tagline}
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const Counter10K: React.FC<Counter10KProps> = ({
  steps,
  goal,
  tagline,
}) => {
  const stepFrames = seconds(STEP_SECONDS);
  return (
    <AbsoluteFill style={{ backgroundColor: brand.ink }}>
      {steps.map((step, i) => (
        <Sequence key={step.year + i} from={i * stepFrames} durationInFrames={stepFrames}>
          <StepCard step={step} from={i === 0 ? 0 : steps[i - 1].count} />
        </Sequence>
      ))}
      <Sequence from={steps.length * stepFrames}>
        <Outro goal={goal} tagline={tagline} />
      </Sequence>
    </AbsoluteFill>
  );
};
