# Data layout

How Bongard-LOGO is stored on disk and in the program files. Numbers come from `scripts/01_inspect.py` (full report in `outputs/logs/01_inspect.txt`, not tracked). Statements about how images were drawn come from the `bongard` 0.0.2 source and from NVlabs/Bongard-LOGO at commit `9df7c78` (2022-03-06); the file is named where it matters.

## Source

- `data/raw/ShapeBongard_V2.zip`, 1,762,748,636 bytes, SHA-256 `8c5542ac7b9ce8a6a14d157a0656dbde9da5b7843424eade4bd653759d9a27d0`, from the Google Drive link in the official README (`scripts/00_download.py`).
- The zip has 372,049 file entries: 168,004 data files, 204,026 `__MACOSX/` entries and 19 `.DS_Store` files. The macOS metadata is not extracted.

## Layout

```
data/ShapeBongard_V2/
  ShapeBongard_V2_split.json                 0.4 MiB   problem ids per split
  ff/ff_action_programs.json                10.2 MiB   3,600 problems (free-form)
  ff/images/<problem_id>/{1,0}/{0..6}.png
  bd/bd_action_programs.json                15.7 MiB   4,000 problems (basic)
  bd/images/<problem_id>/{1,0}/{0..6}.png
  hd/hd_action_programs.json                 9.8 MiB   4,400 problems (abstract)
  hd/images/<problem_id>/{1,0}/{0..6}.png
```

- Folder `1` holds the 7 positive images of a problem, folder `0` the 7 negative images.
- All 12,000 problems have exactly `0.png` to `6.png` in both folders: 168,000 images.

## Images

Checked on 600 images, 200 random per type (seed 0).

- 512 x 512, stored as RGB with R = G = B in every sampled image, so grayscale in practice.
- White background (255), black strokes, anti-aliased: 172 to 256 distinct gray levels per image.
- Drawing extent, bounding box of pixels below 128, median width x height: ff 169 x 170, bd 274 x 288, hd 135 x 139. Largest side seen: 459.
- Drawing pipeline (`bongard_painter.py`): Python turtle on an 800 x 800 Tk canvas, exported to PostScript, rasterized by PIL (Ghostscript) and resized to 512 x 512.

## Programs

`<type>/<type>_action_programs.json` is a dict keyed by problem id. For all three types the keys are exactly the image folder names.

```
problem_id -> [side 0, side 1]            side 0 = positive = folder 1, side 1 = negative = folder 0
side       -> list of 7 images            list index i = file i.png
image      -> list of shapes              1 or 2 shapes
shape      -> list of action strings      1 to 9 actions
```

Evidence for the side-to-folder mapping:

- `BongardProblem.import_from_action_string_list` reads side 0 as positive.
- The painter writes positives to folder `1`.
- The official loader `Bongard-LOGO_Baselines/datasets/shape_program.py` pairs side 0 with `1/*.png`.
- Checked by eye on `ff_nact4_0000` image 0. The two sides differ only in the stroke style of the last action, and the two images differ in the same way.
- Consistent in all five rows of `outputs/figures/02_render_pair.png`. In the bd, bd and hd rows the program is unique among the 14 of its problem, so those rows also check that list index i is file `i.png`.

### Grammar

All 1,270,887 action strings match one of two forms, and every number has three decimals.

```
line_<style>_<length>-<turn>
arc_<style>_<radius>_<arc_angle>-<turn>
```

- `style` is one of `normal`, `zigzag`, `circle`, `square`, `triangle` for both lines and arcs. `circle`, `square` and `triangle` stamp markers along the path.
- `turn` is applied before the stroke is drawn (`BongardShapePainter.draw`). [0, 1] maps to [-180, 180] degrees. 0.5 means no turn, values above 0.5 turn left, below 0.5 turn right.
- `arc_angle`: [0, 1] maps to [-360, 360] degrees.
- `length` and `radius` are relative. The painter multiplies them by a scaling factor, one per shape.

| type | line actions | arc actions | actions per shape (min / median / max) | `normal` share |
|---|---|---|---|---|
| ff | 211,874 | 140,926 | 2 / 4 / 9 | about 20 %, the five styles are near uniform |
| bd | 460,227 | 105,082 | 1 / 6 / 9 | lines 68.0 %, arcs 64.3 % |
| hd | 298,539 | 54,239 | 1 / 6 / 9 | lines 65.7 %, arcs 60.3 % |

### Pose is not stored

A program holds no start position, heading or scale. The painter samples them each time it draws an image (`BongardProblemPainter.save_bongard_images` with `auto_position=True`):

- One shape: start point at distance up to 250 canvas units from the center, heading equal to the polar angle of that point.
- Two shapes: the first starts 125 to 250 units from the center. The second starts at least 300 units from the first, with heading within 60 degrees of the first.
- Scaling factor: one per shape, uniform in a per-type range.
- Validity: a drawing that leaves the [-360, 360] box is redrawn, up to 300 attempts.

The official generation scripts (`examples/02-bongard_logo/generate_*_problems.py`) use these settings:

| type | scaling factor range | `magnifier_effect` | `random_seed` |
|---|---|---|---|
| ff | 80 to 140 | True | 0 |
| bd | 150 to 260 | True | 0 |
| hd | 150 to 320 | True | 0 |

With `magnifier_effect` on, marker size and spacing grow with the scaling factor.

Consequence: drawing a dataset program again does not give the dataset image pixel for pixel. `scripts/02_render_pair.py` draws five programs with the official settings and puts each next to its dataset image (`outputs/figures/02_render_pair.png`):

- **Picks:** ff and bd with one and two shapes, hd with one; seed 0.
- **Same:** in all five the shapes match by eye in strokes, styles, angles and connections.
- **Different:** position, rotation and scale; in two-shape images also the placement of the two shapes.
- **Format:** the drawn images match the dataset images: 512 x 512, R = G = B, 197 to 256 gray levels.

## Two-shape images

A two-shape image is stored as a list of two shape programs. Nothing links the two:

- Their relative position, orientation and scale are not stored.
- The order of the list carries no spatial meaning.

| type | 1-shape images | 2-shape images | problems with 2-shape images |
|---|---|---|---|
| ff | 25,200 | 25,200 | 1,800 |
| bd | 8,778 | 47,222 | 3,373 |
| hd | 61,600 | 0 | 0 |

No problem mixes 1-shape and 2-shape images.

The ff problem ids encode this structure, and the rule holds for all 50,400 ff images. This matches `num_act_lsts` in `generate_ff_problems.py`.

- `ff_nact<a>`: one shape with `a` actions.
- `ff_nact<a>_<b>`: two shapes with `a` and `b` actions.

The official tokenizer (`prog_str2prog_idx` in `shape_program.py`) builds the token sequence as follows:

- **Sequence:** `start`, the actions of shape 1, `and`, the actions of shape 2, `stop`, padded to 21 tokens.
- **Action token:** each action becomes `[action, style, arg0, arg1]`.
- **Arcs:** only `arc_angle` and `turn` are kept, the radius field is dropped. Whether the radius ever differs from 0.500 is open; `03_stats.py` will check.

## Splits

`ShapeBongard_V2_split.json` maps split name to a list of problem ids. The splits are disjoint and together cover all 12,000 problems, so the split is at the problem level. "Problem name" below is the id without its trailing index.

| split | ff | bd | hd | total | notes |
|---|---|---|---|---|---|
| train | 2,700 | 3,238 | 3,362 | 9,300 | ff groups: nact4 to nact8, nact2_5, nact3_3, nact3_4, nact3_5, nact4_4 |
| val | 300 | 282 | 318 | 900 | same ff groups as train; 169 of 451 problem names also in train |
| test_ff | 600 | | | 600 | nact9 and nact4_5, both longer than any train group (9 actions against at most 8) |
| test_bd | | 480 | | 480 | 480 problem names, none in train |
| test_hd_comb | | | 400 | 400 | 20 problem names, none in train |
| test_hd_novel | | | 320 | 320 | 16 problem names, none in train |

Within a problem nothing marks support and query images. The official episode sampler (`Bongard-LOGO_Baselines/datasets/samplers.py`) shuffles the 7 + 7 images for each episode.

### Shape programs shared with train

A shape program is the list of its action strings. The last column gives the share of shape occurrences in a split whose exact program also occurs in train.

| split | shape occurrences | distinct programs | program seen in train |
|---|---|---|---|
| train | 185,654 | 65,815 | |
| val | 18,648 | 8,257 | 56.1 % |
| test_ff | 12,600 | 4,843 | 10.7 % |
| test_bd | 13,440 | 6,287 | 68.7 % |
| test_hd_comb | 5,600 | 3,048 | 62.8 % |
| test_hd_novel | 4,480 | 2,146 | 60.8 % |

Exact match undercounts repetition, since the same shape can be written from another start point or in the other direction.

## Inputs to the decisions

- **Decision 1 (task definition):** programs carry no pose, two-shape images carry no relative placement, and the order of the two shapes is arbitrary.
- **Decision 2 (images):** 512 x 512 grayscale; the median drawing spans 135 to 290 pixels depending on type.
- **Decision 8 (evaluation):**
  - Comparing a rendered program with the dataset image needs pose alignment.
  - 56 to 69 % of shape occurrences in val, test_bd and the two hd test sets have a program seen in train.
  - test_ff is at 10.7 % and has longer programs than train.
- **Open:** arc radius values (`03_stats.py`).
