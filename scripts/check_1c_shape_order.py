"""Check whether the order of the two shapes in a two-shape program follows a rule.

Question: In two-shape programs, is there a rule for which shape is written
          first? Does the same pair of shapes always appear in the same order?
Input:    ff and bd action programs (hd has no two-shape images).
Output:   A text report on stdout and in outputs/logs/1c_shape_order.txt:
          first shape shorter / equal / longer; whether the first shape is the
          same across the images of a problem side; how often a pair of shapes
          that recurs in other images or problems appears in both orders; and
          whether any bd concept name X-Y also exists as Y-X.
Decision: 1c (which shape comes first in the output).

Usage: python scripts/check_1c_shape_order.py
"""

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
LOG = ROOT / "outputs" / "logs" / "1c_shape_order.txt"

STYLE = re.compile(r"_(normal|zigzag|circle|triangle|square)_")
lines = []


def say(text=""):
    print(text)
    lines.append(text)


def no_style(shape):
    """Shape identity with the stroke style removed."""
    return tuple(STYLE.sub("_", a) for a in shape)


def length_order(programs):
    c = Counter()
    for sides in programs.values():
        for side in sides:
            for img in side:
                if len(img) == 2:
                    a, b = len(img[0]), len(img[1])
                    c["first shorter" if a < b else "equal" if a == b else "first longer"] += 1
    return c


def first_shape_per_side(programs):
    c = Counter()
    for sides in programs.values():
        for side in sides:
            two = [img for img in side if len(img) == 2]
            if two:
                c["same first shape in all images of the side" if len({no_style(i[0]) for i in two}) == 1
                  else "first shape varies within the side"] += 1
    return c


def pair_orders(programs, key):
    """For each unordered pair of distinct shapes: images, problems and orders it appears in."""
    pairs = defaultdict(lambda: {"problems": set(), "images": 0, "orders": set()})
    for pid, sides in programs.items():
        for side in sides:
            for img in side:
                if len(img) != 2:
                    continue
                a, b = key(img[0]), key(img[1])
                if a == b:
                    continue
                e = pairs[frozenset((a, b))]
                e["problems"].add(pid)
                e["images"] += 1
                e["orders"].add((a, b))
    in_images = [e for e in pairs.values() if e["images"] > 1]
    in_problems = [e for e in pairs.values() if len(e["problems"]) > 1]
    return (len(pairs), len(in_images), sum(len(e["orders"]) == 2 for e in in_images),
            len(in_problems), sum(len(e["orders"]) == 2 for e in in_problems))


def main():
    for t in ("ff", "bd"):
        programs = json.loads((DATA / t / f"{t}_action_programs.json").read_text())
        say(f"{t}")
        say(f"  two-shape images by length order: {dict(length_order(programs))}")
        say(f"  problem sides with two-shape images: {dict(first_shape_per_side(programs))}")
        for label, key in (("exact programs", tuple), ("style ignored", no_style)):
            n, img, img_both, prob, prob_both = pair_orders(programs, key)
            say(f"  {label}: {n} distinct pairs; {img} recur in more than one image, {img_both} of them in both "
                f"orders; {prob} recur in more than one problem, {prob_both} of them in both orders")
    names = {re.sub(r"_\d+$", "", p) for p in json.loads((DATA / "bd" / "bd_action_programs.json").read_text())}
    xy = [n[3:].split("-") for n in names if n.count("-") == 1]
    say(f"bd concept names of the form X-Y: {len(xy)}; also present as Y-X: "
        f"{sum(f'bd_{y}-{x}' in names for x, y in xy)}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
