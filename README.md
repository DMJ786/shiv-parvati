# Shiv & Parvati — AI short film

A ~57 s epic Indian-mythological short, built stage by stage on fal.ai and finished locally with ffmpeg.

**Deliverables**
- `shiv_parvati_16x9.mp4` — 1080p 16:9 master
- `shiv_parvati_9x16.mp4` — 1080×1920 Reels version, reframed on the subject
- `shiv_parvati_reel.mp4` — 62 s "rotate your phone" Reel: 2.6 s hook (Shiva's eyes on the bell + caption),
  animated rotate prompt, then the full film turned 90° with push-ins, impact zooms, beat pulses,
  punch-in close-ups and a flash + shake on the bell (`python make_video.py reel`, `film/reel.py`)
- `shiv_parvati_reel_cover.jpg` — 1080×1920 cover image for the Reel

## Pipeline

```
pip install -r requirements.txt      # plus ffmpeg on PATH
export FAL_KEY=...

python make_video.py crops           # clean Parvati face refs from parvati_sheet.png   -> refs/
python make_video.py heroes          # Shiva + rishis reference images (Nano Banana Pro)  -> heroes/
python make_video.py keyframes       # one 16:9 still per shot, face-scored               -> keyframes/grid.jpg
python make_video.py video --shots 01 --takes 1          # animate (Kling v3 Pro, 4 s)     -> clips/
python make_video.py music --versions A,B,C              # score (Eleven Music v2.5)      -> music/
python make_video.py edit --music B                      # cut, grade, mix, master, export
```

Every stage is resumable (finished files are skipped); `--redo 03,07` regenerates specific shots.
Shots, prompts, character bibles and the music plan live in `film/shots.py`.

### Face lock
- Four caption-free crops of the character sheet (panels 01, 03, 04, 06) are the identity references.
- Keyframes are generated with Nano Banana Pro edit using those refs; every Parvati keyframe is scored with
  insightface ArcFace (`film/face.py`) and regenerated (up to 4 tries) below a mean cosine of 0.45.
  For scale: the refs score 0.53–0.76 against each other, other people score ≈ 0.0.
- Video takes pass the four refs to Kling as a character element, and each take is scored over 8 frames.

### Edit (`film/edit.py`)
- librosa beat tracking; the climax hit after the near-silent section is detected and becomes the bell.
- A dynamic-programming cut planner puts every cut on a beat (2–4 s shots), hard-cuts into shot 13
  (Shiva's eyes open) on the bell, and uses 0.3 s dissolves only at scene changes.
- Music bus: the score dips to near-silence before the hit, two heartbeats, one temple bell on the cut.
- Kling native ambience sits underneath, −9 dB and side-chain ducked by the music.
- Teal/orange grade, vignette, light temporal grain; Cinzel end card
  "Same Soul. A Different Form. Always Divine." / "HAR HAR MAHADEV".
- Master: −14 LUFS integrated, true peak ≤ −1 dBTP (measured and corrected), H.264 High, AAC 256k.
- 9:16: each shot is cropped around the tracked face (or a hand-set subject path) and scaled to 1080×1920.

`picks.json` records the chosen take per shot. Fonts: Cinzel (SIL OFL, `assets/fonts/`).
