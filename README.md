# bongard-logo-inverse

Inferring LOGO action programs from Bongard-LOGO images.

## Why

Vaishnav and Tammet (CoNLL 2026) show that text-only language models can solve many Bongard-LOGO problems when each image is replaced by the LOGO action program that drew it (the C-G paradigm). The programs come from the dataset, so the result is an upper bound. From the paper's limitations:

> in realistic settings such programs would need to be inferred from pixels via inverse graphics or symbolic detectors.

This repository works on that missing step. Input is one Bongard-LOGO image, output is the action program that draws it.

## Status

Week of 14 to 20 October 2026. The goal for this week is a set of design decisions with evidence, not a trained model. Each decision is recorded in `notes/decisions.md` with the options considered, the choice, the reason and the evidence behind it.

Decisions in scope

1. Task definition (input, output format, two-shape images)
2. Images (dataset images, rendered images, or both; which problem types, which resolution)
3. Model (fine-tune a small VLM or train a small encoder-decoder from scratch)
4. Model size and training method (full fine-tuning or LoRA)
5. Loss (token cross-entropy and alternatives)
6. Sampling (training-time balancing, inference-time decoding, render-and-compare)
7. Hyperparameters
8. Evaluation (program level, render level, task level)

## Data

Bongard-LOGO (Nie et al., 2020). 12,000 problems, 3,600 free-form, 4,000 basic, 4,400 abstract. Each image is paired with a ground-truth action program. Images and programs are downloaded from the links in the official repository, NVlabs/Bongard-LOGO (MIT license). The `data/` directory is not tracked by git.

The official `bongard` package renders programs back to images with Python turtle. On a headless machine run scripts under `xvfb-run`.

## Layout

```
README.md
data/                  downloaded dataset, not tracked
scripts/
  01_inspect.py        data layout, counts, resolution, program storage
  02_render_pair.py    render a program and place it next to the original image
  03_stats.py          program length, stroke types, numeric values, FF length gap
  04_zeroshot.py       ask a VLM through an API to write programs, render, compare
notebooks/
  train_colab.ipynb    small fine-tuning run on Colab (T4)
outputs/
  figures/             plots and side-by-side images
  logs/                zero-shot outputs, training loss
notes/
  decision_log.md     one line per day, decision, evidence, open question
  data_layout.md       data layout notes
  decisions.md          the eight decisions
```

Scripts are numbered in the order they are run. Each script starts with a docstring stating the question it answers, its input, its output and the decision it feeds.

## Setup

```
python -m venv .venv
pip install --no-deps bongard==0.0.2
pip install -r requirements.txt
```

`bongard` 0.0.2 pins `pandas==1.0.5`, which does not build on current Python (tested on 3.14). The renderer does not use pandas, so the package is installed without its dependencies and `requirements.txt` supplies current versions.

Scripts that draw programs (`02_render_pair.py` onwards) also need Ghostscript, which PIL uses to rasterize the painter's PostScript output: `sudo apt install -y xvfb ghostscript` on Linux, `brew install ghostscript` on macOS, and on Windows the 64-bit installer from the official releases (github.com/ArtifexSoftware/ghostpdl-downloads). The Windows installer does not add Ghostscript to PATH; the scripts look in `C:\Program Files\gs`. `bongard` 0.0.2 predates Pillow 11, whose EPS loading breaks the painter's PNG step; `02_render_pair.py` patches that step, see `restore_rgb_eps()`.

Download the dataset into `data/` following the official repository. Then

```
xvfb-run python scripts/01_inspect.py
xvfb-run python scripts/02_render_pair.py
python scripts/03_stats.py
python scripts/04_zeroshot.py
```

`04_zeroshot.py` needs an API key for the chosen VLM in the environment.

## Hardware

No local GPU. Data inspection, rendering, statistics and the zero-shot baseline run on CPU. The fine-tuning run uses a free Colab T4 with a 2B parameter VLM, 4-bit loading and LoRA. This constraint is part of the model and training decisions.

## Evaluation

Three levels, from cheapest to most meaningful.

1. Program level. Exact match and edit distance against the ground-truth program.
2. Render level. The predicted program is rendered and compared with the input image.
3. Task level. Predicted programs replace the ground-truth programs in the C-G setup. The question is how much of the C-G accuracy survives.

Level 1 can punish programs that are correct but written differently, since one shape can have more than one correct program. Level 2 is the primary metric for this reason.

## References

- Nie et al., 2020. Bongard-LOGO: A New Benchmark for Human-Level Concept Learning and Reasoning. NeurIPS.
- Vaishnav and Tammet, 2026. Symbolic Grounding Reveals Representational Bottlenecks in Abstract Visual Reasoning. CoNLL.
- Vaishnav and Tammet, 2025. A Cognitive Paradigm Approach to Probe the Perception-Reasoning Interface in VLMs. arXiv 2501.13620.
- Ellis et al., 2018. Learning to Infer Graphics Programs from Hand-Drawn Images. NeurIPS.