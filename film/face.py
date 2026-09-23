"""Face-identity scoring against reference faces (insightface buffalo_l / ArcFace)."""
import functools
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
IDENTITIES = {
    "parvati": [ROOT / "refs" / f"{n}.png" for n in ("p01", "p03", "p04", "p06")],
    "shiva": [ROOT / "heroes" / "shiva.png"],
}


@functools.lru_cache(maxsize=1)
def _app():
    from insightface.app import FaceAnalysis
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"],
                       allowed_modules=["detection", "recognition"])
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def _detect(im):
    """Faces in an array, largest first. Pads so frame-filling close-ups are still detected."""
    pad = max(im.shape[:2]) // 3
    im = cv2.copyMakeBorder(im, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=(128, 128, 128))
    fs = [f for f in _app().get(im) if f.det_score > 0.5]
    return sorted(fs, key=lambda f: -(f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])), pad


def faces(path):
    """Faces in an image, largest first. Small faces (wide shots) are re-detected on a zoomed crop so the
    landmarks and embedding come from full-resolution pixels, not the 640px detector input."""
    im = cv2.imread(str(path))
    coarse, pad = _detect(im)
    out = []
    for f in coarse:
        x0, y0, x1, y1 = f.bbox - pad
        side = max(x1 - x0, y1 - y0)
        if side * 640 / (max(im.shape[:2]) * 5 / 3) > 160:   # already big in the detector input
            out.append(f)
            continue
        cx, cy, half = (x0 + x1) / 2, (y0 + y1) / 2, side * 1.6
        crop = im[max(0, int(cy - half)):int(cy + half), max(0, int(cx - half)):int(cx + half)]
        crop = cv2.resize(crop, None, fx=480 / max(crop.shape[:2]), fy=480 / max(crop.shape[:2]),
                          interpolation=cv2.INTER_CUBIC)
        fine, _ = _detect(crop)
        out.append(fine[0] if fine else f)
    return out


@functools.lru_cache(maxsize=None)
def ref_embeddings(who):
    return np.stack([faces(p)[0].normed_embedding for p in IDENTITIES[who]])


def score(path, who="parvati"):
    """Cosine similarity of the image's best-matching face to each ref: (mean, max), or None if no face."""
    fs = faces(path)
    if not fs:
        return None
    refs = ref_embeddings(who)
    best = max(fs, key=lambda f: float((refs @ f.normed_embedding).mean()))
    sims = refs @ best.normed_embedding
    return float(sims.mean()), float(sims.max())


def face_box(path, who="parvati"):
    """(x0, y0, x1, y1) in image pixels of the face that best matches `who`, or None."""
    im = cv2.imread(str(path))
    coarse, pad = _detect(im)
    if not coarse:
        return None
    refs = ref_embeddings(who)
    fine = faces(path)
    best = max(range(len(coarse)), key=lambda i: float((refs @ fine[i].normed_embedding).mean()))
    return tuple(float(v) for v in coarse[best].bbox - pad)
