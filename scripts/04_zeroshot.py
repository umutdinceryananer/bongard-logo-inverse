"""Zero-shot test: can a ready-made VLM write the program of a Bongard-LOGO image?

Question: Without training, can Gemini write the action program of one
          Bongard-LOGO image when the grammar and a few examples are given?
          This is the evidence for Decision 3a (fine-tune a VLM or train from
          scratch) and a step beyond the pixel baseline of Vaishnav and
          Tammet (2026).
Input:    150 val images (ff 60, bd 60, hd 30), one per problem, mixed short
          and long programs and one- and two-shape images; three example
          image-program pairs per type from other val problems.
Output:   outputs/logs/zeroshot_sample.json          the sample and the examples
          outputs/logs/zeroshot_prompt.txt           the system prompt
          outputs/logs/zeroshot_<model>_<cond>.jsonl one record per image: raw
                                                     answer, parsed program, scores
          outputs/logs/zeroshot_summary.csv          scores per model, condition
                                                     and type
          outputs/logs/zeroshot_summary.md           the presentation table
Decision: 3a. Decision rule, fixed in advance: the model "cannot read" the
          drawings if style accuracy stays below 65% (majority-class baseline
          55% plus 10 points) AND action-count-within-1 accuracy is below 50%.

Conditions, same 150 images, same models:
  K1  grammar + 3 example programs as text, no example images
  K2  grammar + 3 image-program pairs of the same type
  K3  grammar + 3 image-program pairs of a different type (ff<-bd, bd<-hd, hd<-ff)
Models: gemini-2.5-flash (pixel baseline of the C-G paper) and
gemini-3.8-flash (current). Thinking at the lowest level both models accept
("low"); temperature 0 where the API honours it (Gemini 3.6+ ignores it) and
a fixed seed; one answer per image. Images are sent at their native 512 px:
the API tiles images above 384 px into 768 px tiles and does not downscale,
so the 2c crop is not needed.

The API key is read from the environment variable GEMINI_API_KEY or from a
.env file in the repository root (never committed).

Usage:
  python scripts/04_zeroshot.py sample                     build the sample and the prompt
  python scripts/04_zeroshot.py run --model M --condition K [--limit N]
  python scripts/04_zeroshot.py summary                    tables from all jsonl files
"""

import argparse
import base64
import csv
import json
import os
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
LOG = ROOT / "outputs" / "logs"
SAMPLE_FILE = LOG / "zeroshot_sample.json"
PROMPT_FILE = LOG / "zeroshot_prompt.txt"

TYPES = ["ff", "bd", "hd"]
SAMPLE_PER_TYPE = {"ff": 60, "bd": 60, "hd": 30}
EXAMPLES_PER_TYPE = 3
OTHER_TYPE = {"ff": "bd", "bd": "hd", "hd": "ff"}  # K3: examples from a different type
SIDE_FOLDERS = ["1", "0"]  # JSON side 0 = positive = folder 1
SEPARATOR = "|"

ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
MODELS = {"gemini-2.5-flash": "pixel baseline of Vaishnav and Tammet 2026", "gemini-3.8-flash": "current model"}
GENERATION_CONFIG = {"temperature": 0, "seed": 0, "max_output_tokens": 2048,
                     "thinking_level": "low", "thinking_summaries": "none"}

STYLES = ["normal", "zigzag", "circle", "triangle", "square"]
NUM = r"(\d\.\d{3})"
LINE_RE = re.compile(rf"^line_([a-z]+)_{NUM}-{NUM}$")           # output format: length-turn
ARC_RE = re.compile(rf"^arc_([a-z]+)_{NUM}-{NUM}$")             # output format: angle-turn (radius dropped)
DATASET_ARC_RE = re.compile(rf"^arc_([a-z]+)_{NUM}_{NUM}-{NUM}$")

SYSTEM_PROMPT = """You convert one image into the LOGO-style action program that draws it.

Grammar (EBNF):
  program := shape { "\\n|\\n" shape }
  shape   := action { "\\n" action }
  action  := line | arc
  line    := "line_" style "_" number "-" number      (length, turn)
  arc     := "arc_" style "_" number "-" number       (arc angle, turn)
  style   := "normal" | "zigzag" | "circle" | "triangle" | "square"
  number  := digit "." digit digit digit              (0.000 to 1.000)

Meaning. A pen draws each shape as one continuous stroke. Each action first turns the pen, then draws.
  turn: 0.500 = no turn, 0.750 = 90 degrees left, 0.833 = 120 degrees left, 0.250 = 90 degrees right
        (0.000 to 1.000 maps linearly to -180 to +180 degrees; the first action of a shape has turn 0.500).
  length: relative, 1.000 is the unit length.
  arc angle: 0.625 = 90 degree arc turning left, 0.375 = 90 degree arc turning right
        (0.000 to 1.000 maps linearly to -360 to +360 degrees). The arc radius is never written.
  style: "normal" is a plain stroke; "zigzag" is a zigzag stroke; "circle", "triangle" and "square"
        mean the stroke is a row of small stamps of that shape.

Rules.
  - Two shapes in the image are two shape blocks separated by a line containing only "|".
  - The shape with fewer actions comes first; if equal, the one whose text sorts first alphabetically.
  - Write only the program: one action per line, no explanation, no code fences, no numbering.
"""


# Programs -----------------------------------------------------------------------------------

def to_output_format(program):
    """Dataset nesting (list of shapes, each a list of action strings) -> output string (decisions 1a-1c)."""
    shapes = []
    for shape in program:
        actions = []
        for a in shape:
            m = DATASET_ARC_RE.match(a)
            actions.append(f"arc_{m.group(1)}_{m.group(3)}-{m.group(4)}" if m else a)
        shapes.append(actions)
    return "\n|\n".join("\n".join(s) for s in canonical_order(shapes))


def canonical_order(shapes):
    return sorted(shapes, key=lambda s: (len(s), "\n".join(s)))


def parse_action(line):
    """Output-format action -> (kind, style, numbers) or None."""
    if m := LINE_RE.match(line):
        return "line", m.group(1), (float(m.group(2)), float(m.group(3)))
    if m := ARC_RE.match(line):
        return "arc", m.group(1), (float(m.group(2)), float(m.group(3)))
    return None


def parse_answer(text):
    """Model answer -> (shapes as lists of raw lines, number of invalid lines)."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", text).strip()
    shapes, current, invalid = [], [], 0
    for raw in text.splitlines():
        line = raw.strip().strip("`").strip()
        if not line:
            continue
        if line == SEPARATOR or set(line) <= {"|", " "}:
            if current:
                shapes.append(current)
            current = []
            continue
        if parse_action(line) is None:
            invalid += 1
        current.append(line)
    if current:
        shapes.append(current)
    return shapes, invalid


# Scoring ------------------------------------------------------------------------------------

def align(pred, gold):
    """Action-level Levenshtein alignment. Returns (distance, pairs) where pairs are
    (pred index or None, gold index or None)."""
    n, m = len(pred), len(gold)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        d[i][0] = i
    for j in range(1, m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (pred[i - 1] != gold[j - 1]))
    pairs, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (pred[i - 1] != gold[j - 1]):
            pairs.append((i - 1, j - 1)); i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            pairs.append((i - 1, None)); i -= 1
        else:
            pairs.append((None, j - 1)); j -= 1
    return d[n][m], pairs[::-1]


def simulate(shape):
    """Turtle simulation of one shape (unit length, arc radius 0.5): end point,
    total heading change and path length. Positions in unit lengths."""
    import math
    x = y = 0.0
    heading = 0.0  # degrees, left positive
    total_turn = length = 0.0
    for line in shape:
        p = parse_action(line)
        if p is None:
            continue
        kind, _, (v, turn) = p
        turn_deg = turn * 360 - 180
        heading += turn_deg
        total_turn += turn_deg
        if kind == "line":
            x += v * math.cos(math.radians(heading))
            y += v * math.sin(math.radians(heading))
            length += v
        else:  # arc of radius 0.5, extent v*720-360 degrees, centre to the left of the heading
            r, extent = 0.5, v * 720 - 360
            cx = x - r * math.sin(math.radians(heading))
            cy = y + r * math.cos(math.radians(heading))
            dx, dy = x - cx, y - cy
            e = math.radians(extent)
            x = cx + dx * math.cos(e) - dy * math.sin(e)
            y = cy + dx * math.sin(e) + dy * math.cos(e)
            heading += extent
            total_turn += extent
            length += abs(e) * r
    return (x, y), heading, total_turn, length


CLOSED_TOLERANCE = 0.05  # closed if the end point lies within 5% of the path length from the start


def is_closed(shape):
    (x, y), _, _, length = simulate(shape)
    return length > 0 and (x * x + y * y) ** 0.5 <= CLOSED_TOLERANCE * length


def with_turn(line, turn):
    p = parse_action(line)
    kind, style, (v, _) = p
    return f"{kind}_{style}_{v:.3f}-{turn:.3f}"


def reversed_shape(shape):
    """The same stroke traced in the opposite direction: actions in reverse
    order, arc angles negated (a -> 1-a), junction turns negated and shifted."""
    acts = [parse_action(a) for a in shape]
    if any(a is None for a in acts):
        return list(reversed(shape))
    out = []
    n = len(acts)
    for j in range(n - 1, -1, -1):
        kind, style, (v, _) = acts[j]
        v2 = v if kind == "line" else round(1 - v, 3)
        turn = 0.5 if j == n - 1 else round(1 - acts[j + 1][2][1], 3)
        out.append(f"{kind}_{style}_{v2:.3f}-{turn:.3f}")
    return out


def rotated_shape(shape, k):
    """Closed shape started at action k: the closing junction turn becomes the
    turn of the former first action."""
    if k == 0 or any(parse_action(a) is None for a in shape):
        return list(shape)
    _, heading, _, _ = simulate(shape)
    closing = (-heading + 180) % 360 - 180            # turn needed at the closing junction, degrees
    closing_turn = round((closing + 180) / 360, 3)
    rot = shape[k:] + shape[:k]
    rot[0] = with_turn(rot[0], 0.5)
    rot[len(shape) - k] = with_turn(rot[len(shape) - k], closing_turn)
    return rot


def equivalent_forms(shape):
    """All descriptions of the gold shape that draw the same stroke: for closed
    shapes every start point in both directions, for open shapes both directions."""
    forms = []
    starts = range(len(shape)) if is_closed(shape) else [0]
    for k in starts:
        rot = rotated_shape(shape, k)
        forms.append(rot)
        forms.append(reversed_shape(rot))
    return forms


def match_shapes(pred_shapes, gold_shapes):
    """Pair predicted shapes with gold shapes so that the total action-level edit
    distance is smallest (all assignments are tried; images have at most two
    shapes). Unpaired shapes count as fully unmatched. Returns the total distance
    and the list of (pred index or None, gold index or None) action pairs."""
    from itertools import permutations
    best = None
    n = max(len(pred_shapes), len(gold_shapes))
    for perm in permutations(range(n)):
        total, pairs = 0, []
        for gi, pi in enumerate(perm):
            p = pred_shapes[pi] if pi < len(pred_shapes) else []
            g = gold_shapes[gi] if gi < len(gold_shapes) else []
            d, ap = align(p, g)
            total += d
            pairs += [((pi, a) if a is not None else None, (gi, b) if b is not None else None) for a, b in ap]
        if best is None or total < best[0]:
            best = (total, pairs)
    return best


def score(answer_text, gold_text):
    """Metrics 1-6 of the experiment design for one answer.

    Shapes are paired by the best assignment (not by canonical order) before the
    action-level alignment, so that one missing action, which can change the
    canonical order, does not wreck the whole alignment. Exact match still
    compares the canonical-order strings."""
    pred_shapes, invalid = parse_answer(answer_text)
    gold_shapes = [s.split("\n") for s in gold_text.split("\n|\n")]
    pred_shapes = canonical_order(pred_shapes)
    pred_flat = [a for s in pred_shapes for a in s]
    gold_flat = [a for s in gold_shapes for a in s]
    distance, pairs = match_shapes(pred_shapes, gold_shapes)

    def field_counts(pairs, gold_lookup):
        kind_ok = style_ok = num_ok = num_tol = 0
        for pp, gg in pairs:
            if pp is None or gg is None:
                continue
            p, g = parse_action(pred_shapes[pp[0]][pp[1]]), parse_action(gold_lookup[gg[0]][gg[1]])
            if p is None:
                continue
            kind_ok += p[0] == g[0]
            style_ok += p[1] == g[1]
            num_ok += p[2] == g[2]
            num_tol += all(abs(x - y) <= 0.02 for x, y in zip(p[2], g[2]))
        return kind_ok, style_ok, num_ok, num_tol

    # Column 1, "given order": the gold program as written.
    kind_ok, style_ok, num_ok, num_tol = field_counts(pairs, gold_shapes)
    columns = len(pairs)  # matched pairs plus unmatched actions on either side

    # Column 2, "best alignment": for each paired shape, the equivalent description
    # of the gold shape (start point and direction) with the smallest edit distance.
    assignment = {}
    for pp, gg in pairs:
        if pp is not None and gg is not None:
            assignment[gg[0]] = pp[0]
    best_distance, best_pairs, best_gold = 0, [], {}
    for gi, gold in enumerate(gold_shapes):
        pi = assignment.get(gi)
        pred = pred_shapes[pi] if pi is not None else []
        choice = None
        for form in equivalent_forms(gold):
            d, ap = align(pred, form)
            if choice is None or d < choice[0]:
                choice = (d, ap, form)
        d, ap, form = choice
        best_distance += d
        best_gold[gi] = form
        best_pairs += [((pi, a) if a is not None and pi is not None else None, (gi, b) if b is not None else None)
                       for a, b in ap]
    for pi in range(len(pred_shapes)):  # predicted shapes without a gold partner
        if pi not in assignment.values():
            best_distance += len(pred_shapes[pi])
            best_pairs += [((pi, a), None) for a in range(len(pred_shapes[pi]))]
    b_kind, b_style, b_num, b_tol = field_counts(best_pairs, best_gold)
    b_columns = len(best_pairs)

    pred_text = "\n|\n".join("\n".join(s) for s in pred_shapes)
    return {
        "valid": invalid == 0 and len(pred_flat) > 0,
        "invalid_lines": invalid,
        "shape_count_ok": len(pred_shapes) == len(gold_shapes),
        "action_count_within_1": abs(len(pred_flat) - len(gold_flat)) <= 1,
        "kind_acc": kind_ok / columns if columns else 0.0,
        "style_acc": style_ok / columns if columns else 0.0,
        "number_acc": num_ok / columns if columns else 0.0,
        "number_acc_tol": num_tol / columns if columns else 0.0,
        "kind_acc_best": b_kind / b_columns if b_columns else 0.0,
        "style_acc_best": b_style / b_columns if b_columns else 0.0,
        "number_acc_best": b_num / b_columns if b_columns else 0.0,
        "number_acc_tol_best": b_tol / b_columns if b_columns else 0.0,
        "exact": pred_text == gold_text,
        "edit_distance": distance,
        "edit_distance_best": best_distance,
        "edit_distance_norm": distance / max(len(gold_flat), 1),
        "gold_closed": [is_closed(s) for s in gold_shapes],
        "pred_actions": len(pred_flat),
        "gold_actions": len(gold_flat),
        "pred_program": pred_text,
    }


# Sample -------------------------------------------------------------------------------------

def load_programs():
    return {t: json.loads((DATA / t / f"{t}_action_programs.json").read_text()) for t in TYPES}


def image_record(t, problem, side, index, programs):
    program = programs[t][problem][side][index]
    return {"type": t, "problem": problem, "side": side, "index": index,
            "path": f"{t}/images/{problem}/{SIDE_FOLDERS[side]}/{index}.png",
            "program": program, "target": to_output_format(program),
            "n_shapes": len(program), "n_actions": sum(len(s) for s in program)}


def spread(items, k, key):
    """k items spread evenly over the items sorted by key (short and long programs mixed)."""
    items = sorted(items, key=key)
    if k >= len(items):
        return items
    return [items[round(i * (len(items) - 1) / (k - 1))] for i in range(k)]


def build_sample(seed):
    rng = random.Random(seed)
    programs = load_programs()
    split = json.loads((DATA / "ShapeBongard_V2_split.json").read_text())
    val = defaultdict(list)
    for p in split["val"]:
        val[p.split("_")[0]].append(p)
    sample, examples = [], {}
    for t in TYPES:
        problems = sorted(val[t])
        # one random image per problem, with its length and shape count
        candidates = []
        for p in problems:
            side, index = rng.randrange(2), rng.randrange(7)
            candidates.append(image_record(t, p, side, index, programs))
        k = SAMPLE_PER_TYPE[t]
        if t == "hd":
            chosen = spread(candidates, k, key=lambda r: (r["n_actions"], r["problem"]))
        else:  # ff and bd: half one-shape, half two-shape problems, each half spread over length;
            # if one stratum is too small, the other fills the quota
            chosen = []
            for n_shapes in (1, 2):
                pool = [r for r in candidates if r["n_shapes"] == n_shapes]
                chosen += spread(pool, k // 2, key=lambda r: (r["n_actions"], r["problem"]))
            if len(chosen) < k:
                taken = {r["problem"] for r in chosen}
                pool = [r for r in candidates if r["problem"] not in taken]
                chosen += spread(pool, k - len(chosen), key=lambda r: (r["n_actions"], r["problem"]))
        chosen_problems = {r["problem"] for r in chosen}
        rest = [r for r in candidates if r["problem"] not in chosen_problems]
        examples[t] = rng.sample(rest, EXAMPLES_PER_TYPE)
        sample += chosen
    return {"seed": seed, "built": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sample": sample, "examples": examples}


def cmd_sample(args):
    LOG.mkdir(parents=True, exist_ok=True)
    data = build_sample(args.seed)
    SAMPLE_FILE.write_text(json.dumps(data, indent=1), encoding="utf-8")
    PROMPT_FILE.write_text(SYSTEM_PROMPT, encoding="utf-8")
    by_type = defaultdict(lambda: defaultdict(int))
    for r in data["sample"]:
        by_type[r["type"]][f"{r['n_shapes']} shape"] += 1
    print(f"sample: {len(data['sample'])} images, one per problem; "
          + "; ".join(f"{t}: {dict(c)}" for t, c in by_type.items()))
    for t in TYPES:
        print(f"  {t} actions per image: {sorted(r['n_actions'] for r in data['sample'] if r['type'] == t)}")
        print(f"  {t} examples: {[e['problem'] for e in data['examples'][t]]}")
    print(f"written: {SAMPLE_FILE.relative_to(ROOT).as_posix()}, {PROMPT_FILE.relative_to(ROOT).as_posix()}")


# API ----------------------------------------------------------------------------------------

def api_key():
    key = os.environ.get("GEMINI_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        sys.exit("GEMINI_API_KEY is not set (environment variable or .env in the repository root).")
    return key


def crop_to_ink(path, margin=0.10, size=512):
    """Decision 2c crop: square around the ink bounding box with a proportional
    margin, white padding outside the image, resized back to 512 px so that the
    pixel count sent to the API is the same as without the crop."""
    import numpy as np
    from PIL import Image
    img = Image.open(DATA / path).convert("L")
    ys, xs = np.nonzero(np.asarray(img) < 128)
    x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    side = int(round(max(x1 - x0, y1 - y0) * (1 + 2 * margin)))
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    out = Image.new("L", (side, side), 255)
    out.paste(img.crop((cx - side // 2, cy - side // 2, cx - side // 2 + side, cy - side // 2 + side)), (0, 0))
    return out.resize((size, size), Image.BICUBIC)


def image_item(path, crop=False):
    if crop:
        import io
        buf = io.BytesIO()
        crop_to_ink(path).save(buf, format="PNG")
        raw = buf.getvalue()
    else:
        raw = (DATA / path).read_bytes()
    return {"type": "image", "data": base64.b64encode(raw).decode(), "mime_type": "image/png", "resolution": "high"}


def build_input(record, condition, examples, crop=False):
    """Content items for one query under one condition; the crop applies to every image sent."""
    t = record["type"]
    items = []
    if condition == "K1":
        text = "Three example programs in this format:\n\n" + "\n\n".join(e["target"] for e in examples[t])
        items.append({"type": "text", "text": text})
    else:
        source = t if condition == "K2" else OTHER_TYPE[t]
        items.append({"type": "text", "text": "Three examples, each an image followed by its program."})
        for e in examples[source]:
            items.append({"type": "text", "text": "Image:"})
            items.append(image_item(e["path"], crop))
            items.append({"type": "text", "text": "Program:\n" + e["target"]})
    items.append({"type": "text", "text": "Now write the program of this image.\nImage:"})
    items.append(image_item(record["path"], crop))
    items.append({"type": "text", "text": "Program:"})
    return items


def call_model(key, model, items, retries=5):
    body = {"model": model, "system_instruction": SYSTEM_PROMPT, "input": items,
            "generation_config": GENERATION_CONFIG, "store": False}
    for attempt in range(retries):
        t0 = time.time()
        r = requests.post(ENDPOINT, headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                          json=body, timeout=180)
        latency = time.time() - t0
        if r.status_code == 200:
            return r.json(), latency
        if r.status_code in (429, 500, 502, 503, 504) and attempt < retries - 1:
            wait = 2 ** attempt * 5
            print(f"    HTTP {r.status_code}, retrying in {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    raise RuntimeError("retries exhausted")


def answer_text(response):
    for step in response.get("steps", []):
        if step.get("type") == "model_output":
            return "\n".join(c.get("text", "") for c in step.get("content", []) if c.get("type") == "text")
    return ""


def cmd_run(args):
    if not SAMPLE_FILE.exists():
        sys.exit("run `sample` first")
    key = api_key()
    data = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    out = LOG / f"zeroshot_{args.model}_{args.condition}{'_crop' if args.crop else ''}.jsonl"
    done = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "path" in rec:
                done.add(rec["path"])
    records = [r for r in data["sample"] if r["path"] not in done]
    if args.same_as:  # restrict to the images already answered in another results file
        wanted = [json.loads(l)["path"] for l in Path(args.same_as).read_text(encoding="utf-8").splitlines()
                  if "\"path\"" in l]
        records = [r for r in records if r["path"] in set(wanted)]
    # Round-robin over (type, shape count) so that a partial run mixes types and shape counts.
    groups = defaultdict(list)
    for r in records:
        groups[(r["type"], r["n_shapes"])].append(r)
    order = [groups[k] for k in sorted(groups)]
    records = [g[i] for i in range(max((len(g) for g in order), default=0)) for g in order if i < len(g)]
    if args.limit:
        records = records[:args.limit]
    print(f"{args.model} {args.condition}: {len(done)} done, running {len(records)}")
    with out.open("a", encoding="utf-8") as f:
        if not done:
            f.write(json.dumps({
                "header": True, "endpoint": ENDPOINT, "api_version": "v1beta", "model_requested": args.model,
                "condition": args.condition, "seed": GENERATION_CONFIG["seed"],
                "thinking_level": GENERATION_CONFIG["thinking_level"],
                "temperature": f"{GENERATION_CONFIG['temperature']} requested; ignored by Gemini 3.6 and later "
                               "according to the API documentation (checked 2026-10-18)",
                "generation_config": GENERATION_CONFIG,
                "image_preprocessing": "crop to the ink, 10% proportional margin, square, resized to 512 px"
                                       if args.crop else "none, native 512 px",
                "image_resolution_note": "resolution=high; per the API documentation the API tiles images above "
                                         "384 px into 768 px tiles and does not downscale a 512 px image",
                "closed_shape_rule": f"a gold shape is closed if its simulated end point (unit length, arc radius "
                                     f"0.5, turn before each action) lies within {CLOSED_TOLERANCE:.0%} of the "
                                     "path length from its start point; best-alignment metrics try every start "
                                     "point and both directions for closed shapes, both directions for open ones",
                "started": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")
        for k, rec in enumerate(records, 1):
            response, latency = call_model(key, args.model,
                                           build_input(rec, args.condition, data["examples"], args.crop))
            text = answer_text(response)
            s = score(text, rec["target"])
            row = {"path": rec["path"], "type": rec["type"], "problem": rec["problem"], "target": rec["target"],
                   "answer": text, "model_reported": response.get("model"), "usage": response.get("usage"),
                   "latency_s": round(latency, 2), **s}
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"  [{k}/{len(records)}] {rec['path']}: valid={s['valid']} shapes_ok={s['shape_count_ok']} "
                  f"count+-1={s['action_count_within_1']} style={s['style_acc']:.2f}/{s['style_acc_best']:.2f} "
                  f"num={s['number_acc']:.2f}/{s['number_acc_best']:.2f} exact={s['exact']} "
                  f"ed={s['edit_distance']}/{s['edit_distance_best']}")
            if args.show:
                print("    --- answer ---"); print("    " + text.replace("\n", "\n    "))
                print("    --- target ---"); print("    " + rec["target"].replace("\n", "\n    "))


# Summary ------------------------------------------------------------------------------------

METRICS = [("valid", "1. valid output (%)"), ("shape_count_ok", "2. shape count correct (%)"),
           ("action_count_within_1", "3. action count within +/-1 (%)"),
           ("kind_acc", "4a. action type accuracy, given order (%)"),
           ("kind_acc_best", "4a'. action type accuracy, best alignment (%)"),
           ("style_acc", "4b. style accuracy, given order (%)"),
           ("style_acc_best", "4b'. style accuracy, best alignment (%)"),
           ("number_acc", "4c. number accuracy exact, given order (%)"),
           ("number_acc_best", "4c'. number accuracy exact, best alignment (%)"),
           ("number_acc_tol", "4d. number accuracy within 0.02, given order (%)"),
           ("number_acc_tol_best", "4d'. number accuracy within 0.02, best alignment (%)"),
           ("exact", "5. exact match (%)"),
           ("edit_distance", "6. edit distance, given order (actions, mean)"),
           ("edit_distance_best", "6'. edit distance, best alignment (actions, mean)")]
COUNT_METRICS = {"edit_distance", "edit_distance_best"}
DECISION_MARGIN = 10.0  # style accuracy must exceed the type's majority-class baseline by this many points


def style_baselines():
    """Majority stroke-style share per type in the train split (the baseline the decision rule uses)."""
    split = json.loads((DATA / "ShapeBongard_V2_split.json").read_text())
    train = set(split["train"])
    out = {}
    for t, programs in load_programs().items():
        c = defaultdict(int)
        for p, sides in programs.items():
            if p in train:
                for side in sides:
                    for img in side:
                        for shape in img:
                            for a in shape:
                                c[a.split("_")[1]] += 1
        total = sum(c.values())
        style, n = max(c.items(), key=lambda kv: kv[1])
        out[t] = (style, 100 * n / total)
    return out


def aggregate(rows):
    out = {}
    for key, _ in METRICS:
        vals = [float(r.get(key, float("nan"))) for r in rows]
        out[key] = statistics.mean(vals) * (1 if key in COUNT_METRICS else 100) if vals else float("nan")
    out["n"] = len(rows)
    thoughts = [r["usage"]["total_thought_tokens"] for r in rows if r.get("usage")]
    out["thought_tokens_mean"] = statistics.mean(thoughts) if thoughts else float("nan")
    return out


def cmd_summary(args):
    groups = defaultdict(list)
    for f in sorted(LOG.glob("zeroshot_*_K*.jsonl")):
        m = re.match(r"zeroshot_(.+)_(K[123])(_crop)?$", f.stem)
        if not m:
            continue
        model, cond = m.group(1), m.group(2) + (m.group(3) or "")
        for line in f.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            if "path" in rec:
                groups[(model, cond, rec["type"])].append(rec)
                groups[(model, cond, "all")].append(rec)
                if rec["type"] == "ff":  # ff split by shape count, to read next to bd (two-shape only)
                    n_shapes = rec["target"].count("\n|\n") + 1
                    groups[(model, cond, f"ff_{n_shapes}shape")].append(rec)
    if not groups:
        sys.exit("no results yet")
    keys = sorted(groups)
    baselines = style_baselines()
    with (LOG / "zeroshot_summary.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["model", "condition", "type", "n"] + [k for k, _ in METRICS] + ["thought_tokens_mean"])
        for model, cond, t in keys:
            a = aggregate(groups[(model, cond, t)])
            w.writerow([model, cond, t, a["n"]] + [f"{a[k]:.1f}" for k, _ in METRICS] + [f"{a['thought_tokens_mean']:.1f}"])
    columns = [(m, c) for m, c, t in keys if t == "all"]
    agg = {mc: aggregate(groups[(mc[0], mc[1], "all")]) for mc in columns}
    lines = ["| metric | " + " | ".join(f"{m} {c} (n={agg[(m, c)]['n']})" for m, c in columns) + " |",
             "|---|" + "---|" * len(columns)]
    for key, label in METRICS:
        lines.append(f"| {label} | " + " | ".join(f"{agg[mc][key]:.1f}" for mc in columns) + " |")
    lines.append("| style accuracy, best minus given (points) | "
                 + " | ".join(f"{agg[mc]['style_acc_best'] - agg[mc]['style_acc']:.1f}" for mc in columns) + " |")
    lines.append("| thought tokens, mean | " + " | ".join(f"{agg[mc]['thought_tokens_mean']:.0f}" for mc in columns) + " |")
    lines.append("| baseline, style accuracy: random | " + " | ".join("20.0" for _ in columns) + " |")
    for t in TYPES:
        lines.append(f"| baseline, style accuracy: majority in train, {t} ({baselines[t][0]}) | "
                     + " | ".join(f"{baselines[t][1]:.1f}" for _ in columns) + " |")
    lines.append("")
    lines.append("Per type: style accuracy best alignment / given order | action count within 1 | exact | "
                 "passes its baseline + 10 points?")
    for model, cond, t in keys:
        if t == "all":
            continue
        a = aggregate(groups[(model, cond, t)])
        base = baselines[t.split("_")[0]][1]
        verdict = "yes" if a["style_acc_best"] >= base + DECISION_MARGIN else "no"
        lines.append(f"- {model} {cond} {t} (n={a['n']}): {a['style_acc_best']:.1f} / {a['style_acc']:.1f} | "
                     f"{a['action_count_within_1']:.1f} | {a['exact']:.1f} | {verdict} (baseline {base:.1f})")
    lines.append("")
    lines.append("Decision rule (3a): 'cannot read' only if, in every type, style accuracy (best alignment) is "
                 "below the type's majority baseline + 10 points and action count within 1 is below 50%.")
    (LOG / "zeroshot_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


def cmd_rescore(args):
    """Recompute the scores of every stored answer (after a change to the scoring code)."""
    for f in sorted(LOG.glob("zeroshot_*_K*.jsonl")):
        lines = f.read_text(encoding="utf-8").splitlines()
        out = []
        for line in lines:
            rec = json.loads(line)
            if "path" in rec:
                keep = {k: rec[k] for k in ("path", "type", "problem", "target", "answer", "model_reported",
                                            "usage", "latency_s")}
                rec = {**keep, **score(rec["answer"], rec["target"])}
            out.append(json.dumps(rec))
        f.write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"rescored {f.name}: {sum('\"path\"' in l for l in lines)} answers")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("sample"); p.add_argument("--seed", type=int, default=0); p.set_defaults(func=cmd_sample)
    p = sub.add_parser("run")
    p.add_argument("--model", required=True, choices=sorted(MODELS))
    p.add_argument("--condition", required=True, choices=["K1", "K2", "K3"])
    p.add_argument("--limit", type=int, default=0, help="run only the first N remaining images")
    p.add_argument("--show", action="store_true", help="print each answer and target")
    p.add_argument("--crop", action="store_true", help="crop every image to the ink (decision 2c) before sending")
    p.add_argument("--same-as", help="run only the images already answered in this results file")
    p.set_defaults(func=cmd_run)
    p = sub.add_parser("summary"); p.set_defaults(func=cmd_summary)
    p = sub.add_parser("rescore"); p.set_defaults(func=cmd_rescore)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
