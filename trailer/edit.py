"""Final cut: 'THE SIP' — 40s trailer. Composites café footage + Blender dream renders."""
import sys, json, subprocess
from post import *
from delogo import delogo
from slowmo import resample
import post_city

FPS = 24
FR = np.load(SP + '/frames.npy', mmap_mode='r')

def cafe(i):
    i = int(min(max(i, 0), len(FR) - 1))
    return cv2.cvtColor(delogo(FR[i]), cv2.COLOR_BGR2RGB).astype(np.float32)

def cafe_grade(img, warm=0.0):
    img = grade(img, lift=(0.0, 0.012, 0.02), gain=(1.0 + 0.06 * warm, 1.0, 1.0 - 0.08 * warm), sat=0.92, contrast=1.06)
    return vignette_fast(img, 0.35)

# ---------------------------------------------------------------- timeline (seconds)
T = dict(A=0.0, B=2.5, C=5.0, D1=6.5, D2=10.5, D3=13.5, D4=17.0, D5=21.0, R1=25.0, R2=27.5, R3=33.5, END=37.2, TOTAL=40.0)
SCENE_WORD = {'D1': 'EMPIRE', 'D2': 'WEALTH', 'D3': 'RESPECT', 'D4': 'FAMILY', 'D5': 'PEACE'}

# slow-motion plates (optical-flow interpolated)
def plate(src0, src1, dur):
    n = int(round(dur * FPS))
    idx = np.linspace(src0 * FPS, src1 * FPS, n, endpoint=False)
    lo, hi = int(idx.min()), int(idx.max()) + 2
    frames = [cafe(k) for k in range(lo, hi + 1)]
    return resample(frames, list(idx - lo))

print('building slow-mo plates', file=sys.stderr)
PL_C = plate(12.45, 13.7, T['D1'] - T['C'])       # eyes closing
PL_R1 = plate(13.7, 16.9, T['R2'] - T['R1'])     # eyes open, back in the café
PL_R2 = plate(16.9, 18.35, T['R3'] - T['R2'])     # the smile, ~6x slow

HZ_ROOF = {int(k): v for k, v in json.load(open(SP + '/r/roof_horizon.json')).items()}

def caption(img, word, lt, dur, y=H * 0.14):
    a = ease((lt - 0.35) / 0.5) * (1 - ease((lt - dur + 0.45) / 0.35))
    if a <= 0: return img
    tr = 22 + 10 * lt / dur   # slow tracking drift, classic trailer title
    return title(img, [(word, 'SourceSansPro-Light.ttf', 44, (W / 2, y), (255, 244, 225), a * 0.95, tr)], glow=0.5 * a)

# ---------------------------------------------------------------- dream scene post
def s_city(f):
    return post_city.city(f)

def s_number(f):
    im = load_rgba(f'{SP}/r/number/{f:04d}.png')[..., :3]
    im = bloom(im, 150, 0.8, 12); im = anamorphic(im, 190, 0.35)
    im = grade(im, lift=(0.01, 0.005, 0.0), gain=(1.08, 1.0, 0.9), sat=1.05, contrast=1.08)
    im = vignette_fast(im, 0.55)
    return im

FLASH_T = [(9, 330, 1010), (23, 150, 1080), (31, 520, 990), (47, 90, 1030), (58, 610, 1060), (66, 260, 1000), (77, 470, 1045)]
def s_stage(f):
    im = load_rgba(f'{SP}/r/stage/{f:04d}.png'); m = load_mist(f'{SP}/r/stage/mist/m{f:04d}.png')
    a = im[..., 3:] / 255; rgb = im[..., :3]
    haze = np.array([30, 40, 70], np.float32)
    rgb = rgb + haze * (m[..., None] * 0.6) * a + np.array([4, 5, 10]) * (1 - a)
    # audience camera flashes
    for ff, x, y in FLASH_T:
        k = f - ff
        if 0 <= k < 3:
            s = [1.0, 0.45, 0.12][k]
            d = np.sqrt((XX - x) ** 2 + (YY - y) ** 2)
            rgb = rgb + (np.clip(1 - d / 90, 0, 1) ** 2 * 255 * s)[..., None] + 25 * s
    rgb = bloom(rgb, 160, 0.7, 16); rgb = anamorphic(rgb, 190, 0.4)
    rgb = grade(rgb, lift=(0.0, 0.01, 0.035), gain=(1.02, 1.0, 1.03), sat=1.05, contrast=1.08)
    return vignette_fast(rgb, 0.5)

def s_home(f):
    im = load_rgba(f'{SP}/r/home/{f:04d}.png')[..., :3]
    im = bloom(im, 165, 0.6, 14); im = anamorphic(im, 200, 0.2)
    im = grade(im, lift=(0.0, 0.01, 0.03), gain=(1.06, 1.0, 0.95), sat=1.05, contrast=1.05)
    return vignette_fast(im, 0.45)

ROOF_STARS = stars(200, seed=9)
def s_roof(f):
    im = load_rgba(f'{SP}/r/roof/{f:04d}.png'); m = load_mist(f'{SP}/r/roof/mist/m{f:04d}.png')
    a = im[..., 3:] / 255; rgb = im[..., :3]
    hy = HZ_ROOF[f]
    sky = post_city.sky_for(hy) + ROOF_STARS * np.clip((hy * H - YY[..., None] - 150) / 400, 0, 1)
    sky = cv2.GaussianBlur(sky, (0, 0), 6)  # out of focus like the city
    k = (m ** 1.5)[..., None]
    rgb = rgb * (1 - k) + np.array([200, 110, 80], np.float32) * k * a
    out = rgb + sky * (1 - a)
    # body falls off into shadow
    out = out * (1 - 0.8 * np.clip((YY[..., None] - H * 0.72) / (H * 0.28), 0, 1))
    out = bloom(out, 150, 0.6, 16); out = anamorphic(out, 200, 0.25)
    out = grade(out, lift=(0.01, 0.015, 0.04), gain=(1.04, 0.99, 0.97), sat=1.05, contrast=1.06)
    return vignette_fast(out, 0.5)

SCENES = {'D1': (s_city, 96), 'D2': (s_number, 72), 'D3': (s_stage, 84), 'D4': (s_home, 96), 'D5': (s_roof, 96)}
ORDER = ['D1', 'D2', 'D3', 'D4', 'D5']

# ---------------------------------------------------------------- frame
def frame(i):
    t = i / FPS
    if t < T['B']:
        img = cafe_grade(cafe(t * FPS))
        img = img * ease(t / 0.6)
    elif t < T['C']:
        lt = t - T['B']
        img = cafe_grade(zoom(cafe((9.95 + lt) * FPS), 1.0 + 0.07 * lt / 2.5, 380, 380))
    elif t < T['D1']:
        lt = t - T['C']; k = int(lt * FPS)
        img = PL_C[min(k, len(PL_C) - 1)]
        z = 1.07 + 0.25 * ein(lt / 1.5)
        img = cafe_grade(zoom(img, z, 360, 330), warm=lt / 1.5)
        # the world falls away: blur + glow + white-out
        p = ein((lt - 0.8) / 0.7)
        if p > 0:
            img = img * (1 - p * 0.6) + cv2.GaussianBlur(img, (0, 0), 1 + 14 * p) * p * 0.6
            img = bloom(img, 120, 1.2 * p, 30) + 255 * ein((lt - 1.2) / 0.3)
    elif t < T['R1']:
        for n, key in enumerate(ORDER):
            nxt = T[ORDER[n + 1]] if n + 1 < len(ORDER) else T['R1']
            if t < nxt:
                lt = t - T[key]; fn, N = SCENES[key]
                f = min(int(lt * FPS) + 1, N)
                img = fn(f)
                img = caption(img, SCENE_WORD[key], lt, nxt - T[key])
                # hit-cut flash on every scene entry
                fl = 1 - ease(lt / 0.25)
                if fl > 0: img = img + 255 * fl * (0.9 if key == 'D1' else 0.55)
                if key == 'D5':  # push into his eyes, then white
                    p = ein((lt - 3.3) / 0.7)
                    if p > 0:
                        img = zoom(img, 1 + 0.5 * p, W * 0.55, H * 0.42)
                        img = img + 255 * ein((lt - 3.7) / 0.3)
                break
        img = grain(img, 5)
    elif t < T['R2']:
        lt = t - T['R1']; k = int(lt * FPS)
        img = PL_R1[min(k, len(PL_R1) - 1)]
        img = cafe_grade(zoom(img, 1.12 - 0.08 * eout(lt / 2.5), 360, 340))
        img = img + 255 * (1 - ease(lt / 0.6))   # waking from white
    elif t < T['R3']:
        lt = t - T['R2']; k = int(lt * FPS)
        img = PL_R2[min(k, len(PL_R2) - 1)]
        img = cafe_grade(zoom(img, 1.04 + 0.08 * ease(lt / 6.0), 380, 340), warm=0.6 * ease(lt / 6))
        img = img + light_leak(t, 0.18 * ease(lt / 3))
    elif t < T['END']:
        lt = t - T['R3']
        img = PL_R2[-1]
        img = cafe_grade(zoom(img, 1.12 + 0.03 * lt / 3.7, 380, 340), warm=0.6)
        img = img + light_leak(t, 0.18)
        shade = np.clip((YY[..., None] - H * 0.66) / (H * 0.34), 0, 1) * ease(lt / 0.8)
        img = img * (1 - 0.6 * shade)
        a1 = ease((lt - 0.3) / 0.8); a2 = ease((lt - 1.2) / 0.8)
        img = title(img, [('Some dreams are just memories', 'SourceSansPro-Light.ttf', 38, (W / 2, H * 0.83), (255, 246, 232), a1, 2),
                          ('from the future.', 'SourceSansPro-Light.ttf', 38, (W / 2, H * 0.83 + 52), (255, 246, 232), a2, 2)], glow=0.3)
        img = img * (1 - ein((lt - 3.3) / 0.4))
    else:
        lt = t - T['END']
        img = np.zeros((H, W, 3), np.float32)
        a = ease((lt - 0.35) / 0.6) * (1 - ease((lt - 2.2) / 0.5))
        img = title(img, [('IT ALL WORKS OUT.', 'SourceSansPro-Semibold.ttf', 40, (W / 2, H / 2), (240, 214, 150), a, 7)], glow=0.8 * a)
    if T['C'] <= t < T['R1']:
        pass
    else:
        img = grain(img, 3.5)
    return np.clip(img, 0, 255).astype(np.uint8)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'preview':
        ts = [float(x) for x in sys.argv[2].split(',')]
        cols = 6; rows = (len(ts) + cols - 1) // cols
        m = Image.new('RGB', (cols * 240, rows * 427))
        for k, tt in enumerate(ts):
            m.paste(Image.fromarray(frame(int(tt * FPS))).resize((240, 427)), ((k % cols) * 240, (k // cols) * 427))
        m.save('pv.jpg'); sys.exit()
    N = int(T['TOTAL'] * FPS)
    p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', SP + '/trailer_video.mp4'], stdin=subprocess.PIPE)
    for i in range(N):
        p.stdin.write(frame(i).tobytes())
        if i % 48 == 0: print(i, N, file=sys.stderr)
    p.stdin.close(); p.wait()
