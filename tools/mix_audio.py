# usage: python -I tools/mix_audio.py  -> film/assets/mix.wav at -15 LUFS / -1.5 dBTP
# Voice chain, then the score re-cut on its own bar grid so its sections land on story beats and ducked under the voice, then SFX from build/sfx_cues.json with panning.
import json, os, re, subprocess, wave, numpy as np
os.makedirs('build/audio', exist_ok=True)
TL = json.load(open('build/timeline.json')); CUES = json.load(open('build/sfx_cues.json')); TOTAL = TL['total']
LS = {l['id']: l['start'] for l in TL['lines']}
SR = 48000; BAR = 2.0; PH = 0.05             # assets/audio/score.mp3: 120 BPM, downbeats at 2k + 0.05 s
WS = json.load(open('build/words_fixed.json'))
HIT = LS['title']                            # the title hit is the anchor of the grid: every section below starts on hit + 2k
END = LS['end']
bar = lambda t: HIT + round((t - HIT) / BAR) * BAR
DROP = bar(WS['role'][2]['start'])           # drop lands on "the role"
BRK = bar(WS['things'][6]['start'])          # bass falls away on "not modelled"
CONT = bar(LS['provides'] + 3.4)             # back in as the context example lands
SHIFT = bar(LS['shifting'])
BIG = bar(WS['notposs'][1]['start'])         # biggest section on "not possible before"
GONE = bar(WS['nosystem'][2]['start'])       # "there was no application": everything drops out
BACK = bar(WS['answer'][2]['start'])         # "automatically answer"
def fill(at, a, b, end, db):
    "lay source a..b from edit time at to end, cycling on the bar grid if the source runs out"
    out_, t = [], at; p = a
    while t < end - 1e-6:
        d = min(end - t, b - p); out_.append((t, p, p + d, db)); t += d; p = a if p + d >= b - 1e-6 else p + d
    return out_
# (edit start, source start, source end, gain dB). Sparse sections are lifted so they do not vanish under the voice.
SEGS = [(0.0, 24 + PH - HIT, 24 + PH, 2)]                     # hook: the build that runs straight into the title hit
SEGS += fill(HIT, 24 + PH, 28 + PH, HIT + 4, 3)                # title: first full bars
SEGS += fill(HIT + 4, 8 + PH, 24 + PH, DROP - 8, 3)            # stigma and the fear: groove
SEGS += fill(DROP - 8, 64 + PH, 72 + PH, DROP, 8)              # POV line on a sparse build, the riser running into the drop
SEGS += fill(DROP, 72 + PH, 106 + PH, BRK, 0)                  # loop, sense organ
SEGS += fill(BRK, 56 + PH, 64 + PH, CONT, 6)                   # "not modelled"
SEGS += fill(CONT, 24 + PH, 56 + PH, SHIFT, 0)                 # context, corner cases, scaling
SEGS += fill(SHIFT, 72 + PH - (BIG - SHIFT), 72 + PH, BIG, 7)  # same person, different day: sparse, riser out into the big section
SEGS += fill(BIG, 120 + PH, 152 + PH, GONE, 0)
SEGS += fill(GONE, 160 + PH, 170 + PH, BACK, 8)
SEGS += fill(BACK, 120 + PH + (GONE - BIG), 152 + PH, END, 0)
SEGS += [(END, 172 + PH, 178.1, 5)]                           # final chord on the end card
print('music map:', [(round(a, 2), round(b, 2), round(c, 2)) for a, b, c, _ in SEGS])
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'assets/audio/score.mp3', '-ar', str(SR), '-ac', '2', '-f', 'f32le', 'build/audio/score.f32'], check=True)
music = np.fromfile('build/audio/score.f32', np.float32).reshape(-1, 2)
out = np.zeros((int((TOTAL + 1) * SR), 2), np.float32); XF = int(0.008 * SR)
for at, a, b, db in SEGS:
    x = music[int(a * SR):int(b * SR)].copy()
    x[:XF] *= np.linspace(0, 1, XF)[:, None]; x[-XF:] *= np.linspace(1, 0, XF)[:, None]
    x *= 10 ** (db / 20)
    i = int(at * SR); j = min(i + len(x), len(out)); out[i:j] += x[:j - i]
out[int(TOTAL * SR):] = 0
fo = int(1.0 * SR); e = int(TOTAL * SR); out[e - fo:e] *= np.linspace(1, 0, fo)[:, None] ** 1.5
out.tofile('build/audio/bed.f32')
VOICE = 'highpass=f=85,afftdn=nf=-32:nr=8,equalizer=f=230:t=q:w=1.2:g=-1.5,equalizer=f=3200:t=q:w=1.4:g=2.2,equalizer=f=7000:t=q:w=1.6:g=-1.2,' \
        'dynaudnorm=f=300:g=21:p=0.82:m=5:s=8,acompressor=threshold=-20dB:ratio=2.6:attack=6:release=130:makeup=2'
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'build/vo_raw.wav', '-af', VOICE, '-ar', str(SR), '-ac', '1', 'build/audio/vo.wav'], check=True)
bank = {}
def load(name):
    if name not in bank:
        w = wave.open(f'build/audio/fx3/{name}.wav'); bank[name] = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2) / 32768
    return bank[name]
track = np.zeros((int((TOTAL + 3) * SR), 2), np.float32)
for c in CUES:
    x = load(c['file']) * 10 ** (c['gain'] / 20); n_ = len(x)
    p = np.linspace(c['pan'], c['pan_to'], n_)                       # equal-power pan, travelling with the move on screen
    th = (p + 1) * np.pi / 4; mono = x.mean(1); side = (x[:, 0] - x[:, 1]) * .5
    st_ = np.stack([mono * np.cos(th) * 1.414 + side, mono * np.sin(th) * 1.414 - side], 1)
    i = int(max(c['t'], 0) * SR); j = min(i + n_, len(track)); track[i:j] += st_[:j - i]
track.tofile('build/audio/sfxtrack.f32')
ins = ['-i', 'build/audio/vo.wav', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', 'build/audio/bed.f32', '-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', 'build/audio/sfxtrack.f32']
# the score sits under the voice with a voice-shaped hole in its EQ; a light sidechain lets it surge back in every pause
fc = [f'[0:a]apad=whole_dur={TOTAL},asplit=2[v0][key]',
      '[1:a]volume=-17dB,equalizer=f=2600:t=q:w=1.5:g=-4,equalizer=f=60:t=q:w=1:g=-2[mu0]',
      '[mu0][key]sidechaincompress=threshold=0.04:ratio=2.6:attack=25:release=300:makeup=1[mu]',
      '[v0]aformat=channel_layouts=stereo[vo]',
      f'[vo][mu][2:a]amix=inputs=3:normalize=0:duration=first,atrim=duration={TOTAL}[pre]']
def render(extra, out_):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(fc + [f'[pre]{extra}[out]']), '-map', '[out]', '-ar', str(SR), '-ac', '2', '-c:a', 'pcm_s16le', out_], check=True)
def meas(p):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1]), re.findall(r'Peak:\s+(-?[\d.]+)', r)[-1]
render('anull', 'build/audio/mix_pre.wav'); I, _ = meas('build/audio/mix_pre.wav'); gn = -15.0 - I
render(f'volume={gn:.2f}dB,alimiter=limit=0.84:attack=2:release=60:level=disabled', 'film/assets/mix.wav')
print('pre', I, 'gain', round(gn, 2), 'final', meas('film/assets/mix.wav'))
