# usage: python -I tools/transcribe.py <16k mono wav> <words.json>  -> prints timed segments
import json, sys, wave, numpy as np
from faster_whisper import WhisperModel
src, out = sys.argv[1], sys.argv[2]
m = WhisperModel("small.en", device="cpu", compute_type="int8")
w = wave.open(src); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
segs, info = m.transcribe(a, word_timestamps=True, vad_filter=False, beam_size=5)
words, lines = [], []
for s in segs:
    lines.append(f"[{s.start:7.2f}-{s.end:7.2f}] {s.text.strip()}")
    for x in s.words:
        words.append({"w": x.word.strip(), "s": round(x.start, 3), "e": round(x.end, 3), "p": round(x.probability, 3)})
json.dump(words, open(out, "w"), indent=0)
print("\n".join(lines))
