# Builds Fintan's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>   (the dir holds master-flat.png and rig.json)
# Like Cob, the eyes are cut out of the base and every pose names a hand-drawn eye overlay
# (the master's eyes are drawn back as "open"). The jar is part of the art: the glare on the
# glass over his head is copied into every mouth file, which the renderer draws last, so the
# glass stays on top of the brows in every pose. The base keeps its own copy underneath.
import io, json, os, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image, ImageDraw

W = sys.argv[1]
OUT = f"{W}/layered"
HEX = ["#2c2311", "#fcfefd", "#fdf7e2", "#bdbfbf", "#c9e5e3", "#db8371", "#99bfc4", "#99999b", "#e4b3a1"]
DARK, WHITE, CREAM, GREY, GLASS, SALMON, GLASS_D, GREY_D, PINK = HEX
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in HEX])
D, Wh, C, G, P = 0, 1, 2, 3, 8

img = np.array(Image.open(f"{W}/master-flat.png").convert("RGBA"))
idx = ((img[..., None, :3].astype(int) - PAL[None, None]) ** 2).sum(-1).argmin(-1)
alpha = img[..., 3] > 0
yy, xx = np.mgrid[0:1024, 0:1024]
AXIS = 1029  # x' = AXIS - x mirrors the left side onto the right


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
    return [(AXIS - x, y) for x, y in reversed(poly)]


def inpaint(a, hole):
    # Grows the colours around a hole into it, one pixel ring at a time, so shading carries on.
    a, hole = a.copy(), hole.copy()
    while hole.any():
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            src = np.roll(~hole, (dy, dx), (0, 1))
            val = np.roll(a, (dy, dx), (0, 1))
            take = hole & src
            a[take] = val[take]
            hole &= ~take
    return a


# Regions (left side; the right side mirrors).
EL, ER, EY = 413, AXIS - 413, 391
BROW_L = [(368, 262), (466, 262), (466, 304), (392, 330), (356, 330), (356, 300)]
eye_region = lambda cx: ((xx - cx) / 60) ** 2 + ((yy - 396) / 70) ** 2 < 1
NOSE = (xx > 456) & (xx < 572) & (yy > 422)
GLARE = (xx > 395) & (xx < 462) & (yy > 214) & (yy < 270)
LIP = (xx > 430) & (xx < 596) & (yy > 504) & (yy < 552)

base = idx.copy()
masks = {}
for name, poly in (("brow-l", BROW_L), ("brow-r", mirror(BROW_L))):
    m = in_poly(poly) & (idx == D) & alpha
    masks[name] = m
masks["lip"] = LIP & np.isin(idx, (D, P)) & alpha
masks["glare"] = GLARE & (idx == Wh) & alpha
# The eyes (rings, pupils, lashes, socket shading) go; the pink blush around them stays.
eyes = (eye_region(EL) | eye_region(ER)) & ~NOSE & (idx != P) & alpha
base = inpaint(base, masks["brow-l"] | masks["brow-r"])
base[eyes] = G  # plain head grey: grown shading left streaks where the sockets were
base[masks["lip"]] = C


def save_png(mask, colors, path):
    a = np.zeros((1024, 1024, 4), np.uint8)
    a[..., :3] = PAL[colors]
    a[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(a).save(path)


os.makedirs(OUT, exist_ok=True)
save_png(alpha, base, f"{W}/_base.png")
for name, m in masks.items():
    save_png(m, idx, f"{W}/_{name}.png")


def trace(png, svg_out):
    vtracer.convert_image_to_svg_py(png, svg_out, colormode="color", hierarchical="stacked", mode="spline",
                                    filter_speckle=4, color_precision=8, layer_difference=8, corner_threshold=60,
                                    length_threshold=4.0, splice_threshold=45, path_precision=1)
    s = open(svg_out).read()
    body = s[s.index("<path"):s.rindex("</svg>")]
    return "".join(p for p in body.split("\n") if 'd=""' not in p)


parts = {n: trace(f"{W}/_{n}.png", f"{OUT}/{n}.svg") for n in ("base", "brow-l", "brow-r", "lip", "glare")}
for n in ("lip", "glare"):
    os.remove(f"{OUT}/{n}.svg")  # they ship inside the mouth files


# Hand-drawn overlays in the master's palette (1024 px coordinates).
def eye(cx, inner, look=(6, 0), rx=50, ry=56, prx=28, pry=33):
    # The master's eye: dark rim, white, a big dark pupil with a glint, a small lash under the outer corner.
    lx, ly = inner * look[0], look[1]
    out = -inner
    return (f'<ellipse cx="{cx}" cy="{EY}" rx="{rx}" ry="{ry}" fill="{DARK}"/>'
            f'<ellipse cx="{cx}" cy="{EY + 3}" rx="{rx - 9}" ry="{ry - 10}" fill="{WHITE}"/>'
            f'<ellipse cx="{cx + lx}" cy="{EY + 3 + ly}" rx="{prx}" ry="{pry}" fill="{DARK}"/>'
            f'<circle cx="{cx + lx}" cy="{EY + 3 + ly - pry * .56}" r="{prx * .3:.1f}" fill="{WHITE}"/>'
            f'<path d="M{cx + out * 34} {EY + ry - 2} Q{cx + out * 12} {EY + ry + 12} {cx - out * 6} {EY + ry + 6}" stroke="{DARK}" stroke-width="6" fill="none" stroke-linecap="round"/>')


def lid(cx, inner, cover, look=(6, 0)):
    # The open eye with a grey lid from the top down to `cover` (0 open, 1 shut) and a dark lid line.
    y = EY - 56 + 112 * cover
    cid = f"lid{cx}{int(cover * 100)}"
    return (eye(cx, inner, look) + f'<defs><clipPath id="{cid}"><ellipse cx="{cx}" cy="{EY}" rx="51" ry="57"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})"><path d="M{cx - 60} {EY - 70} L{cx + 60} {EY - 70} L{cx + 60} {y} Q{cx} {y + 12} {cx - 60} {y} Z" fill="{GREY}"/></g>'
            f'<path d="M{cx - 50} {y + 2} Q{cx} {y + 14} {cx + 50} {y + 2}" stroke="{DARK}" stroke-width="10" fill="none" stroke-linecap="round"/>')


def arc(cx, up, w=40, y=EY):
    # A shut eye: a thick dark arc, bowing up when smiling, down when resting.
    k = -26 if up else 26
    return f'<path d="M{cx - w} {y} Q{cx} {y + k} {cx + w} {y}" stroke="{DARK}" stroke-width="11" fill="none" stroke-linecap="round"/>'


MX, MY = 513, 519
glare = parts["glare"]
line = lambda d, w=9: f'<path d="{d}" stroke="{DARK}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
overlays = {
    "eyes-open": eye(EL, 1) + eye(ER, -1),
    "eyes-wide": eye(EL, 1, (3, 0), 55, 62, 21, 25) + eye(ER, -1, (3, 0), 55, 62, 21, 25),
    "eyes-up": eye(EL, 1, (-4, -11)) + eye(ER, -1, (4, -11)),
    "eyes-lidded": lid(EL, 1, .4) + lid(ER, -1, .4),
    "eyes-heavy": lid(EL, 1, .62, (6, 10)) + lid(ER, -1, .62, (6, 10)),
    "eyes-happy": arc(EL, True, y=EY + 12) + arc(ER, True, y=EY + 12),
    "eyes-closed": arc(EL, False, y=EY + 4) + arc(ER, False, y=EY + 4),
    "mouth-neutral": parts["lip"] + glare,
    "mouth-flat": line(f"M{MX - 32} {MY} L{MX + 32} {MY}") + glare,
    "mouth-smile": line(f"M{MX - 56} {MY - 6} Q{MX} {MY + 34} {MX + 56} {MY - 6}", 10) + glare,
    "mouth-frown": line(f"M{MX - 34} {MY + 10} Q{MX} {MY - 12} {MX + 34} {MY + 10}") + glare,
    "mouth-o": f'<ellipse cx="{MX}" cy="{MY + 8}" rx="15" ry="19" fill="{DARK}"/><ellipse cx="{MX}" cy="{MY + 17}" rx="8" ry="6" fill="{PINK}"/>' + glare,
    "mouth-open": (f'<path d="M{MX - 44} {MY - 4} Q{MX} {MY + 2} {MX + 44} {MY - 4} Q{MX + 40} {MY + 48} {MX} {MY + 50} Q{MX - 40} {MY + 48} {MX - 44} {MY - 4} Z" fill="{DARK}"/>'
                   f'<path d="M{MX - 24} {MY + 38} Q{MX} {MY + 22} {MX + 24} {MY + 38} Q{MX} {MY + 50} {MX - 24} {MY + 38} Z" fill="{SALMON}"/>') + glare,
}

rig = json.load(open(f"{W}/rig.json"))
PIV = {"l": (409, 292), "r": (AXIS - 409, 292)}
BODY = (512, 960)


def compose(pose, size=256, view=(0, 0, 1024, 1024), fade=0):
    tilt, dy = pose.get("tilt", 0), pose.get("dy", 0)
    out = [f'<g transform="translate(0,{dy}) rotate({tilt} {BODY[0]} {BODY[1]})">', parts["base"]]
    for side, sign in (("l", -1), ("r", 1)):
        b = pose.get(f"brow_{side}", pose.get("brow", {}))
        cx, cy = PIV[side]
        out.append(f'<g transform="translate(0,{b.get("dy", 0)}) rotate({sign * b.get("inner_up", 0)} {cx} {cy})">{parts["brow-" + side]}</g>')
    out.append(overlays["eyes-" + pose["eyes"]])
    out.append(overlays["mouth-" + pose.get("mouth", "neutral")])
    out.append("</g>")
    defs = ""
    if fade:
        defs = (f'<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="{1 - fade}" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
                f'<mask id="m" maskUnits="userSpaceOnUse" x="{view[0]}" y="{view[1]}" width="{view[2]}" height="{view[3]}"><rect x="{view[0]}" y="{view[1]}" width="{view[2]}" height="{view[3]}" fill="url(#f)"/></mask></defs>')
    body = f'<g mask="url(#m)">{"".join(out)}</g>' if fade else "".join(out)
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
