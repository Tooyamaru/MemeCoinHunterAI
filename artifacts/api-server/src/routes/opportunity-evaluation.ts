import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { Router, type IRouter, type Response } from "express";
import {
  EvaluateOpportunityBody,
  EvaluateOpportunityResponse,
} from "@workspace/api-zod";
import type { OpportunityEvaluationInput } from "@workspace/api-zod";

const EVALUATION_VERSION = "p05-admission-diagnostic-v2";
const PYTHON_EXECUTABLE = "python3";
const SAFETY_DIAGNOSTIC_MODULE = "core.risk.safety_diagnostic_bridge";
const SAFETY_DIAGNOSTIC_TIMEOUT_MS = 5_000;
const MAX_DIAGNOSTIC_OUTPUT_BYTES = 128 * 1024;
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);

type EvaluationInput = OpportunityEvaluationInput;
type SafetyDiagnostic = {
  status: "ELIGIBLE" | "INELIGIBLE" | "UNKNOWN";
  evidence_references: string[];
};

type SafetyDiagnosticFailure = Error & {
  stdout?: unknown;
  code?: string | number;
  killed?: boolean;
  signal?: string;
};

function errorResponse(
  res: Response,
  code: string,
  detail: string,
  status = 400,
) {
  return res.status(status).json({
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
  // This is only a consistency diagnostic over evidence already supplied by
  // the client. It does not authenticate the evidence or replace P03.
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

export function composeOpportunityEvaluation(
  input: EvaluationInput,
  diagnostic?: SafetyDiagnostic,
) {
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
    ![pair.baseToken?.address, pair.quoteToken?.address].includes(tokenAddress) ||
    temporalRecord.chain_id !== chainId ||
    temporalRecord.token_identity !== tokenAddress ||
    temporalRecord.market_subject_id !== `${chainId}:${pair.pairAddress}`
  ) {
    return {
      error: "PAIR_IDENTITY_MISMATCH",
      detail: "The selected pair must preserve its exact chain, pair, token, and market-subject identity.",
    } as const;
  }

  const recomputedStatus = diagnostic?.status ?? recomputeSafetyStatus(safety);
  const blockers: Array<{ code: string; detail: string }> = [
    {
      code: "SAFETY_EVIDENCE_NOT_AUTHENTICATED",
      detail:
        "The browser supplied this safety report; recomputation checks its shape and evidence states but does not authenticate the underlying provider evidence.",
    },
  ];
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
      evidence_references:
        diagnostic?.evidence_references ?? safety.evaluation.evidence_references,
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

async function runSafetyDiagnostic(
  safety: EvaluationInput["safety"],
): Promise<SafetyDiagnostic> {
  const result = await runPythonDiagnosticProcess(safety);
  let parsed: unknown;
  try {
    parsed = JSON.parse(result);
  } catch {
    throw new Error("Safety diagnostic returned malformed output.");
  }
  if (
    !parsed ||
    typeof parsed !== "object" ||
    Array.isArray(parsed) ||
    !("status" in parsed) ||
    !("evidence_references" in parsed) ||
    !(
      parsed.status === "ELIGIBLE" ||
      parsed.status === "INELIGIBLE" ||
      parsed.status === "UNKNOWN"
    ) ||
    !Array.isArray(parsed.evidence_references) ||
    !parsed.evidence_references.every((value) => typeof value === "string")
  ) {
    throw new Error("Safety diagnostic returned an invalid result.");
  }
  return {
    status: parsed.status,
    evidence_references: parsed.evidence_references,
  };
}

function runPythonDiagnosticProcess(
  safety: EvaluationInput["safety"],
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(
      PYTHON_EXECUTABLE,
      ["-m", SAFETY_DIAGNOSTIC_MODULE],
      {
        cwd: repositoryRoot,
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
        stdio: ["pipe", "pipe", "pipe"],
        windowsHide: true,
      },
    );
    const output: Buffer[] = [];
    let outputBytes = 0;
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      child.kill("SIGTERM");
      settled = true;
      reject(
        Object.assign(new Error("Safety diagnostic timed out."), {
          code: "ETIMEDOUT",
          killed: true,
          signal: "SIGTERM",
        }),
      );
    }, SAFETY_DIAGNOSTIC_TIMEOUT_MS);

    const fail = (error: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      reject(error);
    };

    child.stdout.on("data", (chunk: Buffer) => {
      outputBytes += chunk.byteLength;
      if (outputBytes > MAX_DIAGNOSTIC_OUTPUT_BYTES) {
        child.kill("SIGTERM");
        fail(
          Object.assign(new Error("Safety diagnostic output exceeded its limit."), {
            code: "ERR_CHILD_PROCESS_STDIO_MAXBUFFER",
          }),
        );
        return;
      }
      output.push(chunk);
    });
    child.on("error", (error) => {
      fail(error);
    });
    child.on("close", (code, signal) => {
      if (settled) return;
      clearTimeout(timer);
      const stdout = Buffer.concat(output).toString("utf8");
      if (code !== 0) {
        fail(
          Object.assign(new Error("Safety diagnostic process failed."), {
            code: code ?? signal ?? "UNKNOWN",
            signal,
            stdout,
          }),
        );
        return;
      }
      settled = true;
      resolve(stdout);
    });
    child.stdin.end(JSON.stringify(safety));
  });
}

export type SafetyDiagnosticRunner = (
  safety: EvaluationInput["safety"],
) => Promise<SafetyDiagnostic>;

export function createOpportunityEvaluationRouter(
  runner: SafetyDiagnosticRunner = runSafetyDiagnostic,
): IRouter {
  const router: IRouter = Router();
  let activeEvaluations = 0;

  router.post("/opportunity-evaluations", async (req, res) => {
    const input = EvaluateOpportunityBody.safeParse(req.body);
    if (!input.success) {
      return errorResponse(
        res,
        "INVALID_INPUT",
        "Provide one validated inspection, one validated safety assessment, and an explicit pairIndex.",
      );
    }

    if (activeEvaluations >= 1) {
      return errorResponse(
        res,
        "EVALUATION_BUSY",
        "Opportunity evaluation capacity is currently full. Try again after the active local diagnostic finishes.",
        429,
      );
    }

    activeEvaluations += 1;
    let diagnostic: SafetyDiagnostic;
    try {
      diagnostic = await runner(input.data.safety);
    } catch (cause) {
      const failure = cause as SafetyDiagnosticFailure;
      if (
        failure.killed ||
        failure.signal === "SIGTERM" ||
        failure.code === "ETIMEDOUT"
      ) {
        return errorResponse(
          res,
          "SAFETY_DIAGNOSTIC_TIMEOUT",
          "The safety diagnostic timed out. The bounded P03 evaluator did not return a complete result.",
          504,
        );
      }
      if (failure.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
        return errorResponse(
          res,
          "SAFETY_DIAGNOSTIC_OUTPUT_TOO_LARGE",
          "The safety diagnostic response was too large. The bounded P03 evaluator exceeded its output limit.",
          502,
        );
      }
      return errorResponse(
        res,
        "SAFETY_DIAGNOSTIC_FAILURE",
        "The safety diagnostic could not be completed. The existing P03 evaluator rejected the held safety evidence.",
        502,
      );
    } finally {
      activeEvaluations -= 1;
    }

    const result = composeOpportunityEvaluation(input.data, diagnostic);
    if ("error" in result) {
      return errorResponse(res, result.error, result.detail);
    }
    return res.status(200).json(result);
  });

  return router;
}

export default createOpportunityEvaluationRouter();