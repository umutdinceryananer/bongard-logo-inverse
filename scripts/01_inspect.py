"""Describe how the Bongard-LOGO data is stored.

Question: How is the data stored? File layout, images per problem, image
          resolution, where and in which format the action programs are,
          how programs of two-shape images are stored, and how the
          train/val/test splits are defined.
Input:    data/ShapeBongard_V2/ (images, <type>/<type>_action_programs.json,
          ShapeBongard_V2_split.json).
Output:   A plain-text report on stdout, also written to
          outputs/logs/01_inspect.txt.
Decision: 1 (task definition, two-shape images), 2 (images, resolution),
          8 (evaluation: split structure, program overlap between splits).

Usage: python scripts/01_inspect.py [--sample-per-type N] [--seed S]
"""

import argparse
import json
import os
import re
import statistics
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
LOG = ROOT / "outputs" / "logs" / "01_inspect.txt"

TYPES = ["ff", "bd", "hd"]
# Image folder for each side of a problem in the JSON files: side 0 holds the
# positive images (folder "1"), side 1 the negative images (folder "0"). This
# follows bongard.BongardProblemPainter and the official loader in
# Bongard-LOGO_Baselines/datasets/shape_program.py.
SIDE_FOLDERS = ["1", "0"]
IMAGES_PER_SIDE = 7

NUM = r"(\d\.\d{3})"
LINE_RE = re.compile(rf"^line_([a-z]+)_{NUM}-{NUM}$")
ARC_RE = re.compile(rf"^arc_([a-z]+)_{NUM}_{NUM}-{NUM}$")

report = []


def say(*parts):
    text = " ".join(str(p) for p in parts)
    print(text)
    report.append(text)


def heading(title):
    say()
    say(title)
    say("-" * len(title))


def describe(path):
    if path.is_file():
        return f"{path.name}  {path.stat().st_size / 2**20:.1f} MiB"
    return f"{path.name}/  {sum(1 for _ in os.scandir(path))} entries"


def problem_name(problem_id):
    """Problem id without its trailing index, e.g. ff_nact2_5_0270 -> ff_nact2_5."""
    return re.sub(r"_\d+$", "", problem_id)


def show_layout():
    heading("1. File layout under data/ShapeBongard_V2/")
    for entry in sorted(DATA.iterdir()):
        say(f"  {describe(entry)}")
        if entry.is_dir():
            for child in sorted(entry.iterdir()):
                say(f"    {describe(child)}")
    say("  Image path: <type>/images/<problem_id>/<folder>/<index>.png")


def count_images():
    heading("2. Images per problem")
    expected = [f"{i}.png" for i in range(IMAGES_PER_SIDE)]
    problems = {}
    for t in TYPES:
        img_dir = DATA / t / "images"
        names = sorted(e.name for e in os.scandir(img_dir) if e.is_dir())
        problems[t] = names
        per_problem = Counter()
        odd = []
        for name in names:
            if set(os.listdir(img_dir / name)) != set(SIDE_FOLDERS):
                odd.append(name)
            counts = []
            for folder in SIDE_FOLDERS:
                d = img_dir / name / folder
                files = sorted(e.name for e in os.scandir(d)) if d.is_dir() else []
                counts.append(len(files))
                if files != expected:
                    odd.append(f"{name}/{folder}")
            per_problem[tuple(counts)] += 1
        total = sum(sum(k) * n for k, n in per_problem.items())
        dist = {f"{k[0]}+{k[1]}": n for k, n in per_problem.items()}
        say(f"  {t}: {len(names)} problems, (folder 1 + folder 0) images per problem {dist}, {total} images")
        say(f"      problems deviating from folders 0/ and 1/ with 0.png..6.png: {len(odd)} {odd[:5]}")
    return problems


def inspect_images(problems, per_type, seed):
    heading(f"3. Image format ({per_type} random images per type, seed {seed})")
    rng = np.random.default_rng(seed)
    per_problem = 2 * IMAGES_PER_SIDE
    for t in TYPES:
        sizes, modes, backgrounds = Counter(), Counter(), Counter()
        gray, levels, box_w, box_h = 0, [], [], []
        picks = rng.choice(len(problems[t]) * per_problem, size=per_type, replace=False)
        for pick in picks:
            name = problems[t][pick // per_problem]
            folder = SIDE_FOLDERS[(pick % per_problem) // IMAGES_PER_SIDE]
            index = pick % IMAGES_PER_SIDE
            im = Image.open(DATA / t / "images" / name / folder / f"{index}.png")
            sizes[f"{im.size[0]}x{im.size[1]}"] += 1
            modes[im.mode] += 1
            a = np.asarray(im.convert("RGB"))
            gray += bool((a[..., 0] == a[..., 1]).all() and (a[..., 1] == a[..., 2]).all())
            g = a[..., 0]
            values, counts = np.unique(g, return_counts=True)
            backgrounds[int(values[counts.argmax()])] += 1
            levels.append(len(values))
            ys, xs = np.nonzero(g < 128)
            if len(xs):
                box_w.append(int(xs.max() - xs.min() + 1))
                box_h.append(int(ys.max() - ys.min() + 1))
        say(f"  {t}: size {dict(sizes)}, mode {dict(modes)}, R=G=B in {gray}/{per_type}, "
            f"most common value {dict(backgrounds)}")
        say(f"      distinct gray levels per image: min {min(levels)}, "
            f"median {statistics.median(levels):.0f}, max {max(levels)}")
        say(f"      ink bounding box (pixels < 128): width median {statistics.median(box_w):.0f}, "
            f"height median {statistics.median(box_h):.0f}, largest side {max(box_w + box_h)}")


def inspect_programs(problems):
    heading("4. Action programs")
    say("  Nesting: problem_id -> [side 0 = positive (folder 1), side 1 = negative (folder 0)]")
    say("           -> 7 images -> list of shapes -> list of action strings")
    say("  Grammar: line_<style>_<length>-<turn>, arc_<style>_<radius>_<arc_angle>-<turn>")
    programs = {}
    for t in TYPES:
        path = DATA / t / f"{t}_action_programs.json"
        progs = json.loads(path.read_text())
        programs[t] = progs
        keys, dirs = set(progs), set(problems[t])
        say(f"  {path.relative_to(DATA).as_posix()}: {type(progs).__name__} with {len(progs)} problems; "
            f"keys equal image folders: {keys == dirs} "
            f"(only in JSON {len(keys - dirs)}, only on disk {len(dirs - keys)})")

        bad_structure, unmatched = [], []
        kinds, line_styles, arc_styles, lengths = Counter(), Counter(), Counter(), []
        for name, sides in progs.items():
            if len(sides) != 2 or any(len(side) != IMAGES_PER_SIDE for side in sides):
                bad_structure.append(name)
                continue
            for side in sides:
                for image in side:
                    if not image or not all(isinstance(s, list) and s for s in image):
                        bad_structure.append(name)
                        continue
                    for shape in image:
                        lengths.append(len(shape))
                        for action in shape:
                            if m := LINE_RE.match(action):
                                kinds["line"] += 1
                                line_styles[m.group(1)] += 1
                            elif m := ARC_RE.match(action):
                                kinds["arc"] += 1
                                arc_styles[m.group(1)] += 1
                            else:
                                unmatched.append(action)
        say(f"      structure violations: {len(bad_structure)} {bad_structure[:3]}")
        say(f"      actions: {dict(kinds)}, not matching the grammar: {len(unmatched)} {unmatched[:3]}")
        say(f"      line styles {dict(line_styles)}")
        say(f"      arc styles  {dict(arc_styles)}")
        say(f"      actions per shape: min {min(lengths)}, median {statistics.median(lengths):.0f}, "
            f"max {max(lengths)}")
        first = next(iter(progs))
        say(f"      example {first} side 0 image 0: {json.dumps(progs[first][0][0])}")
    return programs


def inspect_multi_shape(programs):
    heading("5. Images with more than one shape")
    for t in TYPES:
        per_image, with_multi, mixed, example = Counter(), 0, 0, None
        for name, sides in programs[t].items():
            counts = [len(image) for side in sides for image in side]
            per_image.update(counts)
            with_multi += max(counts) > 1
            mixed += len(set(counts)) > 1
            if example is None and max(counts) > 1:
                example = next((name, s, i, image) for s, side in enumerate(sides)
                               for i, image in enumerate(side) if len(image) > 1)
        say(f"  {t}: images by number of shapes {dict(sorted(per_image.items()))}; "
            f"problems with a multi-shape image {with_multi}; problems mixing shape counts {mixed}")
        if example:
            name, s, i, image = example
            say(f"      example {t}/images/{name}/{SIDE_FOLDERS[s]}/{i}.png: {json.dumps(image)}")

    # ff ids look like ff_nact<a> or ff_nact<a>_<b>: compare the numbers with the programs.
    match = total = 0
    for name, sides in programs["ff"].items():
        numbers = sorted(int(n) for n in re.findall(r"\d+", problem_name(name)))
        for side in sides:
            for image in side:
                total += 1
                match += sorted(len(shape) for shape in image) == numbers
    say(f"  ff ids ff_nact<a>[_<b>]: {match}/{total} images have one shape per number in the id, "
        f"with that many actions")


def inspect_splits(problems, programs):
    heading("6. Splits")
    path = DATA / "ShapeBongard_V2_split.json"
    split = json.loads(path.read_text())
    say(f"  {path.name}: {type(split).__name__}, " + ", ".join(f"{k} {len(v)}" for k, v in split.items()))

    on_disk = {p for t in TYPES for p in problems[t]}
    union = set().union(*map(set, split.values()))
    names = list(split)
    overlaps = {f"{a}&{b}": n for i, a in enumerate(names) for b in names[i + 1:]
                if (n := len(set(split[a]) & set(split[b])))}
    duplicates = {k: len(v) - len(set(v)) for k, v in split.items() if len(v) != len(set(v))}
    say(f"  splits are disjoint: {not overlaps} {overlaps}; duplicates within a split: {duplicates}")
    say(f"  union equals problems on disk: {union == on_disk} "
        f"(on disk only {len(on_disk - union)}, split only {len(union - on_disk)})")

    train_names = {problem_name(p) for p in split["train"]}
    for k, ids in split.items():
        by_type = Counter(p.split("_")[0] for p in ids)
        groups = Counter(problem_name(p) for p in ids)
        line = f"  {k}: by type {dict(by_type)}, {len(groups)} distinct problem names"
        if k != "train":
            line += f", names also in train {len(groups.keys() & train_names)}/{len(groups)}"
        say(line)
        ff_groups = {g: n for g, n in sorted(groups.items()) if g.startswith("ff_")}
        if ff_groups:
            say(f"      ff names: {ff_groups}")

    say("  Exact shape-program overlap with train (a shape program is the list of its action strings):")
    shape_programs = {}
    for k, ids in split.items():
        c = Counter()
        for p in ids:
            for side in programs.get(p.split("_")[0], {}).get(p, []):
                for image in side:
                    c.update(tuple(shape) for shape in image)
        shape_programs[k] = c
    train = shape_programs["train"]
    for k, c in shape_programs.items():
        total = sum(c.values())
        line = f"  {k}: {total} shape occurrences, {len(c)} distinct programs"
        if k != "train":
            seen = sum(n for s, n in c.items() if s in train)
            line += f", occurrences with a program seen in train {seen}/{total} ({100 * seen / total:.1f}%)"
        say(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample-per-type", type=int, default=200,
                        help="random images per problem type for the image format check")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    show_layout()
    problems = count_images()
    inspect_images(problems, args.sample_per_type, args.seed)
    programs = inspect_programs(problems)
    inspect_multi_shape(programs)
    inspect_splits(problems, programs)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"\nReport written to {LOG.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
