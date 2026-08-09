# Learning Engine Principles

Future learning must preserve immutable decision records, feature snapshots, and outcome records. Evaluation should include:

- Wins, losses, missed opportunities, and correctly avoided losses
- Performance by market regime
- Strategy, feature, decision, entry, and exit quality
- Model and strategy versioning
- Walk-forward validation

A production model and challenger model may be compared under controlled evaluation. Production strategy changes must be reviewed and explicitly promoted; uncontrolled self-modification is prohibited.

Guard against overfitting, look-ahead bias, regime bias, survivorship bias, data leakage, and feedback loops. P00 does not implement models, learning workers, or outcome collection.
