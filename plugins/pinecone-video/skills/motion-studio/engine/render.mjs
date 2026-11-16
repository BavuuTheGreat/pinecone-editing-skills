// Frame-accurate renderer: drives window.seek(t) in headless Chromium, screenshots
// the #c canvas, and pipes PNGs into ffmpeg. Optional sub-frames are averaged into
// each output frame for real motion blur.
//
//   node render.mjs                          full film, defaults below
//   node render.mjs --from 4 --to 7          re-render one section -> out/part_4-7.mp4
//   node render.mjs --still 2.5              one PNG -> out/still_2.5.png
//   node render.mjs --w 1080 --h 1080        square cut from the same timeline
//   node render.mjs --scale 0.5 --sub 1      fast low-res rough cut
//
// Flags: --fps 30 --dur <film.duration> --sub 4 --w 1080 --h 1920 --scale 1 --page index.html
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { readFile } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join } from "node:path";

const flags = {};
for (let i = 2; i < process.argv.length; i += 2) {
  flags[process.argv[i].replace(/^--/, "")] = process.argv[i + 1];
}
const num = (k, d) => (flags[k] === undefined ? d : Number(flags[k]));

const W = num("w", 1080);
const H = num("h", 1920);
const SCALE = num("scale", 1);
const FPS = num("fps", 30);
const SUB = Math.max(1, Math.round(num("sub", 4)));
const PAGE = flags.page ?? "index.html";
mkdirSync("out", { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: Math.round(W * SCALE), height: Math.round(H * SCALE) },
  deviceScaleFactor: 1,
});
// ES modules do not load over file://, so serve this folder on a local port.
const TYPES = { ".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
  ".woff2": "font/woff2", ".mp4": "video/mp4", ".webp": "image/webp" };
const server = createServer((req, res) => {
  const path = join(process.cwd(), decodeURIComponent(new URL(req.url, "http://x").pathname));
  readFile(path)
    .then((body) => res.writeHead(200, { "content-type": TYPES[extname(path)] ?? "application/octet-stream" }).end(body))
    .catch(() => res.writeHead(404).end());
}).listen(0, "127.0.0.1");
await new Promise((r) => server.once("listening", r));
const url = new URL(`http://127.0.0.1:${server.address().port}/${PAGE}`);
url.search = `?w=${Math.round(W * SCALE)}&h=${Math.round(H * SCALE)}&render=1`;
page.on("pageerror", (e) => console.error("[page error]", e.message));
await page.goto(url.href);
await page.evaluate(async () => {
  await document.fonts.ready;
  // Films signal preloaded assets with window.ready (or window.READY in older films).
  const ready = window.ready ?? window.READY;
  if (ready) await ready;
});
const filmDur = await page.evaluate(() => window.film?.duration ?? null);
const canvas = page.locator("#c");
const shot = async (t) => {
  await page.evaluate((x) => window.seek(x), t);
  return canvas.screenshot({ type: "png" });
};

if (flags.still !== undefined) {
  const t = Number(flags.still);
  const file = `out/still_${t}.png`;
  writeFileSync(file, await shot(t));
  console.log(`wrote ${file}`);
  await browser.close();
  server.close();
  process.exit(0);
}

const FROM = num("from", 0);
const TO = num("to", num("dur", filmDur ?? 10));
const partial = flags.from !== undefined || flags.to !== undefined;
const outFile = partial ? `out/part_${FROM}-${TO}.mp4` : flags.out ?? "out/silent.mp4";

// Averaging the last SUB sub-frames, then keeping every SUB-th result, gives each
// output frame a shutter spanning the interval just before it.
const vf = SUB > 1 ? [`tmix=frames=${SUB}`, `framestep=${SUB}`] : [];
const ff = spawn(
  "ffmpeg",
  [
    "-y", "-loglevel", "error",
    "-f", "image2pipe", "-framerate", String(FPS * SUB), "-i", "-",
    ...(vf.length ? ["-vf", vf.join(",")] : []),
    "-r", String(FPS), "-c:v", "libx264", "-crf", "16", "-preset", "slow",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", outFile,
  ],
  { stdio: ["pipe", "inherit", "inherit"] },
);

const frames = Math.round((TO - FROM) * FPS);
const started = Date.now();
for (let f = 0; f < frames; f++) {
  for (let s = 0; s < SUB; s++) {
    // Sub-frames sit just before the frame time; frame f's last sample is exact.
    const t = FROM + f / FPS - (SUB - 1 - s) / (FPS * SUB);
    const png = await shot(Math.max(FROM, t));
    if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once("drain", r));
  }
  if (f % FPS === 0) {
    const secs = ((Date.now() - started) / 1000).toFixed(0);
    console.log(`  ${(FROM + f / FPS).toFixed(1)}s / ${TO}s  (${secs}s elapsed)`);
  }
}
ff.stdin.end();
const code = await new Promise((r) => ff.on("close", r));
await browser.close();
server.close();
if (code !== 0) {
  console.error(`ffmpeg exited with ${code}`);
  process.exit(1);
}
console.log(`wrote ${outFile} (${frames} frames, ${W}x${H} @ ${FPS}fps, sub ${SUB})`);
