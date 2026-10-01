# Local face replacement (InsightFace + INSwapper)

Replaces **only** the main character (the man in the light-pink shirt) with the identity in `face.png`,
entirely on your machine. No generative video API is used.

## Install
    python -m venv .venv && source .venv/bin/activate        # Python >= 3.9
    pip install -r requirements.txt                          # NVIDIA: swap onnxruntime for onnxruntime-gpu
    # ffmpeg + ffprobe must be on PATH

Models go in `models/` (downloaded automatically from the official releases on first run, or place them manually):

| file | source |
|---|---|
| `models/buffalo_l/` (SCRFD detector, ArcFace w600k_r50, 3D-68 landmarks) | github.com/deepinsight/insightface releases `model-zoo/buffalo_l.zip` |
| `models/inswapper_128.onnx` | github.com/facefusion/facefusion-assets releases `models-3.0.0` |
| `models/gfpgan_1.4.onnx` (optional, conservative restoration) | same release |

## Run
    python local_face_replace.py --video "./videoplayback (1).mp4" --face ./face.png \
        --output ./output/local_face_swap_final.mp4 --preview      # 5-8 s preview, then stops
    python local_face_replace.py --video "./videoplayback (1).mp4" --face ./face.png \
        --output ./output/local_face_swap_final.mp4 --full         # whole movie
Other modes: `--scene N`, `--make-contact-sheets`, `--env-check`. Flags: `--resume` (default), `--force`,
`--no-enhance`, `--enhance-blend 0.25`, `--models DIR`.

`face.png` may be a single portrait or a character sheet. Every detected view of the same person is
averaged into one identity embedding, so the identity is the same in every frame and scene.

## How the target is locked
1. **Shots**: PySceneDetect `ContentDetector` → `work/scenes.json`. Every shot is tracked independently,
   so a track can never jump to another actor across a cut.
2. **Faces**: SCRFD detection + ArcFace embedding + 3D pose on every frame (cached in `work/cache/`).
3. **Tracks**: Hungarian matching on IoU + embedding similarity, with re-association across short gaps.
4. **Identity**: all tracks in the movie are clustered by ArcFace identity. The target is the identity with
   the most screen time across the most shots, with the pink-shirt colour score (light + pinkish pixels under
   the face) as a secondary cue.
5. **Per shot**: a track is swapped only if it matches the target identity (`sim ≥ 0.33`) **and** beats every
   other identity by `≥ 0.10`. Borderline matches are accepted only if the pink-shirt cue clearly singles
   them out. If two simultaneous faces both match, the scene is **not guessed**: a contact sheet goes to
   `work/ambiguous/` and the scene keeps its original footage until you set `"target_track_override": <id>`
   in `work/scenes.json` and re-run with `--scene N`.

## Rendering
- Landmarks are temporally smoothed (Gaussian σ = 1 frame) with outlier rejection, and short detection gaps
  are interpolated. This avoids face sliding, width flicker and identity jitter.
- INSwapper runs on 128 px aligned crops. The result is pasted back with a feathered elliptical face mask
  (brows→chin, cheek to cheek), so ears, hair and the head silhouette stay original.
- Colour: LAB mean/std transfer from the original face to the new face, smoothed over ±3 frames
  (per shot, never global).
- Grain: 25 % of the plate's own high-frequency grain is put back, so the face isn't smoother than the film.
- Restoration: GFPGAN at 25 % blend, face only.
- Other faces are explicitly protected: the mask is zeroed inside every non-target face, and QC measures
  the pixel change there. Any change > 1.0 fails the scene and keeps the original.
- Low confidence (lost detection, landmark outlier, |yaw| > 70–85°) fades smoothly back to the original frame.
- Scenes are written as lossless segments and encoded once to H.264 at assembly. The original audio
  stream is copied untouched.

## QC
`work/qc/sNNN_qc.jpg` holds original | swapped at 10/50/90 % of each processed scene (green = target,
red = protected). `work/qc/sNNN_qc.json` holds identity similarity to the source, the non-target pixel
change and the face-width step.

## Known limits
INSwapper only replaces the inner face at 128 px, so hairline and hair shape stay the actor's, and large
close-ups are softer than the plate. Hands crossing the face are handled by detection confidence and
landmark-outlier fading, not by a segmentation model.
