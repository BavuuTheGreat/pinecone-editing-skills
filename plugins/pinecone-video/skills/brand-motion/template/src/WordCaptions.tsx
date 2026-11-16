import React from "react";
import { AbsoluteFill, OffthreadVideo, useCurrentFrame, useVideoConfig } from "remotion";
import { brand } from "./brand";

// Word-by-word captions with the green active-word pill used on every podcast clip.
// `words` comes from podcast-clipper's captions.json (Whisper word timestamps).
export type CaptionWord = {
  text: string;
  startMs: number;
  endMs: number;
};

export type WordCaptionsProps = {
  words: CaptionWord[];
  videoSrc?: string;
  wordsPerLine: number;
};

const chunk = (words: CaptionWord[], size: number): CaptionWord[][] => {
  const lines: CaptionWord[][] = [];
  for (let i = 0; i < words.length; i += size) {
    lines.push(words.slice(i, i + size));
  }
  return lines;
};

export const captionsDurationMs = (words: CaptionWord[]): number =>
  words.length === 0 ? 1000 : words[words.length - 1].endMs + 500;

export const WordCaptions: React.FC<WordCaptionsProps> = ({
  words,
  videoSrc,
  wordsPerLine,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const nowMs = (frame / fps) * 1000;
  const lines = chunk(words, Math.max(1, wordsPerLine));
  const line = lines.find(
    (l) => nowMs >= l[0].startMs && nowMs <= l[l.length - 1].endMs + 150,
  );
  return (
    <AbsoluteFill style={{ backgroundColor: brand.ink }}>
      {videoSrc ? (
        <OffthreadVideo src={videoSrc} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : null}
      <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 640 }}>
        {line ? (
          <div style={{ display: "flex", gap: 14, flexWrap: "wrap", justifyContent: "center", maxWidth: 900 }}>
            {line.map((w, i) => {
              const active = nowMs >= w.startMs && nowMs < w.endMs;
              return (
                <span
                  key={`${w.startMs}-${i}`}
                  style={{
                    fontFamily: brand.font,
                    fontSize: 58,
                    fontWeight: 600,
                    color: brand.paper,
                    padding: "4px 14px",
                    borderRadius: 12,
                    background: active ? brand.captionGreen : "transparent",
                    textShadow: active ? "none" : "0 2px 8px rgba(0,0,0,0.6)",
                  }}
                >
                  {w.text}
                </span>
              );
            })}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
