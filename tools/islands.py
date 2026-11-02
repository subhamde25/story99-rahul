# usage: python -I tools/islands.py  -> build/islands.json + prints speech islands (RMS gate) with the whisper words inside them
import json, wave, numpy as np
w = wave.open('build/raw16k.wav'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
HOP = 160; rms = np.sqrt(np.convolve(a ** 2, np.ones(HOP * 2) / (HOP * 2), 'same')[::HOP])     # 10 ms hop
db = 20 * np.log10(rms + 1e-6)
W = json.load(open('build/raw_words.json'))
SECTIONS = [(40.30, 204.10), (250.30, 305.15), (417.40, 464.50)]
out = []
for sa, sb in SECTIONS:
    seg = db[int(sa * 100):int(sb * 100)]
    floor = np.percentile(seg, 12); peak = np.percentile(seg, 95); th = floor + (peak - floor) * 0.30
    on = seg > th
    i = 0; isl = []
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and (on[j] or on[j:j + 14].any()): j += 1     # bridge gaps < 140 ms
            isl.append((sa + i / 100, sa + j / 100)); i = j
        else: i += 1
    isl = [x for x in isl if x[1] - x[0] > 0.1]
    print(f'## section {sa}-{sb} floor {floor:.1f} peak {peak:.1f} th {th:.1f}')
    for s, e in isl:
        ws = [x['w'] for x in W if s - 0.15 <= (x['s'] + x['e']) / 2 <= e + 0.15]
        print(f'{s:7.2f}-{e:7.2f} ({e - s:4.2f}) {" ".join(ws)}')
        out.append({'s': round(s, 2), 'e': round(e, 2), 'w': ws})
json.dump(out, open('build/islands.json', 'w'), indent=0)
