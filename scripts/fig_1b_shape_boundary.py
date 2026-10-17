"""Show what dropping the shape boundary does to a two-shape program.

Question: If the output of the model lists the actions of a two-shape image as
          one flat sequence (no shape boundary), what does that program draw?
Input:    Two two-shape images from the dataset (one ff, one bd) and their
          programs; the bongard painter with the settings used in
          02_render_pair.py (magnifier off for ff, on for bd).
Output:   outputs/figures/1b_shape_boundary.png with one row per example:
          dataset image | program drawn with the boundary kept (two shapes) |
          the same actions drawn as one shape (boundary dropped).
          Both program strings on stdout.
Decision: 1b (keep the shape boundary in the output or not).

Needs a display for Python turtle and Ghostscript, as 02_render_pair.py.

Usage: python scripts/fig_1b_shape_boundary.py
"""

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
from bongard import BongardImage, BongardProblemPainter
from PIL import EpsImagePlugin, Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
FIGURE = ROOT / "outputs" / "figures" / "1b_shape_boundary.png"
RENDERS = ROOT / "outputs" / "logs" / "1b_shape_boundary"

# (type, problem, folder, index): two-shape images used in 02_render_pair.py.
EXAMPLES = [("ff", "ff_nact3_3_0185", "1", 0), ("bd", "bd_thin_symm_dagger-open_symm_arc60_0000", "0", 6)]
SETTINGS = {"ff": {"scaling": (80, 140), "magnifier": False}, "bd": {"scaling": (150, 260), "magnifier": True}}
SIDE_OF_FOLDER = {"1": 0, "0": 1}


def ensure_ghostscript():
    """Same as 02_render_pair.py: find the Windows Ghostscript install if it is not on PATH."""
    if sys.platform == "win32" and not (shutil.which("gswin64c") or shutil.which("gswin32c")):
        found = glob.glob(r"C:\Program Files\gs\gs*\bin\gswin64c.exe")
        if found:
            newest = max(found, key=lambda p: [int(n) for n in re.findall(r"\d+", Path(p).parents[1].name)])
            os.environ["PATH"] = str(Path(newest).parent) + os.pathsep + os.environ["PATH"]
    if not EpsImagePlugin.has_ghostscript():
        sys.exit("Ghostscript not found. See README, Setup.")


def restore_rgb_eps():
    """Same as 02_render_pair.py: make the painter's PostScript-to-PNG step work with Pillow 11+."""
    bongard_painter.Image = SimpleNamespace(open=lambda fp: Image.open(fp).convert("RGB"))


def simplified(program):
    """Decision 1a format: arc radius removed, shapes separated by ' | '."""
    return " | ".join(" ".join(re.sub(r"^arc_([a-z]+)_0\.500_", r"arc_\1_", a) for a in shape) for shape in program)


def render(painter, t, label, program):
    painter.scaling_factors_range = SETTINGS[t]["scaling"]
    painter.bongard_image_painter.magnifier_effect = SETTINGS[t]["magnifier"]
    painter.save_bongard_images([BongardImage.import_from_action_string_list(program)], image_label=label,
                                bongard_problem_ps_dir=str(RENDERS / "ps"), bongard_problem_png_dir=str(RENDERS / "png"))
    return RENDERS / "png" / label / "0.png"


def main():
    ensure_ghostscript()
    restore_rgb_eps()
    painter = BongardProblemPainter(magnifier_effect=True, random_seed=0)
    rows = []
    for t, problem, folder, index in EXAMPLES:
        program = json.loads((DATA / t / f"{t}_action_programs.json").read_text())[problem][SIDE_OF_FOLDER[folder]][index]
        flat = [[a for shape in program for a in shape]]
        print(f"{t}/images/{problem}/{folder}/{index}.png")
        print(f"  (a) boundary kept:    {simplified(program)}")
        print(f"  (b) boundary dropped: {simplified(flat)}")
        kept = render(painter, t, f"{problem}_kept", program)
        dropped = render(painter, t, f"{problem}_dropped", flat)
        rows.append((DATA / t / "images" / problem / folder / f"{index}.png", kept, dropped, f"{t}: {problem}"))
    try:
        turtle.bye()
    except turtle.Terminator:
        pass

    size, gap, pad, text_h = 400, 16, 16, 26
    font = ImageFont.load_default(size=15)
    width = 2 * pad + 3 * size + 2 * gap
    height = 2 * pad + text_h + len(rows) * (text_h + size + gap) - gap
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    headers = ["dataset image", "(a) boundary kept: drawn as two shapes", "(b) boundary dropped: drawn as one shape"]
    for col, text in enumerate(headers):
        draw.text((pad + col * (size + gap), pad), text, fill="black", font=font)
    y = pad + text_h
    for original, kept, dropped, title in rows:
        draw.text((pad, y), title, fill="black", font=font)
        y += text_h
        for col, path in enumerate((original, kept, dropped)):
            x = pad + col * (size + gap)
            canvas.paste(Image.open(path).convert("RGB").resize((size, size)), (x, y))
            draw.rectangle([x - 1, y - 1, x + size, y + size], outline=(160, 160, 160))
        y += size + gap
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIGURE)
    print(f"Figure written to {FIGURE.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
