"""Episode 2 — "Sati to Parvati": a native 9:16 story reel. New shots are generated vertically; the rest are
re-cropped from the first film's clips."""
from film.shots import PARVATI_LOCK, SHIVA

STYLE = ("Photoreal cinematic vertical 9:16 film still from an epic Indian mythological blockbuster, shot on ARRI "
         "Alexa 65, dramatic volumetric light, crimson fire and gold against cold blue snow, rich texture, shallow "
         "depth of field, soft film grain. No text, no captions, no watermark, no logo, no border.")

SATI_LOCK = PARVATI_LOCK.replace("The woman is", "The woman (Sati, the same soul who is later reborn as Parvati) is")

# id: (refs, keyframe prompt, video action prompt, ambience prompt)
NEW = {
    "s1": (["parvati"], "Night at King Daksha's great yagna: she stands before a towering roaring sacred fire in a stone "
                        "courtyard with carved pillars, tears in her eyes but her face resolute, firelight on her face, "
                        "embers drifting. Medium close-up from a low angle.",
           "She stares into the sacred fire, a single tear falls, her jaw sets with resolve; flames roar and embers "
           "swirl. Slow push-in.",
           "roaring fire, crackling embers, distant murmuring crowd with no clear words"),
    "s2": (["parvati", "kf:s1"], "Same night, same stone courtyard and towering yagna fire as the previous shot: "
                                 "she now faces the fire in profile with folded hands and closed eyes, serene, as "
                                 "brilliant golden light and thousands of glowing golden embers rise around her, her "
                                 "silhouette beginning to turn into light. Divine and peaceful, not frightening, no "
                                 "burning, no snow. Medium shot.",
           "Golden light swells around her and her form slowly dissolves upward into thousands of glowing golden "
           "embers that rise into the night sky. Slow tilt up.",
           "whoosh of rising fire, shimmering sparks, soft wind"),
    "s3": (["shiva"], "Shiva's fury: he stands inside a wall of towering flames at night, trishul with damru raised high, "
                      "long jata whipping in the fire wind, eyes blazing with rage, cobra hood flared. Low heroic angle, "
                      "full figure.",
           "Shiva slams the trishul into the ground, flames explode upward around him and his jata whips in the "
           "firestorm. Low angle, slight camera shake.",
           "explosive roar of fire, deep impact boom, crackling"),
    "s4": (["shiva"], "Shiva's grief: he sits alone in deep snow at dusk on a vast empty Himalayan plateau, head bowed, "
                      "eyes closed, snow settling on his shoulders and jata, cobra around his neck, cold blue light, tiny "
                      "figure in a huge frame. No fire, no campfire, nothing warm: only snow, wind and loneliness.",
           "Snow falls silently on Shiva as he sits motionless with his head bowed; wind drifts snow across the "
           "plateau. Very slow push-in.",
           "soft wind, falling snow, deep silence"),
    "s5": (["parvati"], "Reborn as Parvati, she plants a golden trishul into the snow on a high Himalayan ridge and "
                        "looks up toward the distant peak of Kailash, wind lifting her crimson sari and hair, determined. "
                        "Full figure, low angle.",
           "She drives the golden trishul into the snow with both hands, snow bursts up, then she lifts her gaze to "
           "Kailash as the wind lifts her sari. Low angle.",
           "crunch of snow, metallic thud of the trishul, gusting wind"),
    "s6": (["parvati"], "Close-up: her sheer crimson dupatta veil blows across her face in the mountain wind, her eyes "
                        "glistening with tears looking up, snowflakes, soft backlight.",
           "The wind blows her sheer red veil across her face and away again, revealing her tearful, hopeful eyes "
           "looking up. Slow motion feel.",
           "soft wind, fabric flutter"),
    "s7": (["shiva", "parvati"], "Shiva and Parvati stand together hand in hand on the snowy summit of Kailash at sunrise, "
                                 "seen from a low angle three-quarter view, she in her crimson sari, he with trishul, "
                                 "golden sun rising behind them over a sea of clouds, vast and majestic.",
           "The sun rises behind Shiva and Parvati as they stand hand in hand; golden light floods over the clouds and "
           "their clothes move gently in the wind. Slow crane up.",
           "soft wind, distant temple bell resonance"),
}

# Reused clips from the first film (id -> (clip file stem, subject x for the 9:16 crop)).
REUSE = {
    "r01": ("01_t1", 0.5),     # aerial peaks at dawn
    "r04": ("04_t2", 0.69),    # tapasya in the blizzard
    "r06": ("06_t2", 0.5),     # panchagni ring of fire
    "r10": ("10_t1", 0.61),    # cobra's eye opens
    "r12": ("12_t1", 0.5),     # Shiva's frosted closed eyes
    "r13": ("13_t2", 0.5),     # eyes open, gold glow
    "r14": ("14_t2", 0.55),    # smile and a single tear
}

# Story order, grouped by music section: (section name, seconds, styles, shots)
SECTIONS = [
    ("Yagna", 7, ["slow ominous frame-drum pulse on every beat", "tanpura drone", "mournful solo sarangi",
                  "sorrowful, foreboding, medium-quiet"], ["s1", "s2"]),
    ("Fury", 8, ["explosive and loud", "full-power war drums, dhol and taiko on every beat", "brass hits",
                 "fierce deep wordless male choir chant", "furious"], ["s3", "r10", "s3b"]),
    ("Grief", 5, ["abrupt drop", "very quiet", "only a lonely solo bansuri and soft wind", "no drums"],
     ["s4", "r12a"]),
    ("Rebirth", 11, ["gradual build from quiet to strong", "tabla pulse", "rising strings", "hopeful bansuri melody",
                     "crescendo", "devotional"], ["r01", "s5", "r04", "r06", "s6"]),
    ("Eyes open", 4, ["near silence", "no drums", "held breath"], ["r14", "r12"]),
    ("Union", 10, ["the loudest moment of the whole piece", "massive wordless choir and full orchestra",
                   "huge drums", "triumphant and divine", "gentle bansuri resolve only in the last 3 seconds"],
     ["r13", "s7", "end"]),
]
MUSIC_GLOBAL = ["epic Indian mythological film score", "instrumental", "wordless choir only", "no lyrics",
                "cinematic trailer", "92 bpm", "strong dynamic contrast between sections"]
MUSIC_NEGATIVE = ["lyrics", "sung words", "spoken word", "rap", "pop", "EDM", "electric guitar"]
