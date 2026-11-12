# #138: with the relation solver built (#128–#137), copper's imp, const and opt are bit-identical to the reference chain

**Run:** `python -m pysuto run --case copper --from imp --to opt --base opt_20261112_135523_88fa69f3` →
`imp_20261112_175337_6ef898d3` → `const_20261112_175728_2b85e842` → `opt_20261112_180346_e6fc1463` (label
`#138 relation check 2`; cold, every knob at its default; 30/30 solved). An interim run after #133–#135 and #137,
`imp_20261112_172438_00ebe48c` → `const_20261112_172829_fd2081a6` → `opt_20261112_173446_fbb99623`, gave the same result.
**Against:** the reference chain `imp_20261112_133434_22fc54b3` → `const_20261112_134032_b6802ef3` →
`opt_20261112_135523_88fa69f3` (#149)
**Chain:** the reference's feeds `feed_icsg_20261022_110826_8a031806`, `feed_baci_20261022_110715_fdf3b4ac`,
`feed_crude_ore_20260603_095651_558f7369`. Code main 3d2efe5, worktree `diag/relation-check-2`, `--data-dir` on the main
checkout's `data/`; no other driver running.
**Feeds/params:** acc copper v5; conc v10, eff v4, ore_grade v8, stripping_ratio v2, stock_bounds v6, scrap_share v3
**Date:** 2026-11-12 · **Branch:** `diag/relation-check-2` · **Issues:** #138 (checks #133, #134, #135, #136, #137)
· **ADR:** 0011 (built), 0004, 0010

**Verdict: passes.** §2 of #26 — one params reader, structural relation sources, writer scopes, co-products, one
`Relation` emitted by Stage 3 and solved by Stage 2, params fill rules, the CaseSpec's declared cascade, and the
persisted flat-prior flag — leaves copper's result bit for bit where it was.

## Decision items (pre-registered on #138, amended by the interim comment)

| # | Rule | Result | |
|---|---|---|---|
| 1 | imp arrays bit-identical; log equal ignoring `relaxed`, `assumed_absent`, `step` | 8/8 arrays the reference stores; the new `flat_prior` array (#137) has no counterpart; log rows, order and every other column identical | holds |
| 1a | `step` differs only by renumbering | the dense rank of `step` is equal row by row; per-imputer counts equal (the inert eff imputer left the cascade, #135) | holds |
| 2 | const arrays bit-identical (incl. the no-data masks #137 now builds from the flag) | 280/280 | holds |
| 3 | opt arrays bit-identical, all years solved | 240/240, 30/30 `solved` | holds |
| 4 | `parents.inputs.params` the same entries | equal as a set (order changed by #136's per-entry recording) | holds |

## Consequences

- ADR 0011's relation solver is built; #26 §2 is done. What remains of the σ question (#140) is a choice of rule, not
  a defect: #149 measured copper's sensitivity to the conc fills' σ as nil at every Round-E item.
- Every stage driver now reads relations from one place, so a second case declares sources and fills as data
  (`pysuto.cases.toy`, `toy_coproduct`).
