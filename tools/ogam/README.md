# Ogam's layered parts

`build_layered.py` rebuilds `packs/ogam/parts/` from `master-flat.png` (the 1024 px master
from the old Corylus app icon, snapped to its five colours) and writes a 12-emotion contact
sheet. The brows and lip are cut by colour inside region polygons; hand-drawn overlays
(lids, glints, mouths) live in the script. `rig.json` holds the poses; the shipped copy is
`packs/ogam/character.json` → `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/ogam/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/ogam/parts/`.
