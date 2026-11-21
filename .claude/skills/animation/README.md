# animation: a Claude Code skill that draws whole films in code

Give Claude a few reference images (a painting, a Pinterest pin, a still from a film), a topic, a length and
a format. Claude plans the shots, draws every frame on an HTML canvas in code, makes the music and sound
effects in code, checks its own frames, and gives you an MP4. No video model, no image model, nothing paid.

## What you need
- Claude Code
- Node.js 18 or newer
- ffmpeg

Install Node and ffmpeg if you do not have them:
- macOS: `brew install node ffmpeg`
- Windows: `winget install OpenJS.NodeJS` and `winget install ffmpeg` (then open a new terminal)
- Linux (Debian, Ubuntu): `sudo apt install nodejs npm ffmpeg`

## Install the skill
1. Unzip. You get a folder named `animation`.
2. Move it to your Claude Code skills folder:
   - macOS and Linux: `~/.claude/skills/animation/`
   - Windows: `%USERPROFILE%\.claude\skills\animation\`
   (Create the `skills` folder if it does not exist.)
3. Install the renderer once (Playwright plus its Chromium, about 100 MB):
   ```
   cd ~/.claude/skills/animation/scripts
   npm install
   ```
   On Windows: `cd %USERPROFILE%\.claude\skills\animation\scripts` then `npm install`.
   (If you skip this, Claude runs it for you the first time.)

## Use it
1. Find a style you love and save the images.
2. Open Claude Code in an empty folder, choose Opus 5.5 (or the strongest model you have), and set effort to high.
3. Drop your reference images into the chat.
4. Type `/animation` and say the topic, the length and the format, for example:
   `/animation a koi pond at dawn, 30 seconds, 9:16`
5. Claude writes a style bible and a shot list, draws the shots, makes the sound, renders, checks a contact
   sheet of its own frames, fixes what is wrong, and saves `out/<topic>.mp4`.

Formats: 9:16 (1080 x 1920, default), 1:1 (1080 x 1080), 16:9 (1920 x 1080). Default length 30 s.

## What is inside
| file | what it does |
|---|---|
| `SKILL.md` | the step by step workflow Claude follows |
| `template.html` | a 2 second example page that shows the seek contract (`window.FILM`, `window.seek(f)`) |
| `template-audio.html` | an example sound page (music bed plus a whoosh, made with Web Audio) |
| `scripts/render.mjs` | renders a page to MP4, an audio page to WAV, and joins parts with the sound |
| `scripts/sheet.mjs` | makes a contact sheet (one frame every 0.5 s) or a single still for checking |
| `scripts/package.json` | the one dependency: Playwright 1.65.1 |

## Try the renderer by itself
```
cd ~/.claude/skills/animation/scripts
node render.mjs audio ../template-audio.html --out ~/animation-test/music.wav
node render.mjs video ../template.html --width 540 --height 960 --audio ~/animation-test/music.wav --out ~/animation-test/smoke.mp4
node sheet.mjs ~/animation-test/smoke.mp4 --out ~/animation-test/sheet.png
```
You get a 2 second clip of a moon rising over a lake, with sound, and a contact sheet of it.

## Problems
- `ffmpeg not found`: install ffmpeg and open a new terminal.
- `could not start Chromium`: run `npx playwright install chromium` in the `scripts` folder.
- Rendering is slow: it draws each frame in a real browser. About 10 to 20 frames a second at 1080 x 1920 on
  a laptop, so a 30 second film takes 1 to 2 minutes.
