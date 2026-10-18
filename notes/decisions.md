# Decisions

The eight decisions of the week of 14 to 20 October 2026 (see README). Each entry gives the options considered, the choice, the reason and the evidence. Sub-decisions are numbered 1a, 1b, ... Open items are marked **open**.

## 1. Task definition

Fixed by the data, not decided: the input is one 512 x 512 grayscale image; the output is the action program; pose (position, rotation, scale) is not predicted, since the dataset stores no pose and the concepts are defined to be pose-invariant.

### 1a. Output format: decided 2026-10-18

**Options**
- (a) The dataset's raw action strings, e.g. `arc_zigzag_0.500_0.625-0.500`.
- (b) The raw strings with the arc radius field removed, e.g. `arc_zigzag_0.625-0.500`; line strings unchanged.
- (c) Step-by-step English descriptions of the drawing actions.

**Choice:** (b).

**Reasons**
- The arc radius is 0.500 in all 300,247 arcs of the dataset, so removing it loses nothing, and the dataset format is recovered exactly by inserting `0.500` back. Programs can still be fed to the C-G pipeline in their original form.
- Every other field varies in bd and hd (line length 157 values, arc angle 45, turn 278), so nothing else can be removed without loss.
- The output stays shorter than (a) and keeps the dataset grammar, so program-level comparison with the ground truth is direct and rendering uses the existing parser after the radius is re-inserted.
- (c) is 3 to 5 times longer, needs a free-text parser before scoring or rendering, and adds error surface without adding information.

**Evidence:** `program_statistics.md`, section 3, "Which fields can be dropped from the output" (counts over all 1,270,887 actions).

**Format after the decision**
```
line_<style>_<length>-<turn>
arc_<style>_<arc_angle>-<turn>
```

### 1b. Two-shape images: keep the shape boundary in the output? Decided 2026-10-18

**Options**
- (a) Keep the boundary: the two shapes are written as two groups with a separator between them.
- (b) Drop the boundary: all actions of the image in one flat list.

**Choice:** (a). The separator character is fixed together with the model's tokenizer (Decision 3).

**Reasons**
- The boundary is a drawing instruction: the painter lifts the pen and starts the second shape at a new place. Without it the same actions draw one connected shape, which is a different picture (`outputs/figures/1b_shape_boundary.png`: the triangle and the C of `ff_nact3_3_0185` merge; the dagger and the leaf of `bd_thin_symm_dagger-open_symm_arc60_0000` overlap).
- With the boundary the dataset format is recovered exactly, so the programs can be fed to the C-G pipeline unchanged and rendered for the render-level evaluation. Without it the conversion back is lossy.
- The cost is one extra token per two-shape image, and the two separate parts are visible in the image.

**Evidence:** `scripts/fig_1b_shape_boundary.py`, `outputs/figures/1b_shape_boundary.png`; two-shape images are 50% of ff and 84% of bd, none in hd (`data_layout.md`).

**Check (2026-10-18): do the two shapes ever touch or overlap?** Yes, in a small minority. The painter only enforces a minimum distance between the two start points (300 canvas units), not between the drawn shapes. Measured on all 72,422 two-shape images (`scripts/check_1b_shape_overlap.py`): the ink forms a single group in 3.93% of them (ff 2.54%, bd 4.67%), which means the shapes touch, overlap, or lie within about 24 pixels of each other; in the remaining 96% the two shapes are clearly apart. Control: one-shape images fall apart into two groups in only 0.17% of cases, so the method itself is reliable. Examples in `outputs/figures/1b_touching_examples.png` (a check figure, not for slides) show mostly real overlaps and a few near misses. The decision stands; the touching cases are a harder minority for the model, not a reason to change the output format.

### 1c. Two-shape images: which shape comes first? Decided 2026-10-18

**Options**
- (a) Keep the dataset order as the training target and accept both orders when scoring.
- (b) A fixed order derived from the program text, applied to the training targets and to both sides before scoring.
- (c) An order derived from the image (for example left shape first). Needs each program shape matched to a drawn shape, for which there is no label; too much work for no gain.

**Choice:** (b), with the rule: the shape with fewer actions first; if both have the same number of actions, the one whose string sorts first alphabetically.

**Reasons, three pieces of evidence**
- The dataset order is arbitrary. The same pair of shapes (stroke style ignored) recurs in other problems in both orders: ff 321 of 1,321 recurring pairs (24%), bd 400 of 1,522 (26%). Within one problem the order is fixed only because the images come from the same generation; in bd it follows the concept name X-Y, and no name exists as Y-X. The only partial rule is in ff, where the first shape is never longer than the second; in the 8,400 ff images with two equal-length shapes there is no rule at all.
- The renderer does not use the order for the shape content. Each shape is drawn from its own randomly sampled position, orientation and scale, so changing the order changes nothing about the shapes; in the render-level evaluation the poses are fixed per shape by us.
- The 20-point drop in the C-G paper under "sequence permutation" (FF 78.1 to 58.0, BD 68.8 to 64.2) concerns the order of the strokes inside the query program. The fixed order leaves the strokes of each shape untouched; only the two shape blocks may swap. The sensitivity of C-G to the order of the shape blocks has not been tested (see Open questions).

(a) would also work; models cope with two-way targets, only more slowly. (b) is simpler and removes the ambiguity. The chosen rule coincides with the dataset order in all 16,800 ff images with unequal shapes and in 57% of bd two-shape images.

**Evidence:** `scripts/check_1c_shape_order.py` (report in `outputs/logs/1c_shape_order.txt`); Vaishnav and Tammet 2026, section 5.5.

## 2. Images: **open**

## 3. Model: **open**

## 4. Model size and training method: **open**

## 5. Loss: **open**

## 6. Sampling: **open**

## 7. Hyperparameters: **open**

## 8. Evaluation: **open**

## Open questions

- **Is C-G sensitive to the order of the two shape blocks?** The paper only tested shuffling the strokes inside a program. To test at evaluation level 3: run C-G on ground-truth programs twice, once in the dataset order and once in the fixed order of decision 1c, on the same problems, and compare accuracy. If the difference is large, the fixed order should be reconsidered or the dataset order restored before the C-G step (the mapping is one-to-one, so restoring is possible when the original order is known).
