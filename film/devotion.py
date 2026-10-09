"""The devotion cut (~45 s, 9:16 first): one clear journey, readable without captions.

Parvati's devotion -> the seasons pass around her -> the rishis witness it and carry it to Shiva -> Shiva's
restrained response -> her recognition, the blessing and her relief -> a composed final image and end card.

The seasons are one continuous locked-off shot: keyframe 05 (winter) and four edits of that exact frame
(spring, summer, monsoon, autumn), joined by Kling start/end-frame transitions so her position, the camera, the
tree and the mountains never move while the seasons change. Summer and monsoon carry the Panchabhutas (the ring
of fire and blazing sun, then storm wind, rain and lightning) assailing her tapasya.
"""

SEASON_BASE = "05"
# Season keyframes: edits of keyframe 05 (in order). id: (season name, what changes)
SEASONS = {
    "31": ("spring", "SPRING: the snow has melted into patches of fresh green grass and small wildflowers on the ledge, "
                     "the same rhododendron tree is in full bloom with pink-red blossoms, petals drifting in the air, "
                     "the mountains behind show less snow, soft warm morning light."),
    "32": ("summer", "SUMMER, the fire of tapas: a complete ring of sacred fires burns around her on the bare dry rock "
                     "ledge, a blazing white-hot sun high in a hazy sky, heat shimmer, the same tree in dark green leaf, "
                     "warm harsh golden light, embers drifting."),
    "33": ("monsoon", "MONSOON STORM: dark storm clouds, heavy rain lashing down diagonally, a fierce wind whipping her "
                      "long hair and the end of her sari sideways, the same tree bent in the wind, lightning striking "
                      "behind the mountains, wet glistening rock, steam rising where the fires were, cold grey-blue light."),
    "34": ("autumn", "AUTUMN: the same tree's leaves have turned gold and orange and are falling and swirling around "
                     "her, golden fallen leaves on the rock ledge, a clear sky with warm low golden evening light on the "
                     "mountains."),
}
SEASON_EDIT = ("Image 1 is a film frame. Images 2-5 are identity photos of the young woman. Edit image 1: keep the "
               "camera, framing, composition, her exact position and pose (seated, eyes closed, hands in namaste), her "
               "face, hair, crimson sari, jewellery, the shape and position of the tree, the rocks and the mountain "
               "range exactly the same, and change only the season and weather to: {season} "
               "Photoreal cinematic film frame, no text, no watermark.")

# Season transitions: one Kling take each from one season keyframe to the next (3 s, joined into one 11 s shot).
TRANSITIONS = [("05", "31", "the snow melts away, grass and wildflowers appear and the bare tree bursts into pink "
                            "blossoms, petals drifting"),
               ("31", "32", "the blossoms fall, the tree turns green, the sun grows blazing and a ring of sacred fires "
                            "rises around her"),
               ("32", "33", "storm clouds roll in, wind and heavy rain lash down and hiss on the fires, lightning "
                            "flashes, her hair and sari whip in the wind"),
               ("33", "34", "the storm clears, the leaves turn gold and fall and swirl around her in warm evening "
                            "light")]
TRANSITION_PROMPT = ("Locked-off camera, the frame does not move. Time-lapse of the seasons around @Element1: {change}. "
                     "She stays perfectly still in deep meditation the whole time, eyes closed, hands in namaste, "
                     "exactly in the same place; her face and costume never change.")
TRANSITION_SOUND = "wind changing through the seasons: soft birdsong, crackling fire, rain and thunder, rustling leaves"
SEASONS_CLIP = "30"           # the joined seasons shot: clips/30_t1.mp4
SEASONS_SECONDS = 11.5        # 4 x 3 s takes, retimed to 11.5 s (a little longer than the 11 s it holds, for dissolves)

# New shots (same tuple layout as film.shots.SHOTS). Groupings stay inside the centre third so the 9:16 cut can
# show everyone without a pan.
SHOTS = {
    "25": (["sages", "kf:19"], "Medium shot of the three rishis standing close together on a snowy ridge, grouped in the "
                               "centre of the frame, faces clearly visible: having just seen the young woman meditating "
                               "far away, the rishi in white robes has turned to the other two, and they exchange a "
                               "concerned, deeply moved look. Soft cold light, light snowfall, mountains behind.",
           "The rishi in white turns from the distant view to his two companions; they exchange a concerned, deeply "
           "moved look, then all three nod gravely and turn to set off up the mountain toward Kailash.",
           "soft mountain wind, snow, no voices"),
    "26": (["parvati", "kf:22", "shiva", "kf:21"], "Calm wide two-person shot from the side at eye level on a snowy "
                                                   "Himalayan ledge at sunrise, both figures grouped together in the "
                                                   "centre of the frame and fully visible: on the left Shiva stands in "
                                                   "profile facing right, his face clearly visible with a softened, "
                                                   "gentle compassionate expression, eyes open, his right palm resting "
                                                   "on the head of the young woman; she kneels on the right facing "
                                                   "him in three-quarter view toward camera, hands folded in prayer, "
                                                   "her tear-streaked face lifted toward him in relief. Soft golden "
                                                   "sunrise light, a sea of clouds behind, no dramatic effects.",
           "Shiva rests his palm gently on @Element1's head in blessing; she closes her eyes as tears of relief roll "
           "down and a soft smile forms; golden light, snow drifting. Very slow push-in.",
           "soft wind, a single gentle temple bell"),
}

# Score (~45.5 s): sections cut to the picture. (name, seconds, styles)
MUSIC_GLOBAL = ["Indian devotional film score", "intimate and emotional", "instrumental", "wordless choir only",
                "no lyrics", "D minor, raga Shivaranjani colour", "slow, rubato feel, no steady beat"]
MUSIC_NEGATIVE = ["lyrics", "sung words", "spoken word", "rap", "pop", "EDM", "electric guitar", "trailer hits",
                  "heavy drums"]
MUSIC_SECTIONS = [
    ("Devotion", 3.25, ["solo bansuri phrase over soft tanpura drone", "intimate"]),
    ("Seasons", 11.0, ["quiet mountain wind texture", "sparse bansuri", "soft tanpura", "no drums", "time passing"]),
    ("Rishis", 7.0, ["gradual build", "low strings enter", "soft wordless male choir", "gentle frame drum pulse"]),
    ("Shiva", 7.75, ["anticipation", "sustained strings and choir slowly swelling",
                     "pulls back to a soft held drone in the last two seconds"]),
    ("Blessing", 10.5, ["one resonant temple bell at the start", "warm emotional resolution", "full strings",
                        "gentle wordless female choir", "bansuri melody", "tender and luminous"]),
    ("Ending", 7.0, ["soft resolve", "solo bansuri over tanpura", "fading out gently"]),
]
BELL_AT = 29.0                # start of "Blessing": Shiva's eyes open, the bell rings
DIP = (27.6, 29.0, -9.0)      # a brief reduction (not silence) just before his eyes open: start, end, dB

# The cut: (shot, start, end, dissolve out). Hard cuts inside a beat of the story, dissolves where time passes.
# Cuts are placed for the emotion, not forced onto beats; 21 starts on its first frame so his eyes open on the bell.
TIMELINE = [
    ("03", 0.00, 1.75, False),     # her face: effort and resolve
    ("01", 1.75, 3.25, True),      # the Himalayas
    ("30", 3.25, 14.25, True),     # one locked-off shot through winter, spring, summer, monsoon, autumn
    ("19", 14.25, 16.75, False),   # the rishis see her; one points toward Kailash
    ("25", 16.75, 18.75, True),    # they exchange a concerned look and set off
    ("20", 18.75, 21.25, False),   # at Kailash they plead with Shiva
    ("11", 21.25, 24.21, False),   # Shiva, still, in meditation
    ("21", 24.21, 31.00, True),    # one continuous take: his eyes open gently on the bell, his face softens
    ("14", 31.00, 33.25, False),   # she recognises him: a single tear, a soft smile
    ("26", 33.25, 37.00, False),   # the blessing, wide: his face, his hand on her head, her prayer
    ("22", 37.00, 39.50, True),    # her close-up: tears of relief, hands lifted in prayer
    ("15", 39.50, 41.75, True),    # composed final image
]
TREATMENT = {      # camera on the 9:16 cut: slow, deliberate moves only; nothing on the beat
    "03": {"push": 0.06}, "01": {"push": 0.06}, "30": {"push": 0.035}, "19": {"push": 0.04}, "25": {"push": 0.05},
    "20": {"push": 0.05}, "11": {"push": 0.05}, "21": {"push": 0.12, "point": "eyes"}, "14": {"push": 0.05},
    "26": {"push": 0.035}, "22": {"push": 0.05}, "15": {"push": -0.06},
}
IN_AT = {"30": 0.5, "25": 0.5}
REFRAME = {"30": (0.52, 0.52), "25": (0.5, 0.5), "26": (0.52, 0.55), "11": (0.5, 0.5)}
FIT = {"26": (0.33, 0.72)}   # 9:16: the blessing keeps his face, his hand and her face in one frame
CARD_LINES = ["Through every season,", "her devotion remained."]
CARD_TITLE = "HAR HAR MAHADEV"

# Native 9:16 versions of the rishi shots for the vertical cut (the 16:9 frames are too wide to crop):
# id: (16:9 shot it replaces, refs, keyframe description, video action, ambience, seconds)
VERTICAL = {
    "19v": ("19", ["kf:19", "sages", "parvati"],
            "Vertical 9:16 film frame, layered top to bottom: in the lower foreground the three rishis stand on a snowy "
            "ridge seen from behind and in profile, the rishi in white robes raising his arm to point; beyond them, in "
            "the middle of the frame across a misty gorge, the young woman in a crimson sari meditates alone on her "
            "cliff ledge, eyes closed, hands in namaste; at the top of the frame the sacred pyramid peak of Mount "
            "Kailash glows in the first light. Light snowfall.",
            "The rishi in white points past the meditating woman toward Kailash; the others turn their heads to follow, "
            "awed. She stays perfectly still. Snow drifts. Slow push-in.",
            "soft mountain wind, snow, no voices", "4"),
    "25v": ("25", ["kf:25", "sages"],
            "Vertical 9:16 medium shot: the three rishis standing close together on a snowy ridge, all three fully in "
            "frame from the waist up, the rishi in white in the centre front and the two others just behind him on "
            "either side, faces clearly visible, exchanging a concerned, deeply moved look. Soft cold light, light "
            "snowfall, mountains behind.",
            "The rishi in white turns to his two companions; they exchange a concerned, deeply moved look, then all "
            "three nod gravely and turn to set off up the mountain.",
            "soft mountain wind, snow, no voices", "4"),
    "20v": ("20", ["kf:20", "sages", "shiva"],
            "Vertical 9:16 film frame on the snowy summit of Mount Kailash under a swirling storm sky: in the upper half "
            "Shiva sits in padmasana meditation on a rock, eyes closed, his trishul with damru planted beside him; in "
            "the lower foreground the three rishis kneel in the snow before him, seen from behind and the side, the "
            "rishi in white raising an open palm toward him, pleading, the other two bowing with folded hands.",
            "The kneeling rishi in white raises his open palm toward Shiva and then presses his hand to his heart, "
            "pleading; the other two bow low. Shiva stays perfectly still, eyes closed. Snow streams in the wind. Slow "
            "push-in.",
            "storm wind, distant thunder, no voices", "4"),
}
VERTICAL_IN_AT = {"19": 0.0, "25": 0.5, "20": 0.0}   # 20v: the rishi's raised palm comes at the start of the take
