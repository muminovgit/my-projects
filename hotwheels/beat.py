import sys, wave
import numpy as np

SR = 44100
BPM = 140
DUR = float(sys.argv[2]) if len(sys.argv) > 2 else 12.05
DROP = 8.6          # toy appears
GAP = (8.0, DROP)   # beat cuts out during smoke, riser plays
beat = 60 / BPM
s16 = beat / 4
N = int(DUR * SR)
rng = np.random.default_rng(7)

mix = np.zeros(N)

def add(sig, t, gain=1.0):
    i = int(t * SR)
    if i >= N: return
    j = min(N, i + len(sig))
    mix[i:j] += sig[: j - i] * gain

def env(n, a=0.002, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)

def kick():
    n = int(0.35 * SR); t = np.arange(n) / SR
    f = 45 + 120 * np.exp(-t * 35)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.5 * np.sin(ph) * env(n, 0.001, 0.12))

def clap():
    n = int(0.25 * SR)
    x = rng.standard_normal(n)
    x = np.convolve(x, [1, -0.9], 'same')  # brighten
    e = env(n, 0.001, 0.06)
    for k in (0.01, 0.02):
        e[int(k*SR):] += 0.6 * env(n - int(k*SR), 0.001, 0.02)
    return x * e * 0.5

def hat(open_=False):
    n = int((0.15 if open_ else 0.04) * SR)
    x = np.diff(rng.standard_normal(n + 1))
    return x * env(n, 0.0005, 0.05 if open_ else 0.012) * 0.25

def cowbell(freq, length=0.18):
    # phonk cowbell: two detuned square-ish tones, bandpassed by diff
    n = int(length * SR); t = np.arange(n) / SR
    x = np.sign(np.sin(2*np.pi*freq*t)) + np.sign(np.sin(2*np.pi*freq*1.48*t))
    x = np.diff(np.concatenate([[0], x])) * 0.5 + 0.5 * x * 0.15
    return np.tanh(x * env(n, 0.001, 0.09)) * 0.35

def bass808(f0, length, glide_to=None):
    n = int(length * SR); t = np.arange(n) / SR
    f = np.full(n, f0) if glide_to is None else f0 + (glide_to - f0) * np.clip(t / (length*0.6), 0, 1)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(3 * np.sin(ph) * env(n, 0.003, length * 0.7)) * 0.55

def riser(length):
    n = int(length * SR); t = np.arange(n) / SR
    x = rng.standard_normal(n)
    x = np.convolve(x, np.ones(4) / 4, 'same')
    sweep = np.sin(2*np.pi*np.cumsum(300 + 2500 * (t/length)**2) / SR)
    return (x * 0.15 + sweep * 0.1) * (t / length) ** 2

def impact():
    n = int(1.2 * SR); t = np.arange(n) / SR
    f = 35 + 80 * np.exp(-t * 10)
    sub = np.sin(2*np.pi*np.cumsum(f)/SR) * env(n, 0.002, 0.5)
    noise = rng.standard_normal(n) * env(n, 0.001, 0.15) * 0.3
    return np.tanh(2 * (sub + noise)) * 0.8

# F# minor-ish phonk cowbell riff (Hz), 16 steps per bar, 0 = rest
riff = [740, 0, 740, 0, 880, 0, 740, 0, 659, 0, 0, 659, 554, 0, 659, 0]
bass_notes = [(46.25, 0), (46.25, 6), (55.0, 10), (41.2, 14)]  # (Hz, 16th step)

def in_gap(t):
    return GAP[0] <= t < GAP[1]

def section(start, end, intro=False):
    step = 0
    t = start
    while t < end - 1e-6:
        if not in_gap(t):
            s = step % 16
            if not intro or step >= 16:   # first bar: cowbell + hats only
                if s in (0, 7, 10):
                    add(kick(), t, 0.9)
                if s in (4, 12):
                    add(clap(), t, 0.7)
                for hz, at in bass_notes:
                    if s == at:
                        glide = hz * 0.75 if at == 14 else None
                        add(bass808(hz, s16 * 4, glide), t, 0.8)
            add(hat(open_=(s % 8 == 6)), t, 0.6 if s % 2 else 0.9)
            if s % 2 == 0 and step % 32 >= 16:
                add(hat(), t + s16 / 2, 0.4)  # hat rolls
            if riff[s]:
                add(cowbell(riff[s]), t, 0.8)
        t += s16
        step += 1

section(0.0, GAP[0], intro=True)
add(riser(GAP[1] - GAP[0]), GAP[0], 1.0)
add(impact(), DROP, 1.0)
section(DROP, DUR)

# master: soft clip, fade out last 1.5s
mix = np.tanh(mix * 1.2)
fade = np.ones(N)
fs = int((DUR - 1.5) * SR)
fade[fs:] = np.linspace(1, 0, N - fs)
mix *= fade
mix /= np.max(np.abs(mix)) + 1e-9
mix *= 0.89

# simple stereo width: delay cowbell-ish highs slightly on right
right = np.concatenate([np.zeros(int(0.008 * SR)), mix[:-int(0.008 * SR)]])
st = np.stack([mix, 0.7 * mix + 0.3 * right], axis=1)
pcm = (st * 32767).astype(np.int16)

with wave.open(sys.argv[1], 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print("ok", DUR)
