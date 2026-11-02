# Production notes

How the edit is built, checked, rendered and revised, plus the decisions and fixes along the way.

## Pipeline

```
raw/rahul.mp4 ─ prep_raw.sh ─▶ build/raw48k.wav · raw16k.wav
      │                                 │
      │                    transcribe · probe · check_edl
      │                                 ▼
      │                             edl.json  (the cut, by hand from word timings)
      ▼                                 │
 build_aroll ◀──────────────────────────┘
      │  shots/ · vo_raw.wav · timeline.json
      ├─▶ frame_aroll ─▶ crops.json · aroll.mp4 (1080p preview)
      ├─▶ align_words ─▶ words.json
      ├─▶ build_4k60 interp ─▶ mi60/ · cut0..3.mp4
      └─▶ build_4k60 frame  ─▶ framed60/ ─▶ aroll4k.mp4
                                               │
                                     check_aroll (footage vs raw, pixel by pixel)
                                               ▼
              make_comp ─▶ film/index.html · sfx_cues.json · words_fixed.json
                                               │
 assets/audio ─ prep_fx ─▶ fx3/ ─ mix_audio ─▶ film/assets/mix.wav
                                               ▼
              hyperframes check ─▶ snapshot ─▶ render 4K 60 fps ─▶ check_sync ─▶ deliverables/
```

## Commands

See the [README](../README.md#rebuild). To change something, edit `edl.json` or `tools/make_comp.py`
and rerun from the changed step. Audio-only changes need `mix_audio.py` and a remux with `-c:v copy`,
not a render. Timings on a 7 GB, 8-core machine: interpolation about 1.5 h, 4K framing about 25 min,
render about 72 min.

## Checking sync

The voice is sample-accurate to the timeline, so sync comes down to whether the picture is where the
timeline says it is. Two checks prove that:

- `tools/check_aroll.py` frames sampled moments of the raw clip exactly as the footage was framed,
  then finds which raw frame matches the footage best. Result on v4: 16 samples, median 0 ms, worst
  42 ms, which is one source frame.
- `tools/check_sync.py` cross-correlates frame-to-frame motion in the render against the footage,
  full-frame shots only, searching 2 s either way. Result on v4: 12 shots, 10 at 0 ms. The other two
  were false readings, at the very start of the file and during a wipe; re-measured clear of those,
  they came in at 42 ms.

Frame counts and transcripts prove nothing about lip sync. See v3 below.

## Version history

**v1, first full render (1080p 30 fps).** The story, the reference's visual system and 66 SFX cues
from 7 sounds.

**v2, QA fixes (1080p 30 fps).** "Intern" was clipped at a join and the opening word caught the tail of
"mainly". Contiguous ranges no longer dip at the join, continuous footage no longer changes framing,
and the score's sparse sections came up 9 dB.

**v3, first round of feedback (4K 60 fps).** Listener cutaways of the other two people, which also
hide jump cuts. A new score re-cut on its bar grid. 32 sounds across 55 cues, none used more than
twice, harsh ones treated. Every seam gets its own transition, the camera follows the diagrams, and
key captions turn solid blue and kick the camera. **This version was out of sync**: see Gotchas.

**v4, second round of feedback (4K 60 fps, final).**
- **Sync:** the picture had drifted up to about 4–5 s behind the voice. Fixed at the source, and now
  verified by the two checks above.
- **Transition at 1:18:** a white panel rising from below with y-blur and a messy top strip, replaced
  by a clean edge wipe. It now sits at about 1:20.
- **Framing:** his jaw was cut off with empty space above. He is lifted, with the rows under his chin
  stretched, and shown at full size in split layouts too.
- **Script recheck:** three trims were too tight, so these are back: "I'm talking about the general
  population", "the way I look at is that", "If we look at the world of analytics". Length went from
  2:09 to 2:16. The music map now places sections from the story's beats, so it survives a re-cut.

## Gotchas

- **Timing gaps from concatenating interpolated shots (v3).** Each interpolated file's duration ran
  slightly longer than its frames, because the interpolator ran out of frames at the shot's end.
  `concat -c copy` joins by file duration, so about 5 s of gaps stacked up across the film while the
  frame count stayed correct. The warning sign was a container duration of 130.2 s against a 129.25 s
  timeline. Fix: 4 handle frames on both sides of each shot, and the join goes through Annex B and
  `-r 60` so every timestamp is simply frame number / 60.
- **Rounding shot lengths.** Frame counts worked out from rounded times overlapped 7 shots by a frame
  and crept to 83 ms by 1:45. `frame60()` uses whole numbers so the lengths always add up.
- **Whisper smears word starts across pauses.** Rahul pauses a lot, so a word's reported start is
  often the previous word's end. `align_words.py` pushes starts forward to where the energy begins,
  and every range was checked by transcribing it alone (`check_edl.py`, `probe.py`). The same check
  found his "um"s at 168.6 s and 441.4 s, which looked like words in the first pass.
- **Hiding the label by cropping pushes him down.** A top-anchored crop hid the burned-in name but left
  his chin near the bottom edge. Removing the label with `delogo` freed the framing.
- **Filling below the frame.** Smearing the last row left visible streaks, especially his neck.
  Stretching only the rows under his chin is invisible on shirt and blurred room, though a hand passing
  through can look slightly stretched, as around 0:19.
- **Odd heights break `pad`.** With yuv420p the stretched height must be even, so `L` is rounded up.
- **Extraction runs out of memory.** HyperFrames extracts all five 4K sources at once. On 7 GB one can
  die after a few frames with `VIDEO_SOURCE_UNRENDERABLE`. Rerun it: extracted frames are cached by
  content, so the second pass has far less to do.
- **SVG line draws.** `pathLength=1` looked all-or-nothing mid-draw under GSAP, so it is 1000. A
  zero-length dash with round caps paints a dot at the path's start, so undrawn lines are opacity 0.
- **`minterpolate` returns slightly fewer frames than asked.** Cutaway clip lengths are read from the
  files, not assumed.
- **Snapshots under heavy load.** While the interpolation ran, `snapshot` showed black or missing
  clips because ffprobe timed out. Re-check on a free CPU before calling it a bug.
- **Mix repeatability.** Two runs of `mix_audio.py` are bit-identical, and the mix matches the
  master's audio to −52 dB, which is AAC encoding noise.
