# #56: Stage 4 through `Solver` + `ClarabelBackend` reproduces the final chain's opt bit for bit, in 3 min instead of 12

**Run:** `python -m pysuto run --case copper --from opt --to opt --base opt_20261022_112855_928da10c` →
`opt_20261112_144603_1256b16b` (label `#56 QP backend measure`; cold, 8 workers, every knob at its default,
`FEASIBILITY_CHECK = "all"`; Stage 4 wall 14:44:17 → 14:47:25, 3 min 9 s)
**Against:** `opt_20261022_112855_928da10c` (cold, ADR 0039 tolerances, first-year probe, `solve_wall_s` 535), on the
same constraint run
**Chain:** `const_20261022_111531_df61bf5c` (stores the pre-#11 `cone_type` schema, so #11's legacy loader is exercised)
← `imp_20261022_111102_1b49a2b3` ← the final chain's feeds. Code main f451a14 (#55 bc6c50e, #142 f451a14), worktree
`diag/qp-backend-measure` with `--data-dir` on the main checkout's `data/`; no other driver running.
**Feeds/params:** unchanged — Stage 4 only reads the constraint run
**Date:** 2026-11-12 · **Branch:** `diag/qp-backend-measure` · **Issues:** #56 (measures #55; also covers #142's σ
floors) · **ADR:** 0042 (accepted here), 0039

**Verdict: passes; ADR 0042 is accepted.** The neutral QP per year, solved by the injected `ClarabelBackend`, gives the
same posterior to the last bit: all 240 stored arrays of the opt run equal the base's, every year's objective and
iteration count are equal, and all 30 years are `solved`. The per-period feasibility probe now checks every year in
14.8 s, where the old full-G probe checked only the first in 430–471 s, so Stage 4 drops from ≈ 12 min to 3 min 9 s.

## 1. Change under test

- **#55** (`16ac141`, `ff9a4f0`, `b15a65f`): `pysuto.qp` (neutral `QPProblem`/`QPResult`/`QPBackend`), the only clarabel
  import in `pysuto.clarabel_backend`, `Solver(backend=…)` replacing `ClarabelSolver`, the legacy full-G path removed, the
  feasibility probe per period on the worker pool, neutral statuses with old runs mapped on load.
- **#142** (`8e78228`, `ad30f5f`): the σ floors single-sourced in `_conditioning.py`; the solver calls
  `condition_sigma_c` where it had an inline copy; the floors are recorded in the opt sidecar.

## 2. Decision items (pre-registered on #56 before the driver)

| # | Rule | Result | |
|---|---|---|---|
| 1 | every year `solved` / `solved_inaccurate` | 30/30 `solved` | holds |
| 2 | total Σz² within ±0.1 % of the base | equal: `F_opt`, `eps_opt` and every other array bit-identical (240/240), objective Δ 0.0 in every year | holds |
| 3 | max \|ΔF\| per year (prediction: bit-identical) | 0 in every year — the merged `ZeroConeT` (soft + hard equalities) changes nothing | holds, prediction right |
| 4 | sidecar records `backend`, `backend_settings`; neutral status names | `backend: clarabel`; settings = the ADR 0039 tolerances, `max_iter` 2000, `faer`, `max_threads` 1; statuses `solved`; the four σ floors recorded (#142) | holds |
| 5 | probe and solve timing, reported (prediction: probe < 3 min) | probe 14.8 s for 30 periods on 8 threads (base: 430–471 s for the first period only); `solve_wall_s` 103 (base 535, which included the probe); Stage 4 3 min 9 s | prediction right |

## 3. Consequences

- **ADR 0042 accepted**, citing this run. CLAUDE.md's Stage 4 facts are updated (≈ 3 min, `FEASIBILITY_CHECK = "all"`,
  neutral statuses).
- **The probe now covers every year at no cost**, which `"first"` never did; a later year's infeasibility is caught
  before the solve instead of failing mid-run.
- **Sweeps:** the probe no longer dominates a point's Stage 4. `pipeline.py:388` and `scripts/sweep.py:52` still quote
  the old ≈ 7 min probe in comments; correct them on the next edit of those files.
- **#56's original baseline** (`const_20261008_075717_9ccd0d40` → `opt_20261008_083810_56f905e9`) was pruned on
  2026-10-22; the ticket was rebased to the final chain on 2026-11-11.
