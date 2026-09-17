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
const router: IRouter = Router();

const PYTHON_EXECUTABLE = "python3";
const INSPECTOR_MODULE = "core.data.dexscreener_inspection";
const INSPECTOR_TIMEOUT_MS = 15_000;
const MAX_INSPECTOR_OUTPUT_BYTES = 8 * 1024 * 1024;
const MAX_CONCURRENT_INSPECTIONS = 2;
const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../..",
);
let activeInspections = 0;

type InspectionInput = {
  chainId: string;
  tokenAddress: string;
};

type InspectorFailure = Error & {
  code?: string | number;
  killed?: boolean;
  signal?: string;
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

async function runInspector(input: InspectionInput): Promise<string> {
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
      stdout = await runInspector(input.data);
    } catch (cause) {
      const failure = cause as InspectorFailure;
      if (failure.killed || failure.signal === "SIGTERM") {
        return errorResponse(
          res,
          504,
          "INSPECTOR_TIMEOUT",
          "The inspection timed out.",
          "The upstream inspection was stopped before a complete report was returned.",
        );
      }
      if (failure.code === "ERR_CHILD_PROCESS_STDIO_MAXBUFFER") {
        return errorResponse(
          res,
          502,
          "INSPECTOR_OUTPUT_TOO_LARGE",
          "The inspection response was too large.",
          "The inspector output exceeded the configured safety limit.",
        );
      }
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
        "INVALID_INSPECTOR_REPORT",
        "The inspection returned an invalid report.",
        "The inspector response did not match the published report contract.",
      );
    }

    return res.status(200).json(report);
  } finally {
    activeInspections -= 1;
  }
});

export default router;