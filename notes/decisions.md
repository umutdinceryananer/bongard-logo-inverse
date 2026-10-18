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

**Open check:** whether the two shapes ever overlap or touch in the dataset images. The painter only enforces a minimum distance between the two start points (300 canvas units), not between the drawn shapes.

### 1c. Two-shape images: which shape comes first? **open**

## 2. Images: **open**

## 3. Model: **open**

## 4. Model size and training method: **open**

## 5. Loss: **open**

## 6. Sampling: **open**

## 7. Hyperparameters: **open**

## 8. Evaluation: **open**
