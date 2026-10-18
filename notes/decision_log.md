# Decision log

One line per working day: what was decided, the evidence, the open question. Details live in `decisions.md`.

| date | decision | evidence | open question |
|---|---|---|---|
| 2026-10-15 | Setup: layout, venv, `bongard` installed without its pinned pandas, dataset downloaded (1.68 GB zip). | One image and its program read and matched by eye. | None yet; decisions start after the data checks. |
| 2026-10-16 | No decision. Data layout documented; renderer re-draws programs with the same shapes but different pose; ff stamp density and proportions do not match the published painter settings; renderer fidelity and pose alignment parked. | `data_layout.md`, `outputs/figures/02_render_pair.png`. | Which decisions first; whether rendered training images are ever needed. |
| 2026-10-17 | No decision. Program statistics: programs short (at most 18 actions), all numeric fields finite, arc radius constant, test_ff is a length-extrapolation test. Infrastructure inventory: API provider and evaluation metrics missing. | `program_statistics.md`, figures `03_*.png`. | Order of decisions; start with the task definition. |
| 2026-10-18 | 1a: output format = dataset strings with the arc radius removed. 1b: the shape boundary stays in the output. Notes renamed to English. | Arc radius is 0.500 in all 300,247 arcs; every other field varies in bd and hd. Dropping the boundary draws one connected shape instead of two (`outputs/figures/1b_shape_boundary.png`). The two shapes touch or overlap in at most 3.93% of two-shape images (all 72,422 checked). | 1c shape order. |
