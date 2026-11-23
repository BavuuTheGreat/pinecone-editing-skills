import React from "react";
import { AbsoluteFill, Freeze, Img, interpolate, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import T from "./intro_timing.json";
import { IntroScene, LEFT, TitleBlock, Lockup, Mark } from "./EngIntro";
import { Leak } from "./Leak";
import { MapCard, MapCues } from "./MapCard";
import { ChapterRail, CurtainOut, curtainIncoming, DualScramble } from "./anm";
import { ACCENT, CAP_CORMORANT, CAP_SERIF, CAP_SOURCE, clamp, CREAM, FACE_Y, GHOST, INK, MONO, SANS, SERIF, SETTLE, SMOOTH } from "./tokens";

// Episode of "Engineers matter more with AI": intro -> presenter (one continuous, silence-trimmed take with soft dissolves)
// -> framed screen inserts the presenter slides aside for -> sign-off with an un-accepted ghost suggestion -> optional brand end card.
// Presenter-time = seconds in presenter.mp4; the episode starts that clip at T.presenterStart.
// A stack is one window next to the presenter. Either one video (src) or several layers one after another (a map card, then
// scenes of a screen recording cut to what is being said); layers hand over with a 6-frame cross-dissolve.
export type Layer = { type: "map" | "video"; from: number; to: number; src?: string; label?: string; cues?: MapCues };
export type Stack = { from: number; to: number; kind: "wide" | "tall"; src?: string; layers?: Layer[]; label?: string; enter?: "rise" | "slide" | "zoom" };
export type Fx = { t: number; kind: "blur" | "lift" | "shift"; dir: number };
export type CamKey = { t: number; s: number; x: number }; // presenter-time seconds, scale, pan in px
export type Cap = { from: number; to: number; text: string };
export type Brand = { name: "claude" | "higgsfield" | "text"; label?: string; plain?: boolean; // plain: just the words, no colour wash over the picture
  logo?: string | null; from: number; to: number; color: string; word: string };
export type Chapter = { from: number; to: number; num: string; label: string };
export type EngEpisodeProps = {
  presenter: string;
  presenterSeconds: number;
  fx?: Fx[]; // soft move over a cut: blur (focus breathe), lift, shift
  cam: CamKey[]; // subtle camera path (hold / slow push / pull / drift); continuous across takes
  stacks: Stack[];
  captions: Cap[];
  chapters: Chapter[];
  mark?: string;
  captionFace?: "source" | "cormorant" | "tinos"; // serif of the plate caption (default source: slim Source Serif 4)
  captionStyle?: "plate" | "gip"; // plate (default): white serif on a black plate like the reference reel; gip: the interview-reel caption
  captionFont?: string; // brand-pack GIP woff2 in public/ (testimonial caption face); Manrope when absent
  captionY?: number; // chip bottom edge, default 1620
  leaks?: { t: number; dir: number; tone?: "pink" | "green" }[]; // light-leak flash (the testimonial reels' colourful smooth transition) at these presenter-times
  closerFrames?: number; // length of the closer (the job sets it so the whole video lands on its target length)
  signature?: string; // name + role under the closer title
  closerEp?: string; // small episode label under the closer title
  brands?: Brand[]; // brand moments: colour wash + logo + tinted caption word while a company is named (presenter-seconds)
  nameTag?: { name: string; role: string; from: number; to: number; episode?: string }; // lower-third at the start: presenter-seconds
  noIntro?: boolean; // the talk starts on frame 0 (30 s cut: face and hook right away)
  closer?: boolean; // the Ghost Text title plays at the END (after a pink leak) instead of a sign-off
  moveFrames?: number;
  curtainFrames?: number;
  look?: "split" | "cards"; // split (default, review 2026-11-17): the demo sits edge-to-edge above the presenter like the reference reel; cards = the earlier rounded-card layout
  chapterStyle?: "pill" | "rail"; // chapter label: the pill (default) or a slim process rail
  meta?: boolean; // EP tag + pinecone wordmark/mark in the intro and sign-off (default false: removed in review 2026-11-17)
  outroSeconds: number;
  nextLabel: string; // ghost suggestion in the sign-off, e.g. "EP 02 · soon"
  endCard?: string; // brand end card in public/, dissolves in after the sign-off
  endCardSeconds?: number;
};

const FPS = 30;
const DISSOLVE = 8; // frames the push-in takes after a cut
const OVERLAP = 12; // frames the end card dissolves over the sign-off
export const engFrames = (p: EngEpisodeProps): number =>
  (p.noIntro ? 0 : T.presenterStart) + Math.round(p.presenterSeconds * FPS) + (p.closer ? p.closerFrames ?? CLOSER_F : Math.round(p.outroSeconds * FPS)) + (p.endCard ? Math.round((p.endCardSeconds ?? 0) * FPS) - OVERLAP : 0);

type Rect = { x: number; y: number; w: number; h: number; r: number };
const FULL: Rect = { x: 0, y: 0, w: 1080, h: 1920, r: 0 };
const PRES: Record<string, Rect> = {
  wide: { x: 36, y: 990, w: 1008, h: 700, r: 30 },
  tall: { x: 558, y: 310, w: 484, h: 860, r: 30 },
};
const WIN: Record<string, Rect> = {
  wide: { x: 36, y: 310, w: 1008, h: 537, r: 24 },
  tall: { x: 38, y: 310, w: 484, h: 860, r: 30 },
};
// Captions sit at the bottom of the screen in every layout (review 2026-11-16, third round); `captionY` in the props moves them.
const CHIP_Y: Record<string, number> = { full: 1620, wide: 1620, tall: 1620 };
const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
const lerpRect = (a: Rect, b: Rect, p: number): Rect => ({ x: lerp(a.x, b.x, p), y: lerp(a.y, b.y, p), w: lerp(a.w, b.w, p), h: lerp(a.h, b.h, p), r: lerp(a.r, b.r, p) });
let MOVE = 20; // frames for a stack to open or close (job stack_move_frames; the 30 s cut uses 10)
const SPLIT_H = 575; // height of the edge-to-edge demo region (1080 x 575 = the 1.877 aspect of the screen recordings)
let CURTAIN = 21; // frames of the curtain between two layers of a window (0.7 s; job curtain_frames, the 30 s cut uses 12)
const CLOSER_F = 150; // the Ghost Text title as the closer: 5.0 s (typed, accepted, then about 1.2 s of hold)

// 0..1: how far presenter-frame pf is inside a stack (eased in and out), and which stack
const stackState = (pf: number, stacks: Stack[]): { p: number; s?: Stack } => {
  for (const s of stacks) {
    const a = Math.round(s.from * FPS), b = Math.round(s.to * FPS);
    if (pf >= a - 1 && pf <= b + MOVE) {
      const pin = interpolate(pf, [a, a + MOVE], [0, 1], { ...clamp, easing: SMOOTH });
      const pout = interpolate(pf, [b, b + MOVE], [1, 0], { ...clamp, easing: SMOOTH });
      return { p: Math.min(pin, pout), s };
    }
  }
  return { p: 0 };
};

const Presenter: React.FC<{ P: EngEpisodeProps; pf: number; f: number; E: number }> = ({ P, pf, f, E }) => {
  const { p, s } = stackState(pf, P.stacks);
  const split = P.look !== "cards";
  const rect = split ? { x: 0, y: SPLIT_H * p, w: 1080, h: 1920 - SPLIT_H * p, r: 0 } : s ? lerpRect(FULL, PRES[s.kind], p) : FULL;
  const sc = Math.max(rect.w / 1080, rect.h / 1920);
  const tx = Math.min(0, Math.max(rect.w - 1080 * sc, rect.w / 2 - 540 * sc));
  const fy = FACE_Y + 0.06 * p; // in a card the crop sits a little lower: he leans toward the laptop
  // split: the face sits at 36 % of the region under the demo (head and chest, as in the reference); cards: centred
  const ty = split ? Math.min(0, Math.max(rect.h - 1920, 0.36 * rect.h - FACE_Y * 1920)) : Math.min(0, Math.max(rect.h - 1920 * sc, rect.h / 2 - fy * 1920 * sc));
  // subtle camera: eased between keyframes, held between moves, gone while a card is open so cards stay put
  let push = 1, panx = 0;
  const t = pf / FPS;
  const ks = P.cam;
  for (let i = 0; i < ks.length - 1; i++) {
    if (t >= ks[i].t && t <= ks[i + 1].t) {
      const e = interpolate(t, [ks[i].t, ks[i + 1].t], [0, 1], { ...clamp, easing: SMOOTH });
      push = ks[i].s + (ks[i + 1].s - ks[i].s) * e;
      panx = ks[i].x + (ks[i + 1].x - ks[i].x) * e;
    } else if (t > ks[i + 1].t) {
      push = ks[i + 1].s;
      panx = ks[i + 1].x;
    }
  }
  push = 1 + (push - 1) * (1 - p);
  panx *= 1 - p;
  // soft move over a cut: a bell curve (14 frames) centred on it; different kinds on different cuts
  let blur = 0, lift = 0, shift = 0;
  for (const x of P.fx ?? []) {
    const u = (pf - x.t * FPS) / 7;
    const bell = Math.max(0, 1 - Math.pow(Math.abs(u), 1.6)) * (1 - p);
    if (bell <= 0) continue;
    if (x.kind === "blur") { blur = Math.max(blur, 7 * bell); push *= 1 + 0.03 * bell; } // the scale bump keeps blurred edges out of frame
    if (x.kind === "lift") { lift = -20 * bell; push *= 1 + 0.02 * bell; }
    if (x.kind === "shift") { shift = 12 * bell * x.dir; push *= 1 + 0.025 * bell; }
  }
  // opening onto the first shot, and closing into the sign-off
  const d = P.closer ? 0 : interpolate(f, [E - 28, E - 4], [0, 1], { ...clamp, easing: SMOOTH }); // sign-off: the shot softens and dims into it
  const settle = 1; // the first shot takes over under the light leak: no window, no settle (review 2026-11-16, sixth round)
  const veil = d > 0 ? { filter: `blur(${(d * 24).toFixed(1)}px) brightness(${1 - 0.55 * d})` } : {};
  return (
    <AbsoluteFill style={{ ...veil }}>
      {p > 0 && !split ? (
        // while a card is open the room stays behind it, blurred and dimmed: no black screen between sections
        <div style={{ position: "absolute", inset: 0, opacity: Math.min(1, p * 2), overflow: "hidden" }}>
          <OffthreadVideo src={staticFile(P.presenter)} style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1920, transform: "scale(1.25)", filter: "blur(36px) brightness(0.42)" }} />
        </div>
      ) : null}
      <div style={{ position: "absolute", left: rect.x, top: rect.y, width: rect.w, height: rect.h, borderRadius: rect.r, overflow: "hidden", background: INK,
        boxShadow: p > 0 && !split ? `0 28px 70px rgba(0,0,0,${0.5 * p})` : undefined }}>
        <div style={{ position: "absolute", inset: 0, transform: `translate(${panx + shift}px, ${lift}px) scale(${push * settle})`, transformOrigin: "50% 45%", filter: blur > 0.1 ? `blur(${blur.toFixed(1)}px)` : undefined }}>
          <OffthreadVideo src={staticFile(P.presenter)} style={{ position: "absolute", left: 0, top: 0, width: 1080, height: 1920, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${sc})` }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const P_SPLIT = { current: true }; // set from the props at the top of EngEpisode (a module flag keeps Window's signature small)
const Window: React.FC<{ s: Stack; pf: number; startF: number }> = ({ s, pf, startF }) => {
  const a = Math.round(s.from * FPS), b = Math.round(s.to * FPS);
  // split look: exactly the same progress as the presenter (stackState) so the region and the presenter never leave a gap between them
  const pin = P_SPLIT.current ? interpolate(pf, [a, a + MOVE], [0, 1], { ...clamp, easing: SMOOTH }) : interpolate(pf, [a + 4, a + 4 + MOVE], [0, 1], { ...clamp, easing: SETTLE });
  const pout = P_SPLIT.current ? interpolate(pf, [b, b + MOVE], [1, 0], { ...clamp, easing: SMOOTH }) : interpolate(pf, [b, b + MOVE - 4], [1, 0], { ...clamp, easing: SMOOTH });
  const p = Math.min(pin, pout);
  if (p <= 0) return null;
  if (P_SPLIT.current) {
    // split look: the demo region grows from the top edge, full width, no card, no radius, no shadow
    const SW = 1080, SH = SPLIT_H;
    const lab = (s.layers ? [...s.layers].reverse().find((l) => pf >= Math.round(l.from * FPS))?.label : s.label) ?? undefined;
    return (
      <>
        <div style={{ position: "absolute", left: 0, top: 0, width: SW, height: SH * p, overflow: "hidden", background: "#0B0B0B" }}>
          <div style={{ position: "absolute", left: 0, top: 0, width: SW, height: SH }}>
            {s.layers ? [...s.layers.keys()].reverse().map((i) => {
              const l = s.layers![i], nxt = s.layers![i + 1];
              const lf = Math.round(l.from * FPS), lt = Math.round(l.to * FPS);
              const pOut = nxt ? Math.min(1, Math.max(0, (pf - Math.round(nxt.from * FPS)) / CURTAIN)) : 0;
              const pIn = i > 0 ? Math.min(1, Math.max(0, (pf - lf) / CURTAIN)) : 1;
              if (pf < lf - 1 || (nxt ? pOut >= 1 : pf > lt + MOVE + 2)) return null;
              const inc = curtainIncoming(pIn);
              return (
                <CurtainOut key={i} p={pOut} w={SW} h={SH}>
                  <div style={{ position: "absolute", inset: 0, transform: inc.scale !== 1 ? `scale(${inc.scale})` : undefined }}>
                    {l.type === "map" ? (
                      <div style={{ width: 1008, height: 537, transform: `scale(${SW / 1008})`, transformOrigin: "0 0" }}>
                        <MapCard t={(pf - lf) / FPS} cues={l.cues ?? { arrive: 5, last50: 7, solved: 11 }} />
                      </div>
                    ) : (
                      <Sequence from={startF + lf} durationInFrames={Math.max(1, lt - lf + CURTAIN + 10)}>
                        <OffthreadVideo src={staticFile(l.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 38%" }} />
                      </Sequence>
                    )}
                  </div>
                  {inc.shade > 0.005 ? <div style={{ position: "absolute", inset: 0, background: "#000", opacity: inc.shade }} /> : null}
                </CurtainOut>
              );
            }) : (
              <>
                <Sequence from={startF + a} durationInFrames={15}>
                  <Freeze frame={0}><OffthreadVideo src={staticFile(s.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 38%" }} /></Freeze>
                </Sequence>
                <Sequence from={startF + a + 15}>
                  <OffthreadVideo src={staticFile(s.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover", objectPosition: "50% 38%" }} />
                </Sequence>
              </>
            )}
          </div>
        </div>
        {lab && p > 0.6 ? (
          <div style={{ position: "absolute", left: 24, top: SH * p - 24 - 52, padding: "8px 16px", borderRadius: 10, background: "#000", color: "#fff", fontFamily: SANS, fontWeight: 600, fontSize: 24, opacity: Math.min(1, (p - 0.6) * 4) }}>{lab}</div>
        ) : null}
      </>
    );
  }
  const r = WIN[s.kind];
  const enter = s.enter ?? "rise";
  const active = s.layers ? [...s.layers].reverse().find((l) => pf >= Math.round(l.from * FPS)) : undefined;
  const label = active ? active.label : s.label;
  const motion = enter === "slide" ? `translateX(${-(1 - p) * 150}px)` : enter === "zoom" ? `scale(${0.9 + 0.1 * p})` : `translateY(${(1 - p) * 70}px) scale(${0.96 + 0.04 * p})`;
  return (
    <>
      <div style={{ position: "absolute", left: r.x, top: r.y, width: r.w, height: r.h, borderRadius: r.r, overflow: "hidden", opacity: Math.min(1, p * 3), background: INK,
        transform: motion, filter: enter === "zoom" && p < 1 ? `blur(${(1 - p) * 10}px)` : undefined,
        boxShadow: "0 28px 70px rgba(0,0,0,0.55)", border: "1.5px solid rgba(242,235,220,0.14)" }}>
        {s.layers ? [...s.layers.keys()].reverse().map((i) => {
          // layers hand over with the curtain (curtain-slider motion): the earlier layer is on top and its 12 columns wipe away,
          // the next one settles in beneath. Later layers are drawn first so earlier ones sit above them.
          const l = s.layers![i], nxt = s.layers![i + 1];
          const lf = Math.round(l.from * FPS), lt = Math.round(l.to * FPS);
          const pOut = nxt ? Math.min(1, Math.max(0, (pf - Math.round(nxt.from * FPS)) / CURTAIN)) : 0;
          const pIn = i > 0 ? Math.min(1, Math.max(0, (pf - lf) / CURTAIN)) : 1;
          if (pf < lf - 1 || (nxt ? pOut >= 1 : pf > lt + MOVE + 2)) return null;
          const inc = curtainIncoming(pIn);
          return (
            <CurtainOut key={i} p={pOut} w={r.w} h={r.h}>
              <div style={{ position: "absolute", inset: 0, transform: inc.scale !== 1 ? `scale(${inc.scale})` : undefined }}>
                {l.type === "map" ? (
                  <MapCard t={(pf - lf) / FPS} cues={l.cues ?? { arrive: 5, last50: 7, solved: 11 }} />
                ) : (
                  <Sequence from={startF + lf} durationInFrames={Math.max(1, lt - lf + CURTAIN + 10)}>
                    <OffthreadVideo src={staticFile(l.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  </Sequence>
                )}
              </div>
              {inc.shade > 0.005 ? <div style={{ position: "absolute", inset: 0, background: "#000", opacity: inc.shade }} /> : null}
            </CurtainOut>
          );
        }) : (
          <>
            {/* the footage starts as the window settles and plays for the whole time it is up (it is retimed to fit) */}
            <Sequence from={startF + a} durationInFrames={15}>
              <Freeze frame={0}>
                <OffthreadVideo src={staticFile(s.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </Freeze>
            </Sequence>
            <Sequence from={startF + a + 15}>
              <OffthreadVideo src={staticFile(s.src!)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </Sequence>
          </>
        )}
      </div>
      {label ? (
        <div style={{ position: "absolute", left: r.x + 6, top: r.y + r.h + 18, opacity: Math.min(1, p * 3) * 0.9, fontFamily: SANS, fontWeight: 700, fontSize: label.startsWith("@") ? 26 : 21, letterSpacing: label.startsWith("@") ? 0.5 : 3, color: CREAM }}>{label.startsWith("@") ? label : label.toUpperCase()}</div>
      ) : null}
    </>
  );
};

// Captions (review 2026-11-17: "a font change and a black background, like the reference video"): white Times-like serif (Tinos) on a tight
// square-cornered black plate, 2-4 words, hard cut on and off, lower third. `captionStyle: "gip"` brings back the plain interview-reel
// caption (GIP, white, no box, soft shadow; needs the brand-pack font).
const CaptionText: React.FC<{ P: EngEpisodeProps; pf: number }> = ({ P, pf }) => {
  const t = pf / FPS;
  const cap = P.captions.find((c) => t >= c.from - 1e-6 && t < c.to - 1e-6);
  if (!cap) return null;
  if (P.captionStyle === "gip") {
    const face = P.captionFont ? `@font-face{font-family:GIPCap;src:url(${staticFile(P.captionFont)});font-weight:400}` : "";
    return (
      <div style={{ position: "absolute", left: 0, right: 0, top: P.captionY ?? 1620, display: "flex", justifyContent: "center", transform: "translateY(-100%)" }}>
        <style>{face}</style>
        <div style={{ display: "flex", gap: 13, whiteSpace: "nowrap", fontFamily: P.captionFont ? "GIPCap" : SANS, fontWeight: 600, fontSize: 47, lineHeight: 1, color: "#fff",
          filter: "drop-shadow(0 2px 3px rgba(0,0,0,0.85)) drop-shadow(0 0 10px rgba(0,0,0,0.6))" }}>
          {cap.text.split(" ").map((w, i) => { const b = (P.brands ?? []).find((x) => x.word && w.toLowerCase().startsWith(x.word.toLowerCase()) && t >= x.from - 0.05); return <span key={i} style={b ? { color: b.color } : undefined}>{w}</span>; })}
        </div>
      </div>
    );
  }
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: P.captionY ?? 1620, display: "flex", justifyContent: "center", transform: "translateY(-100%)" }}>
      {(() => {
        const f = P.captionFace ?? "source";
        const spec = f === "cormorant" ? { fam: CAP_CORMORANT, w: 600, size: 56, ls: 0.4 } : f === "tinos" ? { fam: CAP_SERIF, w: 400, size: 50, ls: 0.2 } : { fam: CAP_SOURCE, w: 400, size: 40, ls: 0.3 };
        return <div style={{ padding: "5px 13px 7px", background: "#000", borderRadius: 3, color: "#fff", fontFamily: spec.fam, fontWeight: spec.w, fontSize: spec.size, lineHeight: 1.12, letterSpacing: spec.ls, whiteSpace: "nowrap" }}>{cap.text}</div>;
      })()}
    </div>
  );
};


// Brand moments (review 2026-11-17): when he names Claude / Higgsfield the frame takes that company's colour - a soft colour wash rising
// from the bottom, the logo eased in above his head, and the named word in the captions tinted. Claude = orange, Higgsfield = green.
const BrandMoments: React.FC<{ brands?: Brand[]; pf: number }> = ({ brands, pf }) => {
  const t = pf / FPS;
  return (
    <>
      {(brands ?? []).map((b, i) => {
        const a = b.from - 0.05, z = b.to + (b.name === "higgsfield" ? 0.3 : 0.02);
        if (t < a || t > z + 0.31) return null;
        const inP = interpolate(t, [a, a + 0.28], [0, 1], { ...clamp, easing: SETTLE });
        const outP = interpolate(t, [z, z + (b.name === "higgsfield" ? 0.3 : 0.12)], [1, 0], { ...clamp, easing: SMOOTH });
        const o = Math.min(inP, outP);
        const claude = b.name !== "higgsfield"; // claude + text callouts use the serif wordmark look
        return (
          <React.Fragment key={i}>
            {b.plain ? null : <AbsoluteFill style={{ opacity: o * (b.name === "text" ? 0.22 : 0.42), mixBlendMode: "normal", pointerEvents: "none",
              background: `radial-gradient(ellipse 110% 60% at 50% 100%, ${b.color} 0%, rgba(0,0,0,0) 70%)` }} />}
            <AbsoluteFill style={{ opacity: o * 0.5, pointerEvents: "none", background: "radial-gradient(ellipse 60% 14% at 50% 21%, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 100%)" }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: 380, display: "flex", justifyContent: "center", opacity: o,
              transform: `translateY(${(1 - inP) * 26 + (1 - outP) * -14}px) scale(${0.94 + 0.06 * inP})`, filter: "drop-shadow(0 3px 16px rgba(0,0,0,0.45))" }}>
              <div style={{ display: "flex", alignItems: "center", gap: 18, color: b.color }}>
                {b.logo ? <Img src={staticFile(b.logo)} style={{ width: claude ? 92 : 84, height: claude ? 92 : 84, objectFit: "contain" }} /> : null}
                <div style={{ fontFamily: claude ? SERIF : SANS, fontWeight: claude ? 400 : 800, fontSize: b.name === "text" ? 104 : claude ? 84 : 70, letterSpacing: claude ? -1 : -1.5, lineHeight: 1 }}>
                  {b.label ?? (claude ? "Claude" : "Higgsfield")}
                </div>
              </div>
            </div>
          </React.Fragment>
        );
      })}
    </>
  );
};

// Chapter label: it swaps in place at each chapter start (5-frame fade each way) and its name resolves out of brand-green noise
// (dual-scramble motion). `chapterStyle: "rail"` swaps the pill for a slim process rail (process-rail motion): a bead travels
// along a line and the step it reaches lights up.
const ChapterTag: React.FC<{ chapters: Chapter[]; pf: number; style?: "pill" | "rail"; split?: boolean; stacks?: Stack[] }> = ({ chapters, pf, style = "pill", split = false, stacks = [] }) => {
  const t = pf / FPS;
  if (split) {
    // split look: a chapter is announced by a black plate callout (white bold sans, as the headline plates of the reference reel) for 2.4 s
    // at the top of the presenter area, its name resolving out of green noise; then it is cut off. No persistent label.
    const { p } = stackState(pf, stacks);
    return (
      <>
        {chapters.map((c, i) => {
          const u = t - c.from;
          if (u < 0 || u > 2.4) return null;
          const label = <DualScramble text={c.label} t={u} duration={0.5} color1={ACCENT} color2="#FFFFFF" />;
          return (
            <div key={i} style={{ position: "absolute", left: 0, right: 0, top: SPLIT_H * p + (p > 0.5 ? 34 : 250), display: "flex", justifyContent: "center" }}>
              <div style={{ padding: "16px 34px", borderRadius: 14, background: "#000", color: "#fff", fontFamily: SANS, fontWeight: 800, fontSize: 46, letterSpacing: -0.5, lineHeight: 1.1 }}>{label}</div>
            </div>
          );
        })}
      </>
    );
  }
  return (
    <>
      {chapters.map((c, i) => {
        const a = interpolate(t, [c.from, c.from + 5 / FPS], [0, 1], clamp);
        const b = i + 1 < chapters.length ? interpolate(t, [chapters[i + 1].from - 5 / FPS, chapters[i + 1].from], [1, 0], clamp) : interpolate(t, [c.to - 5 / FPS, c.to], [1, 0], clamp);
        const o = Math.min(a, b);
        if (o <= 0) return null;
        const label = <DualScramble text={c.label} t={t - c.from} duration={0.5} color1={ACCENT} color2={CREAM} />;
        if (style === "rail") {
          return (
            <div key={i} style={{ position: "absolute", left: 54, top: 226, opacity: o, display: "flex", alignItems: "center", gap: 22 }}>
              <ChapterRail n={chapters.length} index={i} t={t - c.from} color={ACCENT} dim="rgba(242,235,220,0.35)" />
              <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 26, letterSpacing: 0.5, color: CREAM, textShadow: "0 1px 8px rgba(0,0,0,0.55)" }}>{label}</span>
            </div>
          );
        }
        return (
          <div key={i} style={{ position: "absolute", left: 54, top: 226, opacity: o, display: "flex", gap: 16, alignItems: "center",
            padding: "10px 22px", borderRadius: 999, background: "rgba(12,13,11,0.62)", fontFamily: SANS, fontWeight: 700, fontSize: 26, letterSpacing: 0.5 }}>
            <span style={{ color: ACCENT, fontWeight: 700 }}>{c.num}</span>
            <span>{label}</span>
          </div>
        );
      })}
    </>
  );
};

// Name and role of the presenter (review 2026-11-17): a small black plate at the lower left for the first seconds, hard cut on and off like the captions.
const NameTag: React.FC<{ tag?: { name: string; role: string; from: number; to: number; episode?: string }; pf: number }> = ({ tag, pf }) => {
  if (!tag) return null;
  const t = pf / FPS;
  if (t < tag.from || t >= tag.to + 0.4) return null;
  // smooth: slides in from the left and fades up over 14 frames (ease-out), slides a little and fades away over 12 frames (ease-in-out)
  const inP = interpolate(t, [tag.from, tag.from + 14 / FPS], [0, 1], { ...clamp, easing: SETTLE });
  const outP = interpolate(t, [tag.to, tag.to + 12 / FPS], [1, 0], { ...clamp, easing: SMOOTH });
  const o = Math.min(inP, outP);
  return (
    <div style={{ position: "absolute", left: 60, top: 1330, lineHeight: 1.15, opacity: o,
      transform: `translateX(${-(1 - inP) * 36 - (1 - outP) * 18}px)` }}>
      {tag.episode ? <div style={{ fontFamily: SANS, fontWeight: 700, fontSize: 30, letterSpacing: 6, color: ACCENT, marginBottom: 10, textShadow: "0 2px 12px rgba(0,0,0,0.7), 0 0 3px rgba(0,0,0,0.5)" }}>{tag.episode}</div> : null}
      <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 40, color: "#fff", letterSpacing: -0.2, textShadow: "0 2px 14px rgba(0,0,0,0.55), 0 0 3px rgba(0,0,0,0.35)" }}>{tag.name}</div>
      <div style={{ fontFamily: SANS, fontWeight: 500, fontSize: 27, color: "rgba(255,255,255,0.88)", marginTop: 4, textShadow: "0 2px 12px rgba(0,0,0,0.7), 0 0 3px rgba(0,0,0,0.5)" }}>{tag.role}</div>
    </div>
  );
};

// Faded Pinecone mark, top centre, over the whole talk (as on the PineQuest reels): quiet brand presence, never over a caption.
const FadedMark: React.FC<{ src?: string; f: number; P0: number; E: number; hide?: number; closer?: boolean }> = ({ src, f, P0, E, hide = 0, closer = false }) => {
  if (!src) return null;
  const a = closer ? interpolate(f, [P0, P0 + 8, E - 10, E - 4], [0, 1, 1, 0], clamp) : interpolate(f, [P0 + T.revealFrames, P0 + T.revealFrames + 12, E - 28, E - 14], [0, 1, 1, 0], clamp);
  if (a <= 0) return null;
  return <Mark src={src} style={{ position: "absolute", top: 86, left: 540 - 29, opacity: 0.5 * a * (1 - Math.min(1, hide * 3)), filter: "blur(0.6px)", backgroundColor: "#D4D4D4" }} />;
};

// Sign-off: the title returns, smaller and solid; then a ghost suggestion for the next episode that nobody accepts yet.
const SignOff: React.FC<{ f: number; E: number; next: string; mark?: string; meta?: boolean }> = ({ f, E, next, mark, meta = false }) => {
  const g = f - (E - 14);
  const veil = interpolate(f, [E - 28, E - 4], [0, 1], { ...clamp, easing: SMOOTH }); // ink comes up under the dimming shot; the title arrives on it
  if (f < E - 28) return null;
  if (g < 0) return <AbsoluteFill style={{ background: INK, opacity: veil }} />;
  const a = interpolate(g, [0, 16], [0, 1], { ...clamp, easing: SETTLE });
  const ghostA = interpolate(g, [34, 46], [0, 1], { ...clamp, easing: SETTLE });
  const typed = Math.max(0, Math.min(next.length, Math.floor((g - 38) / 1.6)));
  const caretOn = Math.floor(g / 15) % 2 === 0;
  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ background: INK, opacity: veil }} />
      {meta ? <div style={{ position: "absolute", left: LEFT, top: 238, right: LEFT, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: a }}>
        <div style={{ fontFamily: SANS, fontSize: 30, fontWeight: 700, letterSpacing: 5, color: ACCENT }}>EP 01</div>
        <Lockup src={mark} text />
      </div> : null}
      <div style={{ position: "absolute", left: LEFT, top: 640, opacity: a, transform: `translateY(${(1 - a) * 26}px)` }}>
        <TitleBlock f={400} size={128} showCaret={false} />
      </div>
      <div style={{ position: "absolute", left: LEFT, top: 640 + 4 * 134 + 56, opacity: ghostA, fontFamily: SANS, fontWeight: 500, fontSize: 40, letterSpacing: 1, color: GHOST, whiteSpace: "pre" }}>
        {next.slice(0, typed)}
        <span style={{ display: "inline-block", width: 5, height: 40, marginLeft: 6, verticalAlign: -6, background: ACCENT, opacity: caretOn ? 1 : 0 }} />
      </div>
    </AbsoluteFill>
  );
};

export const EngEpisode: React.FC<EngEpisodeProps> = (P) => {
  P_SPLIT.current = P.look !== "cards";
  MOVE = P.moveFrames ?? 20;
  CURTAIN = P.curtainFrames ?? 21;
  const f = useCurrentFrame();
  useVideoConfig();
  const P0 = P.noIntro ? 0 : T.presenterStart;
  const PF = Math.round(P.presenterSeconds * FPS);
  const E = P0 + PF;
  const pf = f - P0;
  const exit = interpolate(f, [T.exitStart, T.presenterStart], [0, 1], { ...clamp, easing: SMOOTH });
  const signOffEnd = E + (P.closer ? P.closerFrames ?? CLOSER_F : Math.round(P.outroSeconds * FPS));
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {f < P0 && !P.noIntro ? <IntroScene f={f} mark={P.mark} exit={exit} meta={P.meta} /> : null}
      <Sequence from={P0} durationInFrames={PF + 4} name="presenter">
        <Presenter P={P} pf={pf} f={f} E={E} />
      </Sequence>
      {P.stacks.map((s, i) => <Window key={i} s={s} pf={pf} startF={P0} />)}
      <ChapterTag chapters={P.chapters} pf={pf} style={P.chapterStyle} split={P.look !== "cards"} stacks={P.stacks} />
      <FadedMark src={P.mark} f={f} P0={P0} E={E} closer={P.closer} hide={P.look !== "cards" ? stackState(pf, P.stacks).p : 0} />
      {(P.leaks ?? []).map((l, i) => (
        <Sequence key={`leak${i}`} from={P0 + Math.round(l.t * FPS) - 7} durationInFrames={14} name={`leak ${i + 1}`}>
          <Leak tone={l.tone} dir={l.dir} />
        </Sequence>
      ))}
      {pf >= 0 && f < E ? <BrandMoments brands={P.brands} pf={pf} /> : null}
      {pf >= 0 && f < E ? <NameTag tag={P.nameTag} pf={pf} /> : null}
      {pf >= 0 && f < E ? <CaptionText P={P} pf={pf} /> : null}
      {P.closer ? (f >= E ? <IntroScene f={f - E} mark={P.mark} meta={false} signature={P.signature} ep={P.closerEp} /> : null) : <SignOff f={f} E={E} next={P.nextLabel} mark={P.mark} meta={P.meta} />}
      {P.endCard ? (
        <Sequence from={signOffEnd - OVERLAP} name="end card">
          <AbsoluteFill style={{ opacity: interpolate(f - (signOffEnd - OVERLAP), [0, OVERLAP], [0, 1], { ...clamp, easing: SMOOTH }) }}>
            <OffthreadVideo src={staticFile(P.endCard)} />
          </AbsoluteFill>
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
