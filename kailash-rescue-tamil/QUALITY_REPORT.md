# Kailash Rescue (Tamil): quality report

An AI-created devotional dramatisation, not footage of a real event.
Format: 1080×1920, 24 fps (constant), 26.1 s, no opening logo.

## Deliverables
| File | What |
|---|---|
| `clean_master.mp4` | Main edit (opening A: slipping fingers), no captions |
| `tamil_captioned_A_slipping_fingers.mp4` | Tamil-captioned version, opening A |
| `tamil_captioned_B_breaking_foothold.mp4` | Tamil-captioned version, opening B; same main edit from 2.0 s |
| `clean_B_breaking_foothold.mp4` | Opening B without captions |
| `*_preview.mp4` | Smaller encodes for quick sharing (about 15 MB) |

## Edit
| Time | Beat | Source |
|---|---|---|
| 0.0–5.0 | Ice breaks under the left fingers (A), or the foothold shatters (B, 0–2.0), then the scrape down the face. Overlay: "பிடி நழுவிய அந்த நொடி…" | A / B |
| 5.0–8.2 | Hanging below the ledge, snow hits the lens, the left hand strains upward; whispered "சிவா…" at 5.6 s | C |
| 8.2–11.2 | Shiva's RIGHT hand catches the climber's LEFT forearm (about 9.0 s); the climber's hand stays visible above the grip | D |
| 11.2–15.8 | One-arm lift: the right hand lands on the ledge snow, then a knee onto the rock; the grip is held throughout | E |
| 15.8–20.3 | Recognition; Shiva releases the wrist only after the climber is kneeling and stable | G |
| 20.3–26.1 | Namaste and blessing; the storm light warms gradually; final hold. Overlay: "நீ கைவிட்டாலும்… அவர் கைவிடமாட்டார்." plus a small "AI உருவாக்கிய பக்திச் சித்தரிப்பு" (AI-created devotional depiction) | H |

Only hard cuts on movement are used: no flashes and no dissolves. The final shot starts in the previous shot's cold grade and warms over 3.5 s, so there is no lighting jump at the cut.

## Process
- **Continuity references:** climber's hands, Shiva (later replaced at your request by a gigantic, heavily muscular version with the same face), and the cliff, ledge and peak (`references/`).
- **Keyframes:** nine boundary keyframes generated from those references (`keyframes/`). Each was checked for left/right before any video was made; K3b (the grip) and K6 (the blessing) were regenerated after failing.
- **Video:** one Veo 3.1 shot per action (Fast and Standard), starting from those keyframes, with matching end frames for the catch and the lift.
- **Shots rejected and regenerated after frame-by-frame review:**
  - foothold opening: the climber turned into Shiva, third-person;
  - desperation: the hands turned ash-blue;
  - catch, twice: the climber's hand melted into the sleeve;
  - the four normal-size Shiva shots, replaced after the giant redesign.
- **Sound:**
  - Veo native ambience (wind, ice, breath, contact).
  - The Tamil whisper from Gemini TTS, trimmed to the single word and verified by transcription as only "சிவா" and intelligible.
  - A restrained instrumental Lyria score entering at the catch and resolving on the end card.
  - Mix: −14.6 to −14.9 LUFS integrated, true peak −1.7 dBFS.
- **Text:** added in the edit with Noto Sans Tamil. It sits clear of the top bar, the right-hand icon rail and the bottom caption area, and covers no hands or faces.

## Verified on the exports
- Every file was decoded end to end with zero decoder errors (626–627 frames).
- Video and audio durations match within one frame (26.08–26.13 s against 26.10 s).
- No frozen frames were used to extend the duration, and there is no missing ending.
- A watch-and-listen AI review of the captioned A version found:
  - the whisper audible and intelligible at about 6 s;
  - the ice crack, catch and ledge sounds in sync;
  - the ending resolving naturally;
  - both Tamil overlays readable;
  - the story clear on first viewing.

## Remaining defects (honest list)
1. **Ledge geometry, 16–18 s (shot G).** The snow-covered rock slab behind Shiva reads as if it crosses his waist; the ledge and figure don't sit convincingly in one space. Fixing it needs a regenerated G (about $1.20–3.20).
2. **Final shot style, 20.3–26.1 s (shot H).**
   - The composition is noticeably more static and "composed" than the handheld shots before it.
   - Shiva's raised blessing hand looks very large because it is close to the lens.
   - The colour ramp removes the lighting jump but not the change in style.
3. **The fall (0–5 s) is a scrape down the slope rather than a free drop.** It reads clearly but is less dramatic than a true fall.
4. **Spatial jumps at cuts:**
   - 5.0 s: the climber is suddenly hanging below the ledge.
   - 11.2 s: the camera moves from the close grip to a wider view of Shiva above.

   These are cuts on movement and the story stays clear, but they are spatial jumps rather than continuous moves.
5. **Opening B is assembled from two takes.** Its first 2.0 s come from a foothold take whose later part failed QC; the cut at 2.0 s changes the camera direction (looking down, then at the wall).
6. **The last 0.3 s of the lift (shot E) were trimmed** because the climber's sleeves disappeared after 6.2 s in the source take. No sleeve change is visible in the edit.
7. **The giant scale varies from shot to shot,** which is typical of generated footage: Shiva looks about 2–3× the climber's size depending on the framing.
8. **I could not listen to the audio myself.** It was checked by measurement, by transcription and by one AI watch-and-listen review; a human listen on a phone is still recommended before posting.

No claims about reach or virality are made.
