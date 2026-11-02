# usage: python -I tools/frame_aroll.py  -> build/crops.json + film/assets/aroll.mp4 (1080p preview)
# Finds the face in every shot and crops so the face lands on one canonical point, so the HTML layouts only ever tween one transform.
# The raw has him low in frame, chin close to the bottom edge, so the picture is lifted: the burned-in Zoom label is removed, and the room the lift
# needs below the frame comes from gently stretching only the shirt and shoulder rows under his chin. Sides fill by mirroring the blurred room.
import cv2, json, os, subprocess, numpy as np
from concurrent.futures import ThreadPoolExecutor
TL = json.load(open('build/timeline.json')); W, H = 1920, 1080
CX, CY = 0.445, 0.52                          # where the face centre sits in the output frame
PADX, PADB = 240, 480
ZOOM = {'agency': 1.05, 'everything': 1.08, 'pov': 1.05, 'organ': 1.08, 'works': 1.06, 'notposs': 1.05, 'now': 1.08}
GRADE = 'eq=contrast=1.05:saturation=1.03:gamma=0.985,colorbalance=rm=-0.012:bm=0.012:bs=0.015'
DELOGO = 'delogo=x=18:y=1020:w=176:h=42:show=0'
def framing(c):
    s0, L = c['s0'], c['L']
    stretch = f'split[a][b];[a]crop={W}:{s0}:0:0[t];[b]crop={W}:{H - s0}:0:{s0},scale={W}:{H - s0 + L}:flags=bicubic[u];[t][u]vstack' if L else 'null'
    return f'{stretch},pad={W + 2 * PADX}:{H + L}:{PADX}:0,fillborders=left={PADX}:right={PADX}:mode=mirror,crop={c["w"]}:{c["h"]}:{c["x"] + PADX}:{c["y"]}'
det = cv2.FaceDetectorYN_create('tools/models/yunet.onnx', '', (0, 0), 0.6)
def face(path, frames):
    cap = cv2.VideoCapture(path); out = []
    for i in sorted({0, frames // 2, max(frames - 1, 0)}):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i); ok, fr = cap.read()
        if not ok: continue
        im = cv2.resize(fr, None, fx=.25, fy=.25); det.setInputSize((im.shape[1], im.shape[0]))
        _, fs = det.detect(im)
        if fs is not None and len(fs):
            f = max(fs, key=lambda r: r[2]); out.append(((f[0] + f[2] / 2) * 4, (f[1] + f[3] / 2) * 4, f[2] * 4, f[3] * 4))
    cap.release()
    return np.median(np.array(out), axis=0) if out else None
crops, last = [], (900, 620, 400, 500)
for i, s in enumerate(TL['shots']):
    z = ZOOM.get(s['line'], 1.0)
    if i and s['a'] == TL['shots'][i - 1]['a'] + TL['shots'][i - 1]['f'] and z == crops[-1]['z']:
        crops.append(dict(crops[-1])); continue                      # continuous footage keeps its framing, so holds and joins never jump
    f = face(f'build/shots/{i:03d}.mp4', s['f'])
    if f is None: f = last
    last = f
    cw, ch = round(W / z / 2) * 2, round(H / z / 2) * 2
    x = float(np.clip(f[0] - CX * cw, -PADX, W - cw + PADX)); y = float(np.clip(f[1] - CY * ch, 0, H + PADB - ch))
    chin = f[1] + f[3] / 2
    crops.append({'z': z, 'x': round(x), 'y': round(y), 'w': cw, 'h': ch, 'fx': round(float(f[0])), 'fy': round(float(f[1])), 'fh': round(float(f[3])),
                  's0': int(min(1010, chin + 20)) // 2 * 2, 'L': (max(0, round(y) + ch - H) + 1) // 2 * 2})
json.dump(crops, open('build/crops.json', 'w'), indent=0)
os.makedirs('build/framed', exist_ok=True)
def enc(i):
    c = crops[i]; out = f'build/framed/{i:03d}.mp4'
    vf = f'{DELOGO},{framing(c)},scale={W}:{H}:flags=lanczos,{GRADE},format=yuv420p'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'build/shots/{i:03d}.mp4', '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '14', '-g', '24', '-bf', '0', out], check=True)
with ThreadPoolExecutor(2) as ex: list(ex.map(enc, range(len(crops))))
open('build/framed.txt', 'w').write(''.join(f"file 'framed/{i:03d}.mp4'\n" for i in range(len(crops))))
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'build/framed.txt', '-c', 'copy', '-movflags', '+faststart', 'film/assets/aroll.mp4'], check=True)
ch = [(c['fy'] + c['fh'] / 2 - c['y']) * c['z'] / H for c in crops]
print('face cx', min(c['fx'] for c in crops), max(c['fx'] for c in crops), '| cy', min(c['fy'] for c in crops), max(c['fy'] for c in crops), '| face box bottom in output, %:', round(min(ch) * 100), 'to', round(max(ch) * 100), '| largest lift', max(c['y'] for c in crops), '| most stretched rows', max(round((H - c['s0'] + c['L']) / (H - c['s0']), 2) for c in crops))
