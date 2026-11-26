# Quoth's layered parts

`master-1024.png` is the chosen candidate (`quoth-07.png`, round glasses). `master-flat.png` is it
with the white background cut and every pixel snapped to five colours:

    python tools/prep_master.py <dir with master-1024.png> 8 "#241e10,#30373f,#47515e,#6d7476,#ebe7d3"

`build_layered.py` rebuilds the parts from `master-flat.png` and writes a 12-emotion contact sheet,
plus `idle.png`, `thinking.png`, `talking.png` (128 px) and `preview.png` (96 px).

- The brows (dark arc, grey highlight, dark wedge above each lens) are cut by colour inside region
  polygons, never closer to a lens than the frame.
- The glasses (rims, frames, bridge, temples) are copied from the master into every mouth file. The
  renderer always draws a mouth and draws it last, so the frames stay on top of the brows and of every
  eye overlay in every pose. The base keeps its own copy, so nothing shows through.
- The beak does not move. `mouth-o` and `mouth-open` draw a dark gap and a lower beak under a copy of
  the upper beak clipped along a V; `mouth-neutral` is the glasses alone.
- The eye overlays (lids, wide, happy) are clipped to the inside of each lens.

`rig.json` holds the poses, the viewBox and fadeBottom; the shipped copy of the poses is
`packs/quoth/character.json` -> `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/quoth/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/quoth/parts/` and the four PNGs into `packs/quoth/`.
