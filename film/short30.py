"""The 30 s Reel (native 9:16): make us feel her devotion, not just see it.

0-2 s her prayer against a fierce storm -> 2-8 s the seasons change her (heat, rain, years, frost) in matched
framing -> 8-13 s the rishis witness her and plead with Shiva -> 13-19 s Shiva, then one continuous eye opening ->
19-27 s her upward gaze, his downward gaze, the blessing -> 27-30 s her tear and restrained smile, one line of text.

Two openings for testing with the same remaining edit: "storm" (her enduring the blizzard) and "seasons" (a rapid
time-lapse of the seasons while she stays still). Hard cuts between faces; no dissolves (they read as morphing).
"""

# New native 9:16 shots. id: (refs, keyframe description, video action, ambience, seconds, who to face-score)
# refs: "parvati" = the four face crops, "shiva"/"sages" = hero images, "kf:NN" = an existing keyframe,
# "base:NN" = a keyframe to edit with the same framing (the seasons are matched cuts of one composition).
SHOTS = {
    "70": (["parvati", "kf:04"],
           "Vertical 9:16 medium close-up, waist up and centred: she kneels in prayer on a narrow Himalayan cliff ledge "
           "in a fierce blizzard, snow streaking sideways across the frame, her long hair and crimson sari whipping in "
           "the wind, eyes shut tight, jaw set in determination, palms pressed together in namaste, frost on her "
           "eyelashes, cold blue light, a dizzying white void behind her.",
           "A fierce gust batters @Element1; she sways, then steadies and presses her palms together harder, eyes shut "
           "tight in determination as snow streaks past. Handheld, close.",
           "howling blizzard wind, a sharp breath", "3", "parvati"),
    # The seasons: 71 is the composition, 72-74 are edits of it with the same framing.
    "71": (["parvati", "kf:05"],
           "Vertical 9:16 medium close-up, waist up and centred, eye-level, locked-off: she sits in deep meditation "
           "on a rock ledge, eyes closed, hands in namaste at her chest. SUMMER TAPAS: a blazing white sun behind her, "
           "the orange glow of a ring of fire below the frame lighting her from beneath, heat shimmer, sweat beading "
           "on her forehead and upper lip, flushed skin, tired heavy eyelids, a strand of hair stuck to her damp "
           "cheek.",
           "Heat shimmer ripples around @Element1; a bead of sweat rolls down her temple, her tired eyelids tighten "
           "and she breathes slowly, unmoving. Locked-off.",
           "crackling fire, low roar of heat", "3", "parvati"),
    "72": (["base:71", "parvati"],
           "MONSOON: she is soaked through: hair wet and plastered to her face and shoulders, heavy rain streaming down "
           "her face and dripping from her chin and folded hands, the sari drenched and dark, cold grey storm light, "
           "rain lashing across the frame.",
           "Heavy rain pours over @Element1, streaming down her face and dripping from her folded hands; she stays "
           "still, eyes closed, lips pressed together. Locked-off.",
           "heavy rain, distant thunder roll, water dripping", "3", "parvati"),
    "73": (["base:71", "parvati"],
           "AUTUMN, years later: golden leaves drift past and cling to her hair and shoulders, her face is thinner and "
           "weary with faint shadows under her closed eyes, dust on her sari, warm low golden evening light.",
           "Golden leaves drift past @Element1 and settle on her shoulders; she sways almost imperceptibly with "
           "exhaustion, then steadies. Locked-off.",
           "dry leaves rustling, soft wind", "3", "parvati"),
    "74": (["base:71", "parvati"],
           "DEEP WINTER: the fires are gone, only snow on the ledge around her; frost collecting on her shoulders, hair and eyelashes, snow settling on her head and folded "
           "hands, her breath visible as mist, her folded fingers trembling with cold, pale cold blue light.",
           "Frost creeps over @Element1's shoulders; her folded fingers tremble with cold, then slowly steady and press "
           "together again; her breath mists in the cold air. Locked-off.",
           "thin icy wind, a slow cold breath", "3", "parvati"),
    "75": (["shiva", "kf:21"],
           "Vertical 9:16 close-up of Shiva exactly as in the references, seen slightly from below, head tilted down, "
           "eyelids lowered, his eyes gazing down at someone kneeling below the bottom of the frame, not at the camera, "
           "gazing gently downward "
           "toward someone below him, a softened, compassionate expression with the faintest warmth at the corners of "
           "his mouth, the closed third-eye mark, frost melting on his eyelashes, snowflakes, cool light warming "
           "slightly. No fire, no flames, no glow.",
           "Shiva gazes down with deep compassion; his expression softens further and the faintest gentle smile forms. "
           "Very slow push-in. No glow.",
           "near silence, soft wind", "3", "shiva"),
    "76": (["parvati", "kf:26", "shiva"],
           "Vertical 9:16 blessing with exactly two people, Shiva and one young woman (image 5 shows the same moment "
           "as a wide shot), filling the frame top to bottom: Shiva stands tall in the upper part of the frame, "
           "his face clearly visible looking down at her with a softened, compassionate expression, his right palm "
           "resting on her head; she kneels below him in the lower part of the frame, face lifted toward him in "
           "three-quarter view, tears on her cheeks, hands folded in prayer. Soft golden sunrise light, a sea of "
           "clouds behind, snow. Calm, no dramatic effects.",
           "Shiva rests his palm gently on @Element1's head in blessing; she closes her eyes as tears of relief roll "
           "down. Golden light, snow drifting. Very slow push-in.",
           "soft wind", "4", "parvati"),
}

# The cut (seconds): (shot, start, end). Hard cuts throughout. Native 9:16 clips are listed in NATIVE; the others
# are face-tracked crops of the 16:9 film shots. 21 is placed so his eyes finish opening at DAMARU_AT.
TIMELINE = [
    ("70", 0.00, 2.00),     # her prayer against the storm
    ("71", 2.00, 3.50),     # summer: heat, sweat, tired eyes
    ("72", 3.50, 5.00),     # monsoon: soaked, rain streaming down her face
    ("73", 5.00, 6.50),     # autumn: years later, weary, leaves on her shoulders
    ("74", 6.50, 8.00),     # winter: frost on her shoulders, trembling fingers that steady
    ("19", 8.00, 10.50),    # the rishis witness her (19v)
    ("20", 10.50, 13.00),   # and plead with Shiva (20v)
    ("11", 13.00, 16.25),   # Shiva, still, in the storm
    ("21", 16.25, 19.25),   # one continuous eye opening (clip 3.25-6.25 s)
    ("22", 19.25, 20.75),   # her upward gaze
    ("75", 20.75, 22.25),   # his downward gaze
    ("76", 22.25, 26.75),   # the blessing
    ("14", 26.75, 30.00),   # her tear and restrained smile; the line of text
]
NATIVE = {"70": "70", "71": "71", "72": "72", "73": "73", "74": "74", "75": "75", "76": "76", "19": "19v", "20": "20v"}
IN_POINT = {"21": 3.25, "19": 0.0, "20": 0.0, "22": 0.2, "14": 0.6}   # seconds into each clip; others start at 0.3 s
REFRAME = {"11": (0.5, 0.5)}
OPENING_SEASONS = ("30", 11.5 / 2.0)   # the "seasons" opening: the locked-off season time-lapse, x5.75, 2 s

DAMARU_AT = 19.0          # his gaze settles
DIP = (17.4, 19.0, -7.0)  # the score pulls back before it
TEXT = ["Through every season,", "her devotion remained."]
TEXT_AT = 27.3            # fades in over the last shot

MUSIC_GLOBAL = ["Indian devotional film score", "intimate, emotional, restrained", "instrumental",
                "D minor, raga Shivaranjani colour", "clear mid-range melody that reads on a phone speaker"]
MUSIC_NEGATIVE = ["lyrics", "chanting", "spoken word", "thunder", "trailer impacts", "booming sub bass", "EDM",
                  "heavy drums", "electric guitar"]
MUSIC_SECTIONS = [
    ("Storm", 2.0, ["mountain wind texture", "a breath", "one low sustained cello note"]),
    ("Seasons", 6.0, ["sparse tanpura drone", "a simple three-note bansuri motif, repeated", "soft rain texture"]),
    ("Witness", 5.0, ["a restrained soft rhythmic pulse begins on frame drum", "low strings"]),
    ("Shiva", 4.0, ["low hand percussion", "slowly rising strings", "leave space, not dense"]),
    ("Eyes", 2.25, ["the music pulls back to a quiet held drone"]),
    ("Blessing", 7.75, ["the three-note motif resolves warmly", "bansuri and strings",
                        "a restrained wordless female vocal", "the emotional peak, tender"]),
    ("Tear", 3.0, ["the melody breathes", "solo bansuri", "fading into soft wind"]),
]
DAMARU_PROMPT = ("A single resonant damaru hand drum accent: two quick rattling strikes of an Indian damaru, warm "
                 "and close, with a short temple-like reverb tail. No music.")
