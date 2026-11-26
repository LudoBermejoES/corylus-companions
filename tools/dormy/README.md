# Dormy's layered parts

`master-1024.png` is the chosen candidate (`candidates4/dormy-soft-05.png`, hugging a hazelnut).
`master-flat.png` is it with the white background cut and every pixel snapped to eight colours:

    python tools/prep_master.py <dir with master-1024.png> 12 "#352810,#eeb255,#ca8345,#faf1d0,#e09f4e,#dca27b,#6d4827,#976e47"

`build_layered.py` rebuilds the parts from `master-flat.png` and writes a 12-emotion contact sheet,
plus `idle.png`, `thinking.png`, `talking.png` (128 px) and `preview.png` (96 px).

- The brows are cut by colour inside region polygons and filled with the fur colour.
- His rest face is already sleepy. The master's heavy-lidded eyes are cut out of the base and drawn
  back as `drowsy` (lid drooping to the outer corner, glint, lash); `heavy` and `up` are the same eye
  with the lid lower or the glint raised. `open` and `wide` are the full, round eyes for the moments he
  is wide awake for a second (excited, surprised, curious, concerned). `closed` is fully asleep (it is
  also the blink); `happy` is the smiling arc.
- The cat smile is cut and ships as `mouth-neutral`; the other mouths are drawn, with the philtrum.

`rig.json` holds the poses, the viewBox and fadeBottom; the shipped copy of the poses is
`packs/dormy/character.json` -> `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/dormy/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/dormy/parts/` and the four PNGs into `packs/dormy/`.
