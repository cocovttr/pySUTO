# Trade between regions can run over flow-to-flow edges, declared by an accounting pair

An accounting structure lets the use edges of a tradable flow cross regions: `Ore(Chile) →
Smelting(China)` is a trade leg and a use edge in one. A case with many processes per flow pays
for that in size and in meaning. In a regional carbon table of Austria (CarIO: 838 sectors, nine
states) 84 % of the 1.05 M edges per period and valuation are such cross-region use edges
(10,858 tradable use pairs × 81 region pairs), and a state's receipts of a fuel are a sum over
every user in every other state. A good cannot pass through a state either: a flow node takes
supply only from its own region, so a refinery's diesel cannot reach another state's exports. We
decide that a structure may declare **trade edges** `f(r) → f(s)`, r ≠ s, one per tradable flow
and ordered region pair, by an accounting pair `{"from": "Flow", "to": "Flow", "same_region":
false}`. The trade pairs are implied by the tradable flows (`RuleSet.trade_pairs`); the supply and
use tables do not list them, and a structure without the pair is unchanged. With `Flow → Process`
set `same_region` true, use edges stay in their region and every flow node is a regional pool
fed by local supply and by the other pools: the trade edges are the only route between regions,
a good can pass through a pool, and CarIO shrinks to 0.27 M edges per period and valuation. The
edges carry the built-in mask `trade` (they are `cross_region` too, so bilateral feeds scoped
to cross-region edges, ADR 0014, land on them), node balances count them at both ends, the PSUT
classifies them as block `T`, and the market-share PIOT traces a pool's goods back to the
producers of every region that feeds it: per commodity, `D = S·q̂⁻¹·(I − T·q̂⁻¹)⁻¹`, with `q`
the pool's inflow (local supply + trade in). Trade edges are not edges of the process network.

## Considered options

- **Cross-region use edges (unchanged, still the default).** One edge per producer-free trade leg
  and user; right for copper, where a flow has few users. It grows with the users × regions² and
  cannot pass goods through a region.
- **A pass-through process per region and tradable flow.** Works without a library change, but
  adds the traded tonnes to the gross output of an artificial process, splits every tradable flow
  into a pool and a local node, and has to be removed again in the PSUT.
- **Trade on the supply side** (`Process(r) → Flow(s)`). No new edge kind, but for a case with
  more producers than users per flow it is larger (CarIO: 1.18 M edges), and chains of several
  regions collapse into one step.
- **A new rule table for trade pairs.** Rejected: the pairs are exactly the tradable flows, so a
  table would only repeat them; the accounting pair is the switch an entity-pair rule already is.

**Status:** proposed (2026-11-18; fork `cocovttr/pySUTO`, `feat/flow-trade-edges`). Unit tests in
`tests/test_trade_edges.py` (admissibility, masks, balances, block `T`, PIOT shares); copper declares
no `Flow → Flow` pair and builds the same structure. No run yet: CarIO, its first user, has no
constraint stage.
