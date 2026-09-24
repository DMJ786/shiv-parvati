"""numpy compositing helpers shared by the trailer edit"""
import numpy as np, cv2, os
from PIL import Image, ImageDraw, ImageFont

W, H = 720, 1280
SP = os.path.dirname(os.path.abspath(__file__))
FD = SP + '/fonts/'
rng = np.random.default_rng(5)


def load_rgba(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    im = im.astype(np.float32)
    if im.shape[1] != W:
        im = cv2.resize(im, (W, H), interpolation=cv2.INTER_CUBIC)
    return im


def load_mist(p):
    m = cv2.imread(p, cv2.IMREAD_UNCHANGED).astype(np.float32) / 65535
    if m.ndim == 3: m = m[..., 0]
    return cv2.resize(m, (W, H))


def vgrad(stops, h=H, w=W):
    """stops: list of (pos 0..1 top->bottom, rgb)"""
    y = np.linspace(0, 1, h)
    cols = np.stack([np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops]) for c in range(3)], 1)
    return np.repeat(cols[:, None, :], w, 1).astype(np.float32)


def stars(n=220, seed=3, maxy=0.6):
    r = np.random.default_rng(seed)
    im = np.zeros((H, W), np.float32)
    for _ in range(n):
        x, y = int(r.uniform(0, W)), int(r.uniform(0, H * maxy))
        im[y, x] = r.uniform(80, 255)
    im = cv2.GaussianBlur(im, (0, 0), 0.7) * 3
    return np.repeat(im[..., None], 3, 2)


def bloom(img, thr=170, amt=0.5, r=18):
    hi = np.clip(img - thr, 0, 255)
    return img + amt * (cv2.GaussianBlur(hi, (0, 0), r) + 0.6 * cv2.GaussianBlur(hi, (0, 0), r * 3))


def anamorphic(img, thr=215, amt=0.35):
    hi = np.clip(img - thr, 0, 255)
    k = cv2.GaussianBlur(hi, (0, 0), sigmaX=60, sigmaY=1.5)
    return img + amt * k * np.array([0.6, 0.8, 1.2])


def grade(img, lift=(0, 0, 0), gain=(1, 1, 1), sat=1.0, contrast=1.0):
    x = img / 255
    x = x * np.array(gain) + np.array(lift) * (1 - x)
    g = x.mean(2, keepdims=True)
    x = g + (x - g) * sat
    x = 0.5 + (x - 0.5) * contrast
    return np.clip(x, 0, 1.2) * 255


def vignette(img, s=0.5):
    y, x = np.mgrid[0:H, 0:W]
    d = np.sqrt(((x - W / 2) / (W / 2)) ** 2 + ((y - H / 2) / (H / 2)) ** 2)
    return img * (1 - s * np.clip(d - 0.5, 0, 1)[..., None] ** 1.3)
YY, XX = np.mgrid[0:H, 0:W]
DD = np.sqrt(((XX - W / 2) / (W / 2)) ** 2 + ((YY - H / 2) / (H / 2)) ** 2)
def vignette_fast(img, s=0.5):
    return img * (1 - s * np.clip(DD - 0.5, 0, 1)[..., None] ** 1.3)


def grain(img, s=6.0):
    n = rng.normal(0, s, (H // 2, W // 2)).astype(np.float32)
    n = cv2.resize(n, (W, H), interpolation=cv2.INTER_LINEAR)
    return img + n[..., None]


def letterbox(img, bar):
    if bar > 0:
        img[:bar] = 0; img[H - bar:] = 0
    return img


def zoom(img, s, cx=W / 2, cy=H / 2, dx=0, dy=0):
    M = np.float32([[s, 0, cx - s * cx + dx], [0, s, cy - s * cy + dy]])
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def ease(x):
    x = min(max(x, 0.0), 1.0); return x * x * (3 - 2 * x)


def eout(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3


def ein(x):
    x = min(max(x, 0.0), 1.0); return x ** 3


_fc = {}
def font(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + name, size)
    return _fc[k]


def title(img, lines, glow=0.0):
    """lines: list of (text, fontname, size, (x,y), rgb, alpha, tracking)"""
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for txt, fn, sz, (x, y), col, a, tr in lines:
        if a <= 0.001: continue
        f = font(fn, sz); c = tuple(int(v) for v in col) + (int(255 * min(a, 1)),)
        ws = [d.textlength(ch, font=f) for ch in txt]
        tot = sum(ws) + tr * (len(txt) - 1)
        xx = x - tot / 2
        for ch, w in zip(txt, ws):
            d.text((xx, y), ch, font=f, fill=c, anchor='lm'); xx += w + tr
    L = np.asarray(im).astype(np.float32)
    a = L[..., 3:4] / 255
    out = img * (1 - a) + L[..., :3] * a
    if glow:
        out = out + glow * cv2.GaussianBlur(L[..., :3] * a, (0, 0), 10)
    return out


def light_leak(t, strength=1.0, seed=0):
    """soft moving warm light leak (additive)"""
    cx = W * (0.2 + 0.6 * (0.5 + 0.5 * np.sin(t * 0.9 + seed)))
    cy = H * (0.3 + 0.4 * (0.5 + 0.5 * np.cos(t * 0.6 + seed * 2)))
    d = np.sqrt(((XX - cx) / (W * 0.7)) ** 2 + ((YY - cy) / (H * 0.5)) ** 2)
    k = np.clip(1 - d, 0, 1) ** 2
    return k[..., None] * np.array([255, 150, 60], np.float32) * strength
