# usage: python -I tools/prep_fx.py  -> build/audio/fx3/*.wav
# Makes the generated sounds sit well: harsh ones lose their top end, sub-only ones gain harmonics so they still read on laptop speakers,
# whooshes get a rounded mid-band air layer of their own (a different sweep each), then everything is levelled to the same active loudness.
import glob, os, subprocess, wave, numpy as np
SR = 48000
HARSH = {'glass_bloom', 'pen_sweep', 'rise_sweep', 'shutter_roll', 'slider_glide', 'typing', 'latch'}
SUB = {'zoom_fly', 'low_flyby', 'dark_sweep', 'bass_bloom', 'snap_whip', 'reverse_snap', 'silk_swipe', 'data_morph', 'tom_thud', 'soft_pop', 'subhit', 'felt_tap', 'deep_press'}
AIR = {'zoom_fly': (240, 1500, 300), 'low_flyby': (900, 320, 180), 'dark_sweep': (160, 700, 200), 'snap_whip': (1200, 500, 260), 'reverse_snap': (220, 1100, 1400),
       'silk_swipe': (500, 1800, 700), 'data_morph': (300, 900, 500), 'air_suck': (400, 1300, 1700)}
os.makedirs('build/audio/fx3', exist_ok=True)
def load(p, lp):
    d = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-af', f'highpass=f=28,lowpass=f={lp},lowpass=f={lp}', '-ar', str(SR), '-ac', '2', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(d, np.float32).reshape(-1, 2).copy()
def air_layer(n, sweep, seed):
    "noise pushed through one gaussian band whose centre travels a->b->c; overlap-added FFT frames"
    rng = np.random.default_rng(seed); N, H = 2048, 512; win = np.hanning(N); out = np.zeros(n + N); fr = np.fft.rfftfreq(N, 1 / SR)
    for i in range(0, n, H):
        p = i / max(n - 1, 1); a, b, c = sweep
        f0 = a + (b - a) * (p / .5) if p < .5 else b + (c - b) * ((p - .5) / .5)
        band = np.exp(-.5 * ((np.log(fr + 1) - np.log(f0)) / .55) ** 2)
        out[i:i + N] += np.fft.irfft(np.fft.rfft(rng.standard_normal(N) * win) * band) * win
    return out[:n]
def envelope(x):
    m = np.abs(x).mean(1); k = int(.03 * SR); return np.convolve(m, np.ones(k) / k, 'same')
def active_rms(x):
    f = int(.02 * SR); e = np.array([np.sqrt((x[i:i + f] ** 2).mean()) for i in range(0, max(len(x) - f, 1), f)]) + 1e-9
    return np.sqrt((np.sort(e)[-max(1, len(e) * 2 // 5):] ** 2).mean())
for seed, p in enumerate(sorted(glob.glob('assets/audio/sfx/*.mp3'))):
    name = os.path.basename(p)[:-4]
    x = load(p, 5200 if name in HARSH else 9500)
    x /= np.abs(x).max() + 1e-9
    if name in SUB:                                   # harmonics from gentle saturation, so the body is heard on small speakers
        x = .55 * x + .45 * np.tanh(2.6 * x) / np.tanh(2.6)
    if name in AIR:
        e = envelope(x); a = air_layer(len(x), AIR[name], seed) * e; a /= np.abs(a).max() + 1e-9
        x = x + np.stack([a, np.roll(a, 90)], 1) * .55
    x *= 10 ** (-16 / 20) / active_rms(x)
    pk = np.abs(x).max()
    if pk > .89: x = np.tanh(x / pk * 1.4) / np.tanh(1.4) * .89
    k = int(.003 * SR); x[:k] *= np.linspace(0, 1, k)[:, None]; k = int(.03 * SR); x[-k:] *= np.linspace(1, 0, k)[:, None]
    with wave.open(f'build/audio/fx3/{name}.wav', 'wb') as o:
        o.setnchannels(2); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    f = np.abs(np.fft.rfft(x.mean(1))) ** 2; fr = np.fft.rfftfreq(len(x), 1 / SR)
    print(f'{name:14s} {len(x) / SR:4.2f}s centroid {(f * fr).sum() / f.sum():6.0f} Hz  >6k {100 * f[fr > 6000].sum() / f.sum():4.1f}%  peak {20 * np.log10(np.abs(x).max()):5.1f}')
