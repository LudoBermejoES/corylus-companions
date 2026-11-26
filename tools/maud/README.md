# Maud's layered parts

`master-1024.png` is the chosen candidate (`candidates3/maud-05.png`, knitted hat and logbook).
`master-flat.png` is it with the white background cut and every pixel snapped to ten colours:

    python tools/prep_master.py <dir with master-1024.png> 12 "#2a1e0e,#3c4258,#694833,#f7c294,#828482,#32323e,#d3906c,#5e5d5a,#a8a9a3,#eddec9"

`build_layered.py` rebuilds the parts from `master-flat.png` and writes a 12-emotion contact sheet,
plus `idle.png`, `thinking.png`, `talking.png` (128 px) and `preview.png` (96 px).

The master scowls: her brows run into her upper lids as one dark mass angled down at the inner
ends, with frown lines between them and a downturned mouth. Stern has to read as precise, not
harsh, and her rest face as calm and attentive, so:

- the brows, eyes, the frown lines between the brows and the mouth are cleared out of the base to
  plain skin (the hair at the temples is kept);
- the brows are drawn back as level, heavy shapes (`brow-l.svg`, `brow-r.svg` are drawn, not traced);
- every pose names a drawn eye (`open`, `wide`, `lidded`, `watch`, `aside`, `heavy`, `happy`,
  `closed`) and a drawn mouth. The wrinkles and the rest of the face are the master's.
- `sleepy` is "on watch", per the research: the `watch` eyes are steady and lidded with the iris in
  full view, brows level, no droop or tilt. She never dozes.

`rig.json` holds the poses, the viewBox and fadeBottom; the shipped copy of the poses is
`packs/maud/character.json` -> `layered.rig.emotions`.

    uv venv .venv && uv pip install --python .venv/bin/python vtracer pillow numpy resvg-py
    .venv/bin/python tools/maud/build_layered.py <dir with master-flat.png and rig.json>

Copy the resulting `layered/*.svg` into `packs/maud/parts/` and the four PNGs into `packs/maud/`.
