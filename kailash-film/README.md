# Kailash: The Climb (कैलाश)

A 39.5 s, 1080x1920 (9:16) photoreal devotional short in the style of the storm-sea reference, re-imagined:
a devotee climbing toward Mount Kailash in a blizzard is swept away by an avalanche, falls into darkness,
and is caught and lifted by Lord Shiva, who leads them to the glowing peak beneath an aurora "ॐ".

| Time | Shot |
|---|---|
| 0–4.3 | POV: climbing the icy rock face in the blizzard, golden Kailash and lightning above |
| 4.3–8.3 | The ledge cracks; an avalanche thunders down at the camera |
| 8.3–13.7 | Falling backward into the white-out, fading to black |
| 13.7–17 | Darkness of the chasm; a hand reaches toward a far circle of light |
| 17–21.8 | Shiva's ash-blue hand grips the wrist; a golden burst |
| 21.8–27.2 | Reveal: Shiva on the cliff in the storm (crescent moon, cobra, trishul, third eye) pulls the devotee up |
| 27.2–31.9 | Shiva leads the devotee by the hand along the ridge toward Kailash as the storm parts |
| 31.9–39.5 | Wide: two figures beneath the aurora "ॐ"; title "हर हर महादेव · ॐ नमः शिवाय" |

## How it was made
- **Keyframes:** Gemini 3 Pro Image (`tools/img.py`, `tools/keyframes.sh`). A Shiva character reference
  (`keyframes/shiva_ref.jpg`) was passed into every Shiva shot to keep him consistent.
- **Video:** Veo 3.1 Fast image-to-video, 8 s per shot at 1080x1920 with native sound effects (`tools/veo.py`,
  `tools/clips.sh`; `tools/retry.sh` handles rate limits).
- **Music:** Lyria 3.5 devotional score (`tools/lyria.py`), cut to picture: tension under the climb, near-silence
  in the darkness, and the full choir landing on the divine catch.
- **Edit:** `tools/edit.py` (ffmpeg): trims, fades and white flashes, a light teal/gold grade with vignette,
  the Devanagari title rendered in Chromium (`tools/title.*`), and the music mixed with Veo's native audio.
- Measured: −12.7 LUFS integrated, true peak −1.2 dBFS.

Files: `kailash_the_climb.mp4` (master, 75 MB), `kailash_the_climb_light.mp4` (smaller, for sharing),
`contact_sheet.jpg`, `keyframes/`. All imagery is AI-generated.
