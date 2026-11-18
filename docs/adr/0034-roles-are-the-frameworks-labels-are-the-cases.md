# Roles are the framework's, labels are the case's

**Status:** accepted (2026-11-12, #119 + #122). Copper's labels bound to roles at acc v5 rebuild the structure byte-identically, and the chain `opt_20261112_092114_c8cb8b74` rerun from the final chain's feed runs reproduces `opt_20261022_112855_928da10c` bit for bit in imp, const and opt (REP `analysis_opt_20261112_092114_c8cb8b74_20261112_issue122-roles-casespec-measure.md`).

pySUTO is meant to run any metal's supply-use table, yet nine library modules compare the copper
case's *labels* — `Process`/`Flow`/`SB`, `Nature`/`SEM`/`FD`, `CC`/`Mass` — as string literals
(`acc.py:796-800`, `param_relation.py:163`, `impute/network.py:98,237`, three copies of
`_BALANCE_ENTITIES`, …), and `AccountingStructure.load()` discards the rule-derived masks and
rebuilds them from those literals. A case whose content valuation is not called `CC` breaks before
any imputer runs, and nothing validates the vocabulary a case supplies.

**Decision.** The framework owns a small `Enum` of **roles**; the case binds its labels to them in
`root.ods` via a `role` column, and the library compares roles through `AccountingStructure`
accessors, never labels. The role vocabulary is deliberately the glossary's existing one: boundary
role `nature | secondary | final_demand` (a `secondary` node is an input on a use edge and a residual
output on a supply edge — the direction rule the code already applies) and valuation role
`content | gross`. The entity kinds `Process | Flow | SB` stay **reserved framework words**: they are
the meta-model itself, used by every ADR and the `constraint_id` grammar, and renaming them buys a
metal case nothing. Validation runs on build **and** on load (sector→entity 1:1, exactly one
`content` and one `gross` valuation, every `SB` node has a boundary role), and the masks built from
`rules.ods` are persisted so `load()` returns what `__init__` built.

## Considered options

- **Fixed reserved labels, validation only.** Cheapest, but a tin case would have to call its
  content valuation `CC` and its scrap `SEM`; the literal scatter across nine modules stays.
- **Roles and labels both in a separate case yaml.** One more file per case and two sources of
  truth for the node vocabulary next to `root.ods`.
- **Splitting `secondary` into `secondary_input` / `residual_output`.** Contradicts the single
  `SEM` category the glossary defines (which also carries `PSC`) and forces every case to assign a
  fourth role that edge direction already determines.

> **Amendment (2026-11-18, branch `feat/single-valuation`).** A structure may also declare a
> **single valuation**, which is then bound to both roles (`content` and `gross` name the same
> label). A case that balances each quantity in its own run (CarIO: Mass first, then fossil and
> biogenic carbon from the solved Mass) needs this; with two or more valuations the rule stays
> exactly one `content` and one `gross`, so three valuations still raise. Nothing in the library
> needed to change beyond `_bind_roles`: every role read either filters edges by one valuation
> or pairs a content edge with its gross twin through `conc` params, which match no edge in a
> one-valuation structure (ratio rows naming the absent valuation are skipped with the existing
> warning). The saved role map is keyed by label and keeps one role for the label; `load()`
> binds it to both again. Evidence: the toy case with only `Gross` runs all six stages, every
> year solved, hard rows closed to 1e-10, the `Gross` PSUT balances per node
> (`tests/test_toy_single_valuation.py`).
