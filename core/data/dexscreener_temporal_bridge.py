"""Single-call composition of inspection and temporal evidence.

This module is an integration boundary only.  The inspector remains the sole
owner of source fetching and source-shaped normalization, while the temporal
converter remains pure and deterministic.  No P08 observation is created.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from typing import Any, Callable

from core.data.dexscreener_inspection import inspect_token
from core.data.dexscreener_transport import (
    DexScreenerTransportError,
    fetch_token_pairs,
)
from core.data.market_data_temporal_evidence import (
    TemporalEvidenceError,
    convert_inspection_report,
)


EvaluationClock = Callable[[], datetime]


def _default_evaluation_clock() -> datetime:
    return datetime.now(timezone.utc)


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("evaluation clock must return a timezone-aware datetime")
    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def inspect_token_with_temporal(
    chain_id: str,
    token_address: str,
    *,
    transport: Callable[..., Any] = fetch_token_pairs,
    evaluation_clock: EvaluationClock = _default_evaluation_clock,
) -> dict[str, Any]:
    """Inspect one token once and convert that exact report to temporal evidence."""

    report = inspect_token(
        chain_id,
        token_address,
        transport=transport,
    )
    evaluation_time = evaluation_clock()
    evaluation_timestamp = _utc_timestamp(evaluation_time)
    temporal_evidence = convert_inspection_report(
        report,
        evaluation_time=evaluation_time,
    )
    return {
        "report": report,
        "temporal_evidence": temporal_evidence.as_mapping(),
        "evaluation_time": evaluation_timestamp,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch one DexScreener token inspection and return its temporal "
            "evidence; this does not produce a validated P08 observation."
        )
    )
    parser.add_argument("--chain-id", required=True)
    parser.add_argument("--token-address", required=True)
    return parser


def main(
    argv: list[str] | None = None,
    *,
    transport: Callable[..., Any] = fetch_token_pairs,
    evaluation_clock: EvaluationClock = _default_evaluation_clock,
) -> int:
    args = _build_parser().parse_args(argv)
    try:
        result = inspect_token_with_temporal(
            args.chain_id,
            args.token_address,
            transport=transport,
            evaluation_clock=evaluation_clock,
        )
    except (
        DexScreenerTransportError,
        TemporalEvidenceError,
        ValueError,
    ) as error:
        print(
            json.dumps(
                {
                    "error": {
                        "code": type(error).__name__,
                        "message": str(error),
                    }
                },
                ensure_ascii=False,
            )
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())


__all__ = ["inspect_token_with_temporal", "main"]