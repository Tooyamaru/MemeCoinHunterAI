# Decision Engine Principles

## V1.1 computation model

There is one modular Decision Engine. “AI” does not automatically mean an
LLM. Future computation is explicitly separated into deterministic rules,
statistical/classical models, optional bounded ML analysis, and optional
LLM/narrative analysis.

The V1 hot path is:

```text
DATA
→ HARD RISK FILTER
→ FAST PRE-SCORE
→ OPTIONAL DEEP ANALYSIS
→ DETERMINISTIC DECISION ENGINE
→ RISK/CAPITAL ENGINE
→ PRE-FLIGHT
→ EXECUTION
```

LLM/narrative analysis is deferred research. It must not be the primary
trading brain, block the critical path, trigger BUY by itself, or replace
measurable market/on-chain evidence. Multi-agent architecture is deferred
until a measured bottleneck, defined hypothesis, A/B comparison, and evidence
of improvement.

- An opportunity is not automatically a BUY.
- Confidence is not a guaranteed probability of profit.
- A decision produces a trade intent, not an entry instruction or execution
  authorization.
- The system must support **NO TRADE**.
- Future decisions may include: BUY, WATCH, HOLD, TAKE PROFIT, REDUCE, EXIT, and AVOID.
- Decision and entry must remain separate. Example: `BUY CANDIDATE` with `WAIT` entry.
- Every decision must preserve a point-in-time feature snapshot and the
  evidence, market phase, risk context, invalidation conditions, expected
  edge, uncertainty, and ruleset/model/configuration versions available at
  decision time. This snapshot is required to prevent look-ahead bias,
  future-data leakage, and survivorship bias.
- The Decision Engine cannot bypass the Risk/Capital boundary, directly
  access funds, own or expose private keys, sign, or broadcast.
- A decision is an analytical output; authorization to act is a separate governance decision.
- Execution feasibility is part of the decision. A future initial BUY must
  pass BUY and SELL pre-flight simulation whenever technically possible;
  failure or unreliable execution state means NO TRADE.
- The decision must carry assumptions needed to evaluate expected output,
  price impact, slippage, fees, route validity, chain state, sellability,
  transaction behavior, and relevant contract behavior.
- Decision records must support a future Decision Journal containing timestamp,
  market/token, feature snapshot reference, decision output, risk result,
  execution assumptions, version provenance, and outcome.

P01-T04 and this V1.1 revision document principles only. They do not
implement AI, prediction, signals, simulation, or trading behavior.
