"""Memorization check for the zero-shot test: new images from programs not in the dataset.

Question: Does the VLM read the drawing, or does it recall programs it may have
          seen, since Bongard-LOGO is public? If accuracy on dataset images is
          clearly higher than on new images drawn from programs that do not
          occur in the dataset, memorization is suspected.
Input:    Train-split statistics of bd and hd (program length, action type and
          style frequencies, numeric value sets), the bongard painter with the
          bd and hd settings of the official generator, and the zero-shot
          script (prompt, examples, API, scoring).
Output:   outputs/logs/memorization/<type>_<i>.png   the new images
          outputs/logs/memorization/sample.json      their programs and targets
          outputs/logs/zeroshot_memcheck_<model>.jsonl  answers and scores (K2)
          A side-by-side table of the same metrics on dataset and new images.
Decision: 3a (validity of the zero-shot result).

Method: 10 bd images with two shapes and 10 hd images with one shape. Each
shape is a random valid program: length drawn from the type's train
distribution, action type and style from the train frequencies, numbers from
the train value sets, first turn 0.500; a shape is rejected if its program
occurs anywhere in the dataset or if the painter cannot draw it inside the
canvas. ff is excluded until the renderer fidelity question is settled.

Usage:
  python scripts/check_04_memorization.py generate [--seed S]
  python scripts/check_04_memorization.py run --model M
  python scripts/check_04_memorization.py compare --model M
"""

import argparse
import importlib.util
import json
import random
import statistics
import sys
import turtle
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
OUT = ROOT / "outputs" / "logs" / "memorization"
SAMPLE = OUT / "sample.json"
PER_TYPE = {"bd": (10, 2), "hd": (10, 1)}  # images, shapes per image
PAINTER = {"bd": {"scaling": (150, 260), "magnifier": True}, "hd": {"scaling": (150, 320), "magnifier": True}}

spec = importlib.util.spec_from_file_location("zeroshot", ROOT / "scripts" / "04_zeroshot.py")
zs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zs)


def train_statistics(t, programs, train):
    """Length distribution, action frequencies and value sets of one type in train."""
    lengths, actions = [], Counter()
    values = defaultdict(set)
    for p, sides in programs.items():
        if p not in train:
            continue
        for side in sides:
            for img in side:
                for shape in img:
                    lengths.append(len(shape))
                    for a in shape:
                        kind, style = a.split("_")[:2]
                        actions[(kind, style)] += 1
                        nums = a.split("_")[-1] if kind == "line" else "_".join(a.split("_")[2:])
                        if kind == "line":
                            length, turn = nums.split("-")
                            values["line length"].add(length)
                        else:
                            radius, rest = nums.split("_")
                            angle, turn = rest.split("-")
                            values["arc angle"].add(angle)
                        values["turn"].add(turn)
    return lengths, actions, {k: sorted(v) for k, v in values.items()}


def random_shape(rng, lengths, actions, values):
    n = rng.choice(lengths)
    kinds = list(actions)
    weights = [actions[k] for k in kinds]
    shape = []
    for i in range(n):
        kind, style = rng.choices(kinds, weights)[0]
        turn = "0.500" if i == 0 else rng.choice(values["turn"])
        if kind == "line":
            shape.append(f"line_{style}_{rng.choice(values['line length'])}-{turn}")
        else:
            shape.append(f"arc_{style}_0.500_{rng.choice(values['arc angle'])}-{turn}")
    return shape


def cmd_generate(args):
    import bongard.bongard_painter as bongard_painter
    from bongard import BongardImage, BongardProblemPainter
    from PIL import Image
    sys.path.insert(0, str(ROOT / "scripts"))
    from importlib import import_module
    render_pair = import_module("02_render_pair")
    render_pair.ensure_ghostscript()
    bongard_painter.Image = SimpleNamespace(open=lambda fp: Image.open(fp).convert("RGB"))

    rng = random.Random(args.seed)
    split = json.loads((DATA / "ShapeBongard_V2_split.json").read_text())
    train = set(split["train"])
    programs = zs.load_programs()
    known = {tuple(shape) for t in programs for sides in programs[t].values() for side in sides for img in side
             for shape in img}
    painter = BongardProblemPainter(magnifier_effect=True, random_seed=args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    sample = []
    for t, (n_images, n_shapes) in PER_TYPE.items():
        lengths, actions, values = train_statistics(t, programs[t], train)
        painter.scaling_factors_range = PAINTER[t]["scaling"]
        painter.bongard_image_painter.magnifier_effect = PAINTER[t]["magnifier"]
        made = 0
        while made < n_images:
            program = []
            while len(program) < n_shapes:
                shape = random_shape(rng, lengths, actions, values)
                if tuple(shape) not in known:
                    program.append(shape)
            label = f"{t}_{made:02d}"
            image = BongardImage.import_from_action_string_list(program)
            painter.save_bongard_images([image], image_label=label, bongard_problem_ps_dir=str(OUT / "ps"),
                                        bongard_problem_png_dir=str(OUT / "png"))
            # the painter retries the pose up to 300 times; an invalid drawing stays off-canvas, check the ink
            png = OUT / "png" / label / "0.png"
            from PIL import Image as PILImage
            import numpy as np
            ink = (np.asarray(PILImage.open(png).convert("L")) < 128).sum()
            if ink < 200:
                continue
            final = OUT / f"{label}.png"
            final.write_bytes(png.read_bytes())
            sample.append({"type": t, "problem": label, "path": str(final), "program": program,
                           "target": zs.to_output_format(program), "n_shapes": n_shapes,
                           "n_actions": sum(len(s) for s in program)})
            made += 1
    try:
        turtle.bye()
    except turtle.Terminator:
        pass
    SAMPLE.write_text(json.dumps({"seed": args.seed, "sample": sample}, indent=1), encoding="utf-8")
    print(f"{len(sample)} new images under {OUT.relative_to(ROOT).as_posix()}; none of their shape programs occurs in the dataset")


def cmd_run(args):
    key = zs.api_key()
    data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    examples = json.loads(zs.SAMPLE_FILE.read_text(encoding="utf-8"))["examples"]
    out = zs.LOG / f"zeroshot_memcheck_{args.model}.jsonl"
    done = set()
    if out.exists():
        done = {json.loads(l)["path"] for l in out.read_text(encoding="utf-8").splitlines() if '"path"' in l}
    with out.open("a", encoding="utf-8") as f:
        if not done:
            f.write(json.dumps({"header": True, "model_requested": args.model, "condition": "K2",
                                "generation_config": zs.GENERATION_CONFIG, "images": "new, outside the dataset",
                                "image_preprocessing": "none, native 512 px"}) + "\n")
        for rec in data["sample"]:
            if rec["path"] in done:
                continue
            response, latency = zs.call_model(key, args.model, zs.build_input(rec, "K2", examples))
            text = zs.answer_text(response)
            s = zs.score(text, rec["target"])
            f.write(json.dumps({"path": rec["path"], "type": rec["type"], "problem": rec["problem"],
                                "target": rec["target"], "answer": text, "model_reported": response.get("model"),
                                "usage": response.get("usage"), "latency_s": round(latency, 2), **s}) + "\n")
            f.flush()
            print(f"  {rec['problem']}: valid={s['valid']} count+-1={s['action_count_within_1']} "
                  f"style={s['style_acc_best']:.2f} exact={s['exact']}")


def cmd_compare(args):
    rows = {}
    for name, f in (("dataset", zs.LOG / f"zeroshot_{args.model}_K2.jsonl"),
                    ("new", zs.LOG / f"zeroshot_memcheck_{args.model}.jsonl")):
        recs = [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if '"path"' in l]
        for t in ("bd", "hd"):
            rows[(name, t)] = [r for r in recs if r["type"] == t]
    keys = ["valid", "action_count_within_1", "kind_acc_best", "style_acc_best", "number_acc_best", "exact",
            "edit_distance_best"]
    print(f"{'type':4s} {'images':8s} {'n':>3s} " + " ".join(f"{k:>22s}" for k in keys))
    for t in ("bd", "hd"):
        for name in ("dataset", "new"):
            recs = rows[(name, t)]
            vals = [statistics.mean(float(r[k]) for r in recs) * (1 if k.startswith("edit") else 100) if recs else float("nan")
                    for k in keys]
            print(f"{t:4s} {name:8s} {len(recs):3d} " + " ".join(f"{v:22.1f}" for v in vals))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("generate"); p.add_argument("--seed", type=int, default=0); p.set_defaults(func=cmd_generate)
    p = sub.add_parser("run"); p.add_argument("--model", required=True); p.set_defaults(func=cmd_run)
    p = sub.add_parser("compare"); p.add_argument("--model", required=True); p.set_defaults(func=cmd_compare)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
