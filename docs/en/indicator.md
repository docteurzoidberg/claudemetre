[Version française](../temoin.md)

# The Claudemètre's CLAUDE indicator

The CLAUDE indicator (legend lit by a length of WS2812B) is a **panel-mount
indicator** made by a generic tool, developed separately:
**`~/3d/generateur-temoin-lumineux`** (`temoin` command, driven by the
`temoin-lumineux` skill). The tool makes the indicator; the Claudemètre keeps what is
specific to it.

| Generator (generic) | Claudemètre |
| --- | --- |
| frame, legend, light box, back, screws and inserts | preset `design/temoin/claude.json` |
| multi-filament 3MF, STL, STEP; bill of materials and cutout dimensions in its summary | faceplate cutout, position in the assembly |
| checks (legend strokes, mounting, LEDs) | states and colors in the firmware and the Lovelace card |

The faceplate only has a rectangular cutout and 2 Ø 3.4 holes: changing the
legend means 2 screws and one small part to reprint.

## Usage

You ask for "génère le témoin du claudemètre" (generate the Claudemètre indicator), or
edit the preset to remake it. The `temoin-lumineux` skill reads `design/temoin/claude.json`,
runs the checks then the generation, and writes the files to `design/temoin/export/`
(regenerable, never edited by hand). Then, with the `fusion360` skill, the
`claude` design inserted in `claudometre` is updated, and the faceplate cutout
follows the dimensions in the summary.

## CLAUDE preset

| Setting | Value | Note |
| --- | --- | --- |
| Legend | `CLAUDE`, Barlow Condensed SemiBold, lit letters, `#111111` background | same font as the dials; 6.64 mm capitals (calculated) |
| Window | 32 × 11 mm | |
| Frame | 52 × 18 mm, `#4b5320` | no visor |
| Panel | 3 mm (`platine_ep`) | |
| Mounting | 2 black FHC M3×8 countersunk screws (ISO 10642) + 2 M3 heat-set inserts (Ø 4 × 5.5 hole), 42 spacing | the generator specifies M3×10; M3×8 taken from leftover stock |
| Lighting | 5 V WS2812B strip at 144 LEDs/m, 4 LEDs, wires on the left seen from the front | `led_count: 4` in the firmware; the generator specifies 5 LEDs |
| Filaments | all PETG: khaki frame, black box and back, black mask, transparent letters and diffuser | like the rest of the enclosure |
| States | `claude_actif` breathing amber, `claude_needattention` blinking red, takes priority | |

Derived dimensions: 34.8 × 13.8 mm cutout, 2 Ø 3.4 holes at 42 spacing, centered on
the window. The frame overlaps the cutout by 8.6 mm left and right, by 2.1 mm
top and bottom, and 1.9 mm of faceplate remains between the cutout and each screw hole.

Generator checks: two warnings that don't affect printing, a gap in the mask
thinner than the nozzle (0.05 mm² at x = −2.9) and the end LEDs 0.39 mm
behind the frame, outside the window.

## On the object

- Position: x = 0, z = −26, under RÉINIT., 2.5 mm from that nameplate. Frame edges
  at x = ±26, 12 mm from the SESSION / SEMAINE nameplates.
- 3.3 V signal: the strip is powered through a 1N400x diode, which brings
  its high threshold below 3.3 V, with no level shifter.
- Wires soldered to the strip, ferrules on the terminal board side.
