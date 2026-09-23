"""Shot list, character bibles and prompts for "Shiv & Parvati"."""

STYLE = ("Photoreal cinematic film still from an epic Indian mythological blockbuster, 16:9 widescreen, shot on "
         "ARRI Alexa 65 with anamorphic lenses, dramatic volumetric light, cold blue snow contrasted with crimson "
         "fire and gold, rich texture, shallow depth of field, soft film grain. No text, no captions, no watermark, "
         "no logo, no border.")

PARVATI_LOCK = ("The woman is the exact same person as in the reference photos of her: keep her face identical — same "
                "face shape, full round cheeks, eyes, eyebrows, nose with a tiny gold nose stud, lips, skin tone, red "
                "bindi, gold maang tikka, gold jhumka earrings, long dark curly hair with white jasmine. Do not "
                "beautify, slim, age or alter her face. She wears a deep crimson-red silk sari with a gold zari border.")

SHIVA = ("Lord Shiva: a powerful, serene Indian man in his thirties, clean-shaven with no beard or moustache, broad muscular shoulders, blue-grey ash-smeared "
         "skin, long matted dreadlocked jata piled high in a topknot with a glowing silver crescent moon in it, three "
         "horizontal white ash tripundra lines across his forehead with a closed vertical third eye and a small vermilion dot, a king cobra coiled "
         "around his neck with its hood raised beside his head, several strands of rudraksha beads on his bare chest, "
         "tiger-skin cloth at his waist, a tall iron trishul with a small damru drum tied to it")

SAGES = ("three elderly Hindu rishis with long snow-white beards and matted grey hair in topknots, ash tilak on their "
         "foreheads, rudraksha beads, wooden walking staffs; the one in the centre wears white robes, the two beside "
         "him wear saffron and ochre robes")

# Reference images generated first and reused so every shot stays on-model.
HEROES = {
    "shiva": {
        "refs": [],
        "prompt": (f"Character reference still. {SHIVA}. He sits in padmasana on a snow-dusted rock on a misty "
                   "Himalayan summit, eyes open, calm gaze to camera, trishul with damru planted upright beside him. "
                   "Medium-full shot, face and costume clearly visible, soft overcast light. "),
    },
    "sages": {
        "refs": [],
        "prompt": (f"Character reference still. {SAGES}. They stand together side by side in the snowy Himalayas, "
                   "full body, faces clearly visible and distinct, soft overcast light, light snowfall. "),
    },
}

# id: (refs, keyframe prompt, video action prompt, ambience prompt)
# refs: "parvati" = the four face crops, "shiva"/"sages" = hero images, "kf:NN" = another keyframe.
SHOTS = {
    "01": ([], "Epic aerial wide shot high above an endless range of Himalayan snow peaks at dawn, a sea of clouds "
               "rolling between the ridges, first gold sunlight catching the summits, deep cold blue shadows in the "
               "valleys. No people.",
           "Slow majestic aerial drone glide forward over the peaks, clouds rolling and flowing between the ridges, "
           "sunlight spreading across the summits.",
           "high-altitude wind, deep airy rumble"),
    "02": (["parvati"], "Low-angle tracking shot from knee height: she walks barefoot through deep fresh snow on a "
                        "Himalayan ridge toward camera, her long crimson sari trailing and flowing behind her in the "
                        "wind, bare feet sinking into powder snow, face turned three-quarters toward camera and clearly "
                        "visible, calm and determined. "
                        "Cold blue morning light, snow spray.",
           "Low tracking shot moving alongside her as she walks steadily barefoot through deep snow, sari trailing and "
           "rippling in the wind, snow kicked up by her steps.",
           "footsteps crunching in deep snow, gusting wind, fabric flapping"),
    "03": (["parvati"], "Extreme macro close-up of her face in three-quarter profile, strands of her dark curly hair "
                        "whipping across the frame in the wind, her gold maang tikka glinting with a bright sun flare, "
                        "snowflakes, very shallow depth of field.",
           "Wind whips her hair across her face, the gold maang tikka sways and catches a bright glint of sunlight. "
           "Tiny slow camera drift.",
           "strong wind gusts close to the microphone, tiny metallic jingle"),
    "04": (["parvati"], "She sits cross-legged in deep meditation on a narrow rock ledge of a sheer Himalayan cliff, "
                        "hands in namaste, eyes closed, perfectly still while a fierce blizzard rages around her, snow "
                        "streaking horizontally, a vast misty abyss below. Low heroic angle, cold blue.",
           "A violent blizzard rages around her, snow streaking past and her sari edges flapping, while she stays "
           "perfectly still, eyes closed, hands in namaste. Slow push-in.",
           "howling blizzard wind, snow hiss"),
    "05": (["parvati"], "Locked-off medium-wide shot: she sits in meditation on a mountain ledge, eyes closed, hands "
                        "in namaste, a bare rhododendron tree beside her, light snow falling, soft gold light.",
           "Time-lapse around her while she stays perfectly still: first snow falls and melts, then the tree bursts "
           "into pink blossoms, then golden autumn leaves swirl and fall around her. Locked-off camera.",
           "wind turning into birdsong, then rustling falling leaves"),
    "06": (["parvati"], "Panchagni tapas at sunset: she stands upright with folded hands and closed eyes in the centre "
                        "of a complete circle of roaring sacred fires that surrounds her on all sides on a high mountain "
                        "plateau, the blazing orange sun low behind her as the fifth fire, heat shimmer, embers flying, "
                        "crimson and gold light. Medium-wide shot from a low heroic angle, her face clearly visible.",
           "The ring of fires roars and flares higher around her, embers swirl upward, heat shimmer ripples; she stands "
           "unmoving with folded hands. Slow low-angle push-in.",
           "roaring bonfire flames, crackling, whoosh of flaring fire"),
    "07": (["parvati", "kf:06"], "Extreme close-up of her face lit by flickering orange firelight from below and the "
                                 "side, eyes closed, calm resolute expression, heat shimmer, embers drifting past, "
                                 "dark background.",
           "Firelight flickers and dances across her still face, embers drift past; she stays resolute, eyes closed, "
           "breathing slowly.",
           "close crackling fire, low roar of flames"),
    "08": (["sages"], "The three rishis from the reference emerge out of a howling blizzard walking toward camera, "
                      "robes whipping, snow caked in their beards, their faces awestruck, staring past camera in "
                      "wonder. Backlit cold blue light, low angle.",
           "The rishis push forward out of the blizzard toward camera, then slow down, awestruck, staring in wonder. "
           "Snow blasts past.",
           "howling blizzard, heavy footsteps in snow, no voices"),
    "09": (["sages"], "Wide shot from behind and below: the three rishis climb ancient weathered stone steps carved "
                      "into the mountain toward the sacred pyramid peak of Mount Kailash looming huge in the mist above. "
                      "Only the three rishis in frame: no other people, no fire, no cloth or offerings.",
           "The rishis climb the stone steps slowly with their staffs, mist drifting across Kailash above. Slow crane "
           "up.",
           "footsteps on stone, staffs tapping, distant wind"),
    "10": (["shiva"], "Extreme macro close-up of the king cobra coiled on Shiva's shoulder against his blue-grey ash "
                      "skin and rudraksha beads, frost glistening on its scales, its eye closed, dark moody light.",
           "The cobra's coils shift slowly, then its eye slowly opens and its tongue flicks. Very slow push-in.",
           "soft scaly slither, faint hiss"),
    "11": (["shiva"], "Low wide heroic shot from far below: Shiva from the reference sits in padmasana meditation on the "
                      "snowy summit of Mount Kailash, eyes closed, his trishul with damru planted upright beside him, "
                      "colossal dark storm clouds swirling in a vortex above, lightning flickering.",
           "Storm clouds swirl in a vast vortex above the summit, lightning flickers, snow streams; Shiva stays still. "
           "Slow push-in from below.",
           "rolling thunder, storm wind"),
    "12": (["shiva"], "Extreme close-up of Shiva's face, eyes closed in deep meditation, white tripundra ash lines, the "
                      "closed vertical third-eye mark, frost on his eyelashes, clean-shaven face exactly as in the "
                      "reference, snowflakes suspended motionless in the air around him. Cold blue light, dark misty "
                      "background, no fire.",
           "The wind dies down and the falling snow slows until the snowflakes hang frozen in mid-air around his still "
           "face. Almost imperceptible push-in.",
           "wind fading into total silence"),
    "13": (["shiva", "kf:12"], "The same extreme close-up of Shiva's face, now with his eyes open, a faint golden glow in "
                               "his irises, calm compassionate gaze, a slight gentle smile, clean-shaven, snowflakes "
                               "hanging in the air, warm gold light breaking in from the side. Same framing as image 2.",
           "His eyes glow faintly gold and a slight gentle smile forms, warm light spreads over his face, suspended "
           "snowflakes glint.",
           "near silence, soft low shimmer"),
    "14": (["parvati"], "Close-up: she looks up toward the sky with a soft smile and a single tear rolling down her "
                        "cheek, warm golden sunrise light on her face, snowflakes drifting, Himalayan peaks softly out of "
                        "focus behind.",
           "She slowly lifts her gaze with a soft smile as a single tear rolls down her cheek, warm sunlight grows on "
           "her face. Slow push-in.",
           "soft wind, gentle breath"),
    "15": (["shiva"], "Epic wide sunrise landscape: two small distant silhouettes standing on two separate Himalayan "
                      "peaks facing each other — on the left Shiva with his matted topknot and trishul, on the right a "
                      "woman in a flowing sari — the huge golden sun rising exactly between them, sea of clouds below, "
                      "gold and rose sky.",
           "The sun rises slowly between the two still silhouettes, clouds drift below, golden light floods the sky. "
           "Slow push-in.",
           "soft wind, distant temple bell resonance"),
}
