#!/usr/bin/env node
// render.mjs: turn a seekable HTML page into video frames, a WAV, or a finished MP4.
//
// Three commands:
//   node render.mjs video <page.html> --out part.mp4 [--start F] [--end F] [--width W] [--height H]
//                         [--fps N] [--audio music.wav] [--jpeg] [--crf 18]
//   node render.mjs audio <audio.html> --out music.wav [--seconds S] [--rate 48000]
//   node render.mjs join  <a.mp4> <b.mp4> ... --out film.mp4 [--audio music.wav]
//
// The page contract (video):
//   window.FILM = { width, height, fps, frames }   design size, frame rate, total frames
//   window.seek(f)                                  draw frame f (0 based); may return a Promise
//   window.ready (optional)                         a Promise that resolves when fonts and images are loaded
// The page must draw the same picture for the same f every time: no Date.now, no Math.random
// without a seed, no requestAnimationFrame timing while rendering.
//
// The page contract (audio):
//   window.renderAudio(sampleRate, seconds) -> Promise<AudioBuffer>   usually an OfflineAudioContext render
//
// Needs: Node 18+, ffmpeg on PATH, and `npm install` in this folder (installs Playwright and its Chromium).

import { chromium } from 'playwright';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function fail(msg) {
  console.error(`render.mjs: ${msg}`);
  process.exit(1);
}

function parseArgs(argv) {
  const pos = [];
  const opt = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next === undefined || next.startsWith('--')) opt[key] = true;
      else { opt[key] = next; i++; }
    } else pos.push(a);
  }
  return { pos, opt };
}

function toUrl(p) {
  if (/^https?:\/\//.test(p) || p.startsWith('file:')) return p;
  const abs = path.resolve(p);
  if (!fs.existsSync(abs)) fail(`page not found: ${abs}`);
  return pathToFileURL(abs).href;
}

function num(v, name) {
  if (v === undefined) return undefined;
  const n = Number(v);
  if (!Number.isFinite(n)) fail(`--${name} must be a number, got "${v}"`);
  return n;
}

function runFfmpeg(args, { stdin = false } = {}) {
  const proc = spawn('ffmpeg', args, { stdio: [stdin ? 'pipe' : 'ignore', 'ignore', 'pipe'] });
  let log = '';
  proc.stderr.on('data', (d) => { log = (log + d.toString()).slice(-4000); });
  const done = new Promise((resolve, reject) => {
    proc.on('error', (e) => reject(new Error(
      e.code === 'ENOENT' ? 'ffmpeg not found on PATH. Install it: macOS "brew install ffmpeg", Windows "winget install ffmpeg".' : e.message)));
    proc.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`ffmpeg exited with ${code}:\n${log}`))));
  });
  return { proc, done };
}

async function openPage(url, width, height) {
  let browser;
  try {
    browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb', '--autoplay-policy=no-user-gesture-required'] });
  } catch (e) {
    fail(`could not start Chromium (${e.message.split('\n')[0]}). Run "npx playwright install chromium" in the scripts folder.`);
  }
  const context = await browser.newContext({ viewport: { width, height }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  const sep = url.includes('?') ? '&' : '?';
  await page.goto(`${url}${sep}render=1`, { waitUntil: 'load' });
  return { browser, page, errors };
}

async function readFilm(url) {
  // Open once at a small size just to read FILM, so the real viewport can match it.
  const { browser, page, errors } = await openPage(url, 400, 400);
  try {
    await page.waitForFunction(() => window.FILM && typeof window.seek === 'function', null, { timeout: 15000 })
      .catch(() => fail(`the page must define window.FILM and window.seek(f). Page errors: ${errors.join(' | ') || 'none'}`));
    return await page.evaluate(() => ({ ...window.FILM }));
  } finally {
    await browser.close();
  }
}

async function cmdVideo(pos, opt) {
  const src = pos[0];
  if (!src) fail('usage: node render.mjs video <page.html> --out part.mp4');
  const out = opt.out || 'out/render.mp4';
  const url = toUrl(src);
  const film = await readFilm(url);
  const width = num(opt.width, 'width') ?? film.width;
  const height = num(opt.height, 'height') ?? film.height;
  const fps = num(opt.fps, 'fps') ?? film.fps ?? 30;
  const total = film.frames ?? Math.round((film.seconds ?? 0) * fps);
  if (!width || !height || !total) fail('window.FILM needs width, height and frames (or seconds).');
  if (width % 2 || height % 2) fail(`width and height must be even for H.264, got ${width}x${height}`);
  const start = Math.max(0, num(opt.start, 'start') ?? 0);
  const end = Math.min(total, num(opt.end, 'end') ?? total); // end is exclusive
  if (end <= start) fail(`nothing to render: start ${start}, end ${end}, page has ${total} frames`);
  const jpeg = Boolean(opt.jpeg);
  const crf = String(num(opt.crf, 'crf') ?? 18);

  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  const args = ['-y', '-hide_banner', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', jpeg ? 'mjpeg' : 'png', '-i', '-'];
  if (opt.audio) {
    if (!fs.existsSync(opt.audio)) fail(`audio file not found: ${opt.audio}`);
    args.push('-ss', String(start / fps), '-i', opt.audio, '-map', '0:v', '-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-shortest');
  }
  args.push('-c:v', 'libx264', '-preset', 'medium', '-crf', crf, '-pix_fmt', 'yuv420p',
    '-r', String(fps), '-movflags', '+faststart', out);

  const { browser, page, errors } = await openPage(url, width, height);
  const ff = runFfmpeg(args, { stdin: true });
  const t0 = Date.now();
  try {
    await page.waitForFunction(() => window.FILM && typeof window.seek === 'function', null, { timeout: 15000 });
    await page.evaluate(async () => { if (window.ready) await window.ready; if (document.fonts) await document.fonts.ready; });
    for (let f = start; f < end; f++) {
      await page.evaluate(async (n) => { await window.seek(n); }, f);
      if (errors.length) throw new Error(`page error at frame ${f}: ${errors.join(' | ')}`);
      const buf = await page.screenshot({ type: jpeg ? 'jpeg' : 'png', quality: jpeg ? 95 : undefined });
      if (!ff.proc.stdin.write(buf)) await once(ff.proc.stdin, 'drain');
      const n = f - start + 1;
      if (n % 30 === 0 || f === end - 1) {
        const rate = n / ((Date.now() - t0) / 1000);
        process.stdout.write(`\rframe ${f + 1}/${end}  ${rate.toFixed(1)} fps  `);
      }
    }
    ff.proc.stdin.end();
    await ff.done;
  } catch (e) {
    ff.proc.stdin.destroy();
    ff.proc.kill();
    await browser.close();
    fail(e.message);
  }
  await browser.close();
  process.stdout.write('\n');
  console.log(`wrote ${out}  (${end - start} frames, ${width}x${height}, ${fps} fps, ${((Date.now() - t0) / 1000).toFixed(1)} s)`);
}

async function cmdAudio(pos, opt) {
  const src = pos[0];
  if (!src) fail('usage: node render.mjs audio <audio.html> --out music.wav');
  const out = opt.out || 'out/music.wav';
  const rate = num(opt.rate, 'rate') ?? 48000;
  const { browser, page, errors } = await openPage(toUrl(src), 400, 400);
  let b64;
  try {
    await page.waitForFunction(() => typeof window.renderAudio === 'function', null, { timeout: 15000 })
      .catch(() => { throw new Error(`the page must define window.renderAudio(sampleRate, seconds). Page errors: ${errors.join(' | ') || 'none'}`); });
    const seconds = num(opt.seconds, 'seconds') ?? await page.evaluate(() => (window.FILM ? window.FILM.frames / window.FILM.fps : null));
    if (!seconds) throw new Error('give --seconds, or define window.FILM in the audio page');
    b64 = await page.evaluate(async ([sr, secs]) => {
      const buf = await window.renderAudio(sr, secs);
      const ch = Math.min(2, buf.numberOfChannels);
      const len = buf.length;
      const data = new DataView(new ArrayBuffer(44 + len * ch * 2));
      const str = (o, s) => { for (let i = 0; i < s.length; i++) data.setUint8(o + i, s.charCodeAt(i)); };
      str(0, 'RIFF'); data.setUint32(4, 36 + len * ch * 2, true); str(8, 'WAVE'); str(12, 'fmt ');
      data.setUint32(16, 16, true); data.setUint16(20, 1, true); data.setUint16(22, ch, true);
      data.setUint32(24, buf.sampleRate, true); data.setUint32(28, buf.sampleRate * ch * 2, true);
      data.setUint16(32, ch * 2, true); data.setUint16(34, 16, true); str(36, 'data'); data.setUint32(40, len * ch * 2, true);
      const chans = [...Array(ch)].map((_, c) => buf.getChannelData(c));
      let peak = 0;
      for (const c of chans) for (let i = 0; i < len; i++) peak = Math.max(peak, Math.abs(c[i]));
      const gain = peak > 0.98 ? 0.98 / peak : 1; // never clip
      let o = 44;
      for (let i = 0; i < len; i++) for (let c = 0; c < ch; c++) {
        const s = Math.max(-1, Math.min(1, chans[c][i] * gain));
        data.setInt16(o, s < 0 ? s * 0x8000 : s * 0x7fff, true); o += 2;
      }
      const bytes = new Uint8Array(data.buffer);
      let bin = '';
      for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
      return btoa(bin);
    }, [rate, seconds]);
  } catch (e) {
    await browser.close();
    fail(e.message);
  }
  await browser.close();
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  fs.writeFileSync(out, Buffer.from(b64, 'base64'));
  console.log(`wrote ${out}`);
}

async function cmdJoin(pos, opt) {
  if (pos.length < 1) fail('usage: node render.mjs join <a.mp4> <b.mp4> ... --out film.mp4 [--audio music.wav]');
  const out = opt.out || 'out/film.mp4';
  for (const p of pos) if (!fs.existsSync(p)) fail(`part not found: ${p}`);
  const list = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'anim-join-')), 'parts.txt');
  fs.writeFileSync(list, pos.map((p) => `file '${path.resolve(p).replace(/\\/g, '/').replace(/'/g, "'\\''")}'`).join('\n'));
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  const args = ['-y', '-hide_banner', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', list];
  if (opt.audio) {
    if (!fs.existsSync(opt.audio)) fail(`audio file not found: ${opt.audio}`);
    args.push('-i', opt.audio, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest');
  } else args.push('-c', 'copy');
  args.push('-movflags', '+faststart', out);
  try { await runFfmpeg(args).done; } catch (e) { fail(e.message); }
  console.log(`wrote ${out}  (${pos.length} parts${opt.audio ? ' + audio' : ''})`);
}

const { pos, opt } = parseArgs(process.argv.slice(2));
const cmd = pos.shift();
const commands = { video: cmdVideo, audio: cmdAudio, join: cmdJoin };
if (!commands[cmd]) {
  console.log('usage:\n  node render.mjs video <page.html> --out part.mp4 [--start F --end F --width W --height H --audio a.wav --jpeg]\n  node render.mjs audio <audio.html> --out music.wav [--seconds S]\n  node render.mjs join <a.mp4> <b.mp4> ... --out film.mp4 [--audio music.wav]');
  process.exit(cmd ? 1 : 0);
}
await commands[cmd](pos, opt);
