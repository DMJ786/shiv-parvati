# Gemini Omni face-replacement pipeline

Replaces **only** the man in the light-pink shirt with the identity from `refs/` (crops of the
DP character sheet), using `gemini-omni-1.1-flash` through the `google-genai` Interactions API.
Everyone else in frame is explicitly protected in the prompt and checked by automatic QC.

## Run
    pip install google-genai pillow      # ffmpeg/ffprobe on PATH
    export GEMINI_KEY=...                # read from env only, never printed or saved
    cp /path/to/movie.mp4 work/input.mp4
    python faceswap.py                   # all stages; re-run safely, finished work is cached

Useful flags: `--stages classify,plan` (re-plan only), `--stages edit,assemble`, `--workers 3`,
`--refs a.png b.png c.png`, `--video other.mp4`. Env: `OMNI_MODEL`, `VISION_MODEL`.

## Stages
| stage | what it does | output |
|---|---|---|
| analyze | ffprobe + ffmpeg scene-score cut detection (bursts < 0.5 s merged) | `work/shots.json` |
| classify | `VISION_MODEL` (gemini-3.8-flash) sees 3 frames per shot: is the pink-shirt man's face visible, where, who else is there | `work/shots.json` |
| plan | packs shots into chunks ≤ 9 s, cutting only at shot boundaries; shots > 9 s split evenly; face-less inserts stay untouched; edit chunks < 2 s absorb a neighbour | `work/plan.json` |
| cut | frame-accurate extraction (trim by frame index, CRF 12) | `work/chunks/` |
| edit | Omni `task: edit`, 1080p, chunk + 3 reference angles (+ last edited frame of the previous part when a shot was split). Each take is conformed and scored by a vision QC (identity / others unchanged / performance / realism); up to 3 takes, best kept | `work/edited/`, `work/qc/` |
| conform | every edited clip forced back to the source chunk's exact frame count, 1920×1080, 24 fps; generated audio dropped | — |
| assemble | concat, source audio (if any) remuxed, frame count asserted equal to source; side-by-side compare video | `output/` |

If Gemini's safety filter refuses a chunk (`content_blocked`), the pipeline does **not** retry or
try to work around it: that chunk keeps the original footage and the refusal is recorded in
`work/qc/<chunk>.json`.

## Local backend: FaceFusion (`ff_backend.py`)
For footage Gemini refuses. Runs FaceFusion headless per shot: `inswapper_128` swap + GFPGAN at 35 % blend,
`face_selector_mode=reference` locked on the pink-shirt man (his left→right face index on a reference frame
is chosen by the vision model), box + occlusion masks so hands/coin in front of the face stay intact.
Shots without his face are copied untouched; output is asserted frame-identical in length to the source.

    git clone https://github.com/facefusion/facefusion work/facefusion
    pip install -r work/facefusion/requirements.txt
    python ff_backend.py --shots 0      # one-shot test -> output/ff_shot00_compare.mp4
    python ff_backend.py                # whole movie  -> output/movie_facefusion.mp4

Needs outbound access to github.com and huggingface.co (code + model downloads). CPU works but is slow;
`--no-enhance` roughly halves the time.
