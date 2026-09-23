# Shiv & Parvati — AI film pipeline

## Paste this into Claude Code (in this folder)
> Run make_video.py to generate the Shiv & Parvati film. First check the current input schema for
> bytedance/seedance-2.5/image-to-video and text-to-video on fal.ai and adjust the args in generate() if
> anything differs. Open refs/hero.png and refs/tapasya.png to confirm they are clean face crops with no
> caption text. Generate shot 01 alone first and show me a frame so I can confirm the face match before
> running the rest. Then run with TAKES=3, show me a frame from each take, and write picks.json from my choices.

## Setup
    pip install fal-client pillow
    export FAL_KEY=your_key      # ffmpeg must be installed

## Music (for the best sound)
Make a 60 s track in Suno/Udio, save as music.mp3 here. Prompt:
"cinematic Indian devotional score, bansuri flute and tanpura drone, soft strings enter at 25s,
near silence at 40s, choir Om and full strings swell at 45s, gentle resolve, 60 seconds, instrumental"
The script ducks Seedance's native ambience (wind, bells, diya, footsteps) under the music and masters to -14 LUFS.

## Files
- parvati_sheet.png  – face reference (crops auto-made into refs/)
- clips/  raw takes · norm/  normalised shots · shiv_parvati_final.mp4  output
