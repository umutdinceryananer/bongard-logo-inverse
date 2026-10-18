"""Memorization check for the zero-shot test: images of perturbed dataset programs.

Question: Does the VLM read the drawing, or does it recall programs it may have
          seen, since Bongard-LOGO is public? If accuracy on dataset images is
          clearly higher than on new images whose programs do not occur in the
          dataset, memorization is suspected.
Input:    20 val programs outside the zero-shot sample and its examples (10 bd
          with two shapes, 10 hd with one shape), the bongard painter with the
          bd and hd settings of the official generator, and the zero-shot
          script (prompt, examples, API, scoring).
Output:   outputs/logs/memorization/<type>_<i>.png   the new images
          outputs/logs/memorization/sample.json      programs, perturbations, targets
          outputs/logs/zeroshot_memcheck_<model>.jsonl  answers and scores (K2)
          A side-by-side table of the same metrics on dataset and new images.
Decision: 3a (validity of the zero-shot result).

Method, as the negative examples of the free-form problems in Nie et al.
(2020): in each program exactly one action is changed, either its stroke
style (to another of the five) or its turn (to another value from the type's
train set; never the first action of a shape, whose turn is the start
heading). The perturbed shape program must not occur anywhere in the dataset.
The image is drawn by the painter at a random pose. ff is excluded until the
renderer fidelity question is settled.

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
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
OUT = ROOT / "outputs" / "logs" / "memorization"
SAMPLE = OUT / "sample.json"
PER_TYPE = {"bd": (10, 2), "hd": (10, 1)}  # images, shapes per image
PAINTER = {"bd": {"scaling": (150, 260), "magnifier": True}, "hd": {"scaling": (150, 320), "magnifier": True}}
STYLES = ["normal", "zigzag", "circle", "triangle", "square"]
SIDE_FOLDERS = ["1", "0"]

spec = importlib.util.spec_from_file_location("zeroshot", ROOT / "scripts" / "04_zeroshot.py")
zs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zs)


def train_turns(t, programs, train):
    turns = set()
    for p, sides in programs.items():
        if p in train:
            for side in sides:
                for img in side:
                    for shape in img:
                        for a in shape:
                            turns.add(a.rsplit("-", 1)[1])
    return sorted(turns)


def perturb(rng, program, turns, known):
    """Change one action's style or turn in one shape; retry until the shape is new to the dataset."""
    for _ in range(100):
        new = [list(s) for s in program]
        si = rng.randrange(len(new))
        shape = new[si]
        ai = rng.randrange(len(shape))
        parts = shape[ai].split("_")
        kind, style = parts[0], parts[1]
        if ai == 0 or rng.random() < 0.5:
            what = "style"
            parts[1] = rng.choice([s for s in STYLES if s != style])
            action = "_".join(parts)
        else:
            what = "turn"
            head, turn = shape[ai].rsplit("-", 1)
            action = head + "-" + rng.choice([v for v in turns if v != turn])
        shape[ai] = action
        if tuple(shape) not in known:
            return new, {"shape": si, "action": ai, "changed": what, "from": program[si][ai], "to": action}
    raise RuntimeError("could not find a perturbation that is new to the dataset")


def cmd_generate(args):
    import numpy as np
    import bongard.bongard_painter as bongard_painter
    from bongard import BongardImage, BongardProblemPainter
    from PIL import Image
    sys.path.insert(0, str(ROOT / "scripts"))
    from importlib import import_module
    import_module("02_render_pair").ensure_ghostscript()
    bongard_painter.Image = SimpleNamespace(open=lambda fp: Image.open(fp).convert("RGB"))

    rng = random.Random(args.seed)
    split = json.loads((DATA / "ShapeBongard_V2_split.json").read_text())
    train = set(split["train"])
    programs = zs.load_programs()
    known = {tuple(shape) for t in programs for sides in programs[t].values() for side in sides for img in side
             for shape in img}
    zero = json.loads(zs.SAMPLE_FILE.read_text(encoding="utf-8"))
    excluded = {r["problem"] for r in zero["sample"]} | {e["problem"] for t in zero["examples"] for e in zero["examples"][t]}
    painter = BongardProblemPainter(magnifier_effect=True, random_seed=args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    sample = []
    for t, (n_images, n_shapes) in PER_TYPE.items():
        turns = train_turns(t, programs[t], train)
        pool = [p for p in split["val"] if p.startswith(t + "_") and p not in excluded
                and len(programs[t][p][0][0]) == n_shapes]
        painter.scaling_factors_range = PAINTER[t]["scaling"]
        painter.bongard_image_painter.magnifier_effect = PAINTER[t]["magnifier"]
        made = 0
        for problem in rng.sample(pool, len(pool)):
            if made == n_images:
                break
            side, index = rng.randrange(2), rng.randrange(7)
            original = programs[t][problem][side][index]
            program, change = perturb(rng, original, turns, known)
            label = f"{t}_{made:02d}"
            painter.save_bongard_images([BongardImage.import_from_action_string_list(program)], image_label=label,
                                        bongard_problem_ps_dir=str(OUT / "ps"), bongard_problem_png_dir=str(OUT / "png"))
            png = OUT / "png" / label / "0.png"
            if (np.asarray(Image.open(png).convert("L")) < 128).sum() < 200:  # nothing drawn: off canvas
                continue
            final = OUT / f"{label}.png"
            final.write_bytes(png.read_bytes())
            sample.append({"type": t, "problem": label, "source": f"{t}/images/{problem}/{SIDE_FOLDERS[side]}/{index}.png",
                           "path": str(final), "program": program, "original_program": original, "change": change,
                           "target": zs.to_output_format(program), "n_shapes": n_shapes,
                           "n_actions": sum(len(s) for s in program)})
            made += 1
    try:
        turtle.bye()
    except turtle.Terminator:
        pass
    SAMPLE.write_text(json.dumps({"seed": args.seed, "sample": sample}, indent=1), encoding="utf-8")
    changed = defaultdict(int)
    for r in sample:
        changed[r["change"]["changed"]] += 1
    print(f"{len(sample)} new images under {OUT.relative_to(ROOT).as_posix()}: one action changed per image "
          f"({dict(changed)}); no perturbed shape program occurs in the dataset")


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
                                "generation_config": zs.GENERATION_CONFIG,
                                "images": "perturbed val programs drawn by the painter, outside the dataset",
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
