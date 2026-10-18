"""Count how often the two shapes of a two-shape image touch or overlap.

Question: In the dataset images with two shapes, are the two shapes always
          drawn apart, or do they sometimes touch or overlap?
Input:    All two-shape images (ff and bd; hd has none) and, as a control,
          a sample of one-shape images.
Output:   outputs/logs/1b_shape_overlap.txt (counts) and
          outputs/figures/1b_touching_examples.png (two-shape images whose ink
          forms a single group, for checking by eye).
Decision: 1b (two-shape images), and the task difficulty for Decision 1.

Method: the image is thresholded (ink = pixel value below 128), reduced to a
64 x 64 grid where a cell is ink if any of its 8 x 8 pixels is ink, dilated by
one cell so that stamped strokes (circles, squares, triangles) merge into one
body, and the 8-connected groups of ink cells are counted. Two shapes closer
than about 24 pixels are therefore counted as touching. One-shape images show
how often a single shape falls apart into several groups under this method.

Usage: python scripts/check_1b_shape_overlap.py [--workers N] [--control N]
"""

import argparse
import json
import os
import random
from collections import Counter, deque
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
LOG = ROOT / "outputs" / "logs" / "1b_shape_overlap.txt"
FIGURE = ROOT / "outputs" / "figures" / "1b_touching_examples.png"
SIDE_FOLDERS = ["1", "0"]  # JSON side 0 = positive = folder 1


def ink_groups(path, cell=8):
    """Number of 8-connected ink groups on the reduced, dilated grid."""
    a = np.asarray(Image.open(path).convert("L")) < 128
    h, w = a.shape
    g = a.reshape(h // cell, cell, w // cell, cell).any(axis=(1, 3))
    d = g.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            d |= np.roll(np.roll(g, dy, axis=0), dx, axis=1)
    seen = np.zeros_like(d)
    groups = 0
    for y0, x0 in zip(*np.nonzero(d)):
        if seen[y0, x0]:
            continue
        groups += 1
        seen[y0, x0] = True
        queue = deque([(y0, x0)])
        while queue:
            y, x = queue.popleft()
            for yy in range(max(0, y - 1), min(d.shape[0], y + 2)):
                for xx in range(max(0, x - 1), min(d.shape[1], x + 2)):
                    if d[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True
                        queue.append((yy, xx))
    return groups


def image_paths(n_shapes, rng=None, limit=None):
    """Paths of images with the given number of shapes, optionally a random sample."""
    paths = []
    for t in ("ff", "bd", "hd"):
        programs = json.loads((DATA / t / f"{t}_action_programs.json").read_text())
        for problem, sides in programs.items():
            for s, side in enumerate(sides):
                for i, image in enumerate(side):
                    if len(image) == n_shapes:
                        paths.append((t, DATA / t / "images" / problem / SIDE_FOLDERS[s] / f"{i}.png"))
    if limit is not None and limit < len(paths):
        paths = rng.sample(paths, limit)
    return paths


def count(paths, workers):
    with Pool(workers) as pool:
        groups = pool.map(ink_groups, [p for _, p in paths], chunksize=64)
    return list(zip(paths, groups))


def examples_figure(touching, rng, n=8, size=256):
    picks = rng.sample(touching, min(n, len(touching)))
    cols, pad, text_h = 4, 12, 20
    rows = (len(picks) + cols - 1) // cols
    font = ImageFont.load_default(size=12)
    canvas = Image.new("RGB", (cols * (size + pad) + pad, rows * (size + text_h + pad) + pad), "white")
    draw = ImageDraw.Draw(canvas)
    for k, ((t, path), _) in enumerate(picks):
        x = pad + (k % cols) * (size + pad)
        y = pad + (k // cols) * (size + text_h + pad)
        draw.text((x, y), f"{t}/{path.parent.parent.name}/{path.parent.name}/{path.name}"[:46], fill="black", font=font)
        canvas.paste(Image.open(path).convert("RGB").resize((size, size)), (x, y + text_h))
        draw.rectangle([x - 1, y + text_h - 1, x + size, y + text_h + size], outline=(160, 160, 160))
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIGURE)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    parser.add_argument("--control", type=int, default=3000, help="number of one-shape images for the control")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    two = image_paths(2)
    say(f"Two-shape images: {len(two)} (" + ", ".join(f"{t} {n}" for t, n in Counter(t for t, _ in two).items()) + ")")
    results = count(two, args.workers)
    say("  ink groups after merging (1 = the two shapes touch, overlap or lie within ~24 px):")
    for t in ("ff", "bd"):
        c = Counter(g for (tt, _), g in results if tt == t)
        n = sum(c.values())
        say(f"    {t}: " + ", ".join(f"{g} group{'s' if g > 1 else ''}: {c[g]} ({100 * c[g] / n:.2f}%)" for g in sorted(c)))
    touching = [r for r in results if r[1] == 1]
    say(f"  single-group two-shape images in total: {len(touching)}/{len(two)} ({100 * len(touching) / len(two):.2f}%)")

    one = image_paths(1, rng, args.control)
    control = count(one, args.workers)
    say(f"Control, one-shape images (random {len(one)}): " + ", ".join(
        f"{g} group{'s' if g > 1 else ''}: {n} ({100 * n / len(one):.2f}%)"
        for g, n in sorted(Counter(g for _, g in control).items())))

    if touching:
        examples_figure(touching, rng)
        say(f"  examples: outputs/figures/{FIGURE.name}")
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
