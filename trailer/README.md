# THE SIP — 40s daydream trailer

A man relaxes in a café, closes his eyes, dreams of the life he's building (empire, wealth,
respect, family, peace), then comes back to the café with a smile. *It all works out.*

`output/THE_SIP_trailer_suit.mp4` is the current cut (café footage + Blender-rendered dream scenes).
`veo_trailer.py` is the next step: photoreal dream shots with Gemini + Veo.

## Setup (fresh container)

```bash
cd trailer
pip install opencv-python-headless numpy pillow imageio-ffmpeg ai-edge-litert google-genai
ln -sf "$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')" /usr/local/bin/ffmpeg
python3 -m venv /tmp/bvenv && /tmp/bvenv/bin/pip install bpy==4.5.4   # Blender, kept apart (needs numpy<2)
curl -sSL -o seg.tflite https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/float32/latest/selfie_multiclass_256x256.tflite
```

## Pipeline

| Step | Command | Makes |
|---|---|---|
| Decode video | `python3 prep.py` | `frames.npy` |
| Person cut-out (10–14s) | `python3 mask.py` | `cut.npy` |
| Clothing segmentation | `python3 seg6.py` | `seg6.npy` |
| Suit overlay | `python3 suit.py` | `cut_suit.npy` |
| Scene colour grades | `python3 cutgrade.py` | `cut_night/`, `cut_stage/` |
| Slow-mo sequences + LED wall | `python3 make_seq.py` | `seq_stage/`, `seq_night/`, `led/` |
| 3D scenes | `/tmp/bvenv/bin/python bl/<city,number,stage,home,roof>.py x <samples>` | `r/<scene>/` |
| Sound | `python3 trailer_audio.py` | `trailer.wav` |
| Edit | `python3 edit.py` then mux with ffmpeg | `trailer_video.mp4` |

The Gemini logo is removed by reverse alpha-blending its estimated overlay (`logo_alpha.npy`, used by `delogo.py`).

## Photoreal version (Gemini + Veo)

Add `GEMINI_API_KEY` to the environment, then:

```bash
python3 veo_trailer.py --dry          # show the 8-shot plan
python3 veo_trailer.py                # all shots -> veo/*.png (first frames) and veo/*.mp4
python3 veo_trailer.py 05_daughter    # redo a single shot
```

Veo is billed per second of video on your Google account.
