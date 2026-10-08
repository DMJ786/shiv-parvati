"""Episode 3 — "The Rescue": a climber falls on a Himalayan ridge, cries out to Shiva, and he catches her.
Built from the approved character sheet and the two storyboards in rescue/references/, re-directed for the screen:
18 shots, about 47 s (a divine-light beat, a blessing and a distant-silhouette ending added; four shots re-composed)."""

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

# Shots with no character must not inherit STYLE's character colours (the model then draws a figure).
STYLE_EMPTY = STYLE.replace(" contrasted with her mustard-yellow jacket and Shiva's ash-blue skin and gold", " and warm gold light")

# Story order. id: (who, seconds, keyframe description, video action, ambience)
# who: "c" climber, "s" Shiva, "cs" both, "" neither. Shots in FROM_BOARD keep their storyboard panel as the
# composition reference; the rest are re-directed shots with new, more cinematic compositions.
SHOTS = {
    "01": ("c", 3.0, "Epic high wide shot: she climbs a jagged snowy Himalayan ridge, tiny in the frame, an endless range "
                     "of snow peaks and a sea of clouds below.",
           "FPV drone dive: the camera swoops fast over the knife-edge ridge and down toward her as she climbs; clouds "
           "roll far below.",
           "roaring high-altitude wind, drone whoosh"),
    "02": ("c", 2.5, "Medium close shot: she reaches up for a handhold on the rock face, strained and focused, snow on her "
                     "jacket and hair, breath vapour in the cold air.",
           "Handheld tracking close: she hauls herself up and reaches for the next hold, breath steaming; snow flurries.",
           "heavy breathing, gloves gripping rock, wind"),
    "03": ("c", 2.0, "Low macro shot of her brown hiking boot on a rock ledge as the granite cracks and crumbles under it, "
                     "fragments and snow falling away.",
           "The rock under her boot cracks and breaks away; fragments tumble into the void. Snap zoom in.",
           "rock cracking, debris falling"),
    "04": ("c", 2.0, "Vertigo shot looking straight down from above: she falls backward away from the sheer rock face, arms "
                     "flung up toward camera, rocks and snow falling with her, a dizzying drop of glacier and cloud far "
                     "below.",
           "Top-down vertigo: she drops away from camera down the sheer face, arms reaching up, debris spiralling down.",
           "rush of wind, falling rocks, a sharp gasp"),
    "05": ("c", 2.0, "Close shot: she clings to a snowy edge with one hand, the other reaching up desperately, fear in her "
                     "eyes.",
           "Her fingers slip on the icy edge as she reaches upward desperately; snow crumbles from the lip.",
           "wind, fingers scraping rock, strained breath"),
    "06": ("c", 2.0, "Close-up from slightly above: she looks up and cries out, mouth open, tears and snow on her face.",
           "She looks up and cries out desperately toward the sky; wind tears at her hair.",
           "a desperate wordless cry echoing off the peaks, wind"),
    "17": ("", 2.0, "Looking up from the cliff: dark storm clouds over the summit split open and a single shaft of brilliant "
                    "golden light strikes the bare rock ledge above, snow glittering in the beam. Nothing on the ledge: no people, no "
                    "clothing, no objects, only rock, snow and light.",
           "The storm clouds tear apart and a golden shaft of light blazes down onto the ledge; snow sparkles in the beam.",
           "deep resonant temple bell, wind dropping to a hush"),
    "07": ("cs", 2.5, "As in the storyboard frame: she still dangles below the cliff edge, only her straining arm in the "
                      "mustard sleeve with the red thread bracelet reaching up from the bottom of frame, while Shiva's "
                      "ash-blue hand with rudraksha bracelets reaches down from the top, like Michelangelo's Creation of "
                      "Adam; a brilliant sun flare bursts in the small gap between their fingertips.",
           "In slow motion their hands stretch toward each other and the sun flare blooms between the fingertips.",
           "near silence, a soft rising shimmer"),
    "08": ("cs", 2.0, "Close-up: Shiva's ash-blue hand with rudraksha bracelets firmly grasps her wrist with the red thread "
                      "bracelet, her mustard sleeve, snowy rock.",
           "Slow motion: his hand clamps around her wrist and snow bursts off the grip as her fall stops dead.",
           "a deep impact thud, snow burst"),
    "09": ("cs", 3.0, "Her point of view from below, low heroic angle: Shiva leans over the ledge above holding her wrist, "
                      "backlit by the sun with a rim of golden light, cobra hood raised beside his head, trishul with red "
                      "cloth planted beside him, calm compassionate eyes looking down at her.",
           "Shiva holds her and looks down with calm compassion; the sun flares behind him, jata and cloth stirring in "
           "the wind. Slow push-in.",
           "wind, distant temple bell resonance"),
    "10": ("cs", 3.0, "Wide shot: Shiva pulls her up the rock face by the hand while she climbs with her other hand, snowy "
                      "peaks behind.",
           "Shiva lifts her up the rock face in one steady pull and she scrambles up with his help.",
           "boots scraping rock, effort, wind"),
    "11": ("cs", 2.0, "She gets one knee onto the ledge as Shiva, crouching, holds her hand; she is nearly safe.",
           "She plants a knee on the ledge and pulls herself up as Shiva steadies her.",
           "boots on rock, a relieved breath"),
    "12": ("cs", 3.0, "On safe ground she kneels with her head bowed, and Shiva, kneeling before her, rests his ash-blue hand "
                      "gently on her head in blessing, trishul beside him, soft golden light, snow drifting.",
           "Shiva lays his hand gently on her bowed head in blessing; warm light grows around them.",
           "soft wind, a single gentle bell"),
    "13": ("cs", 3.0, "Close shot over Shiva's shoulder: she joins her hands in namaste, eyes full of tearful gratitude.",
           "She folds her hands in namaste with tearful gratitude and bows her head slightly.",
           "soft wind, gentle breath"),
    "14": ("", 2.5, "The ledge now empty: a single rudraksha bead rests on the snow beside large bare footprints, peaks and "
                    "clouds beyond.",
           "Snow swirls across the empty ledge where he stood; the rudraksha bead rests in the footprints. Slow push-in.",
           "wind, faint bell shimmer"),
    "15": ("c", 3.0, "Close-up: she holds a single rudraksha bead in her open palm, looking down at it with a soft smile, red "
                     "thread on her wrist.",
           "She looks at the rudraksha bead with a soft smile and gently closes her fingers around it.",
           "soft wind"),
    "18": ("s", 3.0, "Extreme wide sunrise: far away on a distant snowy peak, the small silhouette of Shiva stands with his "
                     "trishul against the huge rising golden sun, a sea of glowing clouds between, seen from her ridge.",
           "The sun rises behind Shiva's distant silhouette on the far peak; clouds glow and drift. Very slow push-in.",
           "wind, distant temple bell resonance"),
    "16": ("c", 4.0, "Wide sunrise shot from behind: she walks on along the snowy ridge toward the rising golden sun, a sea "
                     "of clouds below.",
           "She walks away along the ridge toward the golden sunrise as the clouds glow below. Slow crane up.",
           "wind, footsteps in snow"),
}
FROM_BOARD = {"01", "02", "03", "05", "06", "07", "08", "10", "11", "13", "14", "15", "16"}
SCORE = {"02": "climber", "05": "climber", "06": "climber", "13": "climber", "15": "climber",
         "09": "shiva_beard"}

# Kling identity elements per shot (faces big enough to matter): "c" = the Climber, "s" = Shiva.
ELEMENTS = {"02": "c", "04": "c", "05": "c", "06": "c", "09": "s", "10": "cs", "11": "cs", "12": "cs", "13": "c",
            "15": "c"}

# Score, ~48 s, cut to the story (name, seconds, styles). The bell opens "Divine light" on the cut into shot 17;
# the climax lands on the catch (shot 08).
MUSIC_GLOBAL = ["epic Indian devotional film score", "cinematic trailer", "instrumental", "wordless choir only",
                "no lyrics", "strong dynamic contrast between sections"]
MUSIC_NEGATIVE = ["lyrics", "sung words", "spoken word", "rap", "pop", "EDM", "electric guitar"]
MUSIC_SECTIONS = [
    ("Ascent", 7.5, ["tense low string ostinato", "deep taiko pulse", "mountain wind texture", "slowly rising"]),
    ("The fall", 6, ["explosive orchestral hit at the start", "chaotic driving percussion", "dissonant brass",
                     "panic building", "cuts off abruptly at the end"]),
    ("Divine light", 4.5, ["sudden hush", "one deep temple bell strike", "ethereal wordless female choir swelling",
                           "no drums"]),
    ("Rescue", 13, ["massive emotional climax", "full orchestra and wordless choir", "thundering dhol",
                    "soaring strings", "heroic and devotional"]),
    ("Gratitude", 8.5, ["tender and warm", "solo bansuri over soft strings", "gentle tanpura"]),
    ("Ending", 8.5, ["final swell with choir and horns", "then a gentle bansuri resolve", "last temple bell",
                     "fading out"]),
]
