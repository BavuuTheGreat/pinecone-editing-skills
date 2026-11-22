// Pinecone brand tokens, sampled from the Oct 2026 reels.
// Replace with the official brand-book values when available.
export const brand = {
  ink: "#0E1220",
  paper: "#F4F5F1",
  blue: "#2E55E0",
  blueSoft: "#7C9BFF",
  captionGreen: "#3DBE5A",
  muted: "#B9C2D6",
  font: "'Space Grotesk', 'Inter', Arial, sans-serif",
  mono: "'JetBrains Mono', 'Courier New', monospace",
} as const;

export const video = {
  fps: 30,
  width: 1080,
  height: 1920,
} as const;

export const seconds = (s: number): number => Math.round(s * video.fps);
