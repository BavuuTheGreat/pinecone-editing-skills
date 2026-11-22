import { loadFont as loadSerif } from "@remotion/google-fonts/InstrumentSerif";
import { loadFont as loadSans } from "@remotion/google-fonts/Manrope";
import { loadFont as loadTinos } from "@remotion/google-fonts/Tinos";
import { loadFont as loadCormorant } from "@remotion/google-fonts/CormorantGaramond";
import { loadFont as loadSource } from "@remotion/google-fonts/SourceSerif4";
import { Easing } from "remotion";

// "Ghost Text" look for the series "Engineers matter more with AI".
// Idea: an engineer types; the AI's suggestion appears as grey ghost text; Tab accepts it and it turns solid.
// Everything on screen follows that: ghost -> solid captions, a blinking caret, one accent: Pinecone green.
export const SERIF = loadSerif("normal", { weights: ["400"], subsets: ["latin"] }).fontFamily;
export const SERIF_I = loadSerif("italic", { weights: ["400"], subsets: ["latin"] }).fontFamily;
export const SANS = loadSans("normal", { weights: ["500", "700", "800"], subsets: ["latin", "cyrillic", "cyrillic-ext"] }).fontFamily;
// Two faces only (review 2026-11-16, sixth round: "fonts aesthetic and simple"): Instrument Serif for the title, Manrope for every label.
// (The old JetBrains Mono labels are Manrope now; MONO stays as an alias so imports keep working.)
export const MONO = SANS;

// Captions follow the reviewer's reference reel: a Times-like serif (Tinos: Times New Roman metrics, has Cyrillic) in white on a tight black plate.
export const CAP_SERIF = loadTinos("normal", { weights: ["400", "700"], subsets: ["latin", "cyrillic", "cyrillic-ext"] }).fontFamily;

export const CAP_CORMORANT = loadCormorant("normal", { weights: ["500", "600", "700"], subsets: ["latin", "cyrillic", "cyrillic-ext"] }).fontFamily;
export const CAP_SOURCE = loadSource("normal", { weights: ["300", "400", "500"], subsets: ["latin", "cyrillic", "cyrillic-ext"] }).fontFamily;

export const INK = "#0C0D0B"; // warm black
export const CREAM = "#F2EBDC"; // from the office's oak and paper
export const ACCENT = "#00D37F"; // Pinecone green (the pinecone.mn accent, the green of <academy/> on the end card): the only accent (was desk-lamp amber until review 2026-11-17)
export const GHOST = "rgba(242,235,220,0.28)";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
export const SMOOTH = Easing.bezier(0.65, 0, 0.35, 1); // in-out, for moves
export const SETTLE = Easing.bezier(0.16, 1, 0.3, 1); // out, for things arriving
export const hash = (n: number) => {
  const s = Math.sin(n * 12.9898) * 43758.5453;
  return s - Math.floor(s);
};
export const FACE_Y = 0.47; // presenter's face height in the 9:16 frame (0-1), used for card crops
