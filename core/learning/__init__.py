"""Provider-neutral, read-only P08 outcome-learning contracts."""

from core.learning.outcome_observation import (
    OutcomeLearningObservation,
    P08_T01_CONTRACT_VERSION,
    P08_T01_EVALUATOR_VERSION,
    create_outcome_learning_observation,
    observe_outcome,
)

__all__ = [
    "OutcomeLearningObservation",
    "P08_T01_CONTRACT_VERSION",
    "P08_T01_EVALUATOR_VERSION",
    "create_outcome_learning_observation",
    "observe_outcome",
]