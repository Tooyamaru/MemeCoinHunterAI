import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { Router, type IRouter, type Response } from "express";
import {
  AssessTokenSafetyBody,
  AssessTokenSafetyResponse,
} from "@workspace/api-zod";

const execFileAsync = promisify(execFile);
const PYTHON_EXECUTABLE = "python3";
const SAFETY_MODULE = "core.risk.goplus_token_safety";
const SAFETY_TIMEOUT_MS = 15_000;
const MAX_SAFETY_OUTPUT_BYTES = 4 * 1024 * 1024;
const MAX_CONCURRENT_ASSESSMENTS = 1;
const MAX_DIAGNOSTIC_OUTPUT_BYTES = 4 * 1024;
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);

type SafetyInput = {
  chainId: string;
  tokenAddress: string;
};

type SafetyFailure = Error & {
  code?: string | number;
  killed?: boolean;
  signal?: string;
  stdout?: unknown;
  stderr?: unknown;
};

type DiagnosticLogger = {
  error: (fields: Record<string, unknown>, message: string) => void;
};

type RequestDiagnostics = {
  id?: string | number;
  log?: DiagnosticLogger;
};

const BRIDGE_ERROR_CATEGORIES: Record<string, string> = {
  INVALID_INPUT: "validation_failure",
  UNSUPPORTED_CHAIN: "unsupported_chain",
  PROVIDER_AUTH_REQUIRED: "provider_auth_required",
  PROVIDER_FAILURE: "provider_failure",
  PROVIDER_HTTP_ERROR: "provider_http_error",
  PROVIDER_MALFORMED_RESPONSE: "provider_malformed_response",
  PROVIDER_NO_RESULT: "provider_no_result",
  PROVIDER_IDENTITY_MISMATCH: "provider_identity_mismatch",
  PROVIDER_RESPONSE_ERROR: "provider_response_error",
  PROVIDER_RESPONSE_TOO_LARGE: "provider_response_too_large",
  PROVIDER_TIMEOUT: "provider_timeout",
  SAFETY_ASSESSMENT_FAILURE: "assessment_failure",
};

function errorResponse(
  res: Response,
  status: number,
  code: string,
  error: string,
  detail: string,
) {
  return res.status(status).json({ error, code, detail });
}

function safeBridgeCode(value: unknown): string | undefined {
  return typeof value === "string" &&
    /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(value)
    ? value
    : undefined;
}

function safeExcerpt(value: unknown, maxBytes = 512) {
  if (typeof value !== "string" || value.length === 0) return undefined;
  const firstLine = value
    .split(/\r?\n/, 1)[0]
    .replace(/[\u0000-\u001f\u007f]/g, " ")
    .replace(
      /\b(authorization|cookie|password|private[_-]?key|secret|token|api[_-]?key)\b\s*[:=]\s*\S+/gi,
      "$1=[REDACTED]",
    )
    .replace(/(?:[A-Za-z]:)?\/(?:[\w.-]+\/)+[\w.-]+/g, "[PATH]");
  return Buffer.from(firstLine).subarray(0, maxBytes).toString("utf8");
}

function parseBridgeFailure(stdout: unknown): Record<string, unknown> {
  if (typeof stdout !== "string") return { category: "missing_stdout" };
  const stdoutBytes = Buffer.byteLength(stdout, "utf8");
  if (stdoutBytes === 0) return { category: "empty_stdout", stdout_bytes: 0 };
  if (stdoutBytes > MAX_DIAGNOSTIC_OUTPUT_BYTES) {
    return { category: "truncated_stdout", stdout_bytes: stdoutBytes };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return { category: "malformed_stdout", stdout_bytes: stdoutBytes };
  }
  if (
    !parsed ||
    typeof parsed !== "object" ||
    Array.isArray(parsed) ||
    !("error" in parsed)
  ) {
    return { category: "unexpected_stdout", stdout_bytes: stdoutBytes };
  }
  const error = parsed.error;
  if (
    !error ||
    typeof error !== "object" ||
    Array.isArray(error) ||
    !("code" in error) ||
    !("message" in error) ||
    typeof error.code !== "string" ||
    typeof error.message !== "string"
  ) {
    return { category: "unexpected_bridge_error", stdout_bytes: stdoutBytes };
  }
  const bridgeCode = safeBridgeCode(error.code);
  return {
    category: bridgeCode
      ? BRIDGE_ERROR_CATEGORIES[bridgeCode] ?? "unrecognized_bridge_error"
      : "unrecognized_bridge_error",
    stdout_bytes: stdoutBytes,
    bridge_error_code: bridgeCode ?? "unrecognized",
    bridge_message: safeExcerpt(error.message, 256),
  };
}

function logSafetyFailure(
  request: RequestDiagnostics,
  failure: SafetyFailure,
  category: string,
  stdoutDetails: Record<string, unknown>,
) {
  request.log?.error(
    {
      safety_diagnostic: {
        request_id:
          typeof request.id === "string" || typeof request.id === "number"
            ? String(request.id)
            : "unknown",
        category,
        child_code:
          typeof failure.code === "string" || typeof failure.code === "number"
            ? failure.code
            : "missing",
        signal: typeof failure.signal === "string" ? failure.signal : undefined,
        stderr_excerpt: safeExcerpt(failure.stderr),
        ...stdoutDetails,
      },
    },
    "Token safety subprocess failed",
  );
}

async function runSafetyProcess(input: SafetyInput): Promise<string> {
  const result = await execFileAsync(
    PYTHON_EXECUTABLE,
    [
      "-m",
      SAFETY_MODULE,
      "--chain-id",
      input.chainId,
      "--token-address",
      input.tokenAddress,
    ],
    {
      cwd: repositoryRoot,
      timeout: SAFETY_TIMEOUT_MS,
      maxBuffer: MAX_SAFETY_OUTPUT_BYTES,
      windowsHide: true,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    },
  );
  return result.stdout;
}

export type SafetyRunner = (input: SafetyInput) => Promise<string>;

export function createTokenSafetyRouter(
  runner: SafetyRunner = runSafetyProcess,
): IRouter {
  const router: IRouter = Router();
  let activeAssessments = 0;

  router.post("/token-safety", async (req, res) => {
    const input = AssessTokenSafetyBody.safeParse(req.body);
    if (!input.success) {
      return errorResponse(
        res,
        400,
        "INVALID_INPUT",
        "Token safety request is invalid.",
        "Provide a chainId and tokenAddress using only URL-safe identifier characters.",
      );
    }

    if (activeAssessments >= MAX_CONCURRENT_ASSESSMENTS) {
      return errorResponse(
        res,
        429,
        "SAFETY_ASSESSMENT_BUSY",
        "Token safety capacity is currently full.",
        "Try again after the active assessment finishes.",
      );
    }

    activeAssessments += 1;
    try {
      let stdout: string;
      try {
        stdout = await runner(input.data);
      } catch (cause) {
        const failure = cause as SafetyFailure;
        const details = parseBridgeFailure(failure.stdout);
        if (
          failure.killed ||
          failure.signal === "SIGTERM" ||
          failure.code === "ETIMEDOUT"
        ) {
          logSafetyFailure(req as RequestDiagnostics, failure, "timeout", details);
          return errorResponse(
            res,
            504,
            "SAFETY_ASSESSMENT_TIMEOUT",
            "The token safety assessment timed out.",
            "The upstream safety provider was stopped before a complete result was returned.",
          );
        }
        if (failure.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
          logSafetyFailure(req as RequestDiagnostics, failure, "output_limit", details);
          return errorResponse(
            res,
            502,
            "SAFETY_ASSESSMENT_OUTPUT_TOO_LARGE",
            "The token safety response was too large.",
            "The safety adapter output exceeded the configured safety limit.",
          );
        }

        logSafetyFailure(
          req as RequestDiagnostics,
          failure,
          String(details.category),
          details,
        );
        const bridgeCode = details.bridge_error_code;
        if (bridgeCode === "UNSUPPORTED_CHAIN") {
          return errorResponse(
            res,
            422,
            "UNSUPPORTED_CHAIN",
            "Token safety is unavailable for this chain.",
            "The bounded GoPlus integration does not support the requested chain.",
          );
        }
        if (bridgeCode === "INVALID_INPUT") {
          return errorResponse(
            res,
            400,
            "INVALID_INPUT",
            "Token safety request is invalid.",
            "The safety adapter rejected the requested token identity.",
          );
        }
        if (bridgeCode === "PROVIDER_TIMEOUT") {
          return errorResponse(
            res,
            504,
            "SAFETY_PROVIDER_TIMEOUT",
            "The token safety provider timed out.",
            "GoPlus did not return a complete response within the bounded timeout.",
          );
        }
        if (bridgeCode === "PROVIDER_AUTH_REQUIRED") {
          return errorResponse(
            res,
            502,
            "SAFETY_PROVIDER_AUTH_REQUIRED",
            "The token safety provider requires server-side authentication.",
            "Configure the GOPLUS_ACCESS_TOKEN secret for the API server; never send provider credentials from the browser.",
          );
        }
        return errorResponse(
          res,
          502,
          "SAFETY_PROVIDER_FAILURE",
          "The token safety assessment could not be completed.",
          "The safety provider or its response failed bounded validation.",
        );
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(stdout);
      } catch {
        return errorResponse(
          res,
          502,
          "MALFORMED_SAFETY_OUTPUT",
          "The token safety adapter returned malformed output.",
          "The safety adapter did not return valid JSON.",
        );
      }

      const validated = AssessTokenSafetyResponse.safeParse(parsed);
      if (!validated.success) {
        return errorResponse(
          res,
          502,
          "INVALID_SAFETY_RESPONSE",
          "The token safety adapter returned an invalid response.",
          "The safety adapter response did not match the published P03 assessment contract.",
        );
      }
      return res.status(200).json(validated.data);
    } finally {
      activeAssessments -= 1;
    }
  });

  return router;
}

export default createTokenSafetyRouter();