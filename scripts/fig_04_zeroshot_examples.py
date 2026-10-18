"""Zero-shot examples figure: dataset image, the model's program drawn, the true program drawn.

Question: What do the zero-shot answers look like when drawn? Six images, two
          per type, from the K2 answers of one model: the best-scoring answer
          and the median answer of each type.
Input:    outputs/logs/zeroshot_<model>_K2.jsonl, the dataset images, the
          bongard painter.
Output:   outputs/figures/zeroshot_examples.png, one row per image, three
          columns: dataset image | the model's program drawn | the true
          program drawn. Both drawings use the same fixed pose (start point,
          heading, scale), so they differ only where the programs differ.
Decision: 3a (illustration of the zero-shot result).

Selection per type: the answer with the highest best-alignment style accuracy
(ties broken by the smallest best-alignment edit distance) and the answer
with the median best-alignment edit distance.

Needs a display for Python turtle and Ghostscript, as 02_render_pair.py.

Usage: python scripts/fig_04_zeroshot_examples.py --model gemini-3.8-flash
"""

import argparse
import importlib.util
import json
import re
import sys
import turtle
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
LOG = ROOT / "outputs" / "logs"
FIGURE = ROOT / "outputs" / "figures" / "zeroshot_examples.png"
RENDERS = LOG / "zeroshot_examples"

# Fixed pose per shape count: start points, headings and scale, the same for model and truth.
POSE = {1: {"starts": [(-120, -60)], "headings": [0]}, 2: {"starts": [(-280, 80), (40, -120)], "headings": [0, 0]}}
SCALE = {"ff": 110, "bd": 200, "hd": 230}  # middle of the official scaling ranges
ARC_OUT = re.compile(r"^arc_([a-z]+)_(\d\.\d{3})-(\d\.\d{3})$")

spec = importlib.util.spec_from_file_location("zeroshot", ROOT / "scripts" / "04_zeroshot.py")
zs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zs)


def to_dataset_format(program_text):
    """Output format (decisions 1a-1c) -> dataset nesting; lines that do not parse are dropped."""
    shapes = []
    for block in program_text.split("\n|\n"):
        shape = []
        for line in block.splitlines():
            line = line.strip()
            if zs.parse_action(line) is None:
                continue
            m = ARC_OUT.match(line)
            shape.append(f"arc_{m.group(1)}_0.500_{m.group(2)}-{m.group(3)}" if m else line)
        if shape:
            shapes.append(shape)
    return shapes


def draw(painter, t, label, program):
    """Draw a dataset-format program at the fixed pose; returns the PNG path or None."""
    from bongard import BongardImage
    if not program:
        return None
    n = min(len(program), 2)
    program = program[:n]
    image = BongardImage.import_from_action_string_list(program)
    image.set_start_coordinates(POSE[n]["starts"][:n])
    image.set_start_orientations(POSE[n]["headings"][:n])
    image.set_consistent_scaling_factors([SCALE[t]] * n)
    painter.save_bongard_images([image], image_label=label, bongard_problem_ps_dir=str(RENDERS / "ps"),
                                bongard_problem_png_dir=str(RENDERS / "png"), auto_position=False)
    return RENDERS / "png" / label / "0.png"


def select(records):
    chosen = []
    for t in ("ff", "bd", "hd"):
        recs = [r for r in records if r["type"] == t]
        if not recs:
            continue
        best = max(recs, key=lambda r: (r["style_acc_best"], -r["edit_distance_best"]))
        by_ed = sorted(recs, key=lambda r: r["edit_distance_best"])
        median = by_ed[len(by_ed) // 2]
        if median["path"] == best["path"] and len(by_ed) > 1:
            median = by_ed[len(by_ed) // 2 + 1]
        chosen += [("best", best), ("median", median)]
    return chosen


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="gemini-3.8-flash")
    args = parser.parse_args()
    import bongard.bongard_painter as bongard_painter
    from bongard import BongardProblemPainter
    from PIL import Image, ImageDraw, ImageFont
    sys.path.insert(0, str(ROOT / "scripts"))
    from importlib import import_module
    import_module("02_render_pair").ensure_ghostscript()
    bongard_painter.Image = SimpleNamespace(open=lambda fp: Image.open(fp).convert("RGB"))

    records = [json.loads(l) for l in (LOG / f"zeroshot_{args.model}_K2.jsonl").read_text(encoding="utf-8").splitlines()
               if '"path"' in l]
    chosen = select(records)
    painter = BongardProblemPainter(magnifier_effect=True, random_seed=0)
    rows = []
    for tag, r in chosen:
        t = r["type"]
        painter.bongard_image_painter.magnifier_effect = t != "ff"
        label = re.sub(r"[^A-Za-z0-9_]+", "_", r["path"])
        model_png = draw(painter, t, label + "_model", to_dataset_format(r["pred_program"]))
        gold_png = draw(painter, t, label + "_gold", to_dataset_format(r["target"]))
        rows.append((tag, r, model_png, gold_png))
        print(f"{tag:6s} {r['path']}  style best {r['style_acc_best']:.2f}  ed best {r['edit_distance_best']}  exact {r['exact']}")
    try:
        turtle.bye()
    except turtle.Terminator:
        pass

    size, gap, pad, text_h = 400, 16, 16, 24
    font = ImageFont.load_default(size=14)
    width = 2 * pad + 3 * size + 2 * gap
    height = 2 * pad + text_h + len(rows) * (text_h + size + gap) - gap
    canvas = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(canvas)
    for col, text in enumerate(["dataset image", f"the model's program drawn ({args.model}, K2)", "the true program drawn"]):
        d.text((pad + col * (size + gap), pad), text, fill="black", font=font)
    y = pad + text_h
    for tag, r, model_png, gold_png in rows:
        d.text((pad, y), f"{r['type']} {tag}: {r['path']}   style {100 * r['style_acc_best']:.0f}%   "
                         f"edit distance {r['edit_distance_best']}   exact {r['exact']}", fill="black", font=font)
        y += text_h
        for col, path in enumerate((DATA / r["path"], model_png, gold_png)):
            x = pad + col * (size + gap)
            d.rectangle([x - 1, y - 1, x + size, y + size], outline=(160, 160, 160))
            if path is None:
                d.text((x + 20, y + size // 2), "no valid program", fill="black", font=font)
            else:
                canvas.paste(Image.open(path).convert("RGB").resize((size, size)), (x, y))
        y += size + gap
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIGURE)
    print(f"Figure written to {FIGURE.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
