# Learning Engine Principles

## V1.1 learning boundary

Early learning is **READ-ONLY**. It may analyze historical outcomes, measure
expectancy, detect drift, and evaluate parameters, but it must not
autonomously modify live decision thresholds, model weights, or risk limits.
Any parameter or version change requires controlled review, validation, and
explicit approval.

Future learning must preserve immutable decision records, point-in-time feature
snapshots, and outcome records. Point-in-time preservation is required to
prevent look-ahead bias, future-data leakage, survivorship bias, and feedback
loops. Evaluation should include:

- Wins, losses, missed opportunities, and correctly avoided losses
- Expectancy, drawdown, slippage, execution failure rate, latency, and infrastructure cost
- Stale-data events, duplicate-order incidents, and kill-switch behavior
- Performance by market regime
- Strategy, feature, decision, entry, and exit quality
- Model and strategy versioning
- Walk-forward validation
- Confidence intervals and regime diversity

Paper and shadow outcomes must account for slippage, price impact, liquidity,
quote drift, transaction failure, priority fees, MEV effects, and execution
latency. They must not assume infinite liquidity or perfect fills.

A production model and challenger model may be compared under controlled evaluation. Production strategy changes must be reviewed and explicitly promoted; uncontrolled self-modification is prohibited.

The Decision Journal must retain enough provenance to reproduce why a decision
occurred: timestamp, market/token, feature snapshot reference, decision,
risk result, execution assumptions, ruleset/model/configuration versions,
outcome, and future cryptographic/hash references.

Readiness is multi-dimensional and is never based on win rate alone or a
simple fixed trade-count threshold. If controlled testing fails to demonstrate
durable risk-adjusted edge, governance must allow the project to STOP, PAUSE,
or change market. The current revision does not implement models, learning
workers, simulators, or outcome collection.
