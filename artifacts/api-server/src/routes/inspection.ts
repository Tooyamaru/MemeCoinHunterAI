import { execFile } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { Router, type IRouter, type Response } from "express";
import {
  InspectTokenBody,
  InspectTokenResponse,
} from "@workspace/api-zod";

const execFileAsync = promisify(execFile);
const PYTHON_EXECUTABLE = "python3";
const INSPECTOR_MODULE = "core.data.dexscreener_temporal_bridge";
const INSPECTOR_TIMEOUT_MS = 15_000;
const MAX_INSPECTOR_OUTPUT_BYTES = 8 * 1024 * 1024;
const MAX_CONCURRENT_INSPECTIONS = 2;
const MAX_DIAGNOSTIC_OUTPUT_BYTES = 4 * 1024;
const MAX_DIAGNOSTIC_EXCERPT_BYTES = 512;
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);

type InspectionInput = {
  chainId: string;
  tokenAddress: string;
};

type InspectorFailure = Error & {
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
  ConnectionFailureError: "upstream_connection_failure",
  DexScreenerTransportError: "upstream_transport_failure",
  HttpStatusError: "upstream_http_failure",
  InvalidNumericFieldError: "source_payload_failure",
  InvalidSourceShapeError: "source_payload_failure",
  MalformedJsonError: "source_payload_failure",
  NonFiniteNumberError: "source_payload_failure",
  ResponseTooLargeError: "upstream_response_too_large",
  TemporalEvidenceError: "temporal_conversion_failure",
  ValueError: "bridge_validation_failure",
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

function safeToken(value: unknown): string | undefined {
  return typeof value === "string" && /^[A-Z0-9_]{1,64}$/.test(value)
    ? value
    : undefined;
}

function safeBridgeCode(value: unknown): string | undefined {
  return typeof value === "string" &&
    /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(value)
    ? value
    : undefined;
}

function safeExcerpt(value: unknown, maxBytes = MAX_DIAGNOSTIC_EXCERPT_BYTES) {
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

function safeRequestId(request: RequestDiagnostics): string {
  return typeof request.id === "string" || typeof request.id === "number"
    ? String(request.id)
    : "unknown";
}

function failureCodeFields(failure: InspectorFailure): Record<string, unknown> {
  if (typeof failure.code === "number" && Number.isSafeInteger(failure.code)) {
    return {
      child_code_kind: "exit_code",
      exit_code: failure.code,
    };
  }
  if (typeof failure.code === "string") {
    if (failure.code === "ETIMEDOUT") {
      return {
        child_code_kind: "timeout_code",
        timeout_code: failure.code,
      };
    }
    if (failure.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
      return {
        child_code_kind: "output_limit_code",
        output_limit_code: failure.code,
      };
    }
    return {
      child_code_kind: "launch_error_code",
      launch_error_code: safeToken(failure.code) ?? "unrecognized",
    };
  }
  return { child_code_kind: "missing" };
}

function parseBridgeFailure(stdout: unknown): Record<string, unknown> {
  if (typeof stdout !== "string") {
    return { category: "missing_stdout" };
  }

  const stdoutBytes = Buffer.byteLength(stdout, "utf8");
  if (stdoutBytes === 0) {
    return { category: "empty_stdout", stdout_bytes: 0 };
  }
  if (stdoutBytes > MAX_DIAGNOSTIC_OUTPUT_BYTES) {
    return {
      category: "truncated_stdout",
      stdout_bytes: stdoutBytes,
      stdout_truncated: true,
    };
  }

  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    return {
      category: "malformed_stdout",
      stdout_bytes: stdoutBytes,
    };
  }

  if (
    !parsed ||
    typeof parsed !== "object" ||
    Array.isArray(parsed) ||
    !("error" in parsed) ||
    Object.keys(parsed).length !== 1
  ) {
    return {
      category: "unexpected_stdout",
      stdout_bytes: stdoutBytes,
    };
  }

  const error = parsed.error;
  if (
    !error ||
    typeof error !== "object" ||
    Array.isArray(error) ||
    Object.keys(error).length !== 2 ||
    !("code" in error) ||
    !("message" in error) ||
    typeof error.code !== "string" ||
    typeof error.message !== "string"
  ) {
    return {
      category: "unexpected_bridge_error",
      stdout_bytes: stdoutBytes,
    };
  }

  const bridgeCode = safeBridgeCode(error.code);
  const category = bridgeCode
    ? BRIDGE_ERROR_CATEGORIES[bridgeCode]
    : undefined;
  return {
    category: category ?? "unrecognized_bridge_error",
    stdout_bytes: stdoutBytes,
    bridge_error_code: category ? bridgeCode : "unrecognized",
    bridge_message: safeExcerpt(error.message, 256),
  };
}

function genericFailureCategory(
  failure: InspectorFailure,
  stdoutDetails: Record<string, unknown>,
): string {
  const stdoutCategory = stdoutDetails.category;
  if (
    typeof stdoutCategory === "string" &&
    stdoutCategory !== "missing_stdout" &&
    stdoutCategory !== "empty_stdout"
  ) {
    return stdoutCategory;
  }
  if (typeof failure.code === "number") return "child_exit";
  if (typeof failure.code === "string") return "launch_error";
  return "process_failure";
}

function logInspectorFailure(
  request: RequestDiagnostics,
  failure: InspectorFailure,
  category: string,
  stdoutDetails?: Record<string, unknown>,
) {
  const diagnostic: Record<string, unknown> = {
    request_id: safeRequestId(request),
    category,
    ...failureCodeFields(failure),
  };
  if (typeof failure.signal === "string") {
    diagnostic.signal = safeToken(failure.signal) ?? "unrecognized";
  }
  if (typeof failure.killed === "boolean") {
    diagnostic.killed = failure.killed;
  }
  if (typeof failure.stderr === "string" && failure.stderr.length > 0) {
    diagnostic.stderr_bytes = Buffer.byteLength(failure.stderr, "utf8");
    const stderrExcerpt = safeExcerpt(failure.stderr);
    if (stderrExcerpt) diagnostic.stderr_excerpt = stderrExcerpt;
  }
  Object.assign(diagnostic, stdoutDetails);
  diagnostic.category = category;

  const logger = request.log;
  if (logger) {
    logger.error(
      { inspection_diagnostic: diagnostic },
      "Inspection subprocess failed",
    );
  }
}

async function runInspectorProcess(input: InspectionInput): Promise<string> {
  const result = await execFileAsync(
    PYTHON_EXECUTABLE,
    [
      "-m",
      INSPECTOR_MODULE,
      "--chain-id",
      input.chainId,
      "--token-address",
      input.tokenAddress,
    ],
    {
      cwd: repositoryRoot,
      timeout: INSPECTOR_TIMEOUT_MS,
      maxBuffer: MAX_INSPECTOR_OUTPUT_BYTES,
      windowsHide: true,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    },
  );

  return result.stdout;
}

export type InspectorRunner = (input: InspectionInput) => Promise<string>;

export function createInspectionRouter(
  inspector: InspectorRunner = runInspectorProcess,
): IRouter {
  const router: IRouter = Router();
  let activeInspections = 0;

  router.post("/inspections", async (req, res) => {
    const input = InspectTokenBody.safeParse(req.body);
    if (!input.success) {
      return errorResponse(
        res,
        400,
        "INVALID_INPUT",
        "Inspection request is invalid.",
        "Provide a chainId and tokenAddress using only URL-safe identifier characters.",
      );
    }

    if (activeInspections >= MAX_CONCURRENT_INSPECTIONS) {
      return errorResponse(
        res,
        429,
        "INSPECTION_BUSY",
        "Inspection capacity is currently full.",
        "Try again after one of the active inspections finishes.",
      );
    }

    activeInspections += 1;
    try {
      let stdout: string;
      try {
        stdout = await inspector(input.data);
      } catch (cause) {
        const failure = cause as InspectorFailure;
        if (
          failure.killed ||
          failure.signal === "SIGTERM" ||
          failure.code === "ETIMEDOUT"
        ) {
          logInspectorFailure(
            req as RequestDiagnostics,
            failure,
            "timeout",
            parseBridgeFailure(failure.stdout),
          );
          return errorResponse(
            res,
            504,
            "INSPECTOR_TIMEOUT",
            "The inspection timed out.",
            "The upstream inspection was stopped before a complete report was returned.",
          );
        }
        if (failure.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
          logInspectorFailure(
            req as RequestDiagnostics,
            failure,
            "output_limit",
            parseBridgeFailure(failure.stdout),
          );
          return errorResponse(
            res,
            502,
            "INSPECTOR_OUTPUT_TOO_LARGE",
            "The inspection response was too large.",
            "The inspector output exceeded the configured safety limit.",
          );
        }
        const stdoutDetails = parseBridgeFailure(failure.stdout);
        logInspectorFailure(
          req as RequestDiagnostics,
          failure,
          genericFailureCategory(failure, stdoutDetails),
          stdoutDetails,
        );
        return errorResponse(
          res,
          502,
          "INSPECTOR_FAILURE",
          "The inspection could not be completed.",
          "The inspector or its upstream source returned a failure.",
        );
      }

      let report: unknown;
      try {
        report = JSON.parse(stdout);
      } catch {
        return errorResponse(
          res,
          502,
          "MALFORMED_INSPECTOR_OUTPUT",
          "The inspection returned malformed output.",
          "The inspector did not return valid JSON.",
        );
      }

      const validated = InspectTokenResponse.safeParse(report);
      if (!validated.success) {
        return errorResponse(
          res,
          502,
          "INVALID_INSPECTION_RESPONSE",
          "The inspection returned an invalid response.",
          "The inspector response did not match the published inspection and temporal-evidence contract.",
        );
      }

      return res.status(200).json(validated.data);
    } finally {
      activeInspections -= 1;
    }
  });

  return router;
}

export default createInspectionRouter();