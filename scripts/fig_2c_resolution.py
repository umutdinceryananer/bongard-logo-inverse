"""Show small hd shapes at 512, downscaled to 224, and cropped to the ink then 224.

Question: When the image is reduced to a typical VLM input size (224 px), do
          the fine stroke styles (zigzag, circle, square, triangle stamps) of
          a small shape stay legible, and does cropping to the ink help?
Input:    A random sample of hd images whose program uses at least one fine
          style; the examples with the smallest ink bounding box are shown.
Output:   outputs/figures/2c_resolution.png, one row per example (the smallest
          ones and the median one), at true pixel size: original 512 |
          downscaled to 224 without crop | cropped to the ink with a 10%
          margin, then 224. Bounding box sizes and percentiles on stdout.
Decision: 2c (input resolution and cropping).

Usage: python scripts/fig_2c_resolution.py [--sample N] [--rows N] [--size 224] [--seed S]
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
FIGURE = ROOT / "outputs" / "figures" / "2c_resolution.png"
FINE = ("zigzag", "circle", "square", "triangle")
SIDE_FOLDERS = ["1", "0"]
MARGIN = 0.10  # of the longer side of the ink bounding box, on each side


def ink_bbox(gray):
    ys, xs = np.nonzero(np.asarray(gray) < 128)
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def crop_to_ink(img, bbox):
    """Square crop around the ink with a proportional margin; white padding outside the image."""
    x0, y0, x1, y1 = bbox
    side = int(round(max(x1 - x0, y1 - y0) * (1 + 2 * MARGIN)))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    box = (cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)
    out = Image.new("L", (side, side), 255)
    out.paste(img.crop(box), (0, 0))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", type=int, default=3000)
    parser.add_argument("--rows", type=int, default=3, help="number of smallest examples; one median example is added")
    parser.add_argument("--size", type=int, default=224)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    programs = json.loads((DATA / "hd" / "hd_action_programs.json").read_text())
    candidates = [(p, s, i, img) for p, sides in programs.items() for s, side in enumerate(sides)
                  for i, img in enumerate(side) if any(f"_{style}_" in a for a in img[0] for style in FINE)]
    picks = rng.sample(candidates, min(args.sample, len(candidates)))
    measured = []
    for p, s, i, img in picks:
        path = DATA / "hd" / "images" / p / SIDE_FOLDERS[s] / f"{i}.png"
        gray = Image.open(path).convert("L")
        bbox = ink_bbox(gray)
        measured.append((max(bbox[2] - bbox[0], bbox[3] - bbox[1]), path, gray, bbox, img[0]))
    measured.sort(key=lambda m: m[0])
    # The smallest examples (worst case) plus the median example (typical case).
    rows = [("smallest", m) for m in measured[:args.rows]] + [("median", measured[len(measured) // 2])]
    sizes = np.array([m[0] for m in measured])
    print(f"ink box longest side over {len(sizes)} sampled hd images with fine styles: "
          f"p10 {np.percentile(sizes, 10):.0f}, median {np.median(sizes):.0f}, p90 {np.percentile(sizes, 90):.0f} px; "
          f"at most 100 px: {100 * (sizes <= 100).mean():.1f}%; at most 150 px: {100 * (sizes <= 150).mean():.1f}%")
    print(f"after downscaling 512 -> {args.size} without crop, the median shape spans "
          f"{np.median(sizes) * args.size / 512:.0f} px and the smallest 10% at most {np.percentile(sizes, 10) * args.size / 512:.0f} px")

    big, small, gap, pad, text_h = 512, args.size, 16, 16, 22
    font = ImageFont.load_default(size=14)
    width = 2 * pad + 3 * big + 2 * gap
    height = 2 * pad + text_h + len(rows) * (text_h + big + gap) - gap
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    headers = ["original 512 px", f"downscaled to {small} px, no crop", f"cropped to the ink (10% margin), then {small} px"]
    for col, text in enumerate(headers):
        draw.text((pad + col * (big + gap), pad), text, fill="black", font=font)
    y = pad + text_h
    for tag, (longest, path, gray, bbox, actions) in rows:
        styles = sorted({a.split("_")[1] for a in actions})
        label = (f"{tag} example: {path.parent.parent.name}/{path.parent.name}/{path.name}   ink box {longest} px "
                 f"({longest * small / 512:.0f} px at {small})   styles: {', '.join(styles)}")
        print(label)
        draw.text((pad, y), label, fill="black", font=font)
        y += text_h
        views = [gray, gray.resize((small, small), Image.BICUBIC),
                 crop_to_ink(gray, bbox).resize((small, small), Image.BICUBIC)]
        for col, view in enumerate(views):
            x = pad + col * (big + gap)
            draw.rectangle([x - 1, y - 1, x + big, y + big], outline=(200, 200, 200))
            ox, oy = (big - view.width) // 2, (big - view.height) // 2
            canvas.paste(view.convert("RGB"), (x + ox, y + oy))
            draw.rectangle([x + ox - 1, y + oy - 1, x + ox + view.width, y + oy + view.height], outline=(120, 120, 120))
        y += big + gap
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(FIGURE)
    print(f"Figure written to {FIGURE.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
