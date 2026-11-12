# #132: after relation slices 1–4 and their neighbours, copper's imp, const and opt are bit-identical to the reference chain

**Run:** `python -m pysuto run --case copper --from imp --to opt --base opt_20261112_135523_88fa69f3` →
`imp_20261112_154659_f4ec08ae` → `const_20261112_155126_d1e02299` → `opt_20261112_155758_ba77d84a` (label
`#132 relation check 1`; cold, every knob at its default; 30/30 solved)
**Against:** the reference chain `imp_20261112_133434_22fc54b3` → `const_20261112_134032_b6802ef3` →
`opt_20261112_135523_88fa69f3` (#149, built at main 8fe5adf, which already contains #148)
**Chain:** the reference's feeds `feed_icsg_20261022_110826_8a031806`, `feed_baci_20261022_110715_fdf3b4ac`,
`feed_crude_ore_20260603_095651_558f7369`. Code main d71a548, run from the worktree `diag/relation-check-1` with
`--data-dir` on the main checkout's `data/`; no other driver running.
**Feeds/params:** acc copper v5; conc v10, eff v4, ore_grade v8, stripping_ratio v2, stock_bounds v6, scrap_share v3
— the reference's; `input_status.py`: every `current/` at its latest version
**Date:** 2026-11-12 · **Branch:** `diag/relation-check-1` · **Issues:** #132 (checks #128, #129, #130, #131; also #141,
#142, #144, #145, #146, #150, #151 merged since the reference) · **ADR:** 0011, 0010

**Verdict: passes.** Every imp array and the imputation log (rows, order and every column but the two new provenance
columns), all 280 const arrays and all 240 opt arrays equal the reference chain bit for bit, all 30 years solved, and no
out-of-scope write was dropped. The fixed #141 regression (copper's Stage 3 would have raised in `from_mask_anchor`,
repaired by #145) is confirmed: this is the first copper Stage 3 on the merged code.

## 1. Changes under test

Relation 1–4: #128 (one params reader), #129 (recipes and node balances in `pysuto.relation.structure`), #130
(N-product recipes, toy co-product case), #131 (writer scopes through one `PriorLedger`). Alongside: #141 (P_PROP
check), #142 (σ floors in one place), #144, #145, #146 (case algorithms into the library), #150 (relaxed-close
provenance), #151 (objective share by region), #55/#56 (Stage 4 via `ClarabelBackend`, already shown bit-identical).

## 2. Decision items (pre-registered on #132)

| # | Rule | Result | |
|---|---|---|---|
| 1 | imp arrays bit-identical; log equal ignoring `relaxed`, `assumed_absent` | 8/8 | holds |
| 2 | const arrays bit-identical | 280/280 | holds |
| 3 | opt arrays bit-identical, all years solved | 240/240, 30/30 `solved` | holds |
| 4 | no dropped out-of-scope write | none logged | holds |

## 3. Relaxed-close exposure (information for #139)

718 relaxed-close fills (2,674 kt CC; Mass twins are not tagged, #150). #150's helper counts all 718 as exposed —
every assumed-absent primary receives a later write — but who writes it matters:

| Later write of the assumed-absent primary | Primaries | kt CC |
|---|---|---|
| `network_backward` / `_capped` / `_clipped`, value 0 | 672 | 0 |
| `network_balance`, nonzero | 46 | 197.2 (max 30.7) |
| any other imputer (conc, ore_grade, trade, time, share, flat prior) | 0 | 0 |

- **#139's question has exposure zero.** No imputer after the network ever fills a primary a relaxed close counted as
  absent, so moving the relaxed phase after the cascade-wide strict fixpoint cannot change which primaries are known
  through that channel. #139 becomes a cleanup; only second-order effects (later fills unlocking other strict network
  derivations) could move numbers.
- **A different finding.** In 46 cases the network's own re-converged strict sweep derives the assumed-absent primary
  as nonzero through a Flow balance (197 kt CC in all). ADR 0010's guard bars a relaxed-close output from
  *backward-filling* the primary it assumed absent, but not from reaching it through a balance, so the prior holds
  both "this primary is 0" (in the relaxed close) and "this primary is x > 0" (its own value). The amounts are small;
  whether the guard should extend to balances is a modelling question.
