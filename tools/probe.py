# usage: python -I tools/probe.py a-b a-b ...  -> what whisper hears in each exact window + a coarse energy strip (one char per 40 ms)
import sys, wave, numpy as np
from faster_whisper import WhisperModel
w = wave.open('build/raw16k.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
m = WhisperModel('small.en', device='cpu', compute_type='int8')
for arg in sys.argv[1:]:
    s, e = map(float, arg.split('-'))
    x = a[int(s * 16000):int(e * 16000)]
    segs, _ = m.transcribe(np.pad(x, (0, 1600)), beam_size=5, condition_on_previous_text=False)
    print(f'{arg}: {" ".join(t.text.strip() for t in segs)!r}')
    fr = [20 * np.log10(np.sqrt((x[i:i + 640] ** 2).mean()) + 1e-6) for i in range(0, len(x) - 640, 640)]
    print('   ' + ''.join(' .:-=+*#%@'[int(np.clip((v + 70) / 7, 0, 9))] for v in fr), flush=True)
