"""Draw dataset programs with the bongard renderer and compare with the dataset images.

Question: Is an image drawn from its program with the bongard renderer the same
          as the dataset image?
Input:    data/ShapeBongard_V2/ (images and <type>/<type>_action_programs.json),
          the bongard 0.0.2 painter with the settings of the official generation
          scripts (examples/02-bongard_logo/generate_*_problems.py).
Output:   outputs/figures/02_render_pair.png, five rows of dataset image next to
          the image drawn from its program; the drawn PNG and PostScript files
          under outputs/logs/02_render_pair/; the selection on stdout.
Decision: 2 (dataset images, rendered images or both), 8 (render-level evaluation).

Needs a display for Python turtle (on headless Linux run under xvfb-run) and
Ghostscript, which PIL uses to rasterize the painter's PostScript output. With
Pillow 11 or later the painter needs a small patch, see restore_rgb_eps().

Usage: python scripts/02_render_pair.py [--seed S]
"""

import argparse
import glob
import json
import os
import re
import shutil
import sys
import turtle
from pathlib import Path
from types import SimpleNamespace

import bongard.bongard_painter as bongard_painter
import numpy as np
from bongard import BongardImage, BongardProblemPainter
from PIL import EpsImagePlugin, Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
FIGURE = ROOT / "outputs" / "figures" / "02_render_pair.png"
RENDERS = ROOT / "outputs" / "logs" / "02_render_pair"

# (problem type, shapes per image). hd has no two-shape images.
CASES = [("ff", 1), ("ff", 2), ("bd", 1), ("bd", 2), ("hd", 1)]
# Scaling factor range per type in examples/02-bongard_logo/generate_*_problems.py.
# All three scripts also use magnifier_effect=True.
SCALING_FACTORS_RANGE = {"ff": (80, 140), "bd": (150, 260), "hd": (150, 320)}
# JSON side 0 holds the positive images (folder "1"), side 1 the negative (folder "0").
SIDE_FOLDERS = ["1", "0"]


def ensure_ghostscript():
    """The Windows installer does not put Ghostscript on PATH; look in its default location."""
    if sys.platform == "win32" and not (shutil.which("gswin64c") or shutil.which("gswin32c")):
        found = glob.glob(r"C:\Program Files\gs\gs*\bin\gswin64c.exe")
        if found:
            newest = max(found, key=lambda p: [int(n) for n in re.findall(r"\d+", Path(p).parents[1].name)])
            os.environ["PATH"] = str(Path(newest).parent) + os.pathsep + os.environ["PATH"]
    if not EpsImagePlugin.has_ghostscript():
        sys.exit("Ghostscript not found. See README, Setup.")


def restore_rgb_eps():
    """Make the painter's PostScript-to-PNG step behave as with Pillow 10.4 and earlier.

    bongard_painter.py runs Image.open(ps).resize((512, 512)). Up to Pillow 10.4,
    Ghostscript rasterized EPS with the ppmraw device, which always gives RGB.
    Pillow 11 switched to pnmraw, which gives a bilevel ("1") image for a
    black-and-white drawing, and the default bicubic resize rejects that mode.
    Converting to RGB gives the pixels ppmraw would have produced.
    """
    bongard_painter.Image = SimpleNamespace(open=lambda fp: Image.open(fp).convert("RGB"))


def select(seed):
    """Pick one image per case at random among problems with that many shapes per image."""
    rng = np.random.default_rng(seed)
    picks = []
    for t, n_shapes in CASES:
        programs = json.loads((DATA / t / f"{t}_action_programs.json").read_text())
        candidates = sorted(p for p, sides in programs.items() if len(sides[0][0]) == n_shapes)
        problem = candidates[rng.integers(len(candidates))]
        side, index = int(rng.integers(2)), int(rng.integers(7))
        picks.append((t, problem, SIDE_FOLDERS[side], index, programs[problem][side][index]))
    return picks


def render(picks, seed):
    """Draw each program with the official painter; return the paths of the drawn PNGs."""
    painter = BongardProblemPainter(magnifier_effect=True, random_seed=seed)
    paths = []
    for row, (t, problem, folder, index, program) in enumerate(picks):
        painter.scaling_factors_range = SCALING_FACTORS_RANGE[t]
        label = f"{row}_{problem}_{folder}_{index}"
        painter.save_bongard_images([BongardImage.import_from_action_string_list(program)],
                                    image_label=label,
                                    bongard_problem_ps_dir=str(RENDERS / "ps"),
                                    bongard_problem_png_dir=str(RENDERS / "png"))
        paths.append(RENDERS / "png" / label / "0.png")
    try:
        turtle.bye()
    except turtle.Terminator:
        pass
    return paths


def compose(picks, rendered, path):
    """Dataset image on the left, drawn image on the right, one row per pick."""
    size, gap, pad, text_h = 512, 16, 16, 28
    font = ImageFont.load_default(size=16)
    width = 2 * pad + 2 * size + gap
    height = 2 * pad + text_h + len(picks) * (text_h + size + gap) - gap
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    x_left, x_right = pad, pad + size + gap
    draw.text((x_left, pad), "dataset image", fill="black", font=font)
    draw.text((x_right, pad), "drawn from its program (bongard painter)", fill="black", font=font)
    y = pad + text_h
    for (t, problem, folder, index, program), drawn in zip(picks, rendered):
        n_actions = sum(len(shape) for shape in program)
        label = (f"{t}/images/{problem}/{folder}/{index}.png   "
                 f"{len(program)} shape{'s' if len(program) > 1 else ''}, {n_actions} actions")
        draw.text((x_left, y), label, fill="black", font=font)
        y += text_h
        original = DATA / t / "images" / problem / folder / f"{index}.png"
        for x, image_path in ((x_left, original), (x_right, drawn)):
            canvas.paste(Image.open(image_path).convert("RGB"), (x, y))
            draw.rectangle([x - 1, y - 1, x + size, y + size], outline=(160, 160, 160))
        y += size + gap
    path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    ensure_ghostscript()
    restore_rgb_eps()
    picks = select(args.seed)
    for t, problem, folder, index, program in picks:
        print(f"{t}/images/{problem}/{folder}/{index}.png  {json.dumps(program)}")
    rendered = render(picks, args.seed)
    compose(picks, rendered, FIGURE)
    print(f"Figure written to {FIGURE.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
