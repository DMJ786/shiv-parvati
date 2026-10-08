"""Episode 3 — "The Rescue": a climber falls on a Himalayan ridge, cries out to Shiva, and he catches her.
Built from the approved character sheet and the two storyboards in rescue/references/ (16 shots, 42 s)."""

STYLE = ("Photoreal cinematic 16:9 film frame from an epic devotional mountain adventure, shot on ARRI Alexa 65 with "
         "anamorphic lenses, crisp high-altitude daylight, cold blue snow and grey granite contrasted with her mustard-"
         "yellow jacket and Shiva's ash-blue skin and gold, rich texture, shallow depth of field, soft film grain. "
         "No text, no captions, no watermark, no logo, no border.")

CLIMBER = ("The young woman is exactly the person in her identity photos: same face shape, full round cheeks, eyes, "
           "eyebrows, dark brown eyes, nose with a tiny nose stud, lips and skin tone, a small red bindi, small pearl drop earrings, long "
           "dark curly hair in a loose side braid. Do not beautify, slim or alter her face. She wears a mustard-yellow "
           "insulated jacket with a grey fleece collar, a maroon backpack, dark grey trekking trousers, brown hiking boots "
           "and a red thread bracelet on her wrist.")

SHIVA = ("Lord Shiva exactly as in his reference photos: ash-blue skin, full dark beard and moustache, long matted jata "
         "piled in a topknot with rudraksha strands and a silver crescent moon, three white tripundra lines with a red "
         "vertical tilak, gold hoop earrings, a cobra coiled around his neck, many rudraksha malas and bracelets, "
         "tiger-skin and fur garments, a tall bronze trishul with red cloth and a small damru.")

# id: (who, storyboard seconds, keyframe description, video action, ambience)
# who: "c" climber, "s" Shiva, "cs" both, "" neither (refs added accordingly); score = whose face is big enough to score
SHOTS = {
    "01": ("c", 3, "Epic high wide shot: she climbs a jagged snowy Himalayan ridge, tiny in the frame, an endless range "
                   "of snow peaks and a sea of clouds below.",
           "Slow aerial drift forward as she climbs steadily up the ridge; clouds roll far below.",
           "high mountain wind"),
    "02": ("c", 3, "Medium close shot: she reaches up for a handhold on the rock face, strained and focused, snow on her "
                   "jacket and hair.",
           "She pulls herself up and reaches for the next handhold, breathing hard; snow flurries past.",
           "heavy breathing, gloves gripping rock, wind"),
    "03": ("c", 2, "Low macro shot of her brown hiking boot on a rock ledge as the granite cracks and crumbles under it, "
                   "fragments and snow falling away.",
           "The rock under her boot cracks and breaks away; fragments tumble into the void.",
           "rock cracking, debris falling"),
    "04": ("c", 2, "Mid-air: she has lost her grip and is falling backward away from a steep rock face, one hand still "
                   "reaching for the rock, legs swinging out, rocks and snow falling around her, a vast drop of snowy "
                   "peaks below. Dynamic angle from the side, as in the storyboard.",
           "She loses her footing and drops down the rock face, scrabbling for a hold as debris falls.",
           "rush of wind, falling rocks, a sharp gasp"),
    "05": ("c", 2, "Close shot: she clings to a snowy edge with one hand, the other reaching up desperately, fear in her "
                   "eyes.",
           "Her fingers slip on the snowy edge as she reaches upward desperately.",
           "wind, fingers scraping rock, strained breath"),
    "06": ("c", 2, "Close-up from slightly above: she looks up and cries out, mouth open, tears and snow on her face. "
                   "Her face must stay young and exactly hers: the same round face and features as the front identity "
                   "photo, only with the crying expression.",
           "She looks up and cries out desperately toward the sky.",
           "a desperate wordless cry, wind"),
    "07": ("cs", 2, "Her outstretched hand with the red thread bracelet reaches up as Shiva's ash-blue hand with rudraksha "
                    "bracelets reaches down toward it from above, bright sky and peaks behind.",
           "Shiva's hand reaches down toward her straining hand and the gap between their fingers closes.",
           "wind hush, deep low shimmer"),
    "08": ("cs", 2, "Close-up: Shiva's ash-blue hand with rudraksha bracelets firmly grasps her wrist with the red thread "
                    "bracelet, her mustard sleeve, snowy rock.",
           "His hand clasps her wrist firmly and holds; snow drifts past.",
           "firm grip, wind"),
    "09": ("cs", 3, "Low angle over her shoulder: Shiva kneels on the ledge above holding her hand, looking down at her with "
                    "calm compassion, trishul with red cloth planted beside him, bright sky.",
           "Shiva holds her hand and looks down at her calmly as his jata moves in the wind.",
           "wind, distant temple bell resonance"),
    "10": ("cs", 3, "Wide shot: Shiva pulls her up the rock face by the hand while she climbs with her other hand, snowy "
                    "peaks behind.",
           "Shiva pulls her steadily up the rock face and she scrambles up with his help.",
           "boots scraping rock, effort, wind"),
    "11": ("cs", 3, "She gets one knee onto the ledge as Shiva, crouching, holds her hand; she is nearly safe.",
           "She plants a knee on the ledge and pulls herself up as Shiva steadies her.",
           "boots on rock, a relieved breath"),
    "12": ("cs", 3, "Both kneel on the snowy ledge, safe; she looks up at Shiva in awe, still holding his hand, trishul "
                    "beside him.",
           "They kneel on the ledge; she gazes up at him in awe as he gently lets go of her hand.",
           "soft wind, calm"),
    "13": ("cs", 3, "Close shot over Shiva's shoulder: she joins her hands in namaste, eyes full of tearful gratitude.",
           "She folds her hands in namaste with tearful gratitude and bows her head slightly.",
           "soft wind, gentle breath"),
    "14": ("", 2, "The ledge now empty: a single rudraksha bead rests on the snow beside large bare footprints, peaks and "
                  "clouds beyond.",
           "Snow drifts across the empty ledge; the rudraksha bead rests in the footprints. Slow push-in.",
           "wind, faint bell shimmer"),
    "15": ("c", 3, "Close-up: she holds a single rudraksha bead in her open palm, looking down at it with a soft smile, red "
                   "thread on her wrist.",
           "She looks at the rudraksha bead with a soft smile and gently closes her fingers around it.",
           "soft wind"),
    "16": ("c", 4, "Wide sunrise shot from behind: she walks on along the snowy ridge toward the rising golden sun, a sea "
                   "of clouds below.",
           "She walks away along the ridge toward the golden sunrise as the clouds glow below. Slow crane up.",
           "wind, footsteps in snow"),
}
SCORE = {"02": "climber", "05": "climber", "06": "climber", "13": "climber", "15": "climber",
         "09": "shiva_beard", "12": "shiva_beard"}
