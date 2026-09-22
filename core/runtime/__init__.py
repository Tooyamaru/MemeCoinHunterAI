"""Bounded application-runtime compositions over existing domain owners."""

from core.runtime.controlled_paper_run_admission import (
    ControlledPaperRunAdmissionOutcome,
    ControlledPaperRunAdmissionResult,
    prepare_controlled_paper_run,
)
from core.runtime.controlled_paper_lifecycle import (
    ControlledPaperLifecycleOutcome,
    ControlledPaperLifecycleResult,
    P01_RTI_02_CONTRACT_VERSION,
    PaperFillInstruction,
    PaperLifecycleEvidence,
    run_controlled_paper_lifecycle,
)

__all__ = [
    "ControlledPaperRunAdmissionOutcome",
    "ControlledPaperRunAdmissionResult",
    "prepare_controlled_paper_run",
    "ControlledPaperLifecycleOutcome",
    "ControlledPaperLifecycleResult",
    "P01_RTI_02_CONTRACT_VERSION",
    "PaperFillInstruction",
    "PaperLifecycleEvidence",
    "run_controlled_paper_lifecycle",
]
