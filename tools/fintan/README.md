# Fintan's layered parts

`master-1024.png` is the chosen candidate (`candidates4/fintan-soft-05.png`, the salmon in a glass jar).
`master-flat.png` is it with the white background cut and every pixel snapped to nine colours:

    python tools/prep_master.py <dir with master-1024.png> 12 "#2c2311,#fcfefd,#fdf7e2,#bdbfbf,#c9e5e3,#db8371,#99bfc4,#99999b,#e4b3a1"

`build_layered.py` rebuilds the parts from `master-flat.png` and writes a 12-emotion contact sheet,
plus `idle.png`, `thinking.png`, `talking.png` (128 px) and `preview.png` (96 px).

- The brows are cut by colour inside region polygons; the holes are grown over from the grey around them.
- As with Cob, the eyes (rims, pupils, lashes, socket shading) are cut out of the base and filled with
  plain head grey; the pink blush stays. Every pose names a drawn eye overlay. `open` is the master's
  eye redrawn; `wide`, `up`, `lidded`, `heavy`, `happy` and `closed` are variations of it.
- The jar is part of the art. The glare on the glass over his head is copied into every mouth file:
  the renderer always draws a mouth, last, so the glass stays on top of the raised brows in every
  pose. The base keeps its own copy underneath. The whole jar tilts with him.
- The mouth line and the pink under it are cut and ship as `mouth-neutral`; the other mouths are drawn.

`rig.json` holds the poses, the viewBox and fadeBottom; the shipped copy of the poses is
`packs/fintan/character.json` -> `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/fintan/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/fintan/parts/` and the four PNGs into `packs/fintan/`.
