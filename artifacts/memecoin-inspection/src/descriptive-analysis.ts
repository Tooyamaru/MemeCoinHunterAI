import type { InspectionPair } from "@workspace/api-client-react";

export type AnalysisStatus = "available" | "unavailable" | "invalid";

export type AnalysisMetric = {
  status: AnalysisStatus;
  value: string | null;
  detail?: string;
};

export type ActivityAnalysis = {
  buys: AnalysisMetric;
  sells: AnalysisMetric;
  total: AnalysisMetric;
  buyShare: AnalysisMetric;
};

export type AvailabilityAnalysis = {
  label: string;
  metric: AnalysisMetric;
};

type TransactionValue = string | null | undefined;

const DECIMAL_PATTERN =
  /^[+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?$/;

function parseNonNegativeInteger(value: unknown): bigint | null {
  if (typeof value !== "string" || !/^\d+$/.test(value)) return null;

  try {
    return BigInt(value);
  } catch {
    return null;
  }
}

function countMetric(value: TransactionValue): AnalysisMetric & {
  parsed: bigint | null;
} {
  if (value === null || value === undefined) {
    return { status: "unavailable", value: null, parsed: null };
  }

  const parsed = parseNonNegativeInteger(value);
  if (parsed === null) {
    return { status: "invalid", value: null, detail: "Invalid source value", parsed };
  }

  return {
    status: "available",
    value: parsed.toLocaleString("en-US"),
    parsed,
  };
}

function unavailableDerivedMetric(detail: string): AnalysisMetric {
  return { status: "unavailable", value: null, detail };
}

function invalidDerivedMetric(): AnalysisMetric {
  return { status: "invalid", value: null, detail: "Invalid source value" };
}

// Deterministic half-up rounding: calculate tenths of a percent with BigInt,
// then round the fractional tenth at 0.05 percentage points.
function formatPercentageToOneDecimal(numerator: bigint, denominator: bigint) {
  const tenths = (numerator * 1000n * 2n + denominator) / (denominator * 2n);
  return `${tenths / 10n}.${tenths % 10n}%`;
}

export function summarizeActivity(
  pair: Pick<InspectionPair, "txns">,
): ActivityAnalysis {
  const h24 = pair.txns?.h24;
  const buys = countMetric(h24?.buys);
  const sells = countMetric(h24?.sells);
  const hasInvalidCount =
    buys.status === "invalid" || sells.status === "invalid";
  const hasUnavailableCount =
    buys.status === "unavailable" || sells.status === "unavailable";

  if (hasInvalidCount) {
    return {
      buys,
      sells,
      total: invalidDerivedMetric(),
      buyShare: invalidDerivedMetric(),
    };
  }

  if (hasUnavailableCount || buys.parsed === null || sells.parsed === null) {
    const detail = "Unavailable — both 24h counts required";
    return {
      buys,
      sells,
      total: unavailableDerivedMetric(detail),
      buyShare: unavailableDerivedMetric(detail),
    };
  }

  const total = buys.parsed + sells.parsed;
  if (total === 0n) {
    return {
      buys,
      sells,
      total: { status: "available", value: "0" },
      buyShare: unavailableDerivedMetric("Unavailable — no transactions"),
    };
  }

  return {
    buys,
    sells,
    total: { status: "available", value: total.toLocaleString("en-US") },
    buyShare: {
      status: "available",
      value: formatPercentageToOneDecimal(buys.parsed, total),
    },
  };
}

function hasInvalidNumericFinding(
  pair: InspectionPair,
  field: string,
): boolean {
  return pair.inspection.findings.some(
    (finding) =>
      finding.code === "INVALID_NUMERIC_FIELD" &&
      typeof finding.source_field === "string" &&
      finding.source_field.endsWith(`.${field}`),
  );
}

function describeNumericField(
  pair: InspectionPair,
  label: string,
  field: string,
  value: unknown,
): AvailabilityAnalysis {
  if (value === null || value === undefined) {
    return {
      label,
      metric: { status: "unavailable", value: null },
    };
  }

  if (
    hasInvalidNumericFinding(pair, field) ||
    typeof value !== "string" ||
    value.length === 0 ||
    !DECIMAL_PATTERN.test(value)
  ) {
    return {
      label,
      metric: { status: "invalid", value: null, detail: "Invalid source value" },
    };
  }

  return {
    label,
    metric: { status: "available", value },
  };
}

export function summarizeAvailability(
  pair: InspectionPair,
): AvailabilityAnalysis[] {
  const activity = summarizeActivity(pair);
  const activityMetric: AnalysisMetric =
    activity.buys.status === "invalid" || activity.sells.status === "invalid"
      ? { status: "invalid", value: null, detail: "Invalid source value" }
      : activity.buys.status === "unavailable" ||
          activity.sells.status === "unavailable"
        ? {
            status: "unavailable",
            value: null,
            detail: "Unavailable — both 24h counts required",
          }
        : {
            status: "available",
            value: `B ${activity.buys.value} · S ${activity.sells.value}`,
          };

  return [
    describeNumericField(pair, "USD price", "priceUsd", pair.priceUsd),
    describeNumericField(
      pair,
      "Current USD liquidity",
      "liquidity.usd",
      pair.liquidity?.usd,
    ),
    describeNumericField(
      pair,
      "Source-reported 24h volume",
      "volume.h24",
      pair.volume?.h24,
    ),
    { label: "Source-reported 24h buy/sell counts", metric: activityMetric },
    describeNumericField(
      pair,
      "Pair creation time",
      "pairCreatedAt",
      pair.pairCreatedAt,
    ),
  ];
}