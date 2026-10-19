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

## 2. Images

### 2a. Training images: decided 2026-10-18

**Options**
- (a) Only the dataset images.
- (b) Additional images drawn by us from the programs at new poses.
- (c) Both.

**Choice:** (a). Fallback: if the model does not learn enough from the dataset images, add our own drawings (b); for bd and hd the renderer reproduces the dataset images, for ff the renderer fidelity question (parked in `data_layout.md`) would have to be settled first.

**Reasons**
- 168,000 images are available with no extra work. Pose variation (position, rotation, scale) is already in the data: in ff the 7 positive images of every problem are the same program drawn at 7 poses (all 3,600 problems); in bd this holds for 1,125 of 4,000 problems; in hd never, every positive image has its own program (counted 2026-10-19). Extra drawings would add more poses, which ff already has in full.
- Drawing our own ff images is blocked by the renderer mismatch (F3); doing it only for bd and hd would skew the mix.
- Extra data is a remedy for a problem we have not observed yet; the decision can be revisited with evidence from the first training run.

**Evidence:** `data_layout.md` (7 + 7 images per problem; renderer comparison), `findings.md` F2, F3.

### 2b. Problem types in training: decided 2026-10-18

Two questions, answered separately.

**Pipeline trial (this week): ff only.** ff is the cheapest and cleanest case to show that the pipeline works: 100 distinct action strings, line length and arc angle constant, short programs. A short run on a few hundred images on the Colab T4 is enough for one type. What the trial can show is "the pipeline works", not "the model works": a model that does well on ff may struggle with the 157 length and 278 turn values of bd and hd. The presentation states this difference.

**Target model (next week): one model, all three types.** C-G tests all three types and the goal is to replace its oracle programs, so the model must cover all three. Separate models per type (c) would mean three trainings and three times the maintenance, and would be less useful for the C-G experiment; the three types share one language (LOGO), the same stroke types and the same number format, which one model learns once and three models would learn three times.

**Risk:** bd, the largest type, could overshadow ff in a joint model. This belongs to Decision 6a (balancing in training), not here. It will show up in the per-type scores (results are reported per type, Decision 8); if it does, balancing is applied.

**Evidence:** `program_statistics.md` (vocabulary and value counts per type), `findings.md` F6, F7, F8.

### 2c. Input resolution and cropping: decided 2026-10-18, conditional on the model

**Options:** feed the 512 px image as it is (the model resizes it to its input size), or crop to the ink first. Downscaling ourselves is the same as feeding it as is.

**Choice:** depends on the input size of the model chosen in Decision 3.
- Input 448 px or more: the image as it is. A 137 px shape stays about 120 px.
- Input 224 px: crop to the ink first. Square crop around the ink bounding box, margin 10% of the longer side on each side (a proportion, not a pixel count, so large and small shapes are treated alike), white padding where the crop leaves the image, then resize to the input size. The same crop is applied at test time.

**Reasons**
- Cropping loses no information, because the program contains no position and no size (Decision 1); the renderer assigns them at random. The two shapes of a two-shape image are cropped together, so their relative placement is kept.
- At 224 px without cropping, the median hd shape with fine styles spans 72 px and the smallest 10% at most 52 px; in the smallest cases the triangle, circle and square stamps and the zigzag become indistinguishable blobs, while the cropped version stays legible (`outputs/figures/2c_resolution.png`, true pixel size). The figure shows the three smallest examples of the sample (worst case, 29 px at 224) and the median example (typical case, 72 px at 224); the worst case was chosen on purpose, since the model has to work there too.
- One measure for all these numbers: the longer side of the ink bounding box. 29 px is the smallest examples, 52 px the 10th percentile, 72 px the median, all at 224.
- Fine styles (zigzag and the three stamps) are the ones at risk; plain lines are not. Fine styles make up about 35% of hd actions, 33% of bd and 80% of ff (`program_statistics.md`, section 2), so the loss would not be marginal.

**Evidence:** `scripts/fig_2c_resolution.py` (sample of 3,000 hd images with fine styles: ink box longest side p10 118, median 164, p90 222 px; 2.3% at most 100 px), `outputs/figures/2c_resolution.png`.

## 3. Model

### 3a. Model family: **open**, decided by the zero-shot test (2026-10-18)

**Options**
- (a) Fine-tune a small VLM (about 2B parameters, LoRA, 4-bit, Colab T4).
- (b) Train a small vision encoder plus program decoder from scratch, with the program vocabulary as the output vocabulary.

**Plan:** run the zero-shot test (3b) first. If the ready-made VLM cannot read the drawings even when the grammar and examples are given in the prompt, the path is (b). The test separates "cannot read the drawing" from "does not know the program language" by putting the grammar and examples in the prompt.

**Evidence so far:** F6, F7, F8 (short programs, small closed vocabulary) favour (b); the advantage of (a) is pretrained vision, whose value on black-and-white line drawings is unknown.

**Preliminary result (2026-10-19, step 3a, gemini-3.8-flash, K2, 150 val images at 512 px, scored with the corrected best-alignment rule; the crop run, K1, K3 and gemini-2.5-flash are still pending):**

| type | n | valid | action count within 1 | style, best alignment | numbers exact, best | exact match | passes baseline + 10? |
|---|---|---|---|---|---|---|---|
| ff one shape | 30 | 100 | 90 | 62 | 49 | 7 | yes (baseline 20.6) |
| ff two shapes | 30 | 100 | 97 | 67 | 62 | 7 | yes |
| bd | 60 | 100 | 67 | 63 | 8 | 0 | no (baseline 67.5) |
| hd | 30 | 100 | 97 | 88 | 21 | 3 | yes (baseline 64.9) |
| all | 150 | 100 | 83 | 69 | 29 | 3 | |

Reading: every answer is well-formed; the action count is right within 1 in 83% (bd 67%); stroke styles are read far above chance in ff and hd, but in bd the model's 63% does not beat the "normal" majority of 67%; numbers (lengths, turns, arc angles) are weak outside ff (8% in bd, 21% in hd); only 5 of 150 programs are exactly right. Under the decision rule two of three types pass, so the direction is "reads the drawings, coarsely". The final verdict waits for the full run.

**Provisional choice (2026-10-19):** (a), fine-tune a small VLM. The reason for (b), that pretrained vision would not read line drawings, did not hold; what fine-tuning must add is the measurement (lengths, angles, turns). (b) stays as the fallback if fine-tuning does not learn the numbers. Final after K1, K3, gemini-2.5-flash and the memorization check (see `findings.md`, D3a).

### 3b. Zero-shot models: decided 2026-10-18

**Choice:** two models through the Gemini API, same images, same prompts.
- `gemini-2.5-flash`: the pixel baseline of the C-G paper (Vaishnav and Tammet 2026), so the result speaks to the same model: Gemini is near chance on Bongard-LOGO from pixels; can it write the program? Comparability is the only reason to use it. Caveat: the API documentation (checked 2026-10-18) says the 2.5 models are served only to projects that used them before; whether our key can reach it is checked at the first call.
- `gemini-3.8-flash`: a current model, answering a second question: has the ability of VLMs to read line drawings changed since the paper was written with 2.5? If the two results differ, the paper's finding depends on the model generation.

Cheap, and an API key is easy to obtain.

## 4. Model size and training method: **open**

## 5. Loss: **open**

## 6. Sampling: **open**

## 7. Hyperparameters: **open**

## 8. Evaluation: **open** except 8b

### 8b. Program-level metrics, as used in the zero-shot test: decided 2026-10-18

Per answer: (1) valid output, every line matches the grammar; (2) shape count correct; (3) action count within plus or minus 1 of the truth; (4) action-level accuracy of type, style and numbers, separately, numbers both exact and within 0.02; (5) exact match of the normalized program; (6) action-level edit distance. Baselines for style accuracy: random 20%, majority class (normal) 55%.

How (4) and (6) are computed: the predicted shapes are paired with the true shapes by the assignment with the smallest total action-level Levenshtein distance (images have at most two shapes, so all assignments are tried); within each pair the actions are aligned by Levenshtein at the action level; aligned pairs are compared field by field; unaligned actions count as wrong for all three fields. This deviates from the design text, which paired shapes by the canonical order: a single missing action can change the canonical order and would then misalign every action of both shapes. Exact match (5) still compares the canonical-order strings. Implementation: `scripts/04_zeroshot.py`, `score()`.

Metric 4 has two columns (added after the pilot, 2026-10-18). "Given order" compares with the gold program as written. "Best alignment" compares with the equivalent description of each gold shape that is closest to the prediction: for a closed shape every start point in both directions, for an open shape both directions. A shape is closed if its end point, simulated with unit length, arc radius 0.5 and the turn applied before each action, lies within 5% of the path length from its start point. The reason: the pilot showed answers that contain the right actions from a different start point, which the given-order column counts as wrong although the drawing is the same (the one-to-many property of the programs). The decision rule uses the best-alignment column; the difference between the columns is reported.

Correction (2026-10-19): the reversed direction is a valid equivalent only for shapes made of lines alone. In the painter's language an arc always has a positive radius with its centre on the left of the heading, so negating an arc angle draws the mirror image of the arc, not the arc traced backwards; a reversed description of a shape with arcs is therefore a different drawing and must not be credited. Checked numerically: the stroke of each equivalent form was simulated as a polyline and fitted to the original with rotation and translation only; all-line reversals and every restarted closed shape coincide with the original (worst residual below 1% of the path length, equal to the closure gap of the shape), reversals with arcs do not (residual up to 3.7 path lengths). With the correction, the best-alignment scores changed for 10 of the first 58 answers of the 3a run; 4 answers are still matched through a reversed all-line shape, which is a pure rotation of the drawing.

Baselines for style accuracy are per type: random 20%, and the share of the majority style in the train split of that type (ff about 12%, bd and hd about 55%; computed by `summary`).

Decision rule for 3a, fixed before the full run: "cannot read" only if, in every type, style accuracy (best alignment) is below that type's majority baseline plus 10 points and action-count-within-1 accuracy is below 50%. The 10 points are about the width of the confidence interval at 150 answers (plus or minus 8).

Thinking: `thinking_level` is "low" on both models (the lowest level the API offers for them). In the pilot (18 answers, gemini-3.8-flash) the model thought in about half of the calls: 0 thought tokens in 9 answers, about 1,960 in 8, 344 and 1,305 once each. "Low" therefore does not switch thinking off. Accepted as the setting of the experiment; a comparison with "medium" is an open question, not run. The output token budget was raised from 2,048 to 8,192 after one answer was cut off, because the budget covers the thought tokens.

Rate limits: the free tier allows 20 requests per day per model (hit on 2026-10-18 after 21 calls); the full run needs about 1,000 calls and therefore the paid tier (enabled 2026-10-18).

Crop check, preliminary result on 18 images (step 2, 2026-10-18): the same 18 images, gemini-3.8-flash, K2, once at native 512 px and once cropped to the ink (decision 2c crop, resized back to 512; the example images are cropped too). Style accuracy under best alignment: all 77.3 to 83.7 (+6.4 points), ff 76.8 to 83.8, bd 58.3 to 66.7 (n=2), hd 100 to 100; exact match 5.6 to 16.7. Below the 10-point rule, but 18 images are within noise either way. The resolution decision is taken on all 150 images (step 3a: K2 at both resolutions), same rule, 10 points.

**Resolution decision (step 3a, 2026-10-19, 150 images, gemini-3.8-flash, K2, corrected scoring):** style accuracy under best alignment 512 px 68.7 against cropped 70.4 (+1.7 points); by type ff 64.5 to 70.7 (+6.2), bd 63.3 to 65.9 (+2.6), hd 87.8 to 78.6 (-9.2); exact match 3.3 to 4.7; action count within 1 83.3 to 86.7; numbers 29.4 to 33.9. The crop helps ff and bd a little and hurts hd; the overall gain is far below the 10-point rule. **The remaining runs (K1, K3, gemini-2.5-flash) use the native 512 px images, no crop.** The crop run is kept as a secondary result (`zeroshot_gemini-3.8-flash_K2_crop.jsonl`).

## Open questions

- **Does a higher thinking level change the zero-shot result?** The zero-shot test runs at `thinking_level` "low", under which the model still thinks in about half of the calls (up to about 2,000 tokens). A "medium" comparison was not run.
- **Is C-G sensitive to the order of the two shape blocks?** The paper only tested shuffling the strokes inside a program. To test at evaluation level 3: run C-G on ground-truth programs twice, once in the dataset order and once in the fixed order of decision 1c, on the same problems, and compare accuracy. If the difference is large, the fixed order should be reconsidered or the dataset order restored before the C-G step (the mapping is one-to-one, so restoring is possible when the original order is known).
