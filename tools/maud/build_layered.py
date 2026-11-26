# Builds Maud's layered parts from the flat 1024 px master and previews all 12 emotions.
# Usage: python build_layered.py <work dir>   (the dir holds master-flat.png and rig.json)
# The master's brows run into her upper lids as one dark mass, angled into a scowl, with frown
# lines between them and a downturned mouth. Stern has to read as precise, not harsh, so the
# brows, eyes, frown lines and mouth are all cut out of the base and filled with skin; the brows
# are drawn back as their own parts and every pose names a drawn eye and mouth overlay.
import io, json, os, sys
import numpy as np
import resvg_py, vtracer
from PIL import Image, ImageDraw

W = sys.argv[1]
OUT = f"{W}/layered"
HEX = ["#2a1e0e", "#3c4258", "#694833", "#f7c294", "#828482", "#32323e", "#d3906c", "#5e5d5a", "#a8a9a3", "#eddec9"]
DARK, NAVY, BROWN, SKIN, GREY, NAVY_D, SHADE, GREY_D, GREY_L, CREAM = HEX
PAL = np.array([[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in HEX])
D, S, SH = 0, 3, 6
HAIR = (4, 7, 8)

img = np.array(Image.open(f"{W}/master-flat.png").convert("RGBA"))
idx = ((img[..., None, :3].astype(int) - PAL[None, None]) ** 2).sum(-1).argmin(-1)
alpha = img[..., 3] > 0
yy, xx = np.mgrid[0:1024, 0:1024]
AXIS = 1035  # x' = AXIS - x mirrors the left eye onto the right


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


# Regions cleared to plain skin (left side; the right mirrors). The hair at the temples is kept.
BROW_EYE_L = [(398, 266), (440, 260), (500, 278), (506, 300), (500, 322), (484, 350), (470, 364), (420, 366), (396, 358), (386, 330), (388, 298)]
BETWEEN = [(486, 262), (550, 262), (550, 326), (486, 326)]
MOUTH = [(440, 456), (592, 456), (592, 526), (440, 526)]
clear = (in_poly(BROW_EYE_L) | in_poly(mirror(BROW_EYE_L)) | in_poly(BETWEEN) | in_poly(MOUTH)) & alpha & ~np.isin(idx, HAIR)
base = idx.copy()
base[clear] = S


def save_png(mask, colors, path):
    a = np.zeros((1024, 1024, 4), np.uint8)
    a[..., :3] = PAL[colors]
    a[..., 3] = np.where(mask, 255, 0)
    Image.fromarray(a).save(path)


os.makedirs(OUT, exist_ok=True)
save_png(alpha, base, f"{W}/_base.png")


def trace(png, svg_out):
    vtracer.convert_image_to_svg_py(png, svg_out, colormode="color", hierarchical="stacked", mode="spline",
                                    filter_speckle=4, color_precision=8, layer_difference=8, corner_threshold=60,
                                    length_threshold=4.0, splice_threshold=45, path_precision=1)
    s = open(svg_out).read()
    body = s[s.index("<path"):s.rindex("</svg>")]
    return "".join(p for p in body.split("\n") if 'd=""' not in p)


parts = {"base": trace(f"{W}/_base.png", f"{OUT}/base.svg")}

# Hand-drawn parts and overlays in the master's palette (1024 px coordinates).
EL, ER, EY = 438, AXIS - 438, 334


def brow(s):
    # A thick, level brow, heavier at the inner end. s = 1 for the left (inner end at +x), -1 for the right.
    x = lambda v: AXIS - v if s == -1 else v
    return (f'<path d="M{x(502)} 296 C{x(470)} 262 {x(426)} 256 {x(382)} 284 C{x(430)} 282 {x(470)} 294 {x(500)} 318 Z" fill="{DARK}"/>')


parts["brow-l"], parts["brow-r"] = brow(1), brow(-1)
CREASE = lambda cx, s: f'<path d="M{cx - s * 40} {EY - 16} Q{cx} {EY - 32} {cx + s * 38} {EY - 14}" stroke="{SHADE}" stroke-width="6" fill="none" stroke-linecap="round"/>'


def almond(cx, s, top=30, bot=20):
    # The eye opening. s = 1 when the inner corner is at +x (her right eye, on the left of the picture).
    o, i = cx - s * 46, cx + s * 42
    return f"M{o} {EY + 2} Q{cx - s * 6} {EY - top * 2 + 2} {i} {EY + 4} Q{cx + s * 2} {EY + bot * 2 - 4} {o} {EY + 2} Z"


def eye(cx, s, top=27, bot=19, look=(0, 0), r=20, cover=0):
    # Cream eye, dark iris with a glint, a heavy upper lash line, a thin lower lid and the lid crease.
    # `cover` lowers a skin-coloured lid over the eye (0 open, 1 shut); its edge carries the lash line.
    a = almond(cx, s, top, bot)
    cid = f"e{cx}{top}{int(cover * 100)}"
    ix, iy = cx + look[0], EY + look[1]
    lidy = EY + 2 - top + (top + bot) * cover  # the lid edge at the middle of the eye
    o, i = cx - s * 46, cx + s * 42
    edge = f"M{cx - 52} {lidy - 6} Q{cx} {lidy + 6} {cx + 52} {lidy - 6}"
    lid = f'<path d="{edge} L{cx + 52} {EY - 80} L{cx - 52} {EY - 80} Z" fill="{SKIN}"/>' if cover else ""
    upper = f'M{o - s * 6} {EY - 2} Q{cx - s * 6} {EY - top * 2 + 2} {i} {EY + 4}'
    lower = f'M{o + s * 10} {EY + 8} Q{cx + s * 2} {EY + bot * 2 - 4} {i} {EY + 6}'
    lash = (f'<g clip-path="url(#{cid}o)"><path d="{edge}" stroke="{DARK}" stroke-width="10" fill="none"/></g>'
            f'<defs><clipPath id="{cid}o"><path d="{almond(cx, s, top + 4, bot)}"/></clipPath></defs>') if cover else \
        f'<path d="{upper}" stroke="{DARK}" stroke-width="10" fill="none" stroke-linecap="round"/>'
    return (f'<defs><clipPath id="{cid}"><path d="{a}"/></clipPath></defs>'
            f'<g clip-path="url(#{cid})"><path d="{a}" fill="{CREAM}"/>'
            f'<circle cx="{ix}" cy="{iy}" r="{r}" fill="{DARK}"/><circle cx="{ix - 6}" cy="{iy - 8}" r="{r * .26:.1f}" fill="{CREAM}"/>{lid}</g>'
            + CREASE(cx, s) +
            f'<path d="{lower}" stroke="{SHADE}" stroke-width="5" fill="none" stroke-linecap="round"/>' + lash)


def shut(cx, s, up):
    # A shut eye: a dark lash line bowing down (resting) or up (smiling), with the crease above.
    k = -20 if up else 16
    y = EY + (8 if up else 2)
    return CREASE(cx, s) + f'<path d="M{cx - 42} {y} Q{cx} {y + k} {cx + 42} {y}" stroke="{DARK}" stroke-width="10" fill="none" stroke-linecap="round"/>'


both = lambda f, **k: f(EL, 1, **k) + f(ER, -1, **k)
MX, MY = 515, 478
line = lambda d, w=8, c=DARK: f'<path d="{d}" stroke="{c}" stroke-width="{w}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
LOWER = line(f"M{MX - 18} {MY + 18} Q{MX} {MY + 22} {MX + 18} {MY + 18}", 6, SHADE)
overlays = {
    "eyes-open": both(eye),
    "eyes-wide": both(eye, top=34, bot=22, r=17),
    "eyes-lidded": both(eye, cover=.3),
    "eyes-watch": both(eye, cover=.36, look=(0, 3)),
    "eyes-aside": both(eye, look=(-12, -6), cover=.12),
    "eyes-heavy": both(eye, cover=.48, look=(0, 6)),
    "eyes-happy": both(shut, up=True),
    "eyes-closed": both(shut, up=False),
    "mouth-neutral": line(f"M{MX - 40} {MY} Q{MX} {MY + 3} {MX + 40} {MY}") + LOWER,
    "mouth-flat": line(f"M{MX - 28} {MY + 1} L{MX + 28} {MY + 1}", 9) + LOWER,
    "mouth-smile": line(f"M{MX - 46} {MY - 6} Q{MX} {MY + 18} {MX + 46} {MY - 6}") + LOWER,
    "mouth-frown": line(f"M{MX - 34} {MY + 6} Q{MX} {MY - 8} {MX + 34} {MY + 6}") + LOWER,
    "mouth-o": f'<ellipse cx="{MX}" cy="{MY + 6}" rx="13" ry="16" fill="{DARK}"/>',
    "mouth-open": (f'<path d="M{MX - 36} {MY - 2} Q{MX} {MY + 4} {MX + 36} {MY - 2} Q{MX + 30} {MY + 34} {MX} {MY + 36} Q{MX - 30} {MY + 34} {MX - 36} {MY - 2} Z" fill="{DARK}"/>'
                   f'<path d="M{MX - 26} {MY + 2} Q{MX} {MY + 8} {MX + 26} {MY + 2} L{MX + 22} {MY + 10} Q{MX} {MY + 14} {MX - 22} {MY + 10} Z" fill="{CREAM}"/>'),
}

rig = json.load(open(f"{W}/rig.json"))
PIV = {"l": (444, 292), "r": (AXIS - 444, 292)}
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
    for k, v in list(overlays.items()) + [("brow-l", parts["brow-l"]), ("brow-r", parts["brow-r"])]:
        open(f"{OUT}/{k}.svg", "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">{v}</svg>')
    json.dump({k: len(v) for k, v in parts.items()}, sys.stdout)
