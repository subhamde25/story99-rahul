# usage: python -I tools/align_words.py  -> build/words.json
# Word timings on the edit clock. Whisper runs per line so a word can never cross a line; the script's spelling wins, whisper's timing wins.
# Whisper smears a word's start back across a pause, so each word start is pushed forward to where the energy actually begins.
import json, re, wave, difflib, numpy as np
from faster_whisper import WhisperModel
TL = json.load(open('build/timeline.json'))
w = wave.open('build/vo_raw.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
SR = w.getframerate()
HOP = int(SR * 0.01); rms = np.sqrt(np.convolve(a ** 2, np.ones(HOP * 2) / (HOP * 2), 'same')[::HOP]); db = 20 * np.log10(rms + 1e-6)
m = WhisperModel('small.en', device='cpu', compute_type='int8')
a16 = a[::3].copy()
norm = lambda t: re.sub(r"[^a-z']", '', t.lower())
out = []
for li, l in enumerate(TL['lines']):
    if not l['text']: continue
    ref = l['text'].split()
    seg = a16[int(l['start'] * 16000):int(l['end'] * 16000)]
    r, _ = m.transcribe(np.pad(seg, (0, 800)), word_timestamps=True, initial_prompt=l['text'], condition_on_previous_text=False)
    hs = [{'w': x.word.strip(), 's': l['start'] + x.start, 'e': l['start'] + x.end} for g in r for x in g.words]
    sm = difflib.SequenceMatcher(a=[norm(x) for x in ref], b=[norm(h['w']) for h in hs], autojunk=False)
    t = [None] * len(ref)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ('equal', 'replace') and j2 > j1:
            for k in range(i2 - i1):
                j = j1 + min(k, j2 - j1 - 1); t[i1 + k] = [hs[j]['s'], hs[j]['e']]
    for k in range(len(ref)):
        if t[k] is None:
            prev = next((t[j][1] for j in range(k - 1, -1, -1) if t[j]), l['start'])
            nxt = next((t[j][0] for j in range(k + 1, len(ref)) if t[j]), l['end'])
            t[k] = [prev, max(prev + 0.08, (prev + nxt) / 2)]
    for k, word in enumerate(ref):
        s, e = t[k]
        i, i_end = int(s * 100), int(max(e, s + 0.05) * 100)                # first frame inside the word that is clearly voiced
        th = np.percentile(db[int(l['start'] * 100):int(l['end'] * 100)], 45)
        while i < i_end - 2 and db[i] < th: i += 1
        out.append({'line': l['id'], 'i': k, 'text': word, 'start': round(max(l['start'], i / 100), 3), 'end': round(min(l['end'], e), 3)})
json.dump(out, open('build/words.json', 'w'), indent=0)
print(len(out), 'words')
for l in TL['lines']:
    print(l['id'], round(l['start'], 2), ' '.join(f"{x['text']}@{x['start']:.2f}" for x in out if x['line'] == l['id']))
