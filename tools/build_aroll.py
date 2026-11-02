# usage: python -I tools/build_aroll.py  -> build/aroll_raw.mp4 (edit order, 24 fps), build/vo_raw.wav, build/timeline.json
# Every kept range becomes one frame-accurate shot. A line's "gap" holds picture (continues the raw frames of the previous shot) over silence.
import json, os, subprocess, wave, math, numpy as np
from concurrent.futures import ThreadPoolExecutor
E = json.load(open('edl.json')); FPS = E['fps']
RAW = 'raw/rahul.mp4'; os.makedirs('build/shots', exist_ok=True)
w = wave.open('build/raw16k.wav'); w.close()
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', 'build/raw48k.wav', '-ac', '1', '-c:a', 'pcm_f32le', '-f', 'f32le', 'build/raw48k.f32'], check=True)
mono = np.fromfile('build/raw48k.f32', np.float32)
SR = 48000; FS = SR // FPS; FADE = int(0.012 * SR)
shots, audio, t = [], [], 0; last_end_f = None; lines = []; open_tail = None
def fade_out(x):
    k = min(FADE, len(x) // 2); x[-k:] *= np.linspace(1, 0, k)
for l in E['lines']:
    ls = t; rs = []
    for s, e in l['r']:
        a, b = math.floor(s * FPS), math.ceil(e * FPS)
        if last_end_f is not None and a < last_end_f and a > last_end_f - 3: a = last_end_f   # contiguous ranges never repeat a frame
        x = mono[a * FS:b * FS].copy(); k = min(FADE, len(x) // 2)
        contig = open_tail is not None and a == last_end_f               # the same take carrying on: no fade, so no dip mid-word
        if not contig:
            if open_tail is not None: fade_out(open_tail)
            x[:k] *= np.linspace(0, 1, k)
        audio.append(x); open_tail = x; dur = (b - a) / FPS
        shots.append({'line': l['id'], 'layout': l['layout'], 'raw': a / FPS, 'f': b - a, 'start': round(t, 4), 'a': a})
        rs.append((a, b)); t += dur; last_end_f = b
    gap_f = round(l.get('gap', 0) * FPS)
    if gap_f:
        if open_tail is not None: fade_out(open_tail); open_tail = None
        audio.append(np.zeros(gap_f * FS, np.float32))
        shots.append({'line': l['id'], 'layout': l['layout'], 'raw': last_end_f / FPS, 'f': gap_f, 'start': round(t, 4), 'a': last_end_f, 'gap': True})
        last_end_f += gap_f; t += gap_f / FPS
    lines.append({'id': l['id'], 'layout': l['layout'], 'text': l['text'], 'start': round(ls, 4), 'end': round(t - gap_f / FPS, 4), 'hold_end': round(t, 4),
                  'ranges': [[a / FPS, b / FPS] for a, b in rs]})
if open_tail is not None: fade_out(open_tail)
vo = np.concatenate(audio)
with wave.open('build/vo_raw.wav', 'wb') as o:
    o.setnchannels(1); o.setsampwidth(2); o.setframerate(SR); o.writeframes((np.clip(vo, -1, 1) * 32767).astype(np.int16).tobytes())
def cut(i_s):
    i, s = i_s; out = f'build/shots/{i:03d}.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{s["a"] / FPS:.5f}', '-i', RAW, '-frames:v', str(s['f']), '-an', '-map', '0:v:0', '-r', str(FPS),
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '10', '-pix_fmt', 'yuv420p', out], check=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(cut, enumerate(shots)))
open('build/shots.txt', 'w').write(''.join(f"file 'shots/{i:03d}.mp4'\n" for i in range(len(shots))))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'build/shots.txt', '-c', 'copy', 'build/aroll_raw.mp4'], check=True)
os.remove('build/raw48k.f32')
json.dump({'fps': FPS, 'total': round(t, 4), 'shots': shots, 'lines': lines}, open('build/timeline.json', 'w'), indent=0)
print('shots', len(shots), 'total', round(t, 2), 'vo', round(len(vo) / SR, 2))
