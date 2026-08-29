"""Provider-neutral, read-only P08 outcome-learning contracts."""

from core.learning.outcome_observation import (
    OutcomeLearningObservation,
    P08_T01_CONTRACT_VERSION,
    P08_T01_EVALUATOR_VERSION,
    create_outcome_learning_observation,
    observe_outcome,
)
from core.learning.outcome_dataset import (
    OutcomeLearningDatasetSnapshot,
    P08_T02_CONTRACT_VERSION,
    build_outcome_learning_dataset_snapshot,
    create_outcome_learning_dataset_snapshot,
    snapshot_outcome_learning_dataset,
)

__all__ = [
    "OutcomeLearningObservation",
    "P08_T01_CONTRACT_VERSION",
    "P08_T01_EVALUATOR_VERSION",
    "create_outcome_learning_observation",
    "observe_outcome",
    "OutcomeLearningDatasetSnapshot",
    "P08_T02_CONTRACT_VERSION",
    "build_outcome_learning_dataset_snapshot",
    "create_outcome_learning_dataset_snapshot",
    "snapshot_outcome_learning_dataset",
    "OutcomeInterpretationResult",
    "OutcomeInterpretationSnapshot",
    "OutcomeInterpretationStatus",
    "P08_T03_CONTRACT_VERSION",
    "P08_T03_EVALUATOR_VERSION",
    "create_outcome_interpretation_snapshot",
    "interpret_outcome_learning_dataset",
    "interpret_outcomes",
]
from core.learning.outcome_interpretation import (
    OutcomeInterpretationResult,
    OutcomeInterpretationSnapshot,
    OutcomeInterpretationStatus,
    P08_T03_CONTRACT_VERSION,
    P08_T03_EVALUATOR_VERSION,
    create_outcome_interpretation_snapshot,
    interpret_outcome_learning_dataset,
    interpret_outcomes,
)
from core.learning.outcome_evidence import (
    OutcomeEvidenceEvaluationResult,
    OutcomeEvidenceReasonCode,
    OutcomeEvidenceState,
    P08_T04_CONTRACT_VERSION,
    P08_T04_EVALUATOR_VERSION,
    create_outcome_evidence_evaluation,
    evaluate_outcome_evidence,
    evaluate_outcome_interpretation_evidence,
)

__all__ += [
    "OutcomeEvidenceEvaluationResult",
    "OutcomeEvidenceReasonCode",
    "OutcomeEvidenceState",
    "P08_T04_CONTRACT_VERSION",
    "P08_T04_EVALUATOR_VERSION",
    "create_outcome_evidence_evaluation",
    "evaluate_outcome_evidence",
    "evaluate_outcome_interpretation_evidence",
]

from core.learning.outcome_evidence_snapshot import (
    OutcomeEvidenceEvaluationSnapshot,
    P08_T05_CONTRACT_VERSION,
    P08_T05_EVALUATOR_VERSION,
    build_outcome_evidence_evaluation_snapshot,
    create_outcome_evidence_evaluation_snapshot,
    snapshot_outcome_evidence_evaluations,
)

__all__ += [
    "OutcomeEvidenceEvaluationSnapshot",
    "P08_T05_CONTRACT_VERSION",
    "P08_T05_EVALUATOR_VERSION",
    "build_outcome_evidence_evaluation_snapshot",
    "create_outcome_evidence_evaluation_snapshot",
    "snapshot_outcome_evidence_evaluations",
]
