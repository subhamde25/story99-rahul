# usage: python -I tools/check_edl.py [line ids...]  -> transcribes each edl line's kept audio on its own so wrong word boundaries show up as text
import json, sys, wave, re, numpy as np
from faster_whisper import WhisperModel
E = json.load(open('edl.json')); only = set(sys.argv[1:])
w = wave.open('build/raw16k.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
m = WhisperModel('small.en', device='cpu', compute_type='int8')
total = 0
for l in E['lines']:
    dur = sum(e - s for s, e in l['r']); total += dur
    if only and l['id'] not in only: continue
    x = np.concatenate([np.pad(a[int(s * 16000):int(e * 16000)], (0, 800)) for s, e in l['r']])
    segs, _ = m.transcribe(x, beam_size=5, condition_on_previous_text=False, initial_prompt=None, vad_filter=False)
    got = ' '.join(s.text.strip() for s in segs)
    print(f"{l['id']:>10} {dur:5.2f}s | {got}\n{'':>18}| {l['text']}", flush=True)
print('total speech', round(total, 2))
