[Version française](../cahier-des-charges.md)

# Specification

## 1. Style

- Dashboard instrument, for the wooden wall board that holds the PC: khaki shell,
  black faceplate, dark dials, black nameplates with white text.
- Two **analog needle gauges** (repurposed panel voltmeters).
- A **7-segment display** for the session reset time or the time remaining.
- A **CLAUDE indicator light** (backlit legend) for agent activity: breathing
  amber while working, blinking red when one of them is waiting for an
  answer.
- Dials **reprinted as 0-100 %** in place of the volt scale, in
  **multi-filament** on the Snapmaker U1 (4 toolheads, 0.4 nozzle): exact shape of
  the original plate, screwed in its place on the two Ø 5 posts. 2 mm
  thick, colors over 0.8 mm (one color per body), backing behind except for
  counterbores around the posts, face 0.8 mm from the seat. Ticks every
  5 %, numbered every 25 %, red zone 80-100 %, "% · 5 H" / "% · 7 J"
  at the top of the dial. The instrument's name (SESSION / SEMAINE) is on a
  nameplate screwed under the gauge. Drawing: `design/dials/so45_print.py`.
- Visual reference: the Fusion design `claudometre` (see CLAUDE.md).

## 2. Hardware

### Bill of materials

FHC = countersunk screw, CHC = socket head screw.

| Part | Qty | Note |
| --- | --- | --- |
| ESP32-S3-DevKitC-1 N16R8 board (diymore) | 1 | Amazon B0F3XMYYQY |
| MRD076A terminal board | 1 | the ESP32 plugs into it, screw wiring with no soldering; Amazon B0FKBLR2KF; dimensions: `design/references/mrd076a/README.md` |
| "SO-45" 0-5 V analog voltmeter | 2 | brought down to ~3 V full scale by an internal resistor (see below) |
| 4-digit 0.56" 7-seg module with decimal points (TM1637), yellow | 1 | AliExpress 1005001970566474; dimensions: `design/references/tm1637/README.md` |
| CLAUDE indicator: length of 144 LED/m WS2812B strip (4 LEDs), 1N400x diode, 2 FHC M3×8, 2 M3 inserts | 1 | parts printed from the generator, see [indicator.md](indicator.md) |
| 5 V USB cable / power supply | 1 | |
| 5 × 20 panel fuse holder and fuse | 1 | on `plaque_bossage_fusible`, protects the 12 V input; dimensions: `design/references/fusible/README.md` |

Nothing else if possible: no trimmer, no filter board.

### Driving the gauges

- A moving-coil voltmeter is a galvanometer with a series resistor, which alone
  sets the range. A 3.3 V GPIO output would only take a 0-5 V meter two thirds of
  the way.
- **Full scale brought down to about 3 V**: **6.2 kΩ in parallel with `R_s`**
  (the internal series resistor), on both voltmeters, inside the case.
  Nothing visible, no external part. The printed 100 % lands around 2.93 and
  2.95 V. Measurements and calculations:
  [design/references/so45/README.md](../../design/references/so45/README.md) (in French).
- **PWM (LEDC) straight into the voltmeter**, at 25 kHz, above the audible range:
  the inertia of the moving coil averages it. The ESP32-S3 has no DAC.
- No external protection resistor: the internal series resistor already limits
  the current (≈ 1.1 × full scale at 3.3 V, harmless for the moving
  coil). Never 5 V on a GPIO.
- **Software calibration**, no trimmer: a lookup table per gauge
  (0/25/50/75/100 %), adjustable from Home Assistant (ESPHome `number`
  entities), which also corrects the dials' non-linearity. The ESP can go past
  the printed marks at both ends: at the top, ≈ 12 % beyond 100 %
  (≈ 5 % at worst); at the bottom, PWM can't go below zero, so the zero screw
  (on the front) sets the needle's rest position slightly below the printed 0 %, and
  the software 0 % is a small duty cycle.
- SO-45 format: **46.8 × 46.8 × 4.65 mm square** flange with 4 Ø 4 holes
  (37 mm spacing), **Ø 45** bezel protruding 4.65 mm, **Ø 38.8 "D"-shaped**
  window, **Ø 45 × 24.4 mm** body, 2 M4 terminals of 8.5 mm.

### 7-segment display

- **4-digit TM1637 with decimal points** (a dot between each digit, no
  colon): 2 wires (CLK, DIO), powered at 3.3 V,
  adjustable brightness, native ESPHome `tm1637` component. This is not true
  I²C (no address, its own protocol): any two GPIOs, not shared
  with an I²C bus.
- Shows **the session reset time** (`14.32`) or **the time remaining until
  that reset** (`-2.07`), selectable from HA.
- 0.56" module with yellow segments, 66 × 27.2 mm PCB, 4 M3 holes (Ø 3.3) at
  60 × 21.5 spacing. Wires on a right-angle pin header, turned towards the inside of
  the display: the PCB clears the right-hand SO-45 by 0.9 mm.

### ESP32 board

- **diymore ESP32-S3-DevKitC-1 N16R8**: 16 MB of flash, 8 MB of octal PSRAM
  (GPIO33-37 taken), two USB-C ports, Espressif DevKitC-1 pinout.
- **MRD076A terminal board**: 73.6 × 84.7, 20.5 mm stack height with the ESP32.
- **Mounting**: three printed clips, no screws, glued into recesses in the back
  of the shell (1.5 mm deep in a 3 mm back). Board upright, centered,
  antenna at the top. Wiring through the side terminal blocks only, with room for cables
  under the board. See `design/fusion/README.md`.
- Pins (firmware `esphome/claudemetre.yaml`), on the left-hand
  connector: GPIO4 session gauge, GPIO5 week gauge, GPIO6 TM1637 CLK, GPIO7
  TM1637 DIO, GPIO14 indicator strip.

### Power and connectors

- USB power for now, then 12 V brought down to 5 V by an ATC supply, with
  the 2-pole LP-16 connector. The 5 V arrives on the `5V` terminal: the terminal
  board has no power jack, and the ESP32's USB port is not
  accessible inside the enclosure.
- Connectors sit on removable plates, one in each side of the shell, with a blank
  plate on the unused side: changing connector means remaking a plate, not
  the shell. The cable goes through either side.
- `plaque_flanc` is the generic blank plate, which sets the common interface.
  `plaque_bossage` carries the LP-16, tilted 30° upwards.
  `plaque_bossage_fusible` carries the LP-16 and a fuse holder protecting the 12 V
  input, on parallel axes at 45°. See `design/fusion/README.md`.
- Each plate is a complete component, with its connectors and their screws. All
  of them stay in the design: show the one you want and hide the others.

### Manufacturing

- Enclosure entirely 3D printed, everything else off the shelf (voltmeters, display,
  ESP32, connectors, screws).
- Gauges: the SO-45's original black flange is kept.
- Assembly: **M3 screws and heat-set brass inserts** throughout, plus
  gluing (visor, board clips). Hardware models in the Fusion folder
  `claudometre/models/`.
- Dial font: **Barlow Condensed SemiBold**, white text inlaid in the
  black background, printed face down on the bed.
- Nameplates: **Barlow Semi Condensed Medium**, **3 mm** capitals,
  identical on all three, 40 × **8** × **1.8 mm** plates (screw axis
  4 mm from each edge). Stroke of 0.54 mm (stem) and 0.48 mm (bar): below 0.46 mm,
  the slicer loses pieces of letters. The dot in RÉINIT. is drawn separately,
  Ø 0.9. At 1.8 mm, 0.3 mm of material remains under the countersink cone: that is
  the limit.
- Display visor printed separately and glued into a groove in the faceplate,
  which prints front face down on the bed.
- Material: **the whole enclosure in PETG** (shell, faceplate, visor, side plates,
  clips, CLAUDE indicator), except the nameplates: black PLA, text in white PLA.
- Faceplate **already printed**: do not modify it any more.
- One-piece shell, back on the bed. To watch when printing: the bridges of about
  70 and 84 mm over the windows and rebates, for the fit of the plates (0.15 mm
  clearance).
- M3 screws according to stock: FHC from M3×12 up only, CHC in 6, 8, 10,
  12, 16 and up.

  | Location | Screw | Qty |
  | --- | --- | --- |
  | Faceplate to shell | FHC M3×12 | 4 |
  | Nameplates | FHC M3×12 | 6 |
  | Side plates | CHC M3×6, head half sunk | 8 |
  | LP-16 connector on `plaque_bossage` or `plaque_bossage_fusible` | FHC M3×12, into 4 M3 inserts | 4 |
  | Display PCB | CHC M3×6 | 4 |
  | SO-45 flanges | CHC M3×12 | 8 |
  | CLAUDE indicator | FHC M3×8, end of stock (the generator specifies M3×10) | 2 |

  The holes in the side plates stay blind: if they went through, a long screw
  would hit the faceplate screw at the same height.
- Wall mounting: the enclosure hangs by gravity on two protruding-head wood
  screws, 116 mm apart, through two **keyhole slots** that go through the
  back of the shell, in line with the SO-45s. Once hung, the screws are at
  mid-height of the shell. A printed template is used to mark the holes.

## 3. Software

### Principles

- **ESPHome** on the ESP32, **ESP-IDF** framework.
- Usage values exposed as sensors in **Home Assistant**, reusable
  elsewhere (automations, dashboards).
- The numbers cover **all usage on the account**: TUI, `claude -p` launched by
  other tools, Hermes (direct API with the Claude Code login), claude.ai.
- Source: the **OAuth usage endpoint**, read by a script launched by hooks
  (Claude Code, Hermes), no daemon, with the token read-only. See
  [software.md](software.md) and [data-source.md](data-source.md).

### Network

- **WiFi only** (no Bluetooth, unlike Clawdmeter).
- WSL2 in `mirrored` mode: WSL reaches the LAN, Home Assistant and the ESP32 directly.
- WSL pushes to HA by webhook; HA turns it into template sensors; the device
  reads them through the `homeassistant` platform. The object therefore depends on HA.

### ESPHome / Home Assistant entities

| Entity | Type | Unit |
| --- | --- | --- |
| Session usage | sensor | % |
| Week usage | sensor | % |
| Session reset | sensor (timestamp) | — |
| Week reset | sensor (timestamp) | — |
| Last measurement | sensor (timestamp) | — |
| Claude active | binary_sensor | — |
| Claude waiting for an answer (`claude_needattention`) | binary_sensor | — |
| Gauge calibration | number × 5 per gauge | % PWM |
| Display brightness | number | 0-7 |
| Display mode | select | `Heure de reset` (reset time), `Temps restant` (time remaining) |
| Indicator brightness | number | % |

Missing window = unknown value, **not** 0 %.

### Device behavior

- Time: `time: homeassistant`, `Europe/Paris` time zone.
- Startup: needles to 100 % then to 0 %, indicator amber then red. On the display,
  a line runs around and grows until it closes the outline, then `--.--` until the
  first data arrives.
- Needles glide to the new value (full scale in ≈ 2.5 s), for
  a mechanical feel.
- Unknown usage: needle at rest.
- Reset time passed: needle to 0 without waiting for the PC, and `--.--` on
  the display for the session. If the reset happens while the object is running, the
  last value first blinks for 5 s at full brightness.
- Dot between the 2nd and 3rd digits, which blinks when a time or a time
  remaining is shown.
- Time remaining: `-H.MM`, rounded up to the next minute (`-0.01` until the reset,
  never `-0.00`). The selected mode survives a restart.

## 4. Open questions

- [ ] Hang the object on the board, after measuring the head and shank of the
      screws (`accroche_tete_d`, `accroche_tige_d`, 8 and 4 mm for now); the template
      is to be printed afterwards, since its holes follow these values.
- [ ] 12 V power: ATC supply and LP-16. Confirm the M3 mounting on the part
      received before printing `plaque_bossage`.
- [ ] `plaque_bossage_fusible`: test 3MF to print; use it to confirm the fuse holder's
      thread, the nut and how well the tube holds.
- [ ] Wiring diagram (`design/cablage/index.html`) to rework for the terminal
      board: it still describes wires soldered to J1.
- [ ] Lovelace card to realign with the object: indicator (52 × 18 frame, 32 × 11 window),
      shape of the dials and the display, which has a dot and not a colon
      (`card_assets.py`, then redeploy to HA).
- [ ] Display modeled with the colon from the STEP (Fusion design, Blender renders,
      3D model): the object's module only has dots.
- [ ] Lovelace card: it always shows the reset time, without following the mode of
      the object's display.
- [ ] Behavior on the object when data is stale or WiFi is lost: nothing
      is shown for now (the Lovelace card dims the display).
- [ ] Night mode (7-seg brightness by time of day, controllable from HA)?
- [ ] Dedicated login for Hermes, so it no longer shares Claude Code's?
- [ ] Measure `jauge_appui` in `claudometre` (height of the top of the posts, 4 mm
      set by eye): no effect on the object, only on the model.
