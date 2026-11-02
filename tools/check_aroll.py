# usage: python -I tools/check_aroll.py [film/assets/aroll4k.mp4]
# Proves the footage is in sync before spending an hour on a render. Each sampled shot is framed exactly as the raw clip would be, so frames can be
# compared pixel for pixel: the raw frame that matches best must be the one the timeline (and so the voice) expects at that moment.
import json, subprocess, sys, numpy as np
path = sys.argv[1] if len(sys.argv) > 1 else 'film/assets/aroll4k.mp4'
TL = json.load(open('build/timeline.json')); CR = json.load(open('build/crops.json')); FPS = TL['fps']
PADX, W, H = 240, 1920, 1080; S = 4
DELOGO = 'delogo=x=18:y=1020:w=176:h=42:show=0'
HIDDEN = {'title', 'end', 'loop', 'sense', 'shift', 'question'}
def framing(c):
    s0, L = c['s0'], c['L']
    stretch = f'split[a][b];[a]crop={W}:{s0}:0:0[t];[b]crop={W}:{H - s0}:0:{s0},scale={W}:{H - s0 + L}:flags=bicubic[u];[t][u]vstack' if L else 'null'
    return f'{stretch},pad={W + 2 * PADX}:{H + L}:{PADX}:0,fillborders=left={PADX}:right={PADX}:mode=mirror,crop={c["w"]}:{c["h"]}:{c["x"] + PADX}:{c["y"]}'
def run(args):
    d = subprocess.run(['ffmpeg', '-v', 'error', *args, '-f', 'rawvideo', '-'], capture_output=True).stdout
    return np.frombuffer(d, np.uint8).reshape(-1, 270, 480).astype(np.float32)
meta = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets,r_frame_rate,duration', '-of', 'compact=nk=1', path], capture_output=True, text=True).stdout.split('\n')[0]
total_f = sum(s['f'] for s in TL['shots'])
print('file', path, meta, '| expected frames', (total_f * 5 + 1) // 2)
errs = []
shots = [i for i, s in enumerate(TL['shots']) if s['layout'] not in HIDDEN and not s.get('gap') and s['f'] >= 30]
print('edit time  line        offset ms (+ = picture late)   match error (lower is sharper)')
for i in shots[:: S]:
    s, c = TL['shots'][i], CR[i]
    for frac in (0.25, 0.75):
        n = round(s['f'] * frac); t = s['start'] + n / FPS                   # a source-frame instant, so interpolation is not in play
        v = run(['-ss', f'{t:.5f}', '-i', path, '-frames:v', '1', '-vf', 'scale=480:270,format=gray'])[0]
        R = 10; a = max(0, s['a'] + n - R)
        raw = run(['-ss', f'{a / FPS:.5f}', '-i', 'raw/rahul.mp4', '-map', '0:v:0', '-frames:v', str(2 * R + 1), '-vf', f'{DELOGO},{framing(c)},scale=480:270,format=gray'])
        e = [((v - x)[40:230, 80:400] ** 2).mean() for x in raw]; k = int(np.argmin(e))
        off = (s['a'] + n - (a + k)) / FPS * 1000; errs.append(off)
        print(f'{t:9.2f}  {s["line"]:>10} {off:10.0f} {e[k]:18.1f}', flush=True)
errs = np.array(errs)
print(f'samples {len(errs)} | median {np.median(errs):.0f} ms | worst {np.abs(errs).max():.0f} ms | within one source frame (42 ms): {100 * (np.abs(errs) <= 42).mean():.0f}%')
