# usage: python -I tools/check_sync.py <rendered.mp4>
# Checks the finished render against the footage the voice was cut to. tools/check_aroll.py proves that footage matches the raw clip pixel for pixel;
# this proves the render shows it at the right moment. For each long shot of Rahul, the frame-to-frame motion of the render is cross-correlated with the
# same stretch of the footage, searching 2 s either way. Any lag is picture sync error. Cutaways are skipped: those are other people, silent on purpose.
import json, re, subprocess, sys, numpy as np
TL = json.load(open('build/timeline.json')); FPS = TL['fps']; path = sys.argv[1]; REF = 'film/assets/aroll4k.mp4'; REACH = 2.0
VISIBLE = {'full', 'fear', 'reco', 'scale', 'ask'}
page = open('film/index.html', encoding='utf-8').read()
CUTS = [(float(a), float(a) + float(d)) for a, d in re.findall(r'id="cut\d"[^>]*?data-start="([\d.]+)" data-duration="([\d.]+)"', page)]
def motion(src, t, dur):
    "per-frame change of the centre of the picture, at the footage's own 24 fps"
    d = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{max(t, 0):.4f}', '-t', f'{dur:.4f}', '-i', src, '-an', '-map', '0:v:0', '-vf', f'fps={FPS},scale=160:90,crop=52:50:18:18,format=gray', '-f', 'rawvideo', '-'], capture_output=True).stdout
    a = np.frombuffer(d, np.uint8).reshape(-1, 50, 52).astype(np.float32)
    return np.abs(np.diff(a, axis=0)).mean((1, 2))
print(' edit time  line        lag ms (+ = picture late)   correlation')
rows = []
for s in TL['shots']:
    dur = s['f'] / FPS
    if s['layout'] != 'full' or s.get('gap') or dur < 1.0: continue
    if any(a < s['start'] + dur and s['start'] < b for a, b in CUTS): continue
    t0, t1 = s['start'] + 0.12, dur - 0.24                         # stay clear of the transitions at the shot's edges
    v = motion(path, t0, t1); r = motion(REF, t0 - REACH, t1 + 2 * REACH)
    if len(v) < 12 or v.std() < 1e-3: continue
    vz = (v - v.mean()) / (v.std() + 1e-6); best, lag = -9, 0
    for k in range(0, len(r) - len(v) + 1):
        w = r[k:k + len(v)]; c = float((vz * (w - w.mean()) / (w.std() + 1e-6)).mean())
        if c > best: best, lag = c, k
    ms = (round(REACH * FPS) - lag) / FPS * 1000
    rows.append((ms, best))
    print(f'{s["start"]:9.2f}  {s["line"]:>10} {ms:12.0f} {best:18.2f}', flush=True)
lag = np.array([m for m, _ in rows]); cor = np.array([c for _, c in rows])
print(f'shots {len(rows)} | median lag {np.median(lag):.0f} ms | worst {np.abs(lag).max():.0f} ms | within one source frame: {100 * (np.abs(lag) <= 42).mean():.0f}% | mean correlation {cor.mean():.2f}')
