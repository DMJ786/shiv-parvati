"""THE SIP — photoreal dream shots with Gemini (image) + Veo (video).

Step 1: for each shot, Gemini's image model makes a photoreal first frame of *him* (from the
        reference stills) in the scene, in a navy suit.
Step 2: Veo animates that frame into a vertical 9:16 clip.
Clips land in veo/ and are cut into the café footage by the edit script.

Needs GEMINI_API_KEY in the environment.  `python3 veo_trailer.py --dry` just prints the plan.
"""
import os, sys, time, json, pathlib
from google import genai
from google.genai import types

OUT = pathlib.Path(__file__).parent / 'veo'
REFS = ['reference_face_confident.jpg', 'reference_face_smile.jpg']

LOOK = ('Photorealistic 35mm anamorphic film still, shallow depth of field, natural skin texture, subtle film grain, '
        'cinematic color grade, vertical 9:16 composition. The man is exactly the person in the reference photos: '
        'South Asian man, early 30s, thick curly black hair swept back, full trimmed black beard. ')
SUIT = 'He wears a perfectly tailored dark navy suit, crisp white shirt and a dark burgundy tie. '

SHOTS = [
    dict(id='01_tower', dur=4,
         image='Blue hour, he stands in a floor-to-ceiling glass corner office at the top of a skyscraper, city lights '
               'stretching to the horizon below, hands in pockets, calm and powerful, warm lamp light on his face.',
         motion='Slow cinematic dolly-in from behind his shoulder around to his profile; city lights twinkle; he turns his head slightly toward camera.'),
    dict(id='02_bell', dur=3,
         image='A grand stock exchange balcony, he rings a brass opening bell, gold confetti falling through warm light, a cheering crowd below out of focus.',
         motion='Slow motion: he strikes the bell and smiles, confetti drifts across the lens, crowd applauds.'),
    dict(id='03_keynote', dur=4,
         image='He speaks at a podium on a vast dark keynote stage, a giant LED screen behind him showing his face, '
               'haze and light beams, audience silhouettes in the foreground.',
         motion='Slow push-in from behind the audience; stage lights sweep through haze; camera flashes pop in the crowd.'),
    dict(id='04_arrival', dur=3,
         image='Golden hour, he steps out of the back of a black luxury sedan in front of a modern glass villa with palm trees, sun flare behind him.',
         motion='Low angle tracking shot as he steps out and buttons his jacket, sunlight flares across the lens.'),
    dict(id='05_daughter', dur=4,
         image='Golden hour on a green lawn outside the villa, his jacket off and sleeves rolled up, his 5-year-old daughter runs toward him laughing.',
         motion='Slow motion: he kneels, catches his daughter and lifts her into the air, spinning her, backlit by the sun, both laughing.'),
    dict(id='06_father', dur=4,
         image='Warm interior at dusk, his elderly father with grey hair and a white kurta places a hand on his shoulder, proud and teary-eyed; the son looks down, moved.',
         motion='Very slow push-in on the two faces; the father squeezes his shoulder; soft window light.'),
    dict(id='07_dinner', dur=3,
         image='A candlelit family dinner in the villa: his wife, daughter, and elderly parents laughing around the table, his mother serving food.',
         motion='Handheld gentle drift across the table, everyone laughing, candles flicker.'),
    dict(id='08_balcony', dur=4,
         image='Night, he stands alone on a penthouse terrace above glittering city lights, holding a glass, wind in his hair, looking out peacefully.',
         motion='Slow orbit toward his face; he closes his eyes and exhales, content. End on an extreme close-up of his closed eyes.'),
]


def pick(client, kind):
    names = [m.name for m in client.models.list()]
    if kind == 'image':
        pref = [n for n in names if 'image' in n and 'gemini' in n] or [n for n in names if 'imagen' in n]
    else:
        pref = [n for n in names if 'veo' in n]
    pref.sort(reverse=True)   # newest version strings first
    if not pref: sys.exit(f'no {kind} model available for this key: {names}')
    return pref[0]


def first_frame(client, model, shot):
    path = OUT / f"{shot['id']}.png"
    if path.exists(): return path
    parts = [types.Part.from_bytes(data=open(r, 'rb').read(), mime_type='image/jpeg') for r in REFS]
    prompt = LOOK + SUIT + shot['image']
    if shot['id'] == '05_daughter':
        prompt = prompt.replace(SUIT, 'He wears navy suit trousers and a white shirt, sleeves rolled. ')
    r = client.models.generate_content(model=model, contents=parts + [prompt],
                                       config=types.GenerateContentConfig(response_modalities=['IMAGE'],
                                                                          image_config=types.ImageConfig(aspect_ratio='9:16')))
    for p in r.candidates[0].content.parts:
        if p.inline_data:
            path.write_bytes(p.inline_data.data); return path
    raise RuntimeError(f"no image for {shot['id']}: {r.text if hasattr(r, 'text') else r}")


def animate(client, model, shot, frame):
    path = OUT / f"{shot['id']}.mp4"
    if path.exists(): return path
    op = client.models.generate_videos(
        model=model,
        prompt=LOOK + SUIT + shot['image'] + ' ' + shot['motion'] + ' No text, no logos, no watermark.',
        image=types.Image(image_bytes=frame.read_bytes(), mime_type='image/png'),
        config=types.GenerateVideosConfig(aspect_ratio='9:16', number_of_videos=1, person_generation='allow_adult'),
    )
    while not op.done:
        time.sleep(15); op = client.operations.get(op)
    if not op.response or not op.response.generated_videos:
        raise RuntimeError(f"Veo returned nothing for {shot['id']}: {op}")
    v = op.response.generated_videos[0]
    client.files.download(file=v.video)
    v.video.save(str(path))
    return path


if __name__ == '__main__':
    if '--dry' in sys.argv:
        for s in SHOTS: print(s['id'], s['dur'], 's |', s['image'][:80], '...')
        sys.exit()
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key: sys.exit('GEMINI_API_KEY is not set')
    client = genai.Client(api_key=key)
    OUT.mkdir(exist_ok=True)
    im_model, vid_model = pick(client, 'image'), pick(client, 'video')
    print('models:', im_model, vid_model)
    only = [a for a in sys.argv[1:] if not a.startswith('-')]
    for s in SHOTS:
        if only and s['id'] not in only: continue
        f = first_frame(client, im_model, s); print('frame', f)
        v = animate(client, vid_model, s, f); print('clip', v)
