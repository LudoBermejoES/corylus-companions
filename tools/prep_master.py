# Turns a candidate PNG into a flat master: cuts the white background (grown from the border),
# prints a k-means palette of the rest, and with a palette given snaps every pixel to it.
# Usage: python prep_master.py <work dir with master-1024.png> <k> ["#hex,#hex,..."]  -> master-flat.png
import sys
import numpy as np
from PIL import Image, ImageFilter

W, k = sys.argv[1], int(sys.argv[2])
rgb = np.array(Image.open(f"{W}/master-1024.png").convert("RGB")).astype(int)
light = (rgb.min(-1) > 215) & (rgb.max(-1) - rgb.min(-1) < 30)
bg = np.zeros_like(light); bg[[0, -1]] = light[[0, -1]]; bg[:, [0, -1]] = light[:, [0, -1]]
while True:  # grow from the border through light pixels
    g = bg.copy(); g[1:] |= bg[:-1]; g[:-1] |= bg[1:]; g[:, 1:] |= bg[:, :-1]; g[:, :-1] |= bg[:, 1:]; g &= light
    if (g == bg).all(): break
    bg = g
px = rgb[~bg].astype(float)
rng = np.random.default_rng(0)
c = px[rng.choice(len(px), k, replace=False)]
for _ in range(40):
    sample = px[rng.choice(len(px), 60000, replace=False)]
    a = ((sample[:, None] - c[None]) ** 2).sum(-1).argmin(1)
    c = np.array([sample[a == i].mean(0) if (a == i).any() else c[i] for i in range(k)])
a = ((px[:, None] - c[None]) ** 2).sum(-1).argmin(1)
for i in np.argsort(-np.bincount(a, minlength=k)):
    print("#%02x%02x%02x" % tuple(c[i].astype(int)), (a == i).sum())

# Snap to the given palette (argv[3], comma-separated hex) and clean speckle with a 3x3 mode filter.
if len(sys.argv) > 3:
    pal = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in sys.argv[3].split(",")])
    idx = ((rgb[..., None, :] - pal[None, None]) ** 2).sum(-1).argmin(-1)
    idx = np.array(Image.fromarray(idx.astype(np.uint8)).filter(ImageFilter.ModeFilter(3)))
    out = np.zeros((1024, 1024, 4), np.uint8)
    out[..., :3] = pal[idx]; out[..., 3] = np.where(bg, 0, 255)
    Image.fromarray(out).save(f"{W}/master-flat.png")
