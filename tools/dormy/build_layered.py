# Builds Dormy's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>   (the dir holds master-flat.png and rig.json)
# His rest face is already sleepy: the master's heavy-lidded eyes are cut out of the base and
# drawn back as "drowsy", next to fully open ones for the moments he is wide awake for a
# second (excited, surprised) and shut ones for when he is fully asleep. The cat smile is cut
# too and ships as the neutral mouth; the other mouths are drawn.
import io, json, os, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image, ImageDraw

W = sys.argv[1]
OUT = f"{W}/layered"
HEX = ["#352810", "#eeb255", "#ca8345", "#faf1d0", "#e09f4e", "#dca27b", "#6d4827", "#976e47"]
DARK, GOLD, RUST, CREAM, AMBER, PINK, NUT, NUT_L = HEX
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in HEX])
D, G, C, P = 0, 1, 3, 5

img = np.array(Image.open(f"{W}/master-flat.png").convert("RGBA"))
idx = ((img[..., None, :3].astype(int) - PAL[None, None]) ** 2).sum(-1).argmin(-1)
alpha = img[..., 3] > 0
yy, xx = np.mgrid[0:1024, 0:1024]
AXIS = 1018  # x' = AXIS - x mirrors the left side onto the right


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


# Regions (left side; the right side mirrors).
EL, ER, EY = 396, AXIS - 396, 381
BROW_L = [(362, 280), (426, 280), (426, 312), (380, 322), (362, 322)]
eye_region = lambda cx: ((xx - cx) / 62) ** 2 + ((yy - EY) / 48) ** 2 < 1
SMILE = (xx > 430) & (xx < 598) & (yy > 508) & (yy < 556)

base = idx.copy()
masks = {}
for name, poly in (("brow-l", BROW_L), ("brow-r", mirror(BROW_L))):
    masks[name] = in_poly(poly) & np.isin(idx, (D, P)) & alpha
masks["lip"] = SMILE & (idx == D) & alpha
eyes = (eye_region(EL) | eye_region(ER)) & np.isin(idx, (D, C, P)) & alpha
base[eyes | masks["brow-l"] | masks["brow-r"]] = G
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


parts = {n: trace(f"{W}/_{n}.png", f"{OUT}/{n}.svg") for n in ("base", "brow-l", "brow-r", "lip")}
os.remove(f"{OUT}/lip.svg")  # ships as mouth-neutral


# Hand-drawn overlays in the master's palette (1024 px coordinates). o = -1 on the left eye, whose outer corner is at -x.
def lash(cx, o, y):
    return f'<path d="M{cx + o * 38} {y + 2} Q{cx + o * 50} {y - 2} {cx + o * 56} {y - 10}" stroke="{DARK}" stroke-width="8" fill="none" stroke-linecap="round"/>'


def drowsy(cx, o, lid=-18, look=(0, 0)):
    # The master's eye: a dark oval under a heavy, slanting lid, a glint, a lash at the outer corner.
    # `lid` is the lid's height at the middle of the eye, relative to the eye centre.
    cid = f"d{cx}{lid}{look[1]}"
    edge = f"M{cx - 60} {EY + lid - o * 8} Q{cx} {EY + lid - 8} {cx + 60} {EY + lid + o * 8}"  # droops to the outer corner
    gy = max(EY + lid + 12, EY - 10) + look[1]
    return (f'<defs><clipPath id="{cid}"><path d="{edge} L{cx + 60} {EY + 60} L{cx - 60} {EY + 60} Z"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})"><ellipse cx="{cx}" cy="{EY}" rx="41" ry="36" fill="{DARK}"/>'
            f'<circle cx="{cx + 3 + look[0]}" cy="{gy}" r="10" fill="{CREAM}"/></g>'
            f'<path d="M{cx - 40} {EY + lid - o * 7 + 2} Q{cx} {EY + lid - 6} {cx + 40} {EY + lid + o * 7 + 2}" stroke="{DARK}" stroke-width="8" fill="none" stroke-linecap="round"/>'
            + lash(cx, o, EY + lid + 10))


def awake(cx, o, rx=40, ry=44):
    # Wide awake: a full dark oval, a big glint and a small one, the lash at the outer corner.
    return (f'<ellipse cx="{cx}" cy="{EY - 4}" rx="{rx}" ry="{ry}" fill="{DARK}"/>'
            f'<circle cx="{cx + 8}" cy="{EY - ry * .38:.0f}" r="{rx * .3:.0f}" fill="{CREAM}"/><circle cx="{cx - 12}" cy="{EY + ry * .3:.0f}" r="6" fill="{CREAM}"/>'
            + lash(cx, o, EY - ry * .55))


def arc(cx, o, up, y=EY + 6):
    # Shut: a dark arc bowing up when smiling, down when asleep, with the lash at the outer corner.
    k = -30 if up else 24
    return (f'<path d="M{cx - 38} {y} Q{cx} {y + k} {cx + 38} {y}" stroke="{DARK}" stroke-width="10" fill="none" stroke-linecap="round"/>'
            + ("" if up else lash(cx, o, y - 4)))


both = lambda f, *a, **k: f(EL, -1, *a, **k) + f(ER, 1, *a, **k)
MX, MY = 512, 528
PHIL = f'<path d="M{MX} 506 L{MX} {MY + 6}" stroke="{DARK}" stroke-width="8" stroke-linecap="round"/>'
line = lambda d, w=9: f'<path d="{d}" stroke="{DARK}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
overlays = {
    "eyes-drowsy": both(drowsy),
    "eyes-heavy": both(drowsy, lid=2, look=(0, 6)),
    "eyes-up": both(drowsy, lid=-14, look=(6, -4)),
    "eyes-open": both(awake),
    "eyes-wide": both(awake, 46, 52),
    "eyes-happy": both(arc, True),
    "eyes-closed": both(arc, False),
    "mouth-neutral": parts["lip"],
    "mouth-smile": PHIL + line(f"M{MX - 76} {MY - 14} C{MX - 60} {MY + 22} {MX - 14} {MY + 22} {MX} {MY + 4} C{MX + 14} {MY + 22} {MX + 60} {MY + 22} {MX + 76} {MY - 14}", 10),
    "mouth-flat": PHIL + line(f"M{MX - 34} {MY + 8} Q{MX} {MY + 12} {MX + 34} {MY + 8}"),
    "mouth-frown": PHIL + line(f"M{MX - 36} {MY + 18} Q{MX} {MY - 2} {MX + 36} {MY + 18}"),
    "mouth-o": f'<ellipse cx="{MX}" cy="{MY + 4}" rx="15" ry="18" fill="{DARK}"/><ellipse cx="{MX}" cy="{MY + 13}" rx="8" ry="6" fill="{PINK}"/>',
    "mouth-open": PHIL + (f'<path d="M{MX - 46} {MY + 2} Q{MX} {MY + 10} {MX + 46} {MY + 2} Q{MX + 40} {MY + 52} {MX} {MY + 54} Q{MX - 40} {MY + 52} {MX - 46} {MY + 2} Z" fill="{DARK}"/>'
                          f'<path d="M{MX - 26} {MY + 42} Q{MX} {MY + 24} {MX + 26} {MY + 42} Q{MX} {MY + 54} {MX - 26} {MY + 42} Z" fill="{PINK}"/>'),
}

rig = json.load(open(f"{W}/rig.json"))
PIV = {"l": (394, 300), "r": (AXIS - 394, 300)}
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
