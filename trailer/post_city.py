from post import *
import json
HZ = {int(k): v for k, v in json.load(open(SP + '/r/city_horizon.json')).items()}
STARS = stars(260)
def sky_for(hy):
    h = hy * H
    return vgrad([(0, (3, 6, 22)), (max(0.001, (h - 700) / H), (10, 16, 48)), (max(0.002, (h - 300) / H), (60, 36, 78)),
                  (max(0.003, (h - 60) / H), (185, 92, 62)), (max(0.004, h / H), (235, 150, 90)), (max(0.005, h / H) + 0.3, (120, 60, 50))]) if h > 0 else vgrad([(0, (230, 140, 80)), (1, (120, 60, 50))])
def city(f):
    im = load_rgba(f'{SP}/r/city/{f:04d}.png'); m = load_mist(f'{SP}/r/city/mist/m{f:04d}.png')
    a = im[..., 3:] / 255; rgb = im[..., :3]
    hy = HZ[f]
    sky = sky_for(hy) + STARS * np.clip((hy * H - YY[..., None] - 150) / 400, 0, 1)
    fogc = np.array([200, 110, 80], np.float32)
    k = (m ** 1.5)[..., None]
    rgb = rgb * (1 - k) + fogc * k * a
    out = rgb + sky * (1 - a)
    out = bloom(out, 160, 0.6, 14)
    out = anamorphic(out, 200, 0.25)
    out = grade(out, lift=(0.01, 0.02, 0.05), gain=(1.05, 0.98, 0.95), sat=1.1, contrast=1.05)
    return vignette_fast(out, 0.5)
if __name__ == '__main__':
    import sys
    fs = [int(x) for x in sys.argv[1].split(',')]
    m = Image.new('RGB', (len(fs) * 360, 640))
    for k, f in enumerate(fs):
        m.paste(Image.fromarray(np.clip(city(f), 0, 255).astype(np.uint8)).resize((360, 640)), (k * 360, 0))
    m.save('pv.jpg')
