import cv2, numpy as np
_dis = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
def _gray(x): return cv2.cvtColor(np.clip(x[..., :3], 0, 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
def interp(a, b, t, fab=None, fba=None):
    """flow-based in-between of float images a,b (HxWxC) at 0<t<1"""
    if fab is None:
        ga, gb = _gray(a), _gray(b)
        fab = _dis.calc(ga, gb, None); fba = _dis.calc(gb, ga, None)
    h, w = a.shape[:2]
    gx, gy = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    t = float(t)
    wa = cv2.remap(a, (gx + t * fba[..., 0]).astype(np.float32), (gy + t * fba[..., 1]).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    wb = cv2.remap(b, (gx + (1 - t) * fab[..., 0]).astype(np.float32), (gy + (1 - t) * fab[..., 1]).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return wa * (1 - t) + wb * t
def resample(frames, src_times):
    """frames: list/array of float images; src_times: float indices -> interpolated images"""
    cache = {}
    out = []
    for s in src_times:
        i = int(np.floor(s)); t = s - i
        i = min(max(i, 0), len(frames) - 1)
        if t < 1e-3 or i + 1 >= len(frames):
            out.append(np.asarray(frames[i]).astype(np.float32)); continue
        if i not in cache:
            a, b = np.asarray(frames[i]).astype(np.float32), np.asarray(frames[i + 1]).astype(np.float32)
            ga, gb = _gray(a), _gray(b)
            cache = {i: (a, b, _dis.calc(ga, gb, None), _dis.calc(gb, ga, None))}
        a, b, fab, fba = cache[i]
        out.append(interp(a, b, t, fab, fba))
    return out
