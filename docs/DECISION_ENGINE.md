# Decision Engine Principles

- An opportunity is not automatically a BUY.
- Confidence is not a guaranteed probability of profit.
- A decision is not an entry instruction.
- The system must support **NO TRADE**.
- Future decisions may include: BUY, WATCH, HOLD, TAKE PROFIT, REDUCE, EXIT, and AVOID.
- Decision and entry must remain separate. Example: `BUY CANDIDATE` with `WAIT` entry.
- Every decision must preserve the evidence, market phase, risk context, invalidation conditions, expected edge, uncertainty, and versions available at decision time.
- The Decision Engine cannot bypass the Risk Governor or directly access funds.
- A decision is an analytical output; authorization to act is a separate governance decision.

P00 documents these principles only. It does not implement AI, prediction, signals, or trading behavior.
