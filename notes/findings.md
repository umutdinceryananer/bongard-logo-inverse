# Findings

The basket for the presentation: every finding so far, in slide-ready form. Each entry has the finding in one sentence, the numbers behind it, the figure if there is one, the script that produced it, and the decision it feeds. Details are in `data_layout.md`, `program_statistics.md` and `decisions.md`. Pick from here; nothing is pre-selected.

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

- 168,000 images with 7 poses per program already give the variation that extra drawings would add; drawing ff images is blocked by the renderer mismatch (F3). Revisit if the first training run shows the model does not learn enough.
- Details: `decisions.md`, 2a.

### D2b. Pipeline trial with ff; target model is one model over all three types

- ff is the cleanest case (100 action strings, constant length and arc angle) to show the pipeline works; the trial does not show the model works on bd and hd (157 length and 278 turn values). The target model covers all three types because C-G tests all three; one shared LOGO language is learned once, not three times. The overshadowing risk is watched per type and handled by balancing (Decision 6) if it appears.
- Details: `decisions.md`, 2b.

## Open questions

- Is C-G sensitive to the order of the two shape blocks? To be tested at evaluation level 3 with ground-truth programs in both orders.
