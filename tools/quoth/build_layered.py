# Builds Quoth's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>   (the dir holds master-flat.png and rig.json)
# The glasses are cut from the master into their own layer and drawn into every mouth file:
# the renderer always draws a mouth, last, so the frames stay on top of the brows and of
# every eye overlay. The base keeps its own copy underneath, so nothing shows through.
import io, json, os, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image, ImageDraw

W = sys.argv[1]
OUT = f"{W}/layered"
HEX = ["#241e10", "#30373f", "#47515e", "#6d7476", "#ebe7d3"]
DARK, SHADOW, NAVY, GREY, CREAM = HEX
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in HEX])
D, S, N, G, C = range(5)

img = np.array(Image.open(f"{W}/master-flat.png").convert("RGBA"))
idx = ((img[..., None, :3].astype(int) - PAL[None, None]) ** 2).sum(-1).argmin(-1)
alpha = img[..., 3] > 0
yy, xx = np.mgrid[0:1024, 0:1024]
AXIS = 1031  # x' = AXIS - x mirrors the left side onto the right
LENS_L, LENS_R, LENS_RX, LENS_RY = (373, 386), (658, 386), 85, 81


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


def lens_r(c):
    # Distance from a lens centre in units of the cream rim's radius (1 = on the rim).
    return np.sqrt(((xx - c[0]) / LENS_RX) ** 2 + ((yy - c[1]) / LENS_RY) ** 2)


# Brow: the dark arc, the grey highlight band and the dark wedge above each lens, never the frame.
BROW_L = [(286, 270), (294, 226), (340, 203), (410, 208), (432, 222), (462, 272), (480, 302), (470, 318), (300, 318)]
outside_frames = (lens_r(LENS_L) > 1.24) & (lens_r(LENS_R) > 1.24)
masks = {}
base = idx.copy()
for name, poly in (("brow-l", BROW_L), ("brow-r", mirror(BROW_L))):
    m = in_poly(poly) & np.isin(idx, (D, G)) & alpha & outside_frames
    masks[name] = m
    base[m] = N
# Glasses: rims and frames around both lenses, the bridge, the two temple arms. Copied, not cut.
ring = lambda c: (lens_r(c) > 0.93) & (lens_r(c) < 1.24)
BRIDGE = [(444, 304), (588, 304), (588, 352), (444, 352)]
TEMPLE_L = [(218, 296), (292, 296), (292, 340), (218, 340)]
BEAK = [(420, 400), (604, 400), (606, 520), (562, 600), (518, 702), (500, 702), (452, 600), (418, 520)]
masks["beak"] = in_poly(BEAK) & alpha & (lens_r(LENS_L) > 1.24) & (lens_r(LENS_R) > 1.24) & ~in_poly(BRIDGE)
masks["glasses"] = (ring(LENS_L) | ring(LENS_R) | in_poly(BRIDGE) | in_poly(TEMPLE_L) | in_poly(mirror(TEMPLE_L))) & np.isin(idx, (D, C)) & alpha


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


parts = {n: trace(f"{W}/_{n}.png", f"{OUT}/{n}.svg") for n in ("base", "brow-l", "brow-r", "glasses", "beak")}
for n in ("glasses", "beak"):
    os.remove(f"{OUT}/{n}.svg")  # they ship inside the mouth files

# Hand-drawn overlays in the master's palette (1024 px coordinates). Eye centres:
EL, ER, EY = 382, AXIS - 382, 350


def lid(cx, cover):
    # A lid over the eye: navy from the top down to `cover` (0 = open, 1 = shut), dark lash line at its edge.
    y = EY - 54 + 108 * cover
    return (f'<path d="M{cx - 56} {EY - 100} L{cx + 56} {EY - 100} L{cx + 56} {y} Q{cx} {y + 12} {cx - 56} {y} Z" fill="{NAVY}"/>'
            f'<path d="M{cx - 52} {y + 1} Q{cx} {y + 13} {cx + 52} {y + 1}" stroke="{DARK}" stroke-width="9" fill="none" stroke-linecap="round"/>')


def wide(cx, look):
    # Eye opened all the way: a full cream disc, a smaller pupil, a glint.
    return (f'<circle cx="{cx}" cy="{EY}" r="54" fill="{DARK}"/><circle cx="{cx}" cy="{EY}" r="46" fill="{CREAM}"/>'
            f'<circle cx="{cx + look}" cy="{EY + 2}" r="22" fill="{DARK}"/><circle cx="{cx + look - 7}" cy="{EY - 6}" r="7" fill="{CREAM}"/>')


def smiling(cx):
    # Closed and pleased: a dark arc bowing upwards on a lid that fills the eye.
    return (f'<circle cx="{cx}" cy="{EY}" r="56" fill="{NAVY}"/>'
            f'<path d="M{cx - 42} {EY + 14} Q{cx} {EY - 26} {cx + 42} {EY + 14}" stroke="{DARK}" stroke-width="10" fill="none" stroke-linecap="round"/>')


g = parts["glasses"]
def beak_open(cut, drop):
    # The upper beak is copied back on top but clipped along a V, so its tip ends at y=`cut`; under
    # it a dark gap hides the master's tip, and the lower beak hangs `drop` px below the old tip.
    tip = 700 + drop
    return (f'<defs><clipPath id="upper"><path d="M380 380 L640 380 L640 580 L510 {cut} L380 580 Z"/></clipPath></defs>'
            f'<path d="M446 580 L574 580 C562 640 532 {tip - 30} 510 {tip + 6} C488 {tip - 30} 458 640 446 580 Z" fill="{DARK}"/>'
            f'<path d="M476 {cut + 24} Q510 {cut + 46} 544 {cut + 24} C538 {tip - 30} 522 {tip - 12} 510 {tip} C498 {tip - 12} 482 {tip - 30} 476 {cut + 24} Z" '
            f'fill="{NAVY}" stroke="{DARK}" stroke-width="7" stroke-linejoin="round"/>'
            f'<g clip-path="url(#upper)">{parts["beak"]}</g>'
            f'<path d="M454 586 L510 {cut} L566 586" stroke="{DARK}" stroke-width="8" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')


def in_lenses(left, right):
    # Clip each eye to the inside of its lens, so a lid never spills over the frame or the brow.
    clip = "".join(f'<clipPath id="lens-{s}"><ellipse cx="{c[0]}" cy="{c[1]}" rx="{LENS_RX}" ry="{LENS_RY}"/></clipPath>' for s, c in (("l", LENS_L), ("r", LENS_R)))
    return f'<defs>{clip}</defs><g clip-path="url(#lens-l)">{left}</g><g clip-path="url(#lens-r)">{right}</g>'


overlays = {
    "eyes-closed": in_lenses(lid(EL, 1), lid(ER, 1)),
    "eyes-lidded": in_lenses(lid(EL, .45), lid(ER, .45)),
    "eyes-squint": in_lenses(lid(EL, .55), lid(ER, .12)),
    "eyes-heavy": in_lenses(lid(EL, .72), lid(ER, .72)),
    "eyes-wide": in_lenses(wide(EL, 6), wide(ER, -6)),
    "eyes-happy": in_lenses(smiling(EL), smiling(ER)),
    "mouth-neutral": g,
    "mouth-open": beak_open(636, 48) + g,
    "mouth-o": beak_open(662, 18) + g,
}

rig = json.load(open(f"{W}/rig.json"))
PIV = {"l": (380, 258), "r": (AXIS - 380, 258)}
BODY = (512, 960)


def compose(pose, size=256, view=(0, 0, 1024, 1024), fade=0):
    tilt, dy = pose.get("tilt", 0), pose.get("dy", 0)
    out = [f'<g transform="translate(0,{dy}) rotate({tilt} {BODY[0]} {BODY[1]})">', parts["base"]]
    for side, sign in (("l", -1), ("r", 1)):
        b = pose.get(f"brow_{side}", pose.get("brow", {}))
        cx, cy = PIV[side]
        out.append(f'<g transform="translate(0,{b.get("dy", 0)}) rotate({sign * b.get("inner_up", 0)} {cx} {cy})">{parts["brow-" + side]}</g>')
    if pose.get("eyes"):
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
