---
name: animation
description: Make a finished animated video (MP4) where every frame is drawn in code on an HTML canvas and the music and sound effects are synthesised in code too, styled after reference images the user dropped in (a painting, a Pinterest pin, a film still). Plans the shots, draws them, adds sound, checks its own frames on a contact sheet, fixes them, and exports out/<topic>.mp4. Use for "/animation", "animate this", "make an animated video", "make an animation about X", "turn this style into a video".
---

# animation: a drawn film from your references, all in code

You make a short animated film. No video model, no image model, no stock files: every frame is drawn on an
HTML canvas by code you write, and the music and effects are synthesised in code. The user gives references
for the look, a topic, a length and a format. You give back `out/<topic>.mp4`.

The tools sit next to this file (call this folder `SKILL_DIR`; it is the folder that holds this SKILL.md):
- `SKILL_DIR/scripts/render.mjs`: renders a page to MP4 (`video`), an audio page to WAV (`audio`), joins parts (`join`).
- `SKILL_DIR/scripts/sheet.mjs`: contact sheet of a page or MP4 (one labelled frame every 0.5 s), or one full still.
- `SKILL_DIR/template.html`: the smallest working picture page (the seek contract). Copy it, do not edit it.
- `SKILL_DIR/template-audio.html`: the smallest working sound page (OfflineAudioContext).

## 0. Check the machine (once)

Run these and fix what is missing before anything else:
```
node --version          # 18 or newer
ffmpeg -version         # any recent build
```
Missing? macOS: `brew install node ffmpeg`. Windows: `winget install OpenJS.NodeJS` and `winget install ffmpeg`
(then open a new terminal). Linux: your package manager (`sudo apt install nodejs npm ffmpeg`).

If `SKILL_DIR/scripts/node_modules` does not exist, run `npm install` inside `SKILL_DIR/scripts` (it installs
Playwright and downloads its Chromium, about 100 MB, once). Then prove the setup with a 2 second smoke test:
```
cd SKILL_DIR/scripts
node render.mjs video ../template.html --width 540 --height 960 --out <project>/out/smoke.mp4
```
It should print `wrote ... (60 frames ...)`. If Chromium will not start, run `npx playwright install chromium`.

## 1. Get the brief

Read what the user gave you. Ask only for what is missing, in one message:
- **References**: the images they dropped in (paintings, pins, film stills, screenshots). Look at every one.
  No references? Ask for one or two, or offer three named looks to choose from.
- **Topic**: what the film is about (a story, a place, an idea, a product).
- **Length**: default 30 s.
- **Format**: default 9:16 at 1080 x 1920. Also 1:1 at 1080 x 1080, 16:9 at 1920 x 1080. 30 fps.

Make a project folder in the current working directory: `animation-<topic-slug>/` with `out/` inside.

## 2. Write the style bible (`style.md`)

Study the references and write down, in numbers where you can:
- **Palette**: 5 to 8 hex colours with their roles (deep shadow, mid, light, accent, highlight). Sample them by eye from the references.
- **Line**: none, thin ink, thick brush, pixel edge; weight in px at 1080 wide; wobble or clean.
- **Texture**: paper grain, canvas weave, halftone dots, woodblock grain, film grain, dither. How strong.
- **Light**: where it comes from, how hard, glow or not, rim light, colour of shadows.
- **Shape language**: round, angular, flat cut paper, layered depth, how detailed.
- **Motion feel**: floaty and slow, snappy, stop-motion steps (12 fps holds), elastic. Typical ease.
- **Type** (if any words appear): a system font stack or a font file next to the page; size and placement.

Show the user the bible in 6 to 10 lines and go on unless they object.

## 3. Write the shot list (`shots.md` plus `timeline.js`)

Split the length into shots of 2 to 5 s (a 30 s film is about 8 to 10 shots). For each shot:
start and end in seconds, what we see (one big, clear subject), the camera move, what moves inside the frame,
how it hands over to the next shot, and the sound on it.

Put the timing in `timeline.js` so the picture page and the sound page read the same numbers:
```js
const FILM = { width: 1080, height: 1920, fps: 30, frames: 900 };
const SHOTS = [ { id: 1, start: 0, end: 3.2, name: 'whale rises' }, /* ... */ ];
const CUES  = [ { t: 3.0, kind: 'whoosh' }, { t: 3.2, kind: 'hit' } /* ... */ ];
```
The first 2 seconds must already show something beautiful and moving: that is where people decide to watch.

## 4. Draw the film (`film.html`)

One page for the whole film, built from `template.html`. It loads `timeline.js`, then one script per shot
(`shots/01.js`, `shots/02.js`, ...) so each file stays small, then a dispatcher that draws every shot whose
time range covers `t` (two shots overlap during a handover). Load them with plain `<script src="...">` tags,
not `type="module"`: pages are opened from disk (`file://`), where module imports are blocked.

**The seek contract (hard rules, render.mjs depends on them):**
- `window.FILM = { width, height, fps, frames }` and `window.seek(f)` that draws frame `f` completely.
- Time comes only from `f` (`t = f / fps`). Never `Date.now()`, `performance.now()`, timers, or
  `requestAnimationFrame` time while rendering. The renderer adds `?render=1` to the URL; animate a live
  preview only when that is absent.
- All randomness from a seeded generator (the `rng(seed)` in the template). Same `f`, same picture, always.
- Draw in design units (for example 1080 x 1920) and scale to the canvas size, so a 540 x 960 test and the
  full render match.
- Anything that must load first (fonts, images you drew to offscreen canvases) resolves `window.ready`.
- Particle systems: compute positions from `t` (closed form, `x = x0 + vx * t + sin(...)`), never by
  stepping state frame by frame, so any frame can be drawn on its own.

**Quality bar (this is what makes it look made, not generated):**
- Big, lit, beautiful subjects. The subject fills a third or more of the frame, has a light side, a shadow
  side, a glow or rim light, and sits in a scene with depth (foreground, middle, background).
- Art-quality textures from the bible: grain, brush strokes, paper, halftone, dither. Draw them procedurally
  (noise, many small strokes, offscreen canvas patterns), and keep them still or slowly drifting so they do
  not boil unless the style wants that.
- Never placeholder shapes: no plain circles standing for a sun, no rectangles standing for a building. A sun
  has a corona and heat haze; a building has windows, edges, light spill, a roofline.
- Build complex subjects from many parts: a fish is a body path with gradient shading, scales drawn as
  rows of arcs, fins that bend with a sine phase delay, an eye with a highlight.
- **Every element moves, all the time.** Camera always drifts (a few px of pan, a 1 to 2 percent slow zoom),
  layers move at different speeds (parallax), subjects breathe, sway, blink, ripple, particles float.
  A frozen frame anywhere in the film is a defect.
- **No fades between shots.** Shots hand over by motion: a camera push into a detail that becomes the next
  scene, a whip pan, an object that flies across and wipes the frame, a match cut on a shape, a zoom through
  a window. Fades to black only at the very end, if at all.
- Motion with weight: ease in and out, overshoot on arrivals, follow-through on tails and hair, anticipation
  before big moves. Linear motion only for drift.
- Words on screen (only if the topic needs them): large, few, inside the safe area (9:16: keep 220 px clear
  at the top, 450 px at the bottom, 60 px at the sides), and they animate in by motion too.

Preview while you draw: open `film.html` in a browser for the live loop, and grab single frames with
`node SKILL_DIR/scripts/sheet.mjs film.html --still 4.5 --out out/still.png`, then look at the PNG.

## 5. Make the sound (`audio.html`)

Build it from `template-audio.html`: `window.renderAudio(sampleRate, seconds)` returns the AudioBuffer of an
`OfflineAudioContext`. Load the same `timeline.js` so hits land on the frames where things happen.
- **Music bed**: a chord progression that fits the mood of the bible (pads from detuned saws or triangles
  through a low pass, a soft bass, a simple melody from sine or FM bells, a pulse or kick if the film is
  energetic). Change chord on shot starts. Keep it about 12 dB under the effects.
- **Effects**: a whoosh (band-passed noise sweep) on whip pans and pushes, a soft hit (sine drop plus noise
  click) on arrivals, shimmer (high sine partials with fast tremolo) on sparkles, rumble for big moves.
  Use seeded noise so the sound is the same every render.
- Fade the bed in over the first 0.3 s and out over the last 1 s.

Render it: `node SKILL_DIR/scripts/render.mjs audio audio.html --out out/music.wav`
(the length comes from `FILM` in the page, or pass `--seconds 30`).

## 6. Render

Small test first, then full size. Render shot by shot so a fix only re-renders one shot:
```
cd SKILL_DIR/scripts
node render.mjs video <project>/film.html --start 0 --end 96 --out <project>/out/parts/01.mp4
node render.mjs video <project>/film.html --start 96 --end 210 --out <project>/out/parts/02.mp4
...
node render.mjs join <project>/out/parts/01.mp4 <project>/out/parts/02.mp4 ... --audio <project>/out/music.wav --out <project>/out/<topic>.mp4
```
`--start` and `--end` are frame numbers (`end` is not included): shot start and end seconds times fps.
Add `--width 540 --height 960` for a fast test pass. Expect roughly 10 to 20 frames a second at full size on a
laptop, so a 30 s film takes about 1 to 2 minutes. A one-pass render of the whole film also works:
`node render.mjs video film.html --audio out/music.wav --out out/<topic>.mp4`.

## 7. Check your own frames (do not skip)

```
node SKILL_DIR/scripts/sheet.mjs <project>/out/<topic>.mp4 --every 0.5 --out <project>/out/sheet.png
```
Open `sheet.png` and look at it. Write a defect list, one line each with its time, for example:
- a frame that looks the same as the one before (nothing moving),
- a placeholder shape, a flat unlit subject, a subject too small to read,
- a hard jump or a fade at a shot change instead of a motion handover,
- text outside the safe area, cut off, or unreadable on its background,
- colours that drift from the palette in the bible, banding in gradients (add grain),
- an empty or black frame, a layer popping in.
For a close look at one moment: `sheet.mjs film.html --still 12.5 --out out/still.png`.

Fix each defect in its shot file, re-render only that shot's part, join again, make a new sheet, look again.
Stop when the sheet is clean, or after three rounds (then tell the user what is still weak).

## 8. Deliver

Export `out/<topic>.mp4` (H.264, yuv420p, AAC, faststart: it plays on phones and uploads to Instagram,
TikTok and YouTube as is). Tell the user the path, the length, and the contact sheet path, and offer one
round of changes (a shot, the colours, the music tempo).

## Troubleshooting
- `ffmpeg not found`: install it (step 0) and open a new terminal.
- `could not start Chromium`: `npx playwright install chromium` in `SKILL_DIR/scripts`.
- `the page must define window.FILM and window.seek(f)`: a script error stops the page early; open the page
  in a browser and read the console.
- Frames differ between two renders: something reads the clock or unseeded `Math.random`. Search for them.
- Very slow render: lower `--width/--height` for tests, draw heavy textures once into an offscreen canvas
  and reuse it, and avoid `ctx.filter` blur on large areas every frame (draw a soft radial gradient instead).
