# Assets

Every file the edit uses: where it came from, its status, how it was processed and where it lands.

**Storage:** committed are the final master (`deliverables/*.mp4`, Git LFS), the score and SFX
library, the SD watermarks, the face-detection model and the generated `film/index.html`. The
supplied clip (`raw/`), the reference (`ref/`), everything built from them (`build/`,
`film/assets/aroll*.mp4`, `film/assets/cut*.mp4`, `film/assets/mix.wav`), Akaike's logos and drafts
(`renders/`) are not. `tools/` recreates them, given the clip.

## 1. Supplied clip (Story99, not committed)

`raw/rahul.mp4`: a video call in active-speaker view, 1920×1080, 24 fps, 7:44.6, PCM stereo at 48 kHz.
Video and audio both start at 0 and are in sync at the source. `tools/prep_raw.sh` pulls
`build/raw48k.wav` (used for the voice) and `build/raw16k.wav` (used for transcription).

### Rahul's shots → `film/assets/aroll4k.mp4`

Every range in `edl.json` becomes one frame-accurate shot (`tools/build_aroll.py`). Each shot is then:

1. **Burned-in label removed:** `delogo` over the "Rahul Thota" name in the raw frame.
2. **Interpolated 24 → 60 fps** with `minterpolate` (motion-compensated), from the raw clip with 4
   handle frames on both sides, so nothing blends across a cut. Shots behind full-screen panels just
   repeat frames. Cached in `build/mi60/` by raw position.
3. **Reframed:** the raw has him low in frame with his chin near the bottom edge, so the face is
   detected (YuNet) and the picture lifted until the face centre sits at 44.5% across and 52% down.
   Room below comes from stretching only the shirt and shoulder rows under his chin, up to about 3×
   on the tightest shots. The sides fill by mirroring the blurred room. Continuous footage keeps its
   framing, so holds and joins never jump.
4. **Zoomed on key lines:** 1.05–1.08× on "agency", "everything", the POV line, "sense organ",
   "works", "not possible" and "now".
5. **Graded and scaled:** `eq=contrast=1.05:saturation=1.03:gamma=0.985`, a small colour-balance
   move, Lanczos to 3840×2160 and a light unsharp.

### Listener cutaways → `film/assets/cut0..3.mp4`

Four moments from the raw, cropped to drop the burned-in names, slightly desaturated, interpolated to
60 fps and scaled to 4K. Timings are in [`BREAKDOWN.md`](../BREAKDOWN.md).

### Voice → `film/assets/mix.wav`

Cut from the same ranges with 12 ms fades at each join, then `highpass`, light `afftdn`, three EQ
moves, `dynaudnorm` and `acompressor` (`tools/mix_audio.py`).

## 2. Reference (not committed)

The LinkedIn post linked in [`BRIEF.md`](../BRIEF.md), used only for study. Nothing from it is in the film.

## 3. Brand

| File | Source | Status |
|---|---|---|
| `film/assets/logo.svg`, `logo_white.svg`, `logo_allwhite.svg` | Akaike's primary logo SVG from akaike.ai; the other two are recolours for dark panels and the end card (`tools/fetch_logo.py`) | fetched, not committed |
| `film/assets/sd_white.png`, `sd_dark.png` | the author's SD watermark, trimmed, plus a dark recolour for white panels | committed |

Fonts are Inter and Open Sans, bundled with HyperFrames.

## 4. Score

`assets/audio/score.mp3`: 178 s, 120 BPM, generated in Runway from a brief asking for a driving
tech-cinematic instrumental with energy in the lows and low-mids, so a voice sits on top. It was
chosen over an exact-length take because it has real sections to cut between; the other take stayed
flat from 12 s to 124 s. The re-cut is in [`BREAKDOWN.md`](../BREAKDOWN.md). In the mix it sits at
−17 dB with a 4 dB dip at 2.6 kHz and a light sidechain under the voice.

## 5. Sound effects

`assets/audio/sfx/`: 32 short sounds generated in Runway, one prompt each. Three (`subhit`, `typing`,
`chime`) carry over from the first round; the other 29 were made for the second round, after the first
set proved repetitive and harsh. `tools/prep_fx.py` measures and treats them into `build/audio/fx3/`:

| Treatment | Sounds | Why |
|---|---|---|
| low-pass at 5.2 kHz, twice | glass bloom, pen sweep, rise sweep, shutter roll, slider glide, typing, latch | they measured harsh, with too much energy above 6 kHz |
| gentle saturation | zoom fly, low fly-by, dark sweep, bass bloom, snap whip, reverse snap, silk swipe, data morph, tom thud, soft pop, sub hit, felt tap, deep press | nearly all sub-bass, so they would vanish on laptop speakers |
| a rounded mid-band air layer, with its own sweep per sound | zoom fly, low fly-by, dark sweep, snap whip, reverse snap, silk swipe, data morph, air suck | gives the whooshes an audible body without hiss |
| levelled | all | to the same active loudness, peak limited |

## 6. Motion and graphics

All of it is drawn in code in `tools/make_comp.py`: panels, cards, inline SVG icons, charts, the crowd,
the network background, the slider, captions. There is no stock footage and there are no stock assets.
Every cue is a word time from `build/words.json`, so a re-cut moves the graphics with it.

## 7. Models and tools

| Item | Use |
|---|---|
| `tools/models/yunet.onnx` | OpenCV's YuNet face detector, for framing |
| faster-whisper `small.en` | word timings, cut verification and the speech check on the final mix |
| ffmpeg | cutting, interpolation, framing, grading, joining, the voice chain and the mix |
| HyperFrames 0.8.226 | composition and rendering |
