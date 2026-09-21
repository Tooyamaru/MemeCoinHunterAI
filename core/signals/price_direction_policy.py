"""Versioned observational price direction, never a trading instruction."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import hashlib
import json

from core.data.coingecko_onchain_ohlcv import (
    OhlcvOutcome, OhlcvRequest, OhlcvResponse, OhlcvResult, PROVIDER_ID,
    map_pool_ohlcv,
)
from core.data.contracts import FreshnessPolicy
from core.data.market_observations import P02T07PredecessorContext
from core.signals.signal_evidence import SignalEvidence, SignalEvidenceCollection, SignalProvenance


POLICY_VERSION = "price-direction-v1"
SIGNAL_TYPE = "PRICE_DIRECTION_1M"


@dataclass(frozen=True)
class PriceDirectionResult:
    market: OhlcvResult
    signal_evidence: SignalEvidenceCollection | None = None

    @property
    def outcome(self) -> OhlcvOutcome:
        return self.market.outcome


def derive_price_direction(
    *, request: OhlcvRequest, response: OhlcvResponse,
    predecessor: P02T07PredecessorContext, freshness_policy: FreshnessPolicy,
    evaluation_time: datetime | None = None,
) -> PriceDirectionResult:
    """Validate original inputs before producing P04-T01 evidence.

    This deliberately does not accept caller-constructed accepted observations
    or a caller-asserted PRODUCED result as an admission shortcut.
    """
    market = map_pool_ohlcv(
        request=request, response=response, predecessor=predecessor,
        freshness_policy=freshness_policy, evaluation_time=evaluation_time,
    )
    if market.outcome is not OhlcvOutcome.PRODUCED:
        return PriceDirectionResult(market)
    previous, latest = market.observations[-2:]
    # Direct comparison is the sign of delta, without ambient Decimal rounding.
    old, new = Decimal(previous.value), Decimal(latest.value)
    if new > old:
        status, reason = "RISING", "PRICE_CLOSE_INCREASED"
    elif new < old:
        status, reason = "FALLING", "PRICE_CLOSE_DECREASED"
    else:
        status, reason = "FLAT", "PRICE_CLOSE_UNCHANGED"
    metadata = {
        "policy_version": POLICY_VERSION,
        "response_digest": market.provenance.response_digest,
        "pool_address": request.pool_address,
        "observation_ids": [item.observation_id for item in market.observations],
        "observation_fingerprints": [item.fingerprint for item in market.observations],
        "upstream_state_digests": [item.upstream.state_digest for item in market.observations],
        "confidence_meaning": "input_completeness_not_prediction",
    }
    digest = hashlib.sha256(json.dumps(metadata, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    evidence = SignalEvidence(
        chain_id=request.chain_id, token_identity=request.token_mint,
        signal_type=SIGNAL_TYPE, signal_status=status,
        observed_at=latest.observation_time, source_id=PROVIDER_ID,
        evidence_reference=f"{POLICY_VERSION}:{digest}", reason_codes=(reason,), confidence=1.0,
        provenance=SignalProvenance(PROVIDER_ID, POLICY_VERSION, latest.observation_time, metadata),
    )
    return PriceDirectionResult(market, SignalEvidenceCollection.from_evidence([evidence]))
