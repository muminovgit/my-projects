#!/usr/bin/env node
// sheet.mjs: a contact sheet (one labelled thumbnail every N seconds) of a seekable page or an MP4,
// so you can look at the whole film in one picture and list what is wrong.
//
//   node sheet.mjs <page.html | video.mp4> --out sheet.png [--every 0.5] [--cols 8] [--thumb 220]
//                  [--start S] [--end S]
//   node sheet.mjs <page.html> --still 7.5 --out still.png      one full size frame at 7.5 s
//
// A page is read through the same contract as render.mjs: window.FILM and window.seek(f).
// An MP4 is read with ffmpeg (must be on PATH).

import { chromium } from 'playwright';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function fail(msg) { console.error(`sheet.mjs: ${msg}`); process.exit(1); }

const argv = process.argv.slice(2);
const pos = [];
const opt = {};
for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith('--')) {
    const k = argv[i].slice(2);
    const v = argv[i + 1];
    if (v === undefined || v.startsWith('--')) opt[k] = true; else { opt[k] = v; i++; }
  } else pos.push(argv[i]);
}
const src = pos[0];
if (!src) fail('usage: node sheet.mjs <page.html | video.mp4> --out sheet.png [--every 0.5] [--cols 8] [--thumb 220]');
if (!/^https?:/.test(src) && !fs.existsSync(src)) fail(`not found: ${src}`);
const n = (k, d) => { if (opt[k] === undefined) return d; const v = Number(opt[k]); if (!Number.isFinite(v)) fail(`--${k} must be a number`); return v; };
const every = n('every', 0.5);
const cols = n('cols', 8);
const thumb = n('thumb', 220);
const out = opt.out || 'out/sheet.png';
if (every <= 0) fail('--every must be above 0');

async function launch() {
  try { return await chromium.launch(); } catch (e) {
    fail(`could not start Chromium (${e.message.split('\n')[0]}). Run "npx playwright install chromium" in the scripts folder.`);
  }
}

function pageUrl(p) {
  const u = /^https?:/.test(p) ? p : pathToFileURL(path.resolve(p)).href;
  return `${u}${u.includes('?') ? '&' : '?'}render=1`;
}

async function readFilm(browser, url) {
  const page = await browser.newPage({ viewport: { width: 400, height: 400 } });
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.FILM && typeof window.seek === 'function', null, { timeout: 15000 })
    .catch(() => fail('the page must define window.FILM and window.seek(f)'));
  const film = await page.evaluate(() => ({ ...window.FILM }));
  await page.close();
  film.fps = film.fps || 30;
  film.frames = film.frames || Math.round((film.seconds || 0) * film.fps);
  return film;
}

async function framesFromPage(browser, times, w, h) {
  const url = pageUrl(src);
  const film = await readFilm(browser, url);
  const page = await browser.newPage({ viewport: { width: w ?? film.width, height: h ?? film.height }, deviceScaleFactor: 1 });
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto(url, { waitUntil: 'load' });
  await page.waitForFunction(() => window.FILM && typeof window.seek === 'function');
  await page.evaluate(async () => { if (window.ready) await window.ready; if (document.fonts) await document.fonts.ready; });
  const shots = [];
  for (const t of times) {
    const f = Math.min(film.frames - 1, Math.round(t * film.fps));
    await page.evaluate(async (k) => { await window.seek(k); }, f);
    if (errors.length) fail(`page error at ${t} s: ${errors.join(' | ')}`);
    shots.push({ t, png: await page.screenshot({ type: 'png' }) });
  }
  await page.close();
  return { film, shots };
}

function framesFromVideo(times, w) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'anim-sheet-'));
  const shots = [];
  for (const t of times) {
    const file = path.join(dir, `${shots.length}.png`);
    const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-ss', String(t), '-i', src,
      '-frames:v', '1', '-vf', `scale=${w}:-2`, file]);
    if (r.error) fail(r.error.code === 'ENOENT' ? 'ffmpeg not found on PATH' : r.error.message);
    if (r.status !== 0 || !fs.existsSync(file)) break; // past the end
    shots.push({ t, png: fs.readFileSync(file) });
  }
  return shots;
}

function videoSeconds() {
  const r = spawnSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', src], { encoding: 'utf8' });
  const d = Number((r.stdout || '').trim());
  if (!Number.isFinite(d) || d <= 0) fail('could not read the video length with ffprobe');
  return d;
}

const browser = await launch();
const isVideo = /\.(mp4|mov|webm|mkv)$/i.test(src);
fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });

if (opt.still !== undefined) {
  const t = n('still', 0);
  if (isVideo) {
    const r = spawnSync('ffmpeg', ['-y', '-hide_banner', '-loglevel', 'error', '-ss', String(t), '-i', src, '-frames:v', '1', out]);
    if (r.status !== 0) fail(`ffmpeg could not grab ${t} s`);
  } else {
    const { shots } = await framesFromPage(browser, [t]);
    fs.writeFileSync(out, shots[0].png);
  }
  await browser.close();
  console.log(`wrote ${out}`);
  process.exit(0);
}

let length;
let shots;
const tw = thumb * 2; // capture at twice the thumbnail size so the sheet stays sharp
if (isVideo) {
  length = videoSeconds();
  const times = [];
  for (let t = n('start', 0); t < Math.min(length, n('end', length)) - 1e-6; t += every) times.push(+t.toFixed(3));
  shots = framesFromVideo(times, tw);
} else {
  const film = await readFilm(browser, pageUrl(src));
  length = film.frames / film.fps;
  const times = [];
  for (let t = n('start', 0); t < Math.min(length, n('end', length)) - 1e-6; t += every) times.push(+t.toFixed(3));
  const th = Math.round((tw * film.height) / film.width / 2) * 2;
  shots = (await framesFromPage(browser, times, tw, th)).shots;
}
if (!shots.length) fail('no frames captured');

const cells = shots.map((s) => `<figure><img src="data:image/png;base64,${s.png.toString('base64')}"><figcaption>${s.t.toFixed(1)} s</figcaption></figure>`).join('');
const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body{margin:0;background:#111;color:#ddd;font:600 14px system-ui,sans-serif}
  .g{display:grid;grid-template-columns:repeat(${cols},${thumb}px);gap:8px;padding:10px;width:max-content}
  figure{margin:0} img{width:${thumb}px;display:block;border-radius:3px}
  figcaption{padding:3px 2px 0}
  h1{font-size:14px;margin:10px 10px 0;font-weight:600;color:#999}
</style></head><body><h1>${path.basename(src)}  |  every ${every} s  |  ${shots.length} frames  |  ${length.toFixed(2)} s</h1><div class="g">${cells}</div></body></html>`;
const page = await browser.newPage({ viewport: { width: cols * (thumb + 8) + 20, height: 400 } });
await page.setContent(html, { waitUntil: 'load' });
await page.screenshot({ path: out, fullPage: true });
await browser.close();
console.log(`wrote ${out}  (${shots.length} frames)`);
