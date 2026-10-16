"""Statistics of the action programs: length, vocabulary, numeric values, FF length gap.

Question: What does the model have to produce? How long are the programs, which
          action types and styles occur, do the numeric arguments come from a
          small fixed set or from a continuum, and how much longer are the
          test_ff programs than the training ones?
Input:    data/ShapeBongard_V2/<type>/<type>_action_programs.json and
          ShapeBongard_V2_split.json.
Output:   outputs/figures/03_length.png          actions per image by problem type
          outputs/figures/03_vocabulary.png      action type x style by problem type
          outputs/figures/03_numeric_values.png  how many distinct values each
                                                 numeric field takes
          outputs/figures/03_ff_length_gap.png   actions per image in ff by split
          A text report on stdout and in outputs/logs/03_stats.txt; the numbers
          behind the figures in outputs/logs/03_stats.json.
Decision: 1 (output format), 5 (loss: numeric values as tokens or as a
          regression target), 7 (sequence length budget), 8 (test_ff is a
          length-extrapolation test).

Usage: python scripts/03_stats.py
"""

import json
import re
from collections import Counter
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "ShapeBongard_V2"
FIG = ROOT / "outputs" / "figures"
LOG = ROOT / "outputs" / "logs"

TYPES = ["ff", "bd", "hd"]
TYPE_LABEL = {"ff": "ff (free-form)", "bd": "bd (basic)", "hd": "hd (abstract)"}
STYLES = ["normal", "zigzag", "circle", "triangle", "square"]
FIELDS = ["line length", "arc radius", "arc angle", "turn"]

NUM = r"(\d\.\d{3})"
LINE_RE = re.compile(rf"^line_([a-z]+)_{NUM}-{NUM}$")
ARC_RE = re.compile(rf"^arc_([a-z]+)_{NUM}_{NUM}-{NUM}$")

# Colors: the first three categorical slots of the reference data-viz palette,
# validated for all pairs in light mode. Chart chrome from the same palette.
COLORS = {"ff": "#2a78d6", "bd": "#eb6834", "hd": "#1baf7a"}
SPLIT_COLORS = {"train": "#2a78d6", "val": "#eb6834", "test_ff": "#1baf7a"}
SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"

report = []


def say(text=""):
    print(text)
    report.append(text)


def heading(title):
    say()
    say(title)
    say("-" * len(title))


def parse(action):
    """Split an action string into (kind, style, {field: value string})."""
    if m := LINE_RE.match(action):
        return "line", m.group(1), {"line length": m.group(2), "turn": m.group(3)}
    if m := ARC_RE.match(action):
        return "arc", m.group(1), {"arc radius": m.group(2), "arc angle": m.group(3), "turn": m.group(4)}
    raise ValueError(f"action does not match the grammar: {action}")


def load_images():
    """One record per image: type, problem, split, shape lengths, flat action list."""
    split = json.loads((DATA / "ShapeBongard_V2_split.json").read_text())
    where = {p: k for k, v in split.items() for p in v}
    images = []
    for t in TYPES:
        programs = json.loads((DATA / t / f"{t}_action_programs.json").read_text())
        for problem, sides in programs.items():
            for side in sides:
                for image in side:
                    actions = [a for shape in image for a in shape]
                    images.append({"type": t, "problem": problem, "split": where[problem],
                                   "shape_lengths": [len(s) for s in image], "n_actions": len(actions),
                                   "n_chars": len(" ".join(actions)), "actions": actions})
    return images


def describe(values):
    a = np.asarray(values)
    return {"n": int(a.size), "min": int(a.min()), "median": float(np.median(a)),
            "mean": round(float(a.mean()), 2), "p95": float(np.percentile(a, 95)), "max": int(a.max())}


def fmt(d):
    return f"min {d['min']}, median {d['median']:g}, mean {d['mean']}, p95 {d['p95']:g}, max {d['max']}"


def new_axes(nrows=1, ncols=1, figsize=(9, 4.5)):
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize, dpi=150, facecolor=SURFACE)
    for ax in np.atleast_1d(axes).ravel():
        ax.set_facecolor(SURFACE)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(AXIS)
        ax.tick_params(colors=MUTED, labelsize=9, length=0)
        ax.yaxis.grid(True, color=GRID, linewidth=1)
        ax.set_axisbelow(True)
        ax.xaxis.label.set_color(INK2)
        ax.yaxis.label.set_color(INK2)
        ax.title.set_color(INK)
    return fig, axes


def legend(ax, **kw):
    leg = ax.legend(frameon=False, fontsize=9, **kw)
    for text in leg.get_texts():
        text.set_color(INK2)


def save(fig, name):
    FIG.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIG / name, facecolor=SURFACE)
    plt.close(fig)
    say(f"  figure: outputs/figures/{name}")


def grouped_bars(ax, xs, series, colors, labels):
    """Grouped bars: one group per x, one bar per series; series = {name: [y per x]}."""
    k = len(series)
    width = 0.8 / k
    for i, (name, ys) in enumerate(series.items()):
        offsets = [x + (i - (k - 1) / 2) * width for x in xs]
        ax.bar(offsets, ys, width=width * 0.85, color=colors[name], label=labels[name], linewidth=0)
    ax.set_xticks(list(xs))


# 1. Length ---------------------------------------------------------------------------------

def section_length(images):
    heading("1. Program length")
    out = {}
    for t in TYPES:
        imgs = [i for i in images if i["type"] == t]
        per_image = describe([i["n_actions"] for i in imgs])
        per_shape = describe([n for i in imgs for n in i["shape_lengths"]])
        chars = describe([i["n_chars"] for i in imgs])
        say(f"  {t}: actions per image: {fmt(per_image)}")
        say(f"      actions per shape: {fmt(per_shape)}")
        say(f"      characters per program (actions joined by spaces): {fmt(chars)}")
        by_split = {}
        for s in sorted({i["split"] for i in imgs}):
            by_split[s] = describe([i["n_actions"] for i in imgs if i["split"] == s])
            say(f"      {s:13s} actions per image: {fmt(by_split[s])}")
        out[t] = {"per_image": per_image, "per_shape": per_shape, "chars": chars, "by_split": by_split}

    xs = range(1, max(i["n_actions"] for i in images) + 1)
    series = {}
    for t in TYPES:
        counts = Counter(i["n_actions"] for i in images if i["type"] == t)
        n = sum(counts.values())
        series[t] = [100 * counts.get(x, 0) / n for x in xs]
    fig, ax = new_axes()
    grouped_bars(ax, xs, series, COLORS, TYPE_LABEL)
    ax.set_xlabel("actions per image (both shapes together)")
    ax.set_ylabel("share of images (%)")
    ax.set_title("Program length by problem type", loc="left", fontsize=11)
    legend(ax)
    save(fig, "03_length.png")
    return out


# 2. Vocabulary -----------------------------------------------------------------------------

def section_vocabulary(images):
    heading("2. Vocabulary: action type and style")
    combos = [f"{kind} {style}" for kind in ("line", "arc") for style in STYLES]
    out = {}
    all_strings = Counter()
    for t in TYPES:
        c = Counter()
        strings = Counter()
        for i in (i for i in images if i["type"] == t):
            for a in i["actions"]:
                kind, style, _ = parse(a)
                c[f"{kind} {style}"] += 1
                strings[a] += 1
        n = sum(c.values())
        all_strings.update(strings)
        shares = {k: round(100 * c[k] / n, 1) for k in combos}
        say(f"  {t}: {n} actions; share (%) " + ", ".join(f"{k} {v}" for k, v in shares.items()))
        cover = coverage(strings)
        say(f"      distinct action strings: {len(strings)}; strings needed to cover 90% of occurrences: "
            f"{cover[90]}, 99%: {cover[99]}")
        out[t] = {"n_actions": n, "share": shares, "distinct_strings": len(strings), "cover": cover}
    cover = coverage(all_strings)
    say(f"  all types: distinct action strings {len(all_strings)}; 90% coverage {cover[90]}, 99% {cover[99]}")
    out["all"] = {"distinct_strings": len(all_strings), "cover": cover}

    xs = range(len(combos))
    series = {t: [out[t]["share"][k] for k in combos] for t in TYPES}
    fig, ax = new_axes(figsize=(9, 4.5))
    grouped_bars(ax, xs, series, COLORS, TYPE_LABEL)
    ax.set_xticklabels(combos, rotation=30, ha="right")
    ax.set_ylabel("share of actions (%)")
    ax.set_title("Action type and stroke style by problem type", loc="left", fontsize=11)
    legend(ax)
    save(fig, "03_vocabulary.png")
    return out


def coverage(counter):
    """Number of most frequent items needed to cover 90% and 99% of occurrences."""
    total = sum(counter.values())
    acc, result = 0, {}
    for k, (_, n) in enumerate(counter.most_common(), start=1):
        acc += n
        for level in (90, 99):
            if level not in result and acc >= total * level / 100:
                result[level] = k
    return result


# 3. Numeric values -------------------------------------------------------------------------

def section_numeric(images):
    heading("3. Numeric values")
    say("  Values are the 3-decimal strings in the action strings, as the model would see them.")
    values = {t: {f: Counter() for f in FIELDS} for t in TYPES}
    for i in images:
        for a in i["actions"]:
            _, _, fields = parse(a)
            for f, v in fields.items():
                values[i["type"]][f][v] += 1
    out = {}
    for f in FIELDS:
        say(f"  {f}:")
        out[f] = {}
        for t in TYPES:
            c = values[t][f]
            top = ", ".join(f"{v} ({100 * n / sum(c.values()):.1f}%)" for v, n in c.most_common(5))
            cover = coverage(c)
            say(f"      {t}: {len(c)} distinct values; 90% coverage {cover[90]}, 99% {cover[99]}; top: {top}")
            out[f][t] = {"distinct": len(c), "cover": cover, "top": c.most_common(10)}

    fig, axes = new_axes(2, 2, figsize=(9, 6.5))
    for ax, f in zip(axes.ravel(), FIELDS):
        for t in TYPES:
            c = values[t][f]
            shares = np.cumsum(sorted(c.values(), reverse=True)) / sum(c.values()) * 100
            ks = np.arange(1, len(shares) + 1)
            ax.plot(ks, shares, color=COLORS[t], linewidth=2, solid_joinstyle="round", label=TYPE_LABEL[t])
            ax.plot(ks[-1], shares[-1], "o", color=COLORS[t], markersize=6,
                    markeredgecolor=SURFACE, markeredgewidth=1.5)
            ax.annotate(f"{len(c)}", (ks[-1], shares[-1]), textcoords="offset points", xytext=(5, -3),
                        fontsize=8, color=INK2)
        ax.set_xscale("log")
        ax.set_xlim(0.9, 2000)
        ax.set_ylim(0, 105)
        ax.set_title(f, loc="left", fontsize=10)
        ax.set_xlabel("distinct values, most frequent first")
        ax.set_ylabel("cumulative share (%)")
    legend(axes[0, 0], loc="lower right")
    fig.suptitle("How many distinct values each numeric field takes", x=0.02, ha="left", fontsize=11, color=INK)
    save(fig, "03_numeric_values.png")
    return out


# 4. FF length gap --------------------------------------------------------------------------

def section_ff_gap(images):
    heading("4. Free-form length gap between splits")
    ff = [i for i in images if i["type"] == "ff"]
    groups = {}
    for i in ff:
        g = re.sub(r"_\d+$", "", i["problem"])
        groups.setdefault((g, i["split"]), []).append(i)
    say("  group (problem name), split, images, actions per image, actions per shape")
    out = {"groups": []}
    for (g, s), imgs in sorted(groups.items(), key=lambda kv: (kv[0][1] != "train", kv[0][1], kv[0][0])):
        per_image = sorted({i["n_actions"] for i in imgs})
        per_shape = sorted({n for i in imgs for n in i["shape_lengths"]})
        say(f"      {g:12s} {s:8s} {len(imgs):6d}   {per_image}   {per_shape}")
        out["groups"].append({"group": g, "split": s, "images": len(imgs),
                              "actions_per_image": per_image, "actions_per_shape": per_shape})
    train_max = max(i["n_actions"] for i in ff if i["split"] == "train")
    test = [i for i in ff if i["split"] == "test_ff"]
    longer = sum(i["n_actions"] > train_max for i in test)
    say(f"  longest train image: {train_max} actions; test_ff images longer than that: "
        f"{longer}/{len(test)} ({100 * longer / len(test):.0f}%)")
    out["train_max"] = train_max
    out["test_longer_than_train_max"] = [longer, len(test)]

    splits = ["train", "val", "test_ff"]
    xs = range(min(i["n_actions"] for i in ff), max(i["n_actions"] for i in ff) + 1)
    series = {}
    for s in splits:
        counts = Counter(i["n_actions"] for i in ff if i["split"] == s)
        n = sum(counts.values())
        series[s] = [100 * counts.get(x, 0) / n for x in xs]
    fig, ax = new_axes()
    grouped_bars(ax, xs, series, SPLIT_COLORS, {s: s for s in splits})
    ax.set_xlabel("actions per image")
    ax.set_ylabel("share of images (%)")
    ax.set_title("Free-form program length by split", loc="left", fontsize=11)
    legend(ax)
    save(fig, "03_ff_length_gap.png")
    return out


def main():
    plt.rcParams["font.family"] = "sans-serif"
    images = load_images()
    say(f"{len(images)} images, {sum(i['n_actions'] for i in images)} actions")
    results = {
        "length": section_length(images),
        "vocabulary": section_vocabulary(images),
        "numeric": section_numeric(images),
        "ff_gap": section_ff_gap(images),
    }
    LOG.mkdir(parents=True, exist_ok=True)
    (LOG / "03_stats.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    (LOG / "03_stats.json").write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("\nReport written to outputs/logs/03_stats.txt and 03_stats.json")


if __name__ == "__main__":
    main()
