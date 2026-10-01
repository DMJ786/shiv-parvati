#!/usr/bin/env python3
"""
Local video face replacement with explicit target locking.

Replaces ONLY the main character (adult man in the light-pink shirt) with the identity in --face.
Everything runs locally: PySceneDetect (cuts) -> InsightFace SCRFD/ArcFace (detect + embed)
-> per-shot tracking -> identity clustering to lock the target -> INSwapper (128) on temporally
smoothed landmarks -> colour match + feathered mask + grain re-injection -> optional
conservative GFPGAN -> lossless per-scene segments -> H.264 assembly with the untouched
original audio (if the source has any).

  python local_face_replace.py --video "./videoplayback (1).mp4" --face ./face.png \
      --output ./output/local_face_swap_final.mp4 --preview
  python local_face_replace.py ... --full            # whole movie (resumes completed scenes)
  python local_face_replace.py ... --scene 7         # one scene only
  python local_face_replace.py ... --make-contact-sheets
Flags: --resume (default behaviour; kept for clarity), --force (redo finished scenes), --models DIR,
       --no-enhance, --enhance-blend 0.25, --env-check
"""
import argparse, json, math, os, pickle, shutil, subprocess, sys, time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
WORK, OUTDIR = ROOT / "work", ROOT / "output"
D_FRAMES, D_QC, D_AMB, D_CACHE, D_SEG = (WORK / d for d in ("frames", "qc", "ambiguous", "cache", "segments"))
SCENES_JSON = WORK / "scenes.json"

# ----------------------------------------------------------------------------- tunables
DET_SIZE = (640, 640)
MIN_FACE_PX = 36            # ignore tiny background faces
MIN_DET_SCORE = 0.5
MIN_TRACK_LEN = 6           # frames; shorter tracks are never swapped
MAX_GAP = 6                 # frames a track may disappear and be re-associated
INTERP_GAP = 4              # gaps up to this are filled by landmark interpolation (still swapped)
SAME_ID_SIM = 0.40          # ArcFace cosine: tracks merged into one identity cluster
TARGET_MIN_SIM = 0.33       # track must be at least this similar to the target identity
TARGET_MARGIN = 0.10        # ...and this much more similar to target than to any other identity
SHIRT_TIEBREAK = 0.10       # shirt-score lead needed to resolve a borderline identity decision
KPS_SIGMA = 1.0             # temporal Gaussian on landmarks (frames)
COLOR_SIGMA = 3.0           # temporal Gaussian on colour statistics (frames)
OUTLIER_KPS = 0.12          # landmark jump (fraction of face size) treated as a bad detection
YAW_FADE = (85.0, 95.0)     # fade the swap out between these |yaw| degrees (only beyond full profile)
FADE_FRAMES = 3             # ramp length when the swap starts/stops inside a shot
GRAIN = 0.25                # fraction of the original high-frequency grain put back on the new face
NONTARGET_MAX_DIFF = 1.0    # QC: mean abs pixel change allowed inside any non-target face box
PREVIEW_RANGE = (5.0, 8.0)

INSWAPPER_URLS = [  # tried in order if models/inswapper_128.onnx is missing
    "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/inswapper_128.onnx",
    "https://huggingface.co/ezioruan/inswapper_128.onnx/resolve/main/inswapper_128.onnx",
]
GFPGAN_URLS = [
    "https://github.com/facefusion/facefusion-assets/releases/download/models-3.0.0/gfpgan_1.4.onnx",
]
FFHQ_512 = np.array([[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
                     [0.39308822, 0.72541100], [0.61150205, 0.72490465]], np.float32) * 512


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def warn(*a):
    print(time.strftime("%H:%M:%S"), "WARNING:", *a, flush=True)


def run(cmd, binary=False):
    r = subprocess.run(cmd, capture_output=True, text=not binary)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(map(str, cmd[:6]))} ...\n{r.stderr if not binary else r.stderr.decode()[-1500:]}")
    return r.stdout


def save_json(p, o):
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(o, indent=2, default=float))
    tmp.replace(p)


def load_json(p, default=None):
    return json.loads(Path(p).read_text()) if Path(p).exists() else default


# ----------------------------------------------------------------------------- environment
def env_check():
    info = {"python": sys.version.split()[0]}
    if sys.version_info < (3, 9):
        sys.exit("Python >= 3.9 required")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")
    info["ffmpeg"] = run(["ffmpeg", "-version"]).splitlines()[0]
    import onnxruntime as ort
    prov = ort.get_available_providers()
    info["onnxruntime"] = ort.__version__
    info["providers"] = prov
    accel = [p for p in ("CUDAExecutionProvider", "CoreMLExecutionProvider", "DmlExecutionProvider", "ROCMExecutionProvider") if p in prov]
    info["accelerator"] = accel[0] if accel else "CPU"
    if not accel:
        warn("no GPU execution provider (CUDA / CoreML / DirectML) available - running on CPU, this will be slow. "
             "On NVIDIA install onnxruntime-gpu; on Apple Silicon the standard onnxruntime wheel includes CoreML.")
    return info


def providers():
    import onnxruntime as ort
    avail = ort.get_available_providers()
    pref = [p for p in ("CUDAExecutionProvider", "CoreMLExecutionProvider", "DmlExecutionProvider") if p in avail]
    return pref + ["CPUExecutionProvider"]


def download(urls, dest):
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    for u in urls:
        try:
            log(f"downloading {dest.name} from {u.split('/')[2]} ...")
            tmp = dest.with_suffix(".part")
            with urllib.request.urlopen(u, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
            tmp.replace(dest)
            return True
        except Exception as e:
            warn(f"  failed: {type(e).__name__}: {str(e)[:120]}")
    return False


class Models:
    """Lazy holder for the InsightFace analyser, INSwapper and optional GFPGAN."""

    def __init__(self, models_dir, enhance):
        self.dir = Path(models_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.want_enhance = enhance
        self._app = self._swapper = self._gfpgan = None

    @property
    def app(self):
        if self._app is None:
            from insightface.app import FaceAnalysis
            local = self.dir / "buffalo_l"
            name = str(local) if local.is_dir() else "buffalo_l"
            try:
                self._app = FaceAnalysis(name=name, root=str(self.dir), providers=providers(),
                                         allowed_modules=["detection", "recognition", "landmark_3d_68"])
            except Exception as e:
                sys.exit(f"Could not load/download InsightFace 'buffalo_l' ({type(e).__name__}: {e}).\n"
                         f"Download buffalo_l.zip from the InsightFace model zoo and unzip it to {local}/")
            self._app.prepare(ctx_id=0, det_size=DET_SIZE, det_thresh=MIN_DET_SCORE)
        return self._app

    @property
    def swapper(self):
        if self._swapper is None:
            import insightface
            p = next((self.dir / n for n in ("inswapper_128.onnx", "inswapper_128_fp16.onnx") if (self.dir / n).exists()), None)
            if p is None:
                p = self.dir / "inswapper_128.onnx"
                if not download(INSWAPPER_URLS, p):
                    sys.exit(f"inswapper_128.onnx not found. Place it at {p}")
            self._swapper = insightface.model_zoo.get_model(str(p), providers=providers())
        return self._swapper

    @property
    def gfpgan(self):
        if self._gfpgan is None and self.want_enhance:
            import onnxruntime as ort
            p = self.dir / "gfpgan_1.4.onnx"
            if not p.exists() and not download(GFPGAN_URLS, p):
                warn("gfpgan_1.4.onnx unavailable - continuing without face restoration")
                self.want_enhance = False
                return None
            self._gfpgan = ort.InferenceSession(str(p), providers=providers())
        return self._gfpgan


# ----------------------------------------------------------------------------- video io
@dataclass
class Meta:
    width: int
    height: int
    fps: float
    fps_str: str
    frames: int
    duration: float
    vcodec: str
    has_audio: bool
    acodec: str


def probe(path) -> Meta:
    j = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                        "stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_read_frames:format=duration",
                        "-of", "json", str(path)]))
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    n, d = map(int, v["r_frame_rate"].split("/"))
    return Meta(v["width"], v["height"], n / d, v["r_frame_rate"], int(v["nb_read_frames"]), float(j["format"]["duration"]),
                v["codec_name"], a is not None, a["codec_name"] if a else "none")


class FrameReader:
    """Frame-accurate reader for [start, end) using ffmpeg's accurate seek."""

    def __init__(self, path, meta: Meta, start, end):
        self.meta, self.n = meta, end - start
        self.size = meta.width * meta.height * 3
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-ss", f"{start / meta.fps:.6f}", "-i", str(path),
                                   "-frames:v", str(self.n), "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                                  stdout=subprocess.PIPE, bufsize=self.size * 2)

    def __iter__(self):
        for _ in range(self.n):
            b = self.p.stdout.read(self.size)
            if len(b) < self.size:
                break
            yield np.frombuffer(b, np.uint8).reshape(self.meta.height, self.meta.width, 3)
        self.p.stdout.close()
        self.p.wait()


class FrameWriter:
    """Lossless H.264 segment writer (final encode happens once at assembly)."""

    def __init__(self, path, meta: Meta):
        self.p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
                                   "-s", f"{meta.width}x{meta.height}", "-r", meta.fps_str, "-i", "-",
                                   "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", "-pix_fmt", "yuv444p",
                                   "-r", meta.fps_str, str(path)], stdin=subprocess.PIPE)

    def write(self, frame):
        self.p.stdin.write(np.ascontiguousarray(frame).tobytes())

    def close(self):
        self.p.stdin.close()
        if self.p.wait() != 0:
            raise RuntimeError("ffmpeg writer failed")


def read_frame(path, meta, idx):
    return next(iter(FrameReader(path, meta, idx, idx + 1)))


# ----------------------------------------------------------------------------- scenes
def detect_scenes(video, meta: Meta):
    from scenedetect import ContentDetector, SceneManager, open_video
    v = open_video(str(video))
    sm = SceneManager()
    sm.add_detector(ContentDetector(threshold=27.0, min_scene_len=12))
    sm.detect_scenes(v)
    cuts = [s[0].get_frames() for s in sm.get_scene_list()][1:]
    bounds = [0] + [c for c in cuts if 0 < c < meta.frames] + [meta.frames]
    scenes = []
    for i, (a, b) in enumerate(zip(bounds, bounds[1:])):
        scenes.append({"scene": i, "start_frame": a, "end_frame": b, "start_time": round(a / meta.fps, 3),
                       "end_time": round(b / meta.fps, 3), "target_present": None, "target_track_id": None,
                       "status": "detected"})
    log(f"{len(scenes)} scenes detected (PySceneDetect ContentDetector)")
    return scenes


# ----------------------------------------------------------------------------- analysis
def letterbox_rows(frame):
    rows = frame.mean(axis=(1, 2))
    act = np.where(rows > 6)[0]
    return (int(act[0]), int(act[-1]) + 1) if len(act) else (0, frame.shape[0])


def shirt_score(frame, bbox, active):
    """Fraction of 'light, pinkish' pixels in the torso region under a face (secondary cue only)."""
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    cx = (x1 + x2) / 2
    tx1, tx2 = int(max(0, cx - 0.8 * w)), int(min(frame.shape[1], cx + 0.8 * w))
    ty1, ty2 = int(max(active[0], y2 + 0.2 * h)), int(min(active[1], y2 + 1.5 * h))
    if tx2 - tx1 < 8 or ty2 - ty1 < 8:
        return None  # torso out of frame (tight close-up)
    lab = cv2.cvtColor(frame[ty1:ty2, tx1:tx2], cv2.COLOR_BGR2LAB).astype(np.int16)
    L, a, b = lab[..., 0], lab[..., 1], lab[..., 2]
    return float(((L > 90) & ((a - b) >= 4)).mean())


def analyze_scene(models, video, meta, sc):
    """Detect + embed every face on every frame of the scene; cache to work/cache."""
    cp = D_CACHE / f"s{sc['scene']:03d}_faces.pkl"
    if cp.exists():
        return pickle.loads(cp.read_bytes())
    dets = []
    for fi, frame in enumerate(FrameReader(video, meta, sc["start_frame"], sc["end_frame"])):
        active = letterbox_rows(frame)
        faces = []
        for f in models.app.get(frame):
            x1, y1, x2, y2 = f.bbox
            if min(x2 - x1, y2 - y1) < MIN_FACE_PX or f.det_score < MIN_DET_SCORE:
                continue
            pose = getattr(f, "pose", None)
            faces.append({"bbox": f.bbox.astype(np.float32), "kps": f.kps.astype(np.float32), "score": float(f.det_score),
                          "emb": f.normed_embedding.astype(np.float32),
                          "yaw": float(pose[1]) if pose is not None else kps_yaw(f.kps),
                          "shirt": shirt_score(frame, f.bbox, active)})
        dets.append(faces)
    cp.write_bytes(pickle.dumps(dets))
    return dets


def kps_yaw(kps):
    """Rough yaw proxy (degrees) from 5 landmarks when the 3D pose model is unavailable."""
    le, re, nose = kps[0], kps[1], kps[2]
    mid = (le + re) / 2
    d = np.linalg.norm(re - le) + 1e-6
    return float(np.degrees(np.arctan2(nose[0] - mid[0], d)) * 2)


def iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def track_scene(dets):
    """Greedy-Hungarian tracker on IoU + embedding similarity. Adds 'track' to each detection."""
    from scipy.optimize import linear_sum_assignment
    tracks = []  # {id, last_frame, bbox, emb}
    for fi, faces in enumerate(dets):
        live = [t for t in tracks if fi - t["last"] <= MAX_GAP]
        if live and faces:
            C = np.ones((len(live), len(faces)))
            for i, t in enumerate(live):
                for j, f in enumerate(faces):
                    sim = float(np.dot(t["emb"], f["emb"]))
                    ov = iou(t["bbox"], f["bbox"])
                    diag = np.hypot(*(t["bbox"][2:] - t["bbox"][:2]))
                    dist = np.linalg.norm((t["bbox"][:2] + t["bbox"][2:]) / 2 - (f["bbox"][:2] + f["bbox"][2:]) / 2)
                    if ov > 0.15 or (sim > 0.45 and dist < 1.0 * diag):
                        C[i, j] = 1 - (0.5 * ov + 0.5 * max(sim, 0))
            rows, cols = linear_sum_assignment(C)
            used = set()
            for i, j in zip(rows, cols):
                if C[i, j] < 1:
                    t, f = live[i], faces[j]
                    f["track"] = t["id"]
                    t.update(last=fi, bbox=f["bbox"], emb=_norm(0.8 * t["emb"] + 0.2 * f["emb"]))
                    used.add(j)
        for j, f in enumerate(faces):
            if "track" not in f:
                f["track"] = len(tracks)
                tracks.append({"id": f["track"], "last": fi, "bbox": f["bbox"], "emb": f["emb"]})
    summary = {}
    for fi, faces in enumerate(dets):
        for f in faces:
            s = summary.setdefault(f["track"], {"frames": [], "embs": [], "scores": [], "shirt": [], "yaw": []})
            s["frames"].append(fi); s["embs"].append(f["emb"] * f["score"]); s["scores"].append(f["score"])
            s["yaw"].append(f["yaw"])
            if f["shirt"] is not None:
                s["shirt"].append(f["shirt"])
    out = {}
    for tid, s in summary.items():
        out[tid] = {"len": len(s["frames"]), "first": s["frames"][0], "last": s["frames"][-1],
                    "emb": _norm(np.sum(s["embs"], axis=0)), "score": float(np.mean(s["scores"])),
                    "shirt": float(np.median(s["shirt"])) if s["shirt"] else None,
                    "yaw_range": float(np.ptp(s["yaw"])) if s["yaw"] else 0.0}
    return out


def _norm(v):
    return v / (np.linalg.norm(v) + 1e-8)


def cluster_identities(all_tracks):
    """Cluster long tracks across the whole movie by ArcFace identity; returns centroids + target cluster."""
    items = [(sid, tid, t) for sid, tr in all_tracks.items() for tid, t in tr.items() if t["len"] >= MIN_TRACK_LEN]
    items.sort(key=lambda x: -x[2]["len"])
    clusters = []  # {"emb_sum", "len", "shirt": [], "members": []}
    for sid, tid, t in items:
        best, bs = None, -1
        for c in clusters:
            s = float(np.dot(_norm(c["emb_sum"]), t["emb"]))
            if s > bs:
                best, bs = c, s
        if best is not None and bs >= SAME_ID_SIM:
            best["emb_sum"] = best["emb_sum"] + t["emb"] * t["len"]; best["len"] += t["len"]
            best["members"].append((sid, tid))
            if t["shirt"] is not None:
                best["shirt"].append(t["shirt"])
        else:
            clusters.append({"emb_sum": t["emb"] * t["len"], "len": t["len"], "members": [(sid, tid)],
                             "shirt": [t["shirt"]] if t["shirt"] is not None else []})
    for c in clusters:
        c["centroid"] = _norm(c["emb_sum"])
        c["shirt_med"] = float(np.median(c["shirt"])) if c["shirt"] else 0.0
        c["scenes"] = len({m[0] for m in c["members"]})
        # main character: most screen time across most shots, pink shirt as a secondary cue
        c["rank"] = c["len"] * (1 + 0.5 * c["scenes"] / max(1, len(all_tracks))) * (1 + c["shirt_med"])
    clusters.sort(key=lambda c: -c["rank"])
    return clusters


def choose_target(sc, tracks, clusters, override=None):
    """Decide which track(s) in this scene are the target. Returns (track_ids, status, reason)."""
    if override is not None:
        ids = override if isinstance(override, list) else [override]
        return [int(i) for i in ids], "ok", "manual override"
    if not clusters:
        return [], "no_target", "no identities found"
    tgt = clusters[0]["centroid"]
    others = [c["centroid"] for c in clusters[1:]]
    cand = []
    for tid, t in tracks.items():
        if t["len"] < MIN_TRACK_LEN:
            continue
        st = float(np.dot(t["emb"], tgt))
        so = max([float(np.dot(t["emb"], o)) for o in others] or [-1.0])
        cand.append({"tid": tid, "s_t": st, "s_o": so, "shirt": t["shirt"], "first": t["first"], "last": t["last"]})
        t["s_target"], t["s_other"] = st, so
    sure = [c for c in cand if c["s_t"] >= TARGET_MIN_SIM and c["s_t"] - c["s_o"] >= TARGET_MARGIN]
    border = [c for c in cand if c not in sure and c["s_t"] >= TARGET_MIN_SIM - 0.10 and c["s_t"] > c["s_o"]]
    if border and not sure:
        # identity borderline (profiles, blur): accept only if the pink-shirt cue clearly singles it out
        shirts = sorted(((c["shirt"] or 0.0), c["tid"]) for c in cand)
        top = shirts[-1]
        second = shirts[-2][0] if len(shirts) > 1 else 0.0
        b = next((c for c in border if c["tid"] == top[1]), None)
        if b and top[0] - second >= SHIRT_TIEBREAK:
            return [b["tid"]], "ok", f"borderline identity (sim {b['s_t']:.2f}) resolved by pink-shirt cue"
        return [], "manual_review", "target identity borderline and pink-shirt cue not decisive"
    if not sure:
        return [], "no_target", "no face matches the target identity"
    sure.sort(key=lambda c: -c["s_t"])
    chosen = []
    for c in sure:  # two target tracks may not be on screen at the same time
        if any(not (c["last"] < k["first"] or c["first"] > k["last"]) for k in chosen):
            if c["s_t"] > chosen[0]["s_t"] - TARGET_MARGIN:
                return [], "manual_review", "two simultaneous faces both match the target"
            continue
        chosen.append(c)
    return [c["tid"] for c in chosen], "ok", "identity sim " + ", ".join("%.2f" % c["s_t"] for c in chosen)


# ----------------------------------------------------------------------------- source identity
def source_identity(models, face_path):
    img = cv2.imread(str(face_path))
    if img is None:
        sys.exit(f"cannot read {face_path}")
    faces = [f for f in models.app.get(img) if f.det_score > 0.6 and min(f.bbox[2] - f.bbox[0], f.bbox[3] - f.bbox[1]) >= 60]
    if not faces:
        sys.exit(f"no usable face found in {face_path}")
    embs = np.stack([f.normed_embedding for f in faces])
    if len(faces) > 1:  # e.g. a character sheet: all views must be the same person
        c = _norm(embs.mean(0))
        keep = [e for e in embs if float(np.dot(e, c)) > 0.45]
        embs = np.stack(keep) if keep else embs[:1]
    emb = _norm(embs.mean(0))
    log(f"source identity: averaged {len(embs)} face view(s) from {Path(face_path).name}")

    class Src:
        normed_embedding = emb
    return Src()


# ----------------------------------------------------------------------------- per-track signals
def gaussian_smooth(arr, sigma, valid):
    """Smooth along axis 0 using only valid samples (normalised convolution)."""
    if sigma <= 0:
        return arr
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    flat = arr.reshape(len(arr), -1)
    w = valid.astype(np.float64)
    num = np.stack([np.convolve(flat[:, i] * w, k, "same") for i in range(flat.shape[1])], 1)
    den = np.convolve(w, k, "same")[:, None]
    out = np.where(den > 1e-6, num / np.maximum(den, 1e-6), flat)
    return out.reshape(arr.shape)


def build_track_plan(dets, target_ids, n):
    """Per-frame swap plan for the target: smoothed landmarks, confidence alpha, protected boxes."""
    kps = np.zeros((n, 5, 2)); valid = np.zeros(n, bool); score = np.zeros(n); yaw = np.zeros(n)
    protect = [[] for _ in range(n)]
    for fi, faces in enumerate(dets):
        for f in faces:
            if f["track"] in target_ids and not valid[fi]:
                kps[fi], valid[fi], score[fi], yaw[fi] = f["kps"], True, f["score"], f["yaw"]
            else:
                protect[fi].append(f["bbox"].tolist())
    # reject landmark outliers (hand over face, detector glitch)
    if valid.sum() >= 3:
        sm = gaussian_smooth(kps, 2.0, valid)
        size = np.linalg.norm(kps[:, 1] - kps[:, 0], axis=1) * 2.5 + 1e-6
        dev = np.linalg.norm(kps - sm, axis=2).max(1) / size
        bad = valid & (dev > OUTLIER_KPS)
        valid &= ~bad
    # interpolate short gaps
    idx = np.where(valid)[0]
    filled = valid.copy()
    for a, b in zip(idx, idx[1:]):
        if 1 < b - a <= INTERP_GAP + 1:
            for t in range(a + 1, b):
                w = (t - a) / (b - a)
                kps[t] = (1 - w) * kps[a] + w * kps[b]
                yaw[t] = (1 - w) * yaw[a] + w * yaw[b]
                filled[t] = True
    kps_s = gaussian_smooth(kps, KPS_SIGMA, filled)
    alpha = filled.astype(np.float64)
    ay = np.clip((YAW_FADE[1] - np.abs(yaw)) / (YAW_FADE[1] - YAW_FADE[0]), 0, 1)
    alpha *= ay
    # ramp in/out where the swap starts or stops mid-shot (not at the shot edges)
    ramp = alpha.copy()
    for fi in range(n):
        if alpha[fi] > 0:
            lo, hi = max(0, fi - FADE_FRAMES), min(n, fi + FADE_FRAMES + 1)
            nb = alpha[lo:hi]
            if (nb == 0).any():
                d = min(abs(fi - (lo + j)) for j in np.where(nb == 0)[0])
                ramp[fi] = alpha[fi] * d / (FADE_FRAMES + 1)
    return {"kps": kps_s.astype(np.float32), "alpha": ramp, "protect": protect, "detected": valid, "filled": filled}


# ----------------------------------------------------------------------------- swap + composite
_MASK128 = None


def mask128():
    """Feathered face mask in INSwapper's aligned 128px space (brows->chin, cheek to cheek; ears/hair kept)."""
    global _MASK128
    if _MASK128 is None:
        m = np.zeros((128, 128), np.float32)
        cv2.ellipse(m, (64, 74), (41, 52), 0, 0, 360, 1.0, -1)
        m[:12] = 0
        bd = np.minimum.reduce([np.arange(128)[None, :].repeat(128, 0), np.arange(128)[::-1][None, :].repeat(128, 0),
                                np.arange(128)[:, None].repeat(128, 1), np.arange(128)[::-1][:, None].repeat(128, 1)])
        m *= np.clip(bd / 6.0, 0, 1)
        _MASK128 = cv2.GaussianBlur(m, (0, 0), 4.0)
    return _MASK128


def align(img, kps, size=128):
    from insightface.utils import face_align
    M = face_align.estimate_norm(kps, size)
    return cv2.warpAffine(img, M, (size, size), borderValue=0.0), M


def swap_crop(models, frame, kps, src):
    class F:
        pass
    f = F(); f.kps = kps
    fake, M = models.swapper.get(frame, f, src, paste_back=False)
    aimg, _ = align(frame, kps, 128)
    return fake, aimg, M


def lab_stats(img, m):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    sel = lab[m > 0.6]
    return np.concatenate([sel.mean(0), sel.std(0) + 1e-3]) if len(sel) > 20 else None


def color_match(fake, st_fake, st_orig):
    lab = cv2.cvtColor(fake, cv2.COLOR_BGR2LAB).astype(np.float32)
    mf, sf, mo, so = st_fake[:3], st_fake[3:], st_orig[:3], st_orig[3:]
    ratio = np.clip(so / sf, 0.7, 1.4)
    lab = (lab - mf) * ratio + mo
    return cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)


def enhance(models, img, kps, blend):
    sess = models.gfpgan
    if sess is None or blend <= 0:
        return img
    from skimage.transform import SimilarityTransform
    t = SimilarityTransform(); t.estimate(kps, FFHQ_512)
    M = t.params[:2]
    crop = cv2.warpAffine(img, M, (512, 512), borderMode=cv2.BORDER_REFLECT)
    x = (crop[:, :, ::-1].astype(np.float32) / 255 - 0.5) / 0.5
    y = sess.run(None, {sess.get_inputs()[0].name: x.transpose(2, 0, 1)[None]})[0][0]
    out = np.clip((y.transpose(1, 2, 0) * 0.5 + 0.5) * 255, 0, 255)[:, :, ::-1].astype(np.uint8)
    out = cv2.addWeighted(out, blend, crop, 1 - blend, 0)
    m = np.zeros((512, 512), np.float32)
    cv2.ellipse(m, (256, 290), (170, 215), 0, 0, 360, 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), 20)
    IM = cv2.invertAffineTransform(M)
    h, w = img.shape[:2]
    back = cv2.warpAffine(out, IM, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    mb = cv2.warpAffine(m, IM, (w, h))[..., None]
    return (img * (1 - mb) + back * mb).astype(np.uint8)


def protect_mask(shape, boxes):
    m = np.zeros(shape[:2], np.float32)
    for x1, y1, x2, y2 in boxes:
        w, h = x2 - x1, y2 - y1
        cv2.ellipse(m, (int((x1 + x2) / 2), int((y1 + y2) / 2)), (int(w * 0.65), int(h * 0.7)), 0, 0, 360, 1.0, -1)
    return m


def composite(frame, fake, M, alpha, boxes, grain):
    h, w = frame.shape[:2]
    IM = cv2.invertAffineTransform(M)
    corners = cv2.transform(np.array([[[0, 0], [127, 0], [0, 127], [127, 127]]], np.float32), IM)[0]
    x1, y1 = np.floor(corners.min(0)).astype(int) - 2
    x2, y2 = np.ceil(corners.max(0)).astype(int) + 2
    x1, y1, x2, y2 = max(0, x1), max(0, y1), min(w, x2), min(h, y2)
    if x2 - x1 < 4 or y2 - y1 < 4:
        return frame, None
    IMr = IM.copy(); IMr[:, 2] -= (x1, y1)
    roi = frame[y1:y2, x1:x2].astype(np.float32)
    up = cv2.warpAffine(fake, IMr, (x2 - x1, y2 - y1), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE).astype(np.float32)
    m = cv2.warpAffine(mask128(), IMr, (x2 - x1, y2 - y1), flags=cv2.INTER_LINEAR) * alpha
    if boxes:
        pm = protect_mask(frame.shape, boxes)[y1:y2, x1:x2]
        pm = cv2.GaussianBlur(pm, (0, 0), 5)
        m *= (1 - np.clip(pm * 1.5, 0, 1))
    if grain > 0:  # put the scene's own film grain back so the new face is not smoother than the plate
        hf = roi - cv2.GaussianBlur(roi, (0, 0), 1.2)
        up = up + grain * hf
    m3 = m[..., None]
    out = frame.copy()
    out[y1:y2, x1:x2] = np.clip(roi * (1 - m3) + up * m3, 0, 255).astype(np.uint8)
    return out, (x1, y1, x2, y2)


def render_scene(models, video, meta, sc, dets, target_ids, src, args):
    n = sc["end_frame"] - sc["start_frame"]
    seg = D_SEG / f"s{sc['scene']:03d}.mp4"
    plan = build_track_plan(dets, set(target_ids), n)
    # pass 1: swap every target frame (small 128px crops kept in memory) + colour statistics
    fakes, st_f, st_o = [None] * n, np.zeros((n, 6)), np.zeros((n, 6))
    has = np.zeros(n, bool)
    m = mask128()
    t0 = time.time()
    for fi, frame in enumerate(FrameReader(video, meta, sc["start_frame"], sc["end_frame"])):
        if plan["alpha"][fi] <= 0:
            continue
        fake, aimg, M = swap_crop(models, frame, plan["kps"][fi], src)
        a, b = lab_stats(fake, m), lab_stats(aimg, m)
        if a is None or b is None:
            continue
        fakes[fi] = (fake, M); st_f[fi], st_o[fi] = a, b; has[fi] = True
    log(f"  scene {sc['scene']}: swapped {has.sum()}/{n} frames in {time.time() - t0:.0f}s")
    st_f = gaussian_smooth(st_f, COLOR_SIGMA, has); st_o = gaussian_smooth(st_o, COLOR_SIGMA, has)
    # pass 2: colour-match, composite, enhance, write; QC frames + non-target change check
    qc_idx = {int(n * p) for p in (0.1, 0.5, 0.9)}
    qc_pairs, nontarget_diff = {}, 0.0
    wr = FrameWriter(seg, meta)
    for fi, frame in enumerate(FrameReader(video, meta, sc["start_frame"], sc["end_frame"])):
        out = frame
        if has[fi]:
            fake, M = fakes[fi]
            fake = color_match(fake, st_f[fi], st_o[fi])
            out, box = composite(frame, fake, M, float(plan["alpha"][fi]), plan["protect"][fi], GRAIN)
            if box is not None and models.want_enhance and args.enhance_blend > 0:
                out = enhance(models, out, plan["kps"][fi], args.enhance_blend * float(plan["alpha"][fi]))
                # enhancer must never touch other faces
                for x1, y1, x2, y2 in plan["protect"][fi]:
                    ys, xs = slice(max(0, int(y1)), int(y2)), slice(max(0, int(x1)), int(x2))
                    out[ys, xs] = np.where(protect_mask(frame.shape, [[x1, y1, x2, y2]])[ys, xs, None] > 0.5, frame[ys, xs], out[ys, xs])
            for x1, y1, x2, y2 in plan["protect"][fi]:
                ys, xs = slice(max(0, int(y1)), int(y2)), slice(max(0, int(x1)), int(x2))
                if out[ys, xs].size:
                    nontarget_diff = max(nontarget_diff, float(np.abs(out[ys, xs].astype(np.int16) - frame[ys, xs]).mean()))
        if fi in qc_idx:
            qc_pairs[fi] = (frame.copy(), out.copy())
        wr.write(out)
    wr.close()
    got = probe(seg).frames
    assert got == n, f"scene {sc['scene']}: segment has {got} frames, expected {n}"
    return plan, qc_pairs, nontarget_diff


def passthrough_scene(video, meta, sc):
    seg = D_SEG / f"s{sc['scene']:03d}.mp4"
    wr = FrameWriter(seg, meta)
    for frame in FrameReader(video, meta, sc["start_frame"], sc["end_frame"]):
        wr.write(frame)
    wr.close()
    got = probe(seg).frames
    assert got == sc["end_frame"] - sc["start_frame"], f"scene {sc['scene']}: passthrough frame count {got}"


# ----------------------------------------------------------------------------- QC + contact sheets
def draw_faces(img, faces, target_ids):
    out = img.copy()
    for f in faces:
        x1, y1, x2, y2 = f["bbox"].astype(int)
        tgt = f["track"] in target_ids
        c = (0, 220, 0) if tgt else (0, 0, 255)
        cv2.rectangle(out, (x1, y1), (x2, y2), c, 4)
        lab = f"T{f['track']}{' TARGET' if tgt else ''}"
        if "s_target" in f:
            lab += f" sim{f['s_target']:.2f}"
        cv2.putText(out, lab, (x1, max(30, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 1.1, c, 3)
    return out


def qc_scene(models, sc, dets, target_ids, qc_pairs, src, nontarget_diff, plan):
    rows, sims = [], []
    for fi in sorted(qc_pairs):
        orig, sw = qc_pairs[fi]
        left = draw_faces(orig, dets[fi], target_ids)
        rows.append(np.hstack([cv2.resize(left, (960, 540)), cv2.resize(sw, (960, 540))]))
        for f in models.app.get(sw):  # identity of the swapped target face vs the source identity
            tf = [d for d in dets[fi] if d["track"] in target_ids]
            if tf and iou(f.bbox, tf[0]["bbox"]) > 0.3:
                sims.append(float(np.dot(f.normed_embedding, src.normed_embedding)))
    if rows:
        sheet = np.vstack(rows)
        cv2.putText(sheet, f"scene {sc['scene']}  ORIGINAL (green=target, red=protected) | SWAPPED", (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        cv2.imwrite(str(D_QC / f"s{sc['scene']:03d}_qc.jpg"), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    # temporal continuity: frame-to-frame change of the (smoothed) face width
    k = plan["kps"][plan["filled"]]
    width = np.linalg.norm(k[:, 1] - k[:, 0], axis=1) if len(k) > 1 else np.array([1.0])
    jitter = float(np.abs(np.diff(width)).max() / width.mean()) if len(width) > 1 else 0.0
    rep = {"scene": sc["scene"], "qc_frames": sorted(qc_pairs), "source_identity_sim": sims,
           "nontarget_max_mean_abs_diff": nontarget_diff, "face_width_max_step": jitter,
           "frames_swapped": int((plan["alpha"] > 0).sum()), "frames_total": len(plan["alpha"]),
           "passed": nontarget_diff <= NONTARGET_MAX_DIFF}
    save_json(D_QC / f"s{sc['scene']:03d}_qc.json", rep)
    return rep


def contact_sheet(video, meta, sc, dets, target_ids, dest):
    n = len(dets)
    idx = sorted({int(n * p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)})
    tiles = [cv2.resize(draw_faces(read_frame(video, meta, sc["start_frame"] + i), dets[i], target_ids), (640, 360)) for i in idx]
    while len(tiles) < 6:
        tiles.append(np.zeros_like(tiles[0]))
    sheet = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:6])])
    cv2.putText(sheet, f"scene {sc['scene']} {sc['start_time']:.2f}-{sc['end_time']:.2f}s  {sc.get('reason', '')}"[:110],
                (10, 710), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imwrite(str(dest), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])


# ----------------------------------------------------------------------------- assembly
def mux(video_in, source, meta, out, t0=None, t1=None):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video_in)]
    if meta.has_audio:
        if t0 is None:
            cmd += ["-i", str(source), "-map", "0:v:0", "-map", "1:a", "-c:a", "copy"]          # untouched soundtrack
        else:  # preview: sample-accurate cut of the original audio for this time range
            cmd += ["-ss", f"{t0:.6f}", "-t", f"{t1 - t0:.6f}", "-i", str(source), "-map", "0:v:0", "-map", "1:a",
                    "-c:a", "aac", "-b:a", "320k"]
    else:
        cmd += ["-map", "0:v:0"]
    cmd += ["-c:v", "libx264", "-crf", "14", "-preset", "slow", "-pix_fmt", "yuv420p", "-r", meta.fps_str,
            "-movflags", "+faststart", str(out)]
    run(cmd)


def report(src_meta, out):
    m = probe(out)
    print("\n================ ffprobe verification ================")
    print(f"source duration   : {src_meta.duration:.3f} s     output duration   : {m.duration:.3f} s")
    print(f"source fps        : {src_meta.fps_str}          output fps        : {m.fps_str}")
    print(f"source resolution : {src_meta.width}x{src_meta.height}     output resolution : {m.width}x{m.height}")
    print(f"source frames     : {src_meta.frames}          output frames     : {m.frames}")
    print(f"video codec       : {m.vcodec}")
    print(f"audio codec       : {m.acodec if m.has_audio else 'none (source has no audio stream)' if not src_meta.has_audio else 'MISSING'}")
    print("======================================================\n")
    return m


# ----------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True)
    ap.add_argument("--face", required=True)
    ap.add_argument("--output", default=str(OUTDIR / "local_face_swap_final.mp4"))
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--preview", action="store_true")
    mode.add_argument("--full", action="store_true")
    mode.add_argument("--scene", type=int)
    mode.add_argument("--make-contact-sheets", action="store_true")
    mode.add_argument("--env-check", action="store_true")
    ap.add_argument("--resume", action="store_true", help="resume from work/scenes.json (default behaviour)")
    ap.add_argument("--force", action="store_true", help="redo scenes already completed")
    ap.add_argument("--models", default=str(ROOT / "models"))
    ap.add_argument("--no-enhance", action="store_true")
    ap.add_argument("--enhance-blend", type=float, default=0.25)
    args = ap.parse_args()

    info = env_check()
    log(f"python {info['python']} | {info['ffmpeg']} | onnxruntime {info['onnxruntime']} | accelerator: {info['accelerator']}")
    if args.env_check:
        print(json.dumps(info, indent=2)); return
    if not (args.preview or args.full or args.scene is not None or args.make_contact_sheets):
        ap.error("choose one of --preview / --full / --scene N / --make-contact-sheets")
    for d in (WORK, OUTDIR, D_FRAMES, D_QC, D_AMB, D_CACHE, D_SEG):
        d.mkdir(parents=True, exist_ok=True)
    video = Path(args.video)
    meta = probe(video)
    log(f"source: {meta.width}x{meta.height} @ {meta.fps_str} fps, {meta.frames} frames, {meta.duration:.3f}s, "
        f"video {meta.vcodec}, audio {meta.acodec if meta.has_audio else 'none'}")
    if not meta.has_audio:
        warn("the source video has NO audio stream - outputs will be silent (nothing to remux)")

    state = load_json(SCENES_JSON)
    if not state or state.get("video") != str(video.resolve()) or state.get("frames") != meta.frames:
        state = {"video": str(video.resolve()), "frames": meta.frames, "scenes": detect_scenes(video, meta)}
        save_json(SCENES_JSON, state)
    scenes = state["scenes"]
    models = Models(args.models, enhance=not args.no_enhance)

    # 1) analysis of every scene (detection/embedding/tracking) - needed to lock the target identity
    all_tracks, all_dets = {}, {}
    for sc in scenes:
        if not (D_CACHE / f"s{sc['scene']:03d}_faces.pkl").exists():
            log(f"analysing scene {sc['scene']} [{sc['start_time']:.2f}-{sc['end_time']:.2f}s]")
        dets = analyze_scene(models, video, meta, sc)
        tracks = track_scene(dets)
        all_dets[sc["scene"]], all_tracks[sc["scene"]] = dets, tracks
        sc["tracks_cached"] = True
    clusters = cluster_identities(all_tracks)
    if clusters:
        c = clusters[0]
        log(f"target identity locked: cluster of {len(c['members'])} tracks over {c['scenes']} scenes, "
            f"{c['len']} face-frames, pink-shirt score {c['shirt_med']:.2f}")
    for sc in scenes:
        tids, status, reason = choose_target(sc, all_tracks[sc["scene"]], clusters, sc.get("target_track_override"))
        for faces in all_dets[sc["scene"]]:
            for f in faces:
                t = all_tracks[sc["scene"]].get(f["track"], {})
                if "s_target" in t:
                    f["s_target"] = t["s_target"]
        sc["target_present"] = bool(tids)
        sc["target_track_id"] = tids[0] if len(tids) == 1 else (tids or None)
        sc["reason"] = reason
        if sc["status"] not in ("done",) or args.force:
            sc["status"] = {"ok": "pending", "no_target": "pending_passthrough", "manual_review": "manual_review"}[status]
        if status == "manual_review":
            contact_sheet(video, meta, sc, all_dets[sc["scene"]], set(), D_AMB / f"s{sc['scene']:03d}_ambiguous.jpg")
            warn(f"scene {sc['scene']}: {reason} -> kept original, see work/ambiguous/s{sc['scene']:03d}_ambiguous.jpg; "
                 f"set \"target_track_override\" in work/scenes.json to fix")
    save_json(SCENES_JSON, state)

    if args.make_contact_sheets:
        for sc in scenes:
            ids = sc["target_track_id"] if isinstance(sc["target_track_id"], list) else [sc["target_track_id"]]
            contact_sheet(video, meta, sc, all_dets[sc["scene"]], set(i for i in ids if i is not None),
                          D_FRAMES / f"s{sc['scene']:03d}_tracks.jpg")
        log(f"contact sheets -> {D_FRAMES}"); return

    src = source_identity(models, args.face)

    def process(sc):
        sid = sc["scene"]
        seg = D_SEG / f"s{sid:03d}.mp4"
        if sc.get("status") == "done" and seg.exists() and not args.force:
            return sc
        ids = sc["target_track_id"] if isinstance(sc["target_track_id"], list) else [sc["target_track_id"]]
        if not sc["target_present"]:
            passthrough_scene(video, meta, sc)
            sc["status"] = "done" if sc["status"] != "manual_review" else "manual_review"
            sc["processing"] = "untouched"
        else:
            log(f"scene {sid} [{sc['start_time']:.2f}-{sc['end_time']:.2f}s] swapping track(s) {ids} ({sc['reason']})")
            plan, pairs, ntd = render_scene(models, video, meta, sc, all_dets[sid], set(ids), src, args)
            rep = qc_scene(models, sc, all_dets[sid], set(ids), pairs, src, ntd, plan)
            if not rep["passed"]:
                warn(f"scene {sid}: QC FAILED (non-target pixels changed by {ntd:.2f}) -> original kept")
                passthrough_scene(video, meta, sc)
                sc["status"], sc["processing"] = "failed_qc", "untouched"
            else:
                sc["status"], sc["processing"] = "done", "swapped"
            sims = rep["source_identity_sim"]
            log(f"  QC scene {sid}: identity sim to source {np.mean(sims) if sims else float('nan'):.2f}, "
                f"non-target max diff {ntd:.3f}, face-width max step {rep['face_width_max_step']:.3f} -> "
                f"{'PASS' if rep['passed'] else 'FAIL'}  ({D_QC / f's{sid:03d}_qc.jpg'})")
        save_json(SCENES_JSON, state)
        return sc

    if args.preview:
        cand = []
        for sc in scenes:
            if not sc["target_present"] or sc["status"] == "manual_review":
                continue
            n = sc["end_frame"] - sc["start_frame"]
            if n < PREVIEW_RANGE[0] * meta.fps:
                continue
            tr = all_tracks[sc["scene"]]
            ids = sc["target_track_id"] if isinstance(sc["target_track_id"], list) else [sc["target_track_id"]]
            yaw = np.full(n, np.nan)
            for fi, faces in enumerate(all_dets[sc["scene"]]):
                for f in faces:
                    if f["track"] in ids:
                        yaw[fi] = f["yaw"]
            # best <= 8 s window inside the scene by head-rotation range
            win = min(n, int(PREVIEW_RANGE[1] * meta.fps))
            best = (-1.0, 0)
            for st in range(0, n - win + 1, 6):
                y = yaw[st:st + win]
                y = y[~np.isnan(y)]
                if len(y) > 0.8 * win:
                    best = max(best, (float(np.ptp(y)), st))
            others = any(t["len"] >= MIN_TRACK_LEN and k not in ids for k, t in tr.items())
            # priority: clear head rotation, then a second person in frame, then rotation amount
            cand.append((best[0] >= 20, others, best[0], sc, best[1], win))
        if not cand:
            sys.exit("no scene >= 5 s with a confidently identified target - see work/ambiguous/")
        cand.sort(key=lambda c: (c[0], c[1], c[2]), reverse=True)
        _, others, yrange, sc, wst, win = cand[0]
        t0 = sc["start_time"] + wst / meta.fps
        t1 = t0 + win / meta.fps
        log(f"preview: scene {sc['scene']}, window {t0:.2f}-{t1:.2f}s (target yaw range {yrange:.0f} deg, "
            f"other person visible: {others})")
        process(sc)
        seg = D_SEG / f"s{sc['scene']:03d}.mp4"
        if win < sc["end_frame"] - sc["start_frame"]:
            tmp = D_SEG / "preview_cut.mp4"
            run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(seg), "-vf", f"trim=start_frame={wst}:end_frame={wst + win},setpts=PTS-STARTPTS",
                 "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", "-pix_fmt", "yuv444p", str(tmp)])
            seg = tmp
        out = OUTDIR / "local_face_swap_preview.mp4"
        mux(seg, video, meta, out, t0, t1)
        m = probe(out)
        log(f"PREVIEW -> {out}  ({m.width}x{m.height} @ {m.fps_str}, {m.duration:.2f}s, audio: {m.acodec if m.has_audio else 'none'})")
        log("stopping after preview as requested. Full render: re-run with --full")
        return

    if args.scene is not None:
        sc = next(s for s in scenes if s["scene"] == args.scene)
        process(sc); return

    # --full
    for sc in scenes:
        process(sc)
    lst = WORK / "concat.txt"
    lst.write_text("".join(f"file '{D_SEG / ('s%03d.mp4' % sc['scene'])}'\n" for sc in scenes))
    joined = WORK / "joined.mp4"
    run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    mux(joined, video, meta, out)
    m = report(meta, out)
    assert m.frames == meta.frames, "frame count differs from source"
    assert abs(m.duration - meta.duration) < 0.05, "duration differs from source by >= 0.05 s"
    bad = [s["scene"] for s in scenes if s["status"] in ("manual_review", "failed_qc")]
    if bad:
        warn(f"scenes kept ORIGINAL (manual review / QC fail): {bad} - see work/ambiguous and work/qc")
    log(f"FINAL -> {out}")


if __name__ == "__main__":
    main()
