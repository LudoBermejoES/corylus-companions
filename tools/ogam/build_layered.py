# Builds Ogam's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>
import io, json, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image

W = sys.argv[1]
OUT = f"{W}/layered"
DARK, ORANGE, GREY, CREAM, BROWN = "#312911", "#da8f5d", "#969793", "#e1d2b5", "#a27856"
PAL = np.array([[0x31, 0x29, 0x11], [0xda, 0x8f, 0x5d], [0x96, 0x97, 0x93], [0xe1, 0xd2, 0xb5], [0xa2, 0x78, 0x56]])

img = np.array(Image.open(f"{W}/master-flat.png").convert("RGBA"))
idx = ((img[..., None, :3].astype(int) - PAL[None, None]) ** 2).sum(-1).argmin(-1)
alpha = img[..., 3] > 0
yy, xx = np.mgrid[0:1024, 0:1024]


def in_poly(poly):
    # Even-odd point-in-polygon over the whole grid.
    inside = np.zeros((1024, 1024), bool)
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        cond = ((y0 > yy) != (y1 > yy)) & (xx < (x1 - x0) * (yy - y0) / ((y1 - y0) or 1e-9) + x0)
        inside ^= cond
    return inside


# Regions that hold each moving feature; only grey/brown (brows) or orange/brown (lip) pixels move.
BROW_L = [(320, 318), (360, 300), (420, 312), (470, 340), (470, 372), (420, 368), (360, 352), (320, 345)]
BROW_R = [(704, 318), (664, 300), (604, 312), (546, 340), (546, 372), (604, 368), (664, 352), (704, 345)]
LIP = [(455, 615), (565, 615), (565, 650), (455, 650)]

layers = {}
base = idx.copy()
for name, poly, keep in [("brow-l", BROW_L, (2, 4)), ("brow-r", BROW_R, (2, 4)), ("lip", LIP, (1, 4))]:
    m = in_poly(poly) & np.isin(idx, keep) & alpha
    layers[name] = m
    base[m] = 0  # the shadow colour fills where the feature was


def save_png(mask, colors, path):
    a = np.zeros((1024, 1024, 4), np.uint8)
    a[..., :3] = PAL[colors]
    a[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(a).save(path)


import os
os.makedirs(OUT, exist_ok=True)
save_png(alpha, base, f"{W}/_base.png")
for name, m in layers.items():
    save_png(m, idx, f"{W}/_{name}.png")


def trace(png, svg_out):
    vtracer.convert_image_to_svg_py(png, svg_out, colormode="color", hierarchical="stacked", mode="spline",
                                    filter_speckle=4, color_precision=8, layer_difference=8, corner_threshold=60,
                                    length_threshold=4.0, splice_threshold=45, path_precision=1)
    s = open(svg_out).read()
    body = s[s.index("<path"):s.rindex("</svg>")]
    return "".join(p for p in body.split("\n") if 'd=""' not in p)


parts = {"base": trace(f"{W}/_base.png", f"{OUT}/base.svg")}
for name in layers:
    parts[name] = trace(f"{W}/_{name}.png", f"{OUT}/{name}.svg")

# Hand-drawn overlays in the master's palette (1024 px coordinates).
def lid(x0, x1, y):
    # A closed lid: a crescent that sags in the middle, with the lash line along its lower edge.
    m, w = (x0 + x1) / 2, (x1 - x0)
    return (f'<path d="M{x0} {y} C{x0 + w*.3} {y - 8} {x1 - w*.3} {y - 8} {x1} {y} C{x1 - w*.25} {y + 16} {x0 + w*.25} {y + 16} {x0} {y} Z" fill="{ORANGE}"/>'
            f'<path d="M{x0 - 2} {y + 1} C{x0 + w*.25} {y + 17} {x1 - w*.25} {y + 17} {x1 + 2} {y + 1}" stroke="{DARK}" stroke-width="5" fill="none" stroke-linecap="round"/>')
LID_L, LID_R = lid(374, 446, 384), lid(578, 650, 384)
overlays = {
    "eyes-closed": LID_L + LID_R,
    "eyes-glint": f'<ellipse cx="414" cy="386" rx="7" ry="6" fill="{CREAM}"/><ellipse cx="610" cy="386" rx="7" ry="6" fill="{CREAM}"/>',
    "eyes-wide": f'<ellipse cx="408" cy="384" rx="20" ry="13" fill="{CREAM}"/><ellipse cx="616" cy="384" rx="20" ry="13" fill="{CREAM}"/><circle cx="410" cy="385" r="8" fill="{DARK}"/><circle cx="614" cy="385" r="8" fill="{DARK}"/><circle cx="413" cy="382" r="2.5" fill="{CREAM}"/><circle cx="617" cy="382" r="2.5" fill="{CREAM}"/>',
    "mouth-flat": f'<path d="M458 632 C488 624 532 624 562 632 C532 646 488 646 458 632 Z" fill="{ORANGE}"/>',
    "mouth-smile": f'<path d="M452 618 C478 652 542 652 568 618 C546 664 474 664 452 618 Z" fill="{ORANGE}"/>',
    "mouth-open": f'<path d="M468 616 C490 608 530 608 552 616 C540 676 480 676 468 616 Z" fill="#1c170a"/><path d="M466 616 C490 606 530 606 554 616" stroke="{ORANGE}" stroke-width="6" fill="none" stroke-linecap="round"/><path d="M470 650 C490 674 530 674 550 650 C534 664 486 664 470 650 Z" fill="{ORANGE}"/>',
    "mouth-o": f'<ellipse cx="510" cy="636" rx="17" ry="21" fill="#1c170a" stroke="{ORANGE}" stroke-width="9"/>',
}

rig = json.load(open(f"{W}/rig.json"))


def compose(pose, size=256):
    tilt = pose.get("tilt", 0)
    dy = pose.get("dy", 0)
    g = [f'<g transform="translate(0,{dy}) rotate({tilt} 512 900)">', parts["base"]]
    for side, cx, cy, sign in [("l", 395, 335, -1), ("r", 629, 335, 1)]:
        b = pose.get(f"brow_{side}", pose.get("brow", {}))
        ang = sign * b.get("inner_up", 0)
        g.append(f'<g transform="translate(0,{b.get("dy", 0)}) rotate({ang} {cx} {cy})">{parts["brow-" + side]}</g>')
    if pose.get("eyes"):
        g.append(overlays["eyes-" + pose["eyes"]])
    mouth = pose.get("mouth", "neutral")
    g.append(parts["lip"] if mouth == "neutral" else overlays["mouth-" + mouth])
    g.append("</g>")
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="{size}" height="{size}">{"".join(g)}</svg>'
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg)))).convert("RGBA")


emotions = list(rig["emotions"])
cell, small = 256, 96
sheet = Image.new("RGBA", (6 * (cell + 10) + 10, 2 * (cell + small + 40) + 10), (250, 248, 244, 255))
from PIL import ImageDraw
d = ImageDraw.Draw(sheet)
for i, e in enumerate(emotions):
    x = 10 + (i % 6) * (cell + 10)
    y = 10 + (i // 6) * (cell + small + 40)
    sheet.alpha_composite(compose(rig["emotions"][e], cell), (x, y))
    sheet.alpha_composite(compose(rig["emotions"][e], small), (x, y + cell + 4))
    d.text((x + small + 10, y + cell + 40), e, fill=(40, 40, 40, 255))
sheet.save(f"{W}/contact-emotions.png")
json.dump({k: len(v) for k, v in parts.items()}, sys.stdout)
for k, v in overlays.items():
    open(f"{OUT}/{k}.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">{v}</svg>')
