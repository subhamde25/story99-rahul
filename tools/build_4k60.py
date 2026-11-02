# usage: python -I tools/build_4k60.py interp | frame   -> film/assets/aroll4k.mp4 + film/assets/cut0..3.mp4 (3840x2160, 60 fps)
# interp: 24 -> 60 fps per shot, from the raw clip with handle frames on both sides, so the interpolator never runs out of frames at a shot's end.
#         Results are cached by raw position in build/mi60, so a re-cut or reframe only redoes what changed. Shots behind full-screen panels just repeat frames.
# frame:  reframes each cached shot to 4K and joins them. The join rewrites every timestamp as frame number / 60, so sync can never drift:
#         concatenating the files by their own durations is what put the picture seconds behind the voice in v3.
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
TL = json.load(open('build/timeline.json')); FPS = TL['fps']; RAW = 'raw/rahul.mp4'
GRADE = 'eq=contrast=1.05:saturation=1.03:gamma=0.985,colorbalance=rm=-0.012:bm=0.012:bs=0.015,unsharp=7:7:0.45:7:7:0'
DELOGO = 'delogo=x=18:y=1020:w=176:h=42:show=0'
MI = 'minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1'
PADX, PADB, W, H = 240, 480, 1920, 1080
def framing(c):
    s0, L = c['s0'], c['L']
    stretch = f'split[a][b];[a]crop={W}:{s0}:0:0[t];[b]crop={W}:{H - s0}:0:{s0},scale={W}:{H - s0 + L}:flags=bicubic[u];[t][u]vstack' if L else 'null'
    return f'{stretch},pad={W + 2 * PADX}:{H + L}:{PADX}:0,fillborders=left={PADX}:right={PADX}:mode=mirror,crop={c["w"]}:{c["h"]}:{c["x"] + PADX}:{c["y"]}'
HIDDEN = {'title', 'end', 'loop', 'sense', 'shift', 'question'}; HANDLE = 4
os.makedirs('build/mi60', exist_ok=True); os.makedirs('build/framed60', exist_ok=True)
# 60 fps frame number for a count of source frames, in whole numbers so the shot lengths telescope exactly: rounded times once overlapped 7 shots by a frame
def frame60(k): return (k * 5 + 1) // 2
CUM = [0]
for s_ in TL['shots']: CUM.append(CUM[-1] + s_['f'])
def frames_of(i): return frame60(CUM[i + 1]) - frame60(CUM[i])
def count(p):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v', '-count_packets', '-show_entries', 'stream=nb_read_packets', '-of', 'csv=p=0', p], capture_output=True, text=True).stdout.split()
    return int(r[0].strip(',')) if r else -1
def key(s): return f'build/mi60/{s["a"]}_{s["f"]}_{"d" if s["layout"] in HIDDEN else "m"}.mp4'
def interp(i):
    s = TL['shots'][i]; out = key(s)
    if os.path.exists(out) and os.path.getsize(out) > 1000: return
    tmp = out + '.part.mp4'
    if s['layout'] in HIDDEN:
        cmd = ['-ss', f'{s["a"] / FPS:.5f}', '-t', f'{s["f"] / FPS:.5f}', '-i', RAW, '-vf', f'{DELOGO},fps=60']
    else:
        a0 = max(0, s['a'] - HANDLE); pre = s['a'] - a0
        cmd = ['-ss', f'{a0 / FPS:.5f}', '-t', f'{(pre + s["f"] + HANDLE) / FPS:.5f}', '-i', RAW,
               '-vf', f'{DELOGO},{MI},trim=start={pre / FPS:.5f}:end={(pre + s["f"]) / FPS:.5f},setpts=N/60/TB']
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *cmd, '-an', '-map', '0:v:0', '-fps_mode', 'passthrough', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '11', '-g', '30', '-bf', '0', '-threads', '2', tmp], check=True)
    os.replace(tmp, out); print(f'{i:03d} {s["line"]:>10} {s["f"]:4d}f', flush=True)
CUTS = [(416.5, 417.33, 1.0), (38.2, 40.2, 1.0), (249.1, 250.2, 1.0), (344.35, 345.0, 1.54)]    # raw in, raw out, slow-down
CUTGRADE = 'eq=contrast=1.03:saturation=0.94:gamma=1.0,unsharp=7:7:0.4:7:7:0'
def cut(i):
    a, b, slow = CUTS[i]; out = f'film/assets/cut{i}.mp4'
    if os.path.exists(out) and os.path.getsize(out) > 1000: return
    vf = f'trim=0:{b - a:.3f},setpts=PTS-STARTPTS,crop=1778:1000:71:0,setpts={slow}*PTS,{MI},scale=3840:2160:flags=lanczos,{CUTGRADE},format=yuv420p'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{a:.3f}', '-i', RAW, '-an', '-map', '0:v:0', '-vf', vf, '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-g', '60', '-bf', '0', out + '.part.mp4'], check=True)
    os.replace(out + '.part.mp4', out)
def frame(i):
    s = TL['shots'][i]; c = CR[i]; N = frames_of(i); out = f'build/framed60/{i:03d}.mp4'
    if '--only-mismatch' in sys.argv and os.path.exists(out) and count(out) == N: return
    vf = f'{framing(c)},tpad=stop_mode=clone:stop=-1,setpts=N/60/TB,scale=3840:2160:flags=lanczos,{GRADE},format=yuv420p'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', key(s), '-vf', vf, '-frames:v', str(N), '-fps_mode', 'passthrough', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-g', '60', '-bf', '0', '-threads', '3', out], check=True)
if sys.argv[1] == 'interp':
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(cut, range(len(CUTS)))); list(ex.map(interp, range(len(TL['shots']))))
    print('INTERP DONE', flush=True)
else:
    CR = json.load(open('build/crops.json'))
    with ThreadPoolExecutor(3) as ex: list(ex.map(frame, range(len(TL['shots']))))
    open('build/framed60.txt', 'w').write(''.join(f"file 'framed60/{i:03d}.mp4'\n" for i in range(len(TL['shots']))))
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', 'build/framed60.txt', '-c', 'copy', '-bsf:v', 'h264_mp4toannexb', '-f', 'h264', 'build/aroll4k.h264'], check=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-r', '60', '-i', 'build/aroll4k.h264', '-c', 'copy', '-movflags', '+faststart', 'film/assets/aroll4k.mp4'], check=True)
    print('FRAME DONE', sum(count(f'build/framed60/{i:03d}.mp4') for i in range(len(TL['shots']))), 'frames, expected', frame60(CUM[-1]), flush=True)
