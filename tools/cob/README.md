# Cob's layered parts

`master-1024.png` is the chosen candidate (`cob-03.png`, green scarf). `master-flat.png` is it with the
white background cut and every pixel snapped to seven colours:

    python tools/prep_master.py <dir with master-1024.png> 8 "#21190b,#df6945,#e09970,#a55545,#5e6c47,#859c5c,#f8f3d8"

`build_layered.py` rebuilds the parts from `master-flat.png` and writes a 12-emotion contact sheet,
plus `idle.png`, `thinking.png`, `talking.png` (128 px) and `preview.png` (96 px). The brows and the
mouth line are cut by colour inside region polygons. Unlike Ogam, the eyes and the frown lines between
them are cut out of the base as well: the master's eyes are slanted and stern, and Cob's rest face has
to look friendly, so every pose names one of the hand-drawn eye overlays (open, wide, happy, closed,
lidded). Every pose must keep an `eyes` value, or the face shows no eyes.

`rig.json` holds the poses, the viewBox and fadeBottom; the shipped copy of the poses is
`packs/cob/character.json` -> `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/cob/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/cob/parts/` and the four PNGs into `packs/cob/`.
