[Version française](../maquettes.md)

# Mockup

The up-to-date mockup is `jj_fusion`: the geometry comes from the Fusion assembly `claudometre`
(version 28), body by body. Set, lighting and materials are in `cm_lib.py`, with the real
print orientation of each part.

Renders: `design/renders/<variant>.png`; Blender scenes:
`design/blender/scenes/<variant>.blend`; regenerate with
`design/blender/render.sh <variant> final`. Displayed values: session 62 %, week 38 %,
reset at 14:32.

## Current version

| Element | Choice |
| --- | --- |
| Enclosure | khaki shell, black faceplate, straight front, visor above the display |
| Gauges | two SO-45s, flange in front of the faceplate: square and screws visible |
| Dials | dark style; they only carry the unit, at the top: "% · 5 H" or "% · 7 J" |
| Display | TM1637 0.56", yellow segments |
| Nameplates | SESSION, SEMAINE and RÉINIT., screwed on: the instrument's name is here, not on the dial |
| Indicator | lit CLAUDE legend, panel-mount indicator with no visor, centered on the row of SESSION / SEMAINE nameplates |
| Sides | one window per side, closed by a removable plate: changing connector means remaking the plate, not the shell. On the right `plaque_bossage`, LP-16 connector tilted 30° upwards; on the left `plaque_flanc`, blank |

Dimensions and interfaces: `design/fusion/README.md`. Indicator: [indicator.md](indicator.md).

## Views and updating

| Render | View |
| --- | --- |
| `jj_fusion` | overall, connector side, whole cable |
| `jj_fusion_face` | from the front, dials readable |
| `jj_fusion_detail` | close-up of `plaque_bossage` and the plug |
| `jj_fusion_soir` | from the front, evening light; also as a video (`jj_fusion_soir.mp4`) |

- **To update**: `design/fusion/scripts/export_blender.py` in Fusion, copy
  `%TEMP%\claudemetre\export\blender\claudometre.*` to `design/fusion/blender/`, then
  `design/blender/render.sh <variant> final`. The export doesn't change the design.
- **Mockup page** (private artifact, see `ARTEFACTS.md`): source
  `design/gallery/jj_fusion.html`, images in `design/gallery/img/`. To add a view: render
  it, convert it to a 1500 px JPEG in `design/gallery/img/`, then republish to the same URL.
- **Added in `variants6.py`, absent from Fusion**: needles, moving assembly (brass hub,
  brackets), glass and zero screws of the SO-45s, LP-16 plug and Ø 5 cable, 2 FHC screws on the
  indicator frame. None of this is dimensioned: it is illustration, based on
  `design/references/so45/voltmetre_face.jpg`.
- **Needles**: black with a red tip, like the real ones (`SESSION`, `SEMAINE` and `RESET` in
  `variants6.py`). On the dark dial, only the tip shows up well.
- **LP-16 socket**: black, like the real one, not light gray like the STEP.
- **Left out, invisible with the enclosure closed**: board, clips, inserts, back of the display.
- **Animated indicator**: keyframes in the scene, at the firmware's pace (`esphome/temoin.yaml`):
  2 amber breaths of 3.2 s, 100 % → 35 % → 100 %, then 3 red blinks of 1 s, i.e.
  235 frames at 25 frames/s (`SEQUENCE` in `variants6.py`). The scene plays in Blender.
- **Video**: `design/blender/anim.sh <variant> final`. Cycles runs on the CPU (no
  GPU on this machine): `anim.py` only renders 3 frames, indicator off, amber and red at 100 %, and
  computes the others linearly (light adds up). Same result as frame by frame, without
  noise flicker, in a few minutes.

## Assembled / exploded 3D page (`maquette/`)

The model with all the internal parts (board, clips, inserts, screws), in a
three.js page to play with: exploded view slider, four views, indicator at the firmware's pace, parts to hide,
a card for each part on hover. Published to GitHub Pages by an action, and to be updated just before
pushing: procedure in `maquette/README.md`.
