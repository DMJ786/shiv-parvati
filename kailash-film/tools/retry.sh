#!/usr/bin/env bash
# re-submit shots that hit the rate limit, one at a time, backing off on 429
cd "$(dirname "$0")/.."
POV="Handheld first-person POV, the camera is the devotee's eyes; keep his forearms, rudraksha bracelet and red thread consistent. Photoreal, cinematic, no text."
declare -A P
P[s4]="$POV Silence and darkness deep in an icy chasm, his hand slowly reaches up toward a faint circle of pale light far above, snowflakes drift down in slow motion, his fingers tremble. Very slow subtle camera drift. Audio: near silence, slow heartbeat, faint wind far above. No music, no speech."
P[s5]="$POV A powerful ash-blue divine hand with a rudraksha band grips his wrist firmly from above; golden-white light blooms and floods outward, snowflakes glow like sparks, he is pulled upward toward the light. Audio: a deep resonant temple bell and a swelling shimmer, heartbeat stops. No music, no speech."
P[s8]="Slow epic push-in toward the two small silhouettes of Lord Shiva with his trishul and the devotee walking hand in hand along the snowy ridge toward Mount Kailash glowing gold, the vast emerald and violet aurora shaped like the Om symbol shimmering and flowing across the starry sky. Audio: gentle wind, a single deep conch and a soft Om chant swell. No speech. Photoreal, cinematic, no text."
for id in ${@:-s4 s5 s8}; do
  for try in 1 2 3 4 5 6 7 8 9 10; do
    python3 tools/veo.py "clips/$id.mp4" "kf/$id.png" "${P[$id]}" > "clips/$id.log" 2>&1
    if grep -q "saved" "clips/$id.log"; then echo "$id ok"; break; fi
    if grep -q "429" "clips/$id.log"; then sleep 60; else echo "$id failed: $(tail -c 300 clips/$id.log)"; break; fi
  done
done
