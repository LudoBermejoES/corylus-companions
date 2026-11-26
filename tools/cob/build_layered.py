# Builds Cob's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>   (the dir holds master-flat.png and rig.json)
# Unlike Ogam, the eyes are cut out of the base too (with the frown lines between them): the
# master's eyes are slanted and stern, so every pose names one of the rounder eye overlays.
import io, json, os, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image, ImageDraw

W = sys.argv[1]
OUT = f"{W}/layered"
HEX = ["#21190b", "#df6945", "#e09970", "#a55545", "#5e6c47", "#859c5c", "#f8f3d8"]
DARK, ORANGE, LIGHT, SHADOW, GREEN_D, GREEN, CREAM = HEX
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in HEX])
D, O, L, S, C = 0, 1, 2, 3, 6

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


def mirror(poly):
    return [(1022 - x, y) for x, y in reversed(poly)]


# Regions (left side; the right side mirrors about x = 511).
EYE_L = [(334, 360), (380, 372), (437, 400), (444, 420), (442, 476), (430, 488), (352, 488), (340, 462), (338, 400), (332, 378)]
BROW_L = [(318, 352), (338, 314), (366, 302), (402, 308), (442, 350), (452, 398), (437, 400), (380, 372), (334, 360), (324, 374)]
FROWN_L = [(442, 332), (478, 332), (478, 412), (444, 422), (437, 400), (452, 398)]
LIP = [(430, 614), (594, 614), (594, 642), (430, 642)]

cuts = {  # name: (region, colours that move, colour left behind in the base)
    "eye-l": (in_poly(EYE_L), (D, C), O), "eye-r": (in_poly(mirror(EYE_L)), (D, C), O),
    "frown-l": (in_poly(FROWN_L), (D,), O), "frown-r": (in_poly(mirror(FROWN_L)), (D,), O),
}
masks = {}
base = idx.copy()
taken = np.zeros((1024, 1024), bool)
for name, (region, keep, fill) in cuts.items():
    m = region & np.isin(idx, keep) & alpha & ~taken
    masks[name] = m; taken |= m; base[m] = fill
    base[region & np.isin(idx, (S, L)) & ~taken] = O  # socket shading would read as a frown
for name, poly in [("brow-l", BROW_L), ("brow-r", mirror(BROW_L))]:
    m = in_poly(poly) & np.isin(idx, (D, S, L)) & alpha & ~taken
    masks[name] = m; taken |= m; base[m] = O
m = in_poly(LIP) & (idx == D) & alpha
masks["lip"] = m; base[m] = C


def save_png(mask, colors, path):
    a = np.zeros((1024, 1024, 4), np.uint8)
    a[..., :3] = PAL[colors]
    a[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(a).save(path)


os.makedirs(OUT, exist_ok=True)
save_png(alpha, base, f"{W}/_base.png")
for name in ("brow-l", "brow-r", "lip"):
    save_png(masks[name], idx, f"{W}/_{name}.png")


def trace(png, svg_out):
    vtracer.convert_image_to_svg_py(png, svg_out, colormode="color", hierarchical="stacked", mode="spline",
                                    filter_speckle=4, color_precision=8, layer_difference=8, corner_threshold=60,
                                    length_threshold=4.0, splice_threshold=45, path_precision=1)
    s = open(svg_out).read()
    body = s[s.index("<path"):s.rindex("</svg>")]
    return "".join(p for p in body.split("\n") if 'd=""' not in p)


parts = {n: trace(f"{W}/_{n}.png", f"{OUT}/{n}.svg") for n in ("base", "brow-l", "brow-r", "lip")}

# Hand-drawn overlays in the master's palette (1024 px coordinates). Eye centres:
EL, ER, EY = 390, 632, 428


def eye(cx, outer, rx=42, ry=52, glint=11):
    # The master's eye, rounded: a dark oval, a cream crescent on the outer side, a glint high on the inner side.
    s = outer  # -1 for the left eye (outer side is left), 1 for the right
    return (f'<ellipse cx="{cx}" cy="{EY}" rx="{rx}" ry="{ry}" fill="{DARK}"/>'
            f'<path d="M{cx + s*rx*.62} {EY - ry*.62} C{cx + s*rx*.98} {EY - ry*.2} {cx + s*rx*.98} {EY + ry*.3} {cx + s*rx*.55} {EY + ry*.72} '
            f'C{cx + s*rx*.75} {EY + ry*.25} {cx + s*rx*.78} {EY - ry*.2} {cx + s*rx*.62} {EY - ry*.62} Z" fill="{CREAM}"/>'
            f'<circle cx="{cx - s*rx*.12}" cy="{EY - ry*.38}" r="{glint}" fill="{CREAM}"/>')


def arc(cx, up, w=40, depth=16, y=EY):
    # A closed eye: a thick dark arc. up=True bows upwards (a smiling eye), else down (resting).
    k = -depth if up else depth
    return f'<path d="M{cx - w} {y} Q{cx} {y + 2 * k} {cx + w} {y}" stroke="{DARK}" stroke-width="9" fill="none" stroke-linecap="round"/>'


def lidded(cx, outer):
    # Half-closed: the round eye with its top half under an orange lid and a dark lash line.
    return (eye(cx, outer) + f'<path d="M{cx - 45} {EY + 2} A45 55 0 0 1 {cx + 45} {EY + 2} L{cx + 45} {EY + 10} Q{cx} {EY + 22} {cx - 45} {EY + 10} Z" fill="{ORANGE}"/>'
            f'<path d="M{cx - 44} {EY + 10} Q{cx} {EY + 22} {cx + 44} {EY + 10}" stroke="{DARK}" stroke-width="8" fill="none" stroke-linecap="round"/>')


PHIL = f'<path d="M510 604 L510 622" stroke="{DARK}" stroke-width="8" stroke-linecap="round"/>'
overlays = {
    "eyes-open": eye(EL, -1) + eye(ER, 1),
    "eyes-wide": eye(EL, -1, 46, 58, 14) + eye(ER, 1, 46, 58, 14),
    "eyes-closed": arc(EL, False) + arc(ER, False),
    "eyes-happy": arc(EL, True, y=EY + 8) + arc(ER, True, y=EY + 8),
    "eyes-lidded": lidded(EL, -1) + lidded(ER, 1),
    "mouth-flat": PHIL + f'<path d="M472 626 Q510 632 548 626" stroke="{DARK}" stroke-width="8" fill="none" stroke-linecap="round"/>',
    "mouth-frown": PHIL + f'<path d="M474 636 Q510 616 546 636" stroke="{DARK}" stroke-width="8" fill="none" stroke-linecap="round"/>',
    "mouth-smile": PHIL + f'<path d="M432 610 C450 640 488 642 510 620 C532 642 570 640 588 610" stroke="{DARK}" stroke-width="9" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
    "mouth-open": PHIL + f'<path d="M462 620 C486 616 534 616 558 620 C556 668 464 668 462 620 Z" fill="{DARK}"/><path d="M482 652 C496 640 524 640 538 652 C526 662 494 662 482 652 Z" fill="{SHADOW}"/>',
    "mouth-o": PHIL + f'<ellipse cx="510" cy="640" rx="16" ry="19" fill="{DARK}"/><ellipse cx="510" cy="648" rx="9" ry="7" fill="{SHADOW}"/>',
}

rig = json.load(open(f"{W}/rig.json"))
PIV = {"l": (385, 345), "r": (637, 345)}
BODY = (512, 960)


def compose(pose, size=256, view=(0, 0, 1024, 1024), fade=0):
    tilt, dy = pose.get("tilt", 0), pose.get("dy", 0)
    g = [f'<g transform="translate(0,{dy}) rotate({tilt} {BODY[0]} {BODY[1]})">', parts["base"]]
    for side, sign in (("l", -1), ("r", 1)):
        b = pose.get(f"brow_{side}", pose.get("brow", {}))
        cx, cy = PIV[side]
        g.append(f'<g transform="translate(0,{b.get("dy", 0)}) rotate({sign * b.get("inner_up", 0)} {cx} {cy})">{parts["brow-" + side]}</g>')
    g.append(overlays["eyes-" + pose["eyes"]])
    mouth = pose.get("mouth", "neutral")
    g.append(parts["lip"] if mouth == "neutral" else overlays["mouth-" + mouth])
    g.append("</g>")
    defs = ""
    if fade:
        defs = (f'<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="{1 - fade}" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<mask id="m" maskUnits="userSpaceOnUse" x="{view[0]}" y="{view[1]}" width="{view[2]}" height="{view[3]}"><rect x="{view[0]}" y="{view[1]}" width="{view[2]}" height="{view[3]}" fill="url(#f)"/></mask></defs>')
    body = f'<g mask="url(#m)">{"".join(g)}</g>' if fade else "".join(g)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(map(str, view))}" width="{size}" height="{size}">{defs}{body}</svg>'
    return Image.open(io.BytesIO(bytes(resvg_py.svg_to_bytes(svg_string=svg)))).convert("RGBA")


if __name__ == "__main__":
    view, fade = rig.get("viewBox", [0, 0, 1024, 1024]), rig.get("fadeBottom", 0)
    emotions = list(rig["emotions"])
    cell, small = 256, 96
    sheet = Image.new("RGBA", (6 * (cell + 10) + 10, 2 * (cell + small + 40) + 10), (250, 248, 244, 255))
    d = ImageDraw.Draw(sheet)
    for i, e in enumerate(emotions):
        x = 10 + (i % 6) * (cell + 10)
        y = 10 + (i // 6) * (cell + small + 40)
        sheet.alpha_composite(compose(rig["emotions"][e], cell, view, fade), (x, y))
        sheet.alpha_composite(compose(rig["emotions"][e], small, view, fade), (x, y + cell + 4))
        d.text((x + small + 10, y + cell + 40), e, fill=(40, 40, 40, 255))
    sheet.save(f"{W}/contact-emotions.png")
    for name, pose in (("idle", "neutral"), ("thinking", "thinking")):
        compose(rig["emotions"][pose], 128, view, fade).save(f"{W}/{name}.png")
    talk = dict(rig["emotions"]["neutral"], mouth=rig["talk"]["mouths"][0])
    compose(talk, 128, view, fade).save(f"{W}/talking.png")
    compose(rig["emotions"]["neutral"], 96, view, fade).save(f"{W}/preview.png", optimize=True)
    for k, v in overlays.items():
        open(f"{OUT}/{k}.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">{v}</svg>')
    json.dump({k: len(v) for k, v in parts.items()}, sys.stdout)
