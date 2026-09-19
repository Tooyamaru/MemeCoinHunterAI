import { Router, type IRouter, type Response } from "express";
import {
  EvaluateOpportunityBody,
  EvaluateOpportunityResponse,
} from "@workspace/api-zod";
import type { OpportunityEvaluationInput } from "@workspace/api-zod";

const EVALUATION_VERSION = "p05-opportunity-report-bridge-v1";

type EvaluationInput = OpportunityEvaluationInput;

function errorResponse(
  res: Response,
  code: string,
  detail: string,
) {
  return res.status(400).json({
    error: "Opportunity evaluation request is invalid.",
    code,
    detail,
  });
}

function sameIdentity(left: string, right: string): boolean {
  return left === right;
}

function recomputeSafetyStatus(
  safety: EvaluationInput["safety"],
): "ELIGIBLE" | "INELIGIBLE" | "UNKNOWN" {
  if (safety.evidence.length === 0) return "UNKNOWN";
  if (safety.evidence.some((item) => item.status === "FAIL")) return "INELIGIBLE";
  if (
    safety.evidence.some(
      (item) =>
        item.status === "UNKNOWN" ||
        item.quality !== "VALID" ||
        item.freshness_status !== "VALID",
    )
  ) {
    return "UNKNOWN";
  }
  return "ELIGIBLE";
}

export function composeOpportunityEvaluation(input: EvaluationInput) {
  const { chainId, tokenAddress, pairIndex, inspection, safety } = input;
  const report = inspection.report;
  const temporal = inspection.temporal_evidence;
  const pair = report.payload.pairs[pairIndex];
  const temporalRecord = temporal.records[pairIndex];

  if (!pair || !temporalRecord) {
    return {
      error: "PAIR_NOT_FOUND",
      detail: "Select a pair that is present in both the inspection and temporal reports.",
    } as const;
  }
  if (
    !sameIdentity(chainId, report.request.chain_id) ||
    !sameIdentity(tokenAddress, report.request.token_address) ||
    !sameIdentity(chainId, temporal.chain_id) ||
    !sameIdentity(tokenAddress, temporal.token_identity) ||
    !sameIdentity(chainId, safety.identity.chain_id) ||
    !sameIdentity(tokenAddress, safety.identity.token_address)
  ) {
    return {
      error: "REPORT_IDENTITY_MISMATCH",
      detail: "Chain and token identity must match across the request, inspection, temporal, and safety reports.",
    } as const;
  }
  if (
    pair.chainId !== chainId ||
    !pair.pairAddress ||
    temporalRecord.chain_id !== chainId ||
    temporalRecord.token_identity !== tokenAddress ||
    temporalRecord.market_subject_id !== `${chainId}:${pair.pairAddress}`
  ) {
    return {
      error: "PAIR_IDENTITY_MISMATCH",
      detail: "The selected pair must preserve its exact chain, pair, token, and market-subject identity.",
    } as const;
  }

  const recomputedStatus = recomputeSafetyStatus(safety);
  const blockers: Array<{ code: string; detail: string }> = [];
  if (safety.source.source_observed_at === null) {
    blockers.push({
      code: "SAFETY_SOURCE_OBSERVATION_TIME_UNAVAILABLE",
      detail: "Safety receipt time is not a source observation time.",
    });
  }
  if (temporalRecord.source_observed_at === null) {
    blockers.push({
      code: "MARKET_SOURCE_OBSERVATION_TIME_UNAVAILABLE",
      detail: "The selected market record has no documented source observation time.",
    });
  }
  if (recomputedStatus !== "ELIGIBLE") {
    blockers.push({
      code:
        recomputedStatus === "INELIGIBLE"
          ? "P03_ELIGIBILITY_INELIGIBLE"
          : "P03_ELIGIBILITY_UNKNOWN",
      detail:
        recomputedStatus === "INELIGIBLE"
          ? "Recomputed safety evidence is not eligible."
          : "Recomputed safety evidence is incomplete or unknown.",
    });
  }
  blockers.push(
    {
      code: "P04_SIGNAL_SNAPSHOT_UNAVAILABLE",
      detail: "The held inspection report does not contain a canonical P04 signal snapshot.",
    },
    {
      code: "P04_FEATURE_SNAPSHOT_UNAVAILABLE",
      detail: "The held inspection report does not contain canonical P04 feature snapshots.",
    },
    {
      code: "P05_CANONICAL_INPUT_UNAVAILABLE",
      detail: "P05 evaluation requires validated P04 snapshots; no score or opportunity decision was produced.",
    },
  );

  const result = {
    evaluation_version: EVALUATION_VERSION,
    status: "BLOCKED" as const,
    identity: {
      chain_id: chainId,
      token_identity: tokenAddress,
      pair_address: pair.pairAddress,
      pair_index: pairIndex,
      market_subject_id: temporalRecord.market_subject_id,
    },
    safety: {
      claimed_status: safety.evaluation.status,
      recomputed_status: recomputedStatus,
      evidence_references: safety.evaluation.evidence_references,
      source_observed_at: safety.source.source_observed_at,
    },
    blockers,
    p04_status: "UNAVAILABLE" as const,
    p05_status: "BLOCKED" as const,
    provider_requests: 0 as const,
    canonical_discovery: "NOT_ADMITTED" as const,
    p08_acceptance: "NOT_ATTEMPTED" as const,
    inspection_received_at: report.receipt.received_at,
    safety_received_at: safety.source.received_at,
    source_observed_at: temporalRecord.source_observed_at,
  };
  return EvaluateOpportunityResponse.parse(result);
}

export function createOpportunityEvaluationRouter(): IRouter {
  const router: IRouter = Router();

  router.post("/opportunity-evaluations", (req, res) => {
    const input = EvaluateOpportunityBody.safeParse(req.body);
    if (!input.success) {
      return errorResponse(
        res,
        "INVALID_INPUT",
        "Provide one validated inspection, one validated safety assessment, and an explicit pairIndex.",
      );
    }

    const result = composeOpportunityEvaluation(input.data);
    if ("error" in result) {
      return errorResponse(res, result.error, result.detail);
    }
    return res.status(200).json(result);
  });

  return router;
}

export default createOpportunityEvaluationRouter();