# Program statistics

What the model has to produce. Numbers from `scripts/03_stats.py` over all 168,000 images and 1,270,887 actions (full report in `outputs/logs/03_stats.txt`, not tracked). Each figure carries one finding.

## 1. Length (`outputs/figures/03_length.png`)

Finding: programs are short. One image has at most 18 actions, one shape at most 9.

| type | actions per image (min / median / p95 / max) | actions per shape (median / max) | characters per program (median / max) |
|---|---|---|---|
| ff | 4 / 7 / 9 / 9 | 4 / 9 | 189 / 266 |
| bd | 1 / 10 / 15 / 18 | 6 / 9 | 256 / 465 |
| hd | 1 / 6 / 8 / 9 | 6 / 9 | 143 / 240 |

By split, actions per image (median / p95 / max): ff train 7 / 8 / 8, val 7 / 8 / 8, test_ff 9 / 9 / 9; bd train 10 / 15 / 18, val 11 / 15 / 18, test_bd 11 / 16 / 18; hd train 6 / 8 / 9, val 6 / 8 / 9, test_hd_comb 6 / 8 / 9, test_hd_novel 7 / 9 / 9.

## 2. Vocabulary (`outputs/figures/03_vocabulary.png`)

Finding: ff uses the ten type x style combinations almost uniformly; bd and hd are dominated by plain lines.

| share of actions (%) | ff | bd | hd |
|---|---|---|---|
| line normal | 11.8 | 55.3 | 55.6 |
| line zigzag / circle / triangle / square | 12.2 / 11.9 / 11.7 / 12.4 | 6.3 / 7.2 / 6.4 / 6.1 | 8.7 / 7.3 / 6.7 / 6.4 |
| arc normal | 7.8 | 12.0 | 9.3 |
| arc zigzag / circle / triangle / square | 8.0 / 7.8 / 8.1 / 8.3 | 1.6 / 1.8 / 1.6 / 1.5 | 1.7 / 1.5 / 1.4 / 1.4 |

Distinct full action strings (type, style and numbers together): ff 100, bd 3,054, hd 3,049, all types 3,101. Strings needed to cover 90% of occurrences: ff 17, bd 1,364, hd 1,300, all 1,145.

## 3. Numeric values (`outputs/figures/03_numeric_values.png`)

Finding: every numeric field takes values from a finite set, not from a continuum. In ff three of the four fields are constants.

| field | ff | bd | hd |
|---|---|---|---|
| line length | 1 value (1.000) | 157 values, 57 cover 90% | 157 values, 58 cover 90% |
| arc radius | 1 value (0.500) | 1 value (0.500) | 1 value (0.500) |
| arc angle | 1 value (0.625 = 90 degrees) | 45 values, 15 cover 90% | 45 values, 11 cover 90% |
| turn | 11 values, 3 cover 98% (0.500, 0.750, 0.833) | 278 values, 85 cover 90% | 278 values, 93 cover 90% |

The most frequent values in bd and hd: line length 0.500 (16%), then 0.400, 0.200, 1.000, 0.300; arc angle 0.625 (29-31%), 0.583, 0.667, 0.648, 0.750; turn 0.500 (21-23%), 0.750 (16-18%).

The arc radius is 0.500 in all 300,247 arcs. This closes the open question in `data_layout.md`.

### Which fields can be dropped from the output

Rule: a field can be left out of the model's output without loss only if it takes one value in the whole dataset. Distinct values per field over all 1,270,887 actions:

| field | ff | bd | hd | whole dataset |
|---|---|---|---|---|
| action type (line / arc) | 2 | 2 | 2 | 2 |
| style | 5 | 5 | 5 | 5 |
| line length | 1 | 157 | 157 | 157 |
| arc radius | 1 | 1 | 1 | **1** (0.500 in all 300,247 arcs) |
| arc angle | 1 | 45 | 45 | 45 |
| turn | 11 | 278 | 278 | 278 |

Only the arc radius is constant over the whole dataset, so it is the only field that can be dropped without loss. Line length and arc angle are constant in ff only; they vary in bd and hd and must stay.

## 4. Free-form length gap (`outputs/figures/03_ff_length_gap.png`)

Finding: every train and val ff image has 4 to 8 actions; every test_ff image has 9. All 8,400 test_ff images are longer than the longest training image.

| group | split | actions per image | actions per shape |
|---|---|---|---|
| nact4, nact5, nact6, nact7, nact8 | train, val | 4, 5, 6, 7, 8 | same |
| nact3_3, nact2_5, nact3_4, nact3_5, nact4_4 | train, val | 6, 7, 7, 8, 8 | 3; 2 and 5; 3 and 4; 3 and 5; 4 |
| nact9 | test_ff | 9 | 9 |
| nact4_5 | test_ff | 9 | 4 and 5 |

Train and val have the same ten groups in the same proportions (3,780 and 420 images per group).

## Inputs to the decisions

- **Decision 1 (output format):** the arc radius field carries no information and can be left out of the output. In ff the whole program is a sequence over 100 possible action strings. In bd and hd a string is type + style + two numbers, each number from a set of at most 278 values.
- **Decision 5 (loss):** the numbers are discrete, so predicting them as tokens with cross-entropy is a natural fit; a regression loss is not needed for the dataset values.
- **Decision 7 (hyperparameters):** at most 18 actions and 465 characters per program; the token budget for the output is small. The exact token count depends on the tokenizer of the chosen model.
- **Decision 8 (evaluation):** test_ff is a length-extrapolation test (train at most 8 actions, test 9). test_hd_novel programs are slightly longer than training ones (median 7 against 6).
