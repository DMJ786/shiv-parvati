"""Dress him in a navy suit, white shirt and tie, using the polo's own folds for shading."""
import numpy as np, cv2, sys

C = np.load('cut.npy', mmap_mode='r')      # 96 x 1280 x 720 x 4 RGBA
P = np.load('seg6.npy')                     # 96 x 256 x 256 x 6
H, W = 1280, 720
NAVY = np.array([20, 24, 38], np.float32)
SHIRT = np.array([238, 238, 242], np.float32)
TIE = np.array([112, 24, 40], np.float32)


def up(p):
    return cv2.resize(p.astype(np.float32) / 255, (W, H), interpolation=cv2.INTER_LINEAR)


def anchors(k):
    p = P[k]
    skin, face, clothes = up(p[..., 2]), up(p[..., 3]), up(p[..., 4])
    fm = face > 0.5
    ys, xs = np.nonzero(fm)
    fx0, fx1, fy1 = xs.min(), xs.max(), ys.max()
    neck = (skin > 0.5)
    neck[:fy1 - 60] = False; neck[fy1 + 330:] = False
    neck[:, :fx0 - 40] = False; neck[:, fx1 + 40:] = False
    n, lab, st, _ = cv2.connectedComponentsWithStats(neck.astype(np.uint8))
    if n > 1:
        kk = np.argmax(st[1:, 4]) + 1; neck = lab == kk
    ys, xs = np.nonzero(neck)
    ny = ys.max()
    nx_bottom = xs[ys > ny - 8].mean()
    yc = int(ny - 85)
    row = np.nonzero(neck[yc])[0]
    if len(row) < 10: row = np.nonzero(neck[ys.min() + 40])[0]
    xl, xr = row.min(), row.max()
    return np.array([nx_bottom, ny, xl, xr, yc], np.float32)


A = np.stack([anchors(k) for k in range(len(C))])
# temporal smoothing
Ks = 5
As = np.stack([A[max(0, k - Ks // 2):k + Ks // 2 + 1].mean(0) for k in range(len(A))])


def poly(mask, pts, ss=4):
    cv2.fillPoly(mask, [np.round(np.array(pts) * ss).astype(np.int32)], 1.0, lineType=cv2.LINE_AA, shift=2)


def dress(k):
    im = np.array(C[k]).astype(np.float32)
    rgb, a = im[..., :3], im[..., 3] / 255
    p = P[k]
    skin, clothes, other = up(p[..., 2]), up(p[..., 4]), up(p[..., 5])
    nxb, ny, xl, xr, yc = As[k]
    cx = (xl + xr) / 2 * 0.5 + nxb * 0.5
    hw = (xr - xl) / 2
    depth = 330
    lum0 = rgb.mean(2)
    lum = cv2.medianBlur(np.clip(lum0, 0, 255).astype(np.uint8), 9).astype(np.float32)   # kills logo / collar edges
    lum = cv2.GaussianBlur(lum, (0, 0), 4) * 0.85 + cv2.GaussianBlur(lum0, (0, 0), 2.5) * 0.15
    cl = clothes > 0.5
    ref = np.median(lum[cl]) if cl.any() else 128
    shade = np.clip(lum / ref, 0.35, 1.7) ** 1.15

    # --- regions (all 1-channel float masks)
    V = np.zeros((H, W), np.float32)
    poly(V, [(cx - hw - 8, yc - 36), (cx - hw * 0.3, yc - 6), (cx + hw * 0.3, yc - 6), (cx + hw + 8, yc - 36), (cx + 6, yc + depth)])
    collarL = np.zeros_like(V); collarR = np.zeros_like(V)
    poly(collarL, [(cx - hw - 12, yc - 40), (cx - 4, yc + 2), (cx - 26, yc + 72), (cx - hw + 2, yc + 26)])
    poly(collarR, [(cx + hw + 12, yc - 40), (cx + 4, yc + 2), (cx + 26, yc + 72), (cx + hw - 2, yc + 26)])
    knot = np.zeros_like(V)
    poly(knot, [(cx - 27, yc + 0), (cx + 27, yc + 0), (cx + 17, yc + 50), (cx - 17, yc + 50)])
    blade = np.zeros_like(V)
    poly(blade, [(cx - 17, yc + 46), (cx + 17, yc + 46), (cx + 36, yc + depth + 60), (cx + 4, yc + depth + 95), (cx - 30, yc + depth + 60)])
    lapL = np.zeros_like(V); lapR = np.zeros_like(V)
    poly(lapL, [(cx - hw - 26, yc - 14), (cx - hw - 70, yc + 10), (cx - hw - 62, yc + 105), (cx - hw - 90, yc + 118),
                (cx - 18, yc + depth + 40), (cx + 6, yc + depth), (cx - hw - 26 + 8, yc + 40)])
    poly(lapR, [(cx + hw + 26, yc - 14), (cx + hw + 70, yc + 10), (cx + hw + 62, yc + 105), (cx + hw + 90, yc + 118),
                (cx + 30, yc + depth + 40), (cx + 6, yc + depth), (cx + hw + 26 - 8, yc + 40)])
    for m in (V, collarL, collarR, knot, blade, lapL, lapR):
        m[:] = cv2.GaussianBlur(m, (0, 0), 0.8)
    lap = np.maximum(lapL, lapR) * (1 - V)

    # arms become sleeves, except the hand around the glass
    near_glass = cv2.dilate((other > 0.4).astype(np.uint8), np.ones((1, 1), np.uint8))
    dist = cv2.distanceTransform(1 - near_glass, cv2.DIST_L2, 5)
    arm = skin * (np.arange(H)[:, None] > ny + 60) * np.clip((dist - 70) / 40, 0, 1)
    jacket_m = np.clip(clothes + arm, 0, 1)

    out = rgb.copy()
    noise = cv2.GaussianBlur(np.random.default_rng(k).normal(0, 1, (H, W)).astype(np.float32), (0, 0), 0.7)
    jac = NAVY * shade[..., None] * (1 + 0.04 * noise[..., None])
    # lapel: slightly darker with a satin sheen and a stitched edge highlight
    # lapel rolls: soft sheen on the lapel, a shadow where it lies on the jacket
    outer = np.clip(cv2.GaussianBlur(lap, (0, 0), 5) - lap, 0, 1) * 1.6
    jac = jac * (1 + 0.12 * lap[..., None]) * (1 - 0.45 * outer[..., None])
    body = jacket_m * (1 - V)
    out = out * (1 - body[..., None]) + jac * body[..., None]
    # shirt inside the V (only within his silhouette)
    vin = V * (a > 0.3)
    sh_shade = np.clip(0.82 + 0.25 * (shade - 1), 0.6, 1.1)
    shirt = SHIRT * sh_shade[..., None]
    # soft shadow under the collar and along the lapels
    occ = np.clip(cv2.GaussianBlur(np.maximum(collarL, collarR) + lap, (0, 0), 7), 0, 1)
    shirt = shirt * (1 - 0.25 * occ[..., None])
    out = out * (1 - vin[..., None]) + shirt * vin[..., None]
    # tie (subtle diagonal stripes) + knot
    yy, xx = np.mgrid[0:H, 0:W]
    stripe = (((xx + yy) // 9) % 4 == 0).astype(np.float32)
    tie = TIE * (0.85 + 0.25 * stripe[..., None]) * sh_shade[..., None]
    tm = np.clip(blade * V + knot, 0, 1)
    tie = tie * (1 - 0.35 * np.clip(cv2.GaussianBlur(knot, (0, 0), 3) - knot, 0, 1)[..., None])
    out = out * (1 - tm[..., None]) + tie * tm[..., None]
    # collar wings (white, on top of neck skin)
    col = np.maximum(collarL, collarR) * (a > 0.3)
    colc = SHIRT * (0.95 - 0.12 * np.clip(cv2.GaussianBlur(knot, (0, 0), 6), 0, 1))[..., None]
    out = out * (1 - col[..., None]) + colc * col[..., None]
    # thin shadow line around the collar wings so they read as fabric edges
    cedge = np.clip(cv2.GaussianBlur(col, (0, 0), 2.0) - col, 0, 1) * 2.2
    out = out * (1 - 0.5 * cedge[..., None])
    # neck shadow just above the collar
    ns = np.clip(cv2.GaussianBlur(col, (0, 0), 6) - col, 0, 1) * (np.arange(H)[:, None] < yc + 10)
    out = out * (1 - 0.35 * ns[..., None])
    # jacket button
    by = int(yc + depth + 70); bx = int(cx + 10)
    cv2.circle(out, (bx, by), 7, (14, 16, 26), -1, cv2.LINE_AA)
    return np.dstack([np.clip(out, 0, 255), im[..., 3:]]).astype(np.uint8)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ks = [int(x) for x in sys.argv[1].split(',')]
        row = []
        for k in ks:
            d = dress(k)[:1020]
            al = d[..., 3:] / 255
            row.append((d[..., :3] * al + np.array([20, 16, 30]) * (1 - al)).astype(np.uint8))
        cv2.imwrite('pv.jpg', cv2.cvtColor(cv2.resize(np.hstack(row), None, fx=0.45, fy=0.45), cv2.COLOR_RGB2BGR))
    else:
        out = np.stack([dress(k) for k in range(len(C))])
        np.save('cut_suit.npy', out)
        print('saved', out.shape)
