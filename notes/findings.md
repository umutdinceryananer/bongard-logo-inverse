# Findings

The basket for the presentation: every finding so far, in slide-ready form. Each entry has the finding in one sentence, the numbers behind it, the figure if there is one, the script that produced it, and the decision it feeds. Details are in `data_layout.md`, `program_statistics.md` and `decisions.md`; zero-shot numbers in `outputs/logs/zeroshot_summary.md`. Pick from here; nothing is pre-selected.

## Data

### F1. The dataset is 12,000 problems, 168,000 images, every image paired with its program

- 3,600 free-form (ff), 4,000 basic (bd), 4,400 abstract (hd) problems; 7 positive and 7 negative images each; 512 x 512, grayscale.
- Programs: `<type>/<type>_action_programs.json`, nested problem > side > image > shape > action strings; all 1,270,887 action strings follow one two-form grammar.
- Script: `01_inspect.py`. Feeds: scope of the task.

### F2. A program says what to draw, not where: position, rotation and scale are not stored

- The painter samples them at drawing time; re-drawing a program gives the same shape at a different pose.
- Figure: `outputs/figures/02_render_pair.png` (dataset image next to its program re-drawn).
- Script: `02_render_pair.py`. Feeds: Decision 1 (pose is not predicted), Decision 8 (render-level comparison must be pose-free).

### F3. The published renderer reproduces bd and hd images but not ff images

- In ff the stamp density and the line-to-arc proportions differ from the published painter settings; the images were drawn with an earlier version of the generator.
- Figure: `outputs/figures/02_render_pair.png` (rows 1 and 2).
- Script: `02_render_pair.py`. Feeds: Decision 2 (rendered training images would need this settled first); parked.

### F4. Half of ff and 84% of bd images contain two shapes; the shapes touch or overlap in at most 3.9% of them

- Two-shape images: ff 25,200 of 50,400; bd 47,222 of 56,000; hd none. The two shapes are stored as separate lists with no relative placement.
- Measured on all 72,422 two-shape images: single ink group (touching, overlapping, or within about 24 px) in 3.93% (ff 2.54%, bd 4.67%); one-shape control fragments in 0.17%.
- Figure (check only): `outputs/figures/1b_touching_examples.png`.
- Scripts: `01_inspect.py`, `check_1b_shape_overlap.py`. Feeds: Decision 1b, task difficulty.

### F5. The official test_ff split is a length-extrapolation test: every test program is longer than every training program

- ff train and val images have 4 to 8 actions; all 8,400 test_ff images have 9.
- Official splits: train 9,300, val 900, test_ff 600, test_bd 480, test_hd_comb 400, test_hd_novel 320 problems; disjoint; cover all 12,000.
- Share of shape programs in a split that also occur in train: val 56%, test_bd 69%, test_hd_comb 63%, test_hd_novel 61%, test_ff 11% (a property of the splits, by design of the benchmark).
- All 627 one-shape bd problems are in train; val and test_bd contain only two-shape bd problems. A bd evaluation therefore measures two-shape images only.
- Figure: `outputs/figures/03_ff_length_gap.png`.
- Scripts: `01_inspect.py`, `03_stats.py`. Feeds: Decision 8 (report per split; test_ff measures one skill).

## Programs

### F6. Programs are short: at most 18 actions per image, 9 per shape, 465 characters

- Median actions per image: ff 7, bd 10, hd 6. Median characters: ff 189, bd 256, hd 143.
- Figure: `outputs/figures/03_length.png`.
- Script: `03_stats.py`. Feeds: Decision 7 (output length budget), Decision 3.

### F7. ff uses all ten stroke types evenly; bd and hd are 55% plain lines

- Distinct full action strings: ff 100, bd 3,054, hd 3,049, all types 3,101; 17 strings cover 90% of ff, about 1,300 cover 90% of bd or hd.
- Figure: `outputs/figures/03_vocabulary.png`.
- Script: `03_stats.py`. Feeds: Decision 3, Decision 6 (style imbalance).

### F8. Every numeric field takes values from a finite set; the arc radius is the same in all 300,247 arcs

- Distinct values over the whole dataset: line length 157, arc radius 1 (0.500), arc angle 45, turn 278. In ff three of the four fields are constants.
- Rule: a field can be dropped from the output without loss only if it takes one value in the whole dataset; the arc radius is the only such field.
- Figure: `outputs/figures/03_numeric_values.png`.
- Script: `03_stats.py`. Feeds: Decisions 1a and 5.

### F9. At a 224 px input, the smallest hd shapes lose their stroke style unless the image is cropped to the ink

- One measure throughout: the longer side of the ink bounding box. Among hd images with fine styles it is median 164 px at 512 (p10 118, p90 222); downscaled to 224 the median shape spans 72 px, the smallest 10% at most 52 px, the smallest examples 29 px. In the smallest cases the triangle, circle and square stamps become blobs; cropped to the ink with a 10% margin they stay legible. The median example stays readable without cropping but small.
- Cropping loses no information, because the program contains no position and no size.
- Fine styles (zigzag, circle, square, triangle) are 35% of hd actions, 33% of bd, 80% of ff, so this is not an hd-only detail.
- Figure: `outputs/figures/2c_resolution.png` (three smallest examples, worst case on purpose, plus the median example; original 512 | 224 no crop | cropped then 224, at true pixel size).
- Script: `fig_2c_resolution.py`. Feeds: Decision 2c.

## Zero-shot

### F10. Reversing the direction of a shape is a valid rewrite only for shapes made of lines; reversing an arc mirrors it

- In the painter's language an arc has a positive radius with its centre on the left of the heading, so negating the arc angle draws the mirror image of the arc, not the arc traced backwards. A reversed description of a shape with arcs is a different drawing.
- Checked numerically on 300 dataset shapes: all-line reversals and every restart of a closed shape coincide with the original after rotation and translation (residual below 1% of the path length); reversals with arcs do not (residual up to 3.7 path lengths).
- Effect on scoring: the best-alignment scores changed for 10 of the first 58 zero-shot answers; 4 answers are still matched through an all-line reversal, which is a pure rotation of the drawing.
- Figure: `outputs/figures/zeroshot_examples.png`, row 1 (edit distance 0, the drawing rotated, verified as a rotation).
- Script: `04_zeroshot.py`, `score()`. Feeds: Decision 8b (program-level scoring); the one-to-many property of programs (Nie et al., 2020).

### F11. An untrained VLM reads what is drawn but not how much: valid output 100%, action count 83%, style 69%, numbers 29%, exact programs 3%

- gemini-3.8-flash, condition K2 (grammar plus three same-type image-program pairs), 150 val images (ff 30 one-shape, 30 two-shape, bd 60, hd 30, one per problem), native 512 px, seed 0, thinking level "low", scored with the corrected best-alignment rule.
- Style accuracy (best alignment) against the majority baseline of the type: ff one shape 62 (baseline 21), ff two shapes 67 (21), bd 63 (68), hd 88 (65). ff and hd pass baseline + 10; bd does not.
- Numbers (lengths, arc angles, turns), exact: ff one shape 49, ff two shapes 62, bd 8, hd 21. The ff numbers are inflated: line length and arc angle are constants in ff, so the model writes them without reading them. The bd and hd values are the real measure.
- Exact programs: 5 of 150. Action count within 1: 83% (bd 67%).
- Reading: format, stroke count and most stroke styles are read; lengths and angles are not. The model sees the structure, not the measurement.
- Table: `outputs/logs/zeroshot_summary.md`. Figure: `outputs/figures/zeroshot_examples.png`.
- Script: `04_zeroshot.py`. Feeds: Decision 3a (model family), Decision 5 (the numbers are the missing part), the C-G paper's bottleneck claim (open question).
- Pending: K1 and K3 (text-only examples, other-type examples), gemini-2.5-flash, the memorization check.

### F12. At full input resolution, cropping to the ink adds nothing: +1.7 points on style over 150 images, hd drops 9

- Same 150 images, gemini-3.8-flash, K2, native 512 px against cropped to the ink (10% margin, resized back to 512; example images cropped too). Gemini tiles images above 384 px and does not downscale a 512 px image.
- Style accuracy, best alignment, 512 to cropped: ff one shape 62.0 to 67.6, ff two shapes 66.9 to 73.8, bd 63.3 to 65.9, hd 87.8 to 78.6, all 68.7 to 70.4. Exact match 3.3 to 4.7. Below the 10-point rule.
- Reading: the crop matters when the model downscales the image (F9), not when it sees the full resolution. Consistent with D2c.
- Logs: `outputs/logs/zeroshot_gemini-3.8-flash_K2.jsonl`, `outputs/logs/zeroshot_gemini-3.8-flash_K2_crop.jsonl`. Feeds: Decision 2c (confirmed), Decision 3b (remaining runs at 512 px).

## Decisions taken

### D1a. Output format: the dataset strings with the arc radius removed

- Lossless (the radius is constant), shorter output, dataset format recovered by inserting `0.500`. Alternatives: raw strings, English descriptions.
- Evidence: F8. Details: `decisions.md`, 1a.

### D1b. The shape boundary stays in the output

- The boundary is a drawing instruction (lift the pen); without it the same actions draw one connected shape, a different picture.
- Figure: `outputs/figures/1b_shape_boundary.png` (dataset image, boundary kept, boundary dropped).
- Script: `fig_1b_shape_boundary.py`. Evidence: F4. Details: `decisions.md`, 1b.

### D1c. The two shapes are written in a fixed order: fewer actions first, ties alphabetical

- The dataset order is arbitrary: the same pair of shapes recurs in other problems in both orders (ff 24%, bd 26% of recurring pairs). The renderer does not use the order; the C-G paper's 20-point "sequence permutation" drop concerns stroke order inside a program, which stays untouched.
- Script: `check_1c_shape_order.py`. Details: `decisions.md`, 1c.

### D2a. Training uses the dataset images only; own drawings are a fallback

- 168,000 images are available without extra work. Pose variation is already there where it matters most: in ff the 7 positives of every problem are one program drawn at 7 poses (all 3,600 problems); in bd 1,125 of 4,000 problems; in hd every positive image has its own program. Drawing ff images is blocked by the renderer mismatch (F3). Revisit if the first training run shows the model does not learn enough.
- Details: `decisions.md`, 2a.

### D2b. Pipeline trial with ff; target model is one model over all three types

- ff is the cleanest case (100 action strings, constant length and arc angle) to show the pipeline works; the trial does not show the model works on bd and hd (157 length and 278 turn values). The target model covers all three types because C-G tests all three; one shared LOGO language is learned once, not three times. The overshadowing risk is watched per type and handled by balancing (Decision 6) if it appears.
- Details: `decisions.md`, 2b.

### D2c. Resolution depends on the model; at 224 px input the image is cropped to the ink

- Input 448 px or more: image as it is. Input 224 px: square crop around the ink with a 10% proportional margin, same at test time. Cropping removes nothing the model predicts (no pose in the program) and keeps the relative placement of two shapes.
- Checked at full resolution on 150 images (F12): the crop adds 1.7 points on style and hurts hd by 9, below the 10-point rule. The remaining zero-shot runs use the native 512 px images.
- Evidence: F9, F12. Details: `decisions.md`, 2c.

### D3a. Model family: fine-tune a small VLM, provisional until the full zero-shot run

- Rule fixed before the run: train from scratch (b) only if the ready-made VLM cannot read the drawings. It can (F11): two of three types pass the style baseline + 10, the action count is right within 1 in 83%.
- What fine-tuning has to add is the measurement (lengths, angles, turns), which the untrained model does not read. The main reason for (b), that pretrained vision would not read black-and-white line drawings, did not hold.
- Size and method follow from the hardware: no local GPU, free Colab T4, so a 2B model, 4-bit, LoRA. (b) stays as the fallback if fine-tuning does not learn the numbers.
- Evidence: F11, F12. Details: `decisions.md`, 3a. Final verdict after K1, K3, gemini-2.5-flash and the memorization check.

## Open questions

- Is C-G sensitive to the order of the two shape blocks? To be tested at evaluation level 3 with ground-truth programs in both orders.
- Does a higher thinking level change the zero-shot result? At "low" the model still thinks in about half of the calls (up to about 2,000 tokens). A "medium" comparison was not run.
- Does the VLM memorize dataset programs? 20 perturbed dataset programs (one action changed, not in the dataset) are drawn and ready; the run is pending. If accuracy on them is far below the dataset images, memorization is suspected.
- Is gemini-2.5-flash still reachable through the API? If not, the comparison with the paper's pixel baseline is lost and only the current model is reported.
- Does "reads the structure, not the measurement" fit the paper's claim that the bottleneck is representational? To discuss with Mohit.
