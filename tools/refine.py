# usage: python -I tools/refine.py  -> re-transcribes each rough slice alone (tighter word timing than the full-file pass); prints words + 40 ms energy valleys
import json, wave, numpy as np
from faster_whisper import WhisperModel
w = wave.open('build/raw16k.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
m = WhisperModel('small.en', device='cpu', compute_type='int8')
SL = [(50.5, 55.0), (60.3, 70.0), (73.5, 87.0), (87.3, 97.5), (100.0, 108.2), (107.3, 119.6), (123.6, 133.0), (133.0, 151.0), (154.0, 162.6), (165.0, 187.6), (187.4, 201.2), (417.4, 426.2), (426.0, 441.2), (441.0, 451.5), (451.5, 464.2)]
out = []
for s, e in SL:
    x = a[int(s * 16000):int(e * 16000)]
    segs, _ = m.transcribe(x, word_timestamps=True, beam_size=5, condition_on_previous_text=False)
    ws = [{'w': g.word.strip(), 's': round(s + g.start, 2), 'e': round(s + g.end, 2)} for sg in segs for g in sg.words]
    out.append({'s': s, 'e': e, 'words': ws})
    print(f'== {s}-{e}\n' + ' '.join(f"{g['w']}[{g['s']:.2f}-{g['e']:.2f}]" for g in ws), flush=True)
json.dump(out, open('build/refined.json', 'w'), indent=0)
