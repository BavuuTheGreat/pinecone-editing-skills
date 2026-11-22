import React from "react";
import { AbsoluteFill, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// Captions styled like dash.pinecone.mn/reel: GIP SemiBold, white, no box, hard cut on/off, word gap 4%.
export type Caption = { from: number; to: number; text: string; dy?: number };
export type CaptionStyle = { size: number; gap: number; baseline: number; cx: number; thin?: boolean; shadow?: string }; // thin default true (bootcamp)
const FONT = "GIPCap";
const face = `@font-face{font-family:${FONT};src:url(${staticFile("GIP-Regular.woff2")});font-weight:400}`;

export const Captions: React.FC<{ captions: Caption[]; style: CaptionStyle }> = ({ captions, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cap = captions.find((c) => t >= c.from - 1e-6 && t < c.to - 1e-6);
  return (
    <AbsoluteFill>
      <style>{face}</style>
      <svg width="0" height="0" style={{ position: "absolute" }}><filter id="thin"><feMorphology operator="erode" radius="0.7" /></filter></svg>
      {cap ? (
        <div
          style={{
            position: "absolute", left: style.cx, top: style.baseline + (cap.dy ?? 0), transform: "translate(-50%, -100%)",
            whiteSpace: "nowrap", display: "flex", gap: style.gap, fontFamily: FONT, fontWeight: 600,
            fontSize: style.size, lineHeight: 1, color: "#fff", filter: style.thin === false ? (style.shadow ?? "drop-shadow(0 1px 2px rgba(0,0,0,0.35))") : "url(#thin)",
          }}
        >
          {cap.text.split(" ").map((w, i) => <span key={i}>{w}</span>)}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
