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

### 1b. Two-shape images: keep the shape boundary in the output? **open**

### 1c. Two-shape images: which shape comes first? **open**

## 2. Images: **open**

## 3. Model: **open**

## 4. Model size and training method: **open**

## 5. Loss: **open**

## 6. Sampling: **open**

## 7. Hyperparameters: **open**

## 8. Evaluation: **open**
