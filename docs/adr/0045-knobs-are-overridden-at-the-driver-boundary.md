# Knobs are overridden at the driver boundary; the pipeline composes drivers as subprocesses

**Status:** accepted (2026-10-21; #100, #103); its condition is measured and holds (2026-10-22, #106).
`opt_20261022_091224_7ce11edb` (no overrides) and `opt_20261022_093350_82d7c31d` (all 66 knobs explicit at their
defaults) reproduce `opt_20261021_131744_58504ad3` in every stored array, `F_opt` in 30/30 years, except one. The
imputation log holds the same rows in another order. That order is drawn per process by a NetworkImputer set
iteration older than this decision (#113). Since `0d49c45` the balances are visited in sorted order: two runs under
different hash seeds reproduce `imp_20261022_111102_1b49a2b3` in every array and write one log (2026-11-02, #113,
`imp_20261102_094925_95744204`).

A sensitivity study varies the stage drivers' tuning constants (**knobs**) across many chains. The
knobs live as UPPER_CASE constants in each driver's `# USER CONFIGURATION` block, read inside `main()`,
with the library layer below taking every one as a kwarg. We decide that a knob is overridden at the
driver boundary — the driver lists its `KNOBS`, accepts `--set KNOB=VALUE` as a type-checked Python
literal and records the pairs in `stage_config["overrides"]` — and that `pysuto.pipeline` runs each
driver as a subprocess through that protocol rather than importing it. The alternative was to move
≈ 65 constants into one config dataclass per stage, passed to an importable `main()`: typed and
testable in-process, but the larger refactor, and the pipeline would then live in `scripts/` (the
data layer never imports it), inherit the drivers' import-time side effects (`load_config`, log
handlers) and hold Stage 3's 0.85 GB and Stage 4's eight solver threads in one process across a sweep.
The boundary keeps every knob's single home in its driver, keeps per-stage logs, frees each stage's
memory between steps and costs ≈ 20 lines per driver; its price is string parsing, a `KNOBS` list kept
by hand (a test checks it against the module), and function defaults bound at import that must be
passed explicitly (`scale_total_cv` in Stage 3). Knobs that must agree across stages are declared in
`pipeline.TIED` and refused when set apart; derived constants are not knobs.

## Amendment (#108, 2026-10-22): a sweep keeps only Stage 4 through a scratch store

The knob study keeps only Stage 4 of each point, which reopened the in-process option. Imp and
const held in memory would not take the ≈ 0.93 GB per point (`imp_20261021_125954_b112b170`
80 MB, `const_20261021_130426_c5331a7f` 851 MB) that limits a full-chain sweep to ≈ 9 points,
with 11.6 GB free and the 3 GB reserve on 2026-10-22. It is rejected again, for the reasons
above. Instead a sweep points its imp and const steps at a RAM-backed scratch store through two
new driver flags (`--imp-dir`, `--const-dir`, defaulting to today's `data/proc` paths), and
deletes a run once no remaining point reuses it. A point then costs the opt run's 0.08 GB, and
#106's gate still covers the drivers.

## Amendment (#186, 2026-11-17): #185 supersedes the subprocess half; the knob protocol stands

The decision's subprocess half is superseded by the packaging spec (#185 Q4): Stages 4–6 became
library functions (`pysuto.stages.run_opt`, `run_uncprop`, `run_psut`) beside `run_imp` and
`run_const`, and `pysuto.pipeline` passes the `CaseSpec` object and each stage's overrides to them
in-process instead of spawning a driver, so `python -m pysuto run` needs no `scripts/` directory.
The knob-protocol half stands unchanged: the same names, type checks and precedence (defaults, then
the case's `driver_knobs`, then the overrides), the drivers' `--set` being one caller of it. The
Stage 4–6 constants moved with their values to `pysuto.stages`; the drivers list them as `KNOBS`.
Bit-identity holds: the copper chain downstream of `opt_20261116_134050_b54f65dc` reproduces every
stored array, `parents.inputs` and the imputation log through both entry points
(`opt_20261117_120417_fff166be` via `python -m pysuto run`, `opt_20261117_125807_848d6e22` via the
scripts).

The memory objection above is **not met**: it is measured, and it holds. Two points of
`Pipeline(("imp","const","opt"))` on that base chain ran in one process (RSS and peak RSS, GB, read
from `/proc/self/status` after each step; imp and const written to `/dev/shm`):

| step | point 1 RSS (peak) | point 2 RSS (peak) |
|---|---|---|
| imp   | 11.5 (11.9) | 32.5 (42.9) |
| const | 23.5 (23.8) | 42.9 (43.2) |
| opt   | 33.1 (36.8) | ≥ 46.0 sampled during the solve; not read after the step |

Memory is not returned to the system between steps: the process holds 33.1 GB after point 1, and
point 2 starts there and grows to 43.2 GB by the end of its const step against point 1's 36.8 GB
peak. Its opt step was sampled at 46.0 GB during the solve, and the run was stopped by hand while
the diagnostics rendered, when `MemAvailable` fell under 4.5 GB of the machine's 62 GB; the opt run
had been persisted by then, without its `diag/`. So point 2's peak is at least 9 GB (25 %) above
point 1's, and a third point would not fit. `Sweep` runs its points through `Pipeline`, so
`scripts/sweep.py` inherits this: a multi-point sweep needs each step's memory released (a
`malloc_trim`, or a worker process per step, neither measured here) before it can run in-process
again. This is open, not resolved by this amendment. The two opt runs,
`opt_20261117_134648_3231ec7e` (point 1) and `opt_20261117_140050_847fbe73` (point 2, no `diag/`),
reproduce `opt_20261116_134050_b54f65dc` in all 240 arrays and tables and in `parents.inputs`.
