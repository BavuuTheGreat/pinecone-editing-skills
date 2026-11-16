import { loadFont as loadManrope } from "@remotion/google-fonts/Manrope";
import { loadFont as loadOswald } from "@remotion/google-fonts/Oswald";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";

// Manrope: rounded geometric sans closest to the reels' card/caption face (has Cyrillic).
// Oswald: condensed bold for the kinetic keyword titles (has Cyrillic).
export const ROUND = loadManrope("normal", { weights: ["500", "700", "800"], subsets: ["latin", "cyrillic", "cyrillic-ext"] })
  .fontFamily;
export const CONDENSED = loadOswald("normal", { weights: ["600", "700"], subsets: ["latin", "cyrillic", "cyrillic-ext"] })
  .fontFamily;
export const MONO = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] }).fontFamily;

export const GREEN = "#00D37F"; // pinecone.mn accent
export const CARD_BG = "#131313"; // sampled from DfEm-d-iLUz question card
export const MARK = "pinecone_mark.svg"; // pinecone.mn inline SVG
