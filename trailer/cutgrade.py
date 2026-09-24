import numpy as np, cv2, os
c = np.load('cut_suit.npy', mmap_mode='r')
def rim(a, side):
    """edge light on one side of the silhouette"""
    b = cv2.GaussianBlur(a, (0, 0), 7)
    edge = np.clip(a - b, 0, 1) * 4
    gx = cv2.Sobel(cv2.GaussianBlur(a, (0, 0), 5), cv2.CV_32F, 1, 0, ksize=5)
    dirk = np.clip(-gx * side * 3, 0, 1) if side else 1
    return np.clip(edge * (0.4 + dirk), 0, 1.5)
def gradeset(name, mul, gamma, rimcol, side, contrast=1.1, lift=0.0):
    os.makedirs(name, exist_ok=True)
    for i in range(len(c)):
        im = np.array(c[i][:1020]).astype(np.float32)
        rgb, a = im[..., :3] / 255, im[..., 3] / 255
        x = rgb ** gamma
        x = 0.5 + (x - 0.5) * contrast
        x = np.clip(x * np.array(mul) + lift, 0, 1)
        # soft falloff from face (top) to body - pools light on face
        yy = np.linspace(0, 1, x.shape[0])[:, None, None]
        x = x * (1.0 - 0.35 * np.clip((yy - 0.45) / 0.55, 0, 1))
        r = rim(a, side)[..., None] * np.array(rimcol)
        x = np.clip(x + r, 0, 1)
        out = np.dstack([x * 255, a * 255]).astype(np.uint8)
        cv2.imwrite(f'{name}/{i+1:04d}.png', cv2.cvtColor(out, cv2.COLOR_RGBA2BGRA))
gradeset('cut_night', (0.62, 0.66, 0.85), 1.25, (0.6, 0.36, 0.17), 1, 1.15)
gradeset('cut_stage', (1.0, 0.9, 0.82), 1.1, (0.45, 0.65, 1.0), -1, 1.15)
