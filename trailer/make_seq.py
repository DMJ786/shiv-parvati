"""Slow-motion (optical flow) cut-out sequences for the stage/rooftop scenes + the stage LED-wall frames."""
import cv2, numpy as np, os
from PIL import Image, ImageDraw, ImageFont
from slowmo import resample


def seq(src, out, start, n, speed):
    os.makedirs(out, exist_ok=True)
    fr = [cv2.cvtColor(cv2.imread(f'{src}/{i+1:04d}.png', -1), cv2.COLOR_BGRA2RGBA) for i in range(96)]
    for k, im in enumerate(resample(fr, [start + k * speed for k in range(n)])):
        cv2.imwrite(f'{out}/{k+1:04d}.png', cv2.cvtColor(np.clip(im, 0, 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA))


def led():
    os.makedirs('led', exist_ok=True)
    Wd, Hd = 1280, 720
    y, x = np.mgrid[0:Hd, 0:Wd]
    bg = np.zeros((Hd, Wd, 3), np.float32); bg[:] = np.array([6, 14, 40])
    bg += (np.clip(1 - np.sqrt(((x - 420) / 700) ** 2 + ((y - 360) / 500) ** 2), 0, 1) ** 2 * 90)[..., None] * np.array([0.5, 0.7, 1.2])
    grid = (((x % 4) < 3) & ((y % 4) < 3)).astype(np.float32)[..., None] * 0.35 + 0.65
    fb = ImageFont.truetype('fonts/SourceSansPro-Black.ttf', 86); fl = ImageFont.truetype('fonts/SourceSansPro-Light.ttf', 34)
    for k in range(84):
        im = cv2.cvtColor(cv2.imread(f'seq_stage/{k+1:04d}.png', -1), cv2.COLOR_BGRA2RGBA).astype(np.float32)
        face = cv2.resize(im[40:740, 60:700], (int(640 * 1.03), int(700 * 1.03)))
        fh, fw = face.shape[:2]; canvas = bg.copy(); x0, y0 = 120, Hd - fh + 40
        sub = canvas[max(y0, 0):y0 + fh, x0:x0 + fw]; f = face[max(0, -y0):max(0, -y0) + sub.shape[0], :sub.shape[1]]
        a = f[..., 3:] / 255
        canvas[max(y0, 0):y0 + fh, x0:x0 + fw] = sub * (1 - a) + f[..., :3] * a
        pil = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(pil)
        d.text((820, 250), 'FOUNDER', font=fl, fill=(232, 196, 110), anchor='lm')
        d.text((820, 330), 'THE', font=fb, fill=(255, 255, 255), anchor='lm')
        d.text((820, 415), 'VISIONARY', font=fb, fill=(255, 255, 255), anchor='lm')
        d.line([(820, 480), (1180, 480)], fill=(232, 196, 110), width=4)
        d.text((820, 520), 'GLOBAL SUMMIT  ·  KEYNOTE', font=fl, fill=(200, 210, 230), anchor='lm')
        out = np.clip(np.asarray(pil).astype(np.float32) * grid, 0, 255).astype(np.uint8)
        cv2.imwrite(f'led/{k+1:04d}.png', cv2.cvtColor(out, cv2.COLOR_RGB2BGR))


if __name__ == '__main__':
    seq('cut_stage', 'seq_stage', 8, 84, 0.5)
    seq('cut_night', 'seq_night', 6, 96, 0.5)
    led()
