import { FormEvent, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  listCandidateTokens,
  useAssessTokenSafety,
  useEvaluateOpportunity,
  useInspectToken,
} from "@workspace/api-client-react";
import type {
  CandidateListingEntry,
  CandidateListingResponse,
  InspectionPair,
  InspectionWithTemporalEvidence,
  OpportunityEvaluation,
  SafetyEvidenceItem,
  TokenSafetyAssessment,
  TemporalEvidenceRecord,
  WindowValues,
} from "@workspace/api-client-react";
import {
  summarizeActivity,
  summarizeAvailability,
  type AnalysisMetric,
} from "./descriptive-analysis";
import { AlertCircle, ChevronDown, Database, LoaderCircle, Search } from "lucide-react";
import { Route, Router as WouterRouter, Switch, useLocation } from "wouter";
import { ErrorBoundary } from "@/components/error-boundary";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import NotFound from "@/pages/not-found";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";

const queryClient = new QueryClient();

const WINDOWS: Array<[keyof WindowValues, string]> = [
  ["m5", "5m"],
  ["h1", "1h"],
  ["h6", "6h"],
  ["h24", "24h"],
];

function displayValue(value: unknown, unavailable = "Unavailable") {
  return value === null || value === undefined || value === "" ? unavailable : String(value);
}

function formatReceivedAt(value: string | null) {
  if (!value) return "Unavailable";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

function WindowGrid({
  label,
  values,
  unit,
}: {
  label: string;
  values: WindowValues | null | undefined;
  unit?: string;
}) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {WINDOWS.map(([key, windowLabel]) => (
          <div key={String(key)} className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">{windowLabel}</div>
            <div className="mt-1 break-all font-mono text-sm text-slate-800">
              {displayValue(values?.[key])}{values?.[key] != null && unit ? ` ${unit}` : ""}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function analysisMetricText(metric: AnalysisMetric) {
  if (metric.status === "available") return metric.value ?? "Unavailable";
  return metric.detail ?? (metric.status === "invalid" ? "Invalid source value" : "Unavailable");
}

function analysisStatusText(status: AnalysisMetric["status"]) {
  if (status === "available") return "Available";
  if (status === "invalid") return "Invalid";
  return "Unavailable";
}

function safetyStatusClass(status: SafetyEvidenceItem["status"]) {
  if (status === "FAIL") {
    return "border-rose-200 bg-rose-50 text-rose-900";
  }
  if (status === "PASS") {
    return "border-emerald-200 bg-emerald-50 text-emerald-900";
  }
  return "border-amber-200 bg-amber-50 text-amber-950";
}

function safetyStatusLabel(status: SafetyEvidenceItem["status"]) {
  if (status === "FAIL") return "Risk flag";
  if (status === "PASS") return "Pass";
  return "Unknown";
}

function SafetyAssessmentPanel({ result }: { result: TokenSafetyAssessment }) {
  const evaluationLabel =
    result.evaluation.status === "INELIGIBLE"
      ? "Fail-closed: risk evidence present"
      : result.evaluation.status === "ELIGIBLE"
        ? "Non-authoritative represented-domain result"
        : "Unknown: evidence is incomplete";
  const evaluationClass =
    result.evaluation.status === "INELIGIBLE"
      ? "border-rose-200 bg-rose-50 text-rose-950"
      : "border-amber-200 bg-amber-50 text-amber-950";

  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="border-b border-slate-100 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-amber-700">
              Token safety assessment
            </div>
            <CardTitle className="mt-1 text-xl">Source-backed findings</CardTitle>
            <CardDescription className="mt-1">
              {result.identity.chain_id} · {result.identity.token_address}
            </CardDescription>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${evaluationClass}`}>
            {evaluationLabel}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 bg-white pt-5">
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm leading-6 text-amber-950">
          <div className="font-semibold">Not a safety guarantee</div>
          <div>
            GoPlus evidence is evaluated through the existing P03 contracts. This result is
            non-authoritative: it does not approve trading, authorize capital, or establish P08
            acceptance.
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">Provider</div>
            <div className="mt-1 font-medium text-slate-900">{result.source.source_id}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">Source observation</div>
            <div className="mt-1 font-medium text-slate-900">Unavailable</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">Source freshness</div>
            <div className="mt-1 font-medium text-slate-900">{result.source.source_freshness}</div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">Evidence records</div>
            <div className="mt-1 font-medium text-slate-900">{result.evidence.length}</div>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Evaluated domain results
          </div>
          <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(result.evaluation.domain_results).map(([domain, status]) => (
              <div key={domain} className={`rounded-lg border px-3 py-2 ${safetyStatusClass(status)}`}>
                <div className="text-[11px] font-semibold tracking-[0.08em]">{domain}</div>
                <div className="mt-1 text-sm font-semibold">{safetyStatusLabel(status)}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
            Provider findings
          </div>
          <div className="mt-2 space-y-2">
            {result.evidence.map((item) => {
              const providerField = item.evidence_context.provider_field;
              const providerValue = item.evidence_context.provider_value;
              return (
                <div
                  key={item.evidence_reference}
                  className={`rounded-lg border px-3 py-3 ${safetyStatusClass(item.status)}`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className="text-sm font-semibold">
                        {typeof providerField === "string" && providerField
                          ? providerField
                          : item.domain}
                      </div>
                      <div className="mt-1 text-xs opacity-80">{item.domain}</div>
                    </div>
                    <span className="rounded-full bg-white/70 px-2 py-1 text-[11px] font-semibold">
                      {safetyStatusLabel(item.status)}
                    </span>
                  </div>
                  <div className="mt-2 text-xs leading-5">
                    Provider value: <span className="font-mono">{displayValue(providerValue)}</span>
                    {" · "}
                    {item.reason_codes.join(" · ")}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <details className="rounded-lg border border-slate-200 bg-slate-50/50">
          <summary className="cursor-pointer list-none px-4 py-3 text-sm font-semibold text-slate-700">
            Evidence limitations ({result.missing_evidence.length})
          </summary>
          <div className="space-y-3 border-t border-slate-200 px-4 py-4 text-sm">
            <ul className="space-y-2 text-slate-700">
              {result.missing_evidence.map((item, index) => (
                <li key={`${item.domain}-${item.reason}-${index}`}>
                  <span className="font-semibold">{item.domain}</span>
                  <span className="text-slate-500"> · {item.reason}</span>
                </li>
              ))}
            </ul>
            <div className="border-t border-slate-200 pt-3 text-xs leading-5 text-slate-600">
              {result.limitations.join(" ")}
            </div>
            <div className="border-t border-slate-200 pt-3 text-xs text-slate-500">
              Received {formatReceivedAt(result.source.received_at)} · evaluated{" "}
              {formatReceivedAt(result.evaluation.evaluation_timestamp)}
            </div>
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

function OpportunityEvaluationPanel({ result }: { result: OpportunityEvaluation }) {
  return (
    <Card className="border-indigo-200 bg-indigo-50/60">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg text-indigo-950">
          Opportunity admission diagnostic: {result.status === "BLOCKED" ? "Blocked" : "Qualified"}
        </CardTitle>
        <CardDescription className="text-indigo-900/75">
          Pair {result.identity.pair_index + 1} · {result.identity.pair_address} · no provider request was made.
          This is not a completed P04/P05 evaluation or an authenticated safety decision.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 pt-0 text-sm text-indigo-950">
        <div className="grid gap-2 sm:grid-cols-2">
          <div className="rounded-lg border border-indigo-200 bg-white/70 px-3 py-2">
            <div className="text-xs text-indigo-700">Safety eligibility used</div>
            <div className="mt-1 font-semibold">{result.safety.recomputed_status}</div>
            <div className="mt-1 text-xs text-indigo-800/70">
              Client claim: {result.safety.claimed_status}
            </div>
          </div>
          <div className="rounded-lg border border-indigo-200 bg-white/70 px-3 py-2">
            <div className="text-xs text-indigo-700">P04 / P05 readiness</div>
            <div className="mt-1 font-semibold">
              {result.p04_status} / {result.p05_status}
            </div>
            <div className="mt-1 text-xs text-indigo-800/70">
              Canonical discovery: {result.canonical_discovery} · P08: {result.p08_acceptance}
            </div>
          </div>
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-800">
            Why this is blocked
          </div>
          <ul className="mt-2 space-y-2">
            {result.blockers.map((blocker) => (
              <li key={blocker.code} className="rounded-lg border border-indigo-200 bg-white/60 px-3 py-2">
                <span className="font-semibold">{blocker.code}</span>
                <span className="ml-2 text-indigo-900/75">{blocker.detail}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="text-xs leading-5 text-indigo-900/75">
          This action does not rank pairs, create an opportunity score, admit the token, or authorize trading.
          Canonical P04 signal and feature snapshots are still required before the existing Python P05
          evaluator can produce an opportunity score.
        </div>
      </CardContent>
    </Card>
  );
}

function CurrentLiquidity({ values }: { values: InspectionPair["liquidity"] }) {
  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
        Liquidity · current source values
      </div>
      <div className="grid grid-cols-3 gap-2">
        {[
          ["USD", values?.usd, "USD"],
          ["Base", values?.base, undefined],
          ["Quote", values?.quote, undefined],
        ].map(([label, value, unit]) => (
          <div key={label as string} className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">{label as string}</div>
            <div className="mt-1 break-all font-mono text-sm text-slate-800">
              {displayValue(value)}{value != null && unit ? ` ${unit}` : ""}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function DescriptiveAnalysis({ pair }: { pair: InspectionPair }) {
  const activity = summarizeActivity(pair);
  const availability = summarizeAvailability(pair);

  return (
    <div className="space-y-4 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
      <div>
        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-800">
          Descriptive analysis
        </div>
        <div className="mt-1 text-sm font-semibold text-slate-900">Activity summary</div>
        <div className="mt-1 text-xs leading-5 text-slate-600">
          Based on the source-reported 24h rolling window. Transaction-count share is not buying pressure or volume share.
        </div>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {[
          ["Buys", activity.buys],
          ["Sells", activity.sells],
          ["Total transactions", activity.total],
          ["Buy transaction share", activity.buyShare],
        ].map(([label, metric]) => (
          <div key={label as string} className="rounded-lg border border-emerald-100 bg-white/80 px-3 py-2">
            <div className="text-[11px] font-medium text-slate-500">{label as string}</div>
            <div className="mt-1 break-words font-mono text-sm font-semibold text-slate-900">
              {analysisMetricText(metric as AnalysisMetric)}
            </div>
          </div>
        ))}
      </div>
      <div>
        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          Data availability
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
          {availability.map(({ label, metric }) => (
            <div key={label} className="rounded-lg border border-slate-200 bg-white/80 px-3 py-2">
              <div className="text-[11px] font-medium text-slate-500">{label}</div>
              <div className="mt-1 text-xs font-semibold text-slate-800">
                {analysisStatusText(metric.status)}
              </div>
              <div className="mt-1 break-words font-mono text-xs text-slate-700">
                {analysisMetricText(metric)}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="text-xs leading-5 text-slate-600">
        This describes the returned report only. Source freshness remains Unknown; receipt time does not establish source freshness; P08 acceptance remains NOT_ATTEMPTED.
      </div>
    </div>
  );
}

function PairCard({
  pair,
  index,
  temporalRecord,
  onEvaluate,
  canEvaluate,
  isEvaluating,
}: {
  pair: InspectionPair;
  index: number;
  temporalRecord: TemporalEvidenceRecord | undefined;
  onEvaluate: (index: number) => void;
  canEvaluate: boolean;
  isEvaluating: boolean;
}) {
  const base = pair.baseToken?.symbol || pair.baseToken?.name || "Unknown base";
  const quote = pair.quoteToken?.symbol || pair.quoteToken?.name || "Unknown quote";
  const pairLabel = `${base} / ${quote}`;
  const findingCount = pair.inspection.findings.length;

  return (
    <Card className="overflow-hidden border-slate-200 shadow-sm">
      <CardHeader className="border-b border-slate-100 bg-white pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">
              <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-emerald-50 text-emerald-700">
                {index + 1}
              </span>
              Pair returned by source
            </div>
            <CardTitle className="text-xl text-slate-950">{pairLabel}</CardTitle>
            <CardDescription className="mt-1">
              {displayValue(pair.dexId, "DEX unavailable")} · {displayValue(pair.chainId, "Chain unavailable")}
            </CardDescription>
          </div>
          {findingCount > 0 && (
            <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">
              {findingCount} finding{findingCount === 1 ? "" : "s"}
            </span>
          )}
          <Button
            type="button"
            variant="outline"
            disabled={!canEvaluate || isEvaluating}
            onClick={() => onEvaluate(index)}
            className="border-indigo-300 bg-white text-indigo-900 hover:bg-indigo-50"
          >
            {isEvaluating ? <LoaderCircle className="animate-spin" /> : null}
            {isEvaluating ? "Evaluating…" : "Evaluate this pair"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-6 bg-white pt-5">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Price USD", pair.priceUsd, "USD"],
            ["Price native", pair.priceNative, undefined],
            ["FDV", pair.fdv, "USD"],
            ["Market cap", pair.marketCap, "USD"],
          ].map(([label, value, unit]) => (
            <div key={label as string}>
              <div className="text-xs font-medium text-slate-500">{label as string}</div>
              <div className="mt-1 break-all font-mono text-sm font-semibold text-slate-900">
                {displayValue(value)}{value != null && unit ? ` ${unit}` : ""}
              </div>
            </div>
          ))}
        </div>
        <DescriptiveAnalysis pair={pair} />
        <div className="grid gap-5 lg:grid-cols-2">
          <WindowGrid label="Volume · rolling source windows" values={pair.volume} unit="USD" />
          <WindowGrid label="Price change · source windows" values={pair.priceChange} unit="%" />
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <CurrentLiquidity values={pair.liquidity} />
          <div className="space-y-2">
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Transaction counts</div>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              {WINDOWS.map(([key, windowLabel]) => {
                const transaction = pair.txns?.[key] as
                  | { buys?: string | null; sells?: string | null }
                  | null
                  | undefined;
                return (
                  <div key={String(key)} className="rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
                    <div className="text-[11px] font-medium text-slate-500">{windowLabel}</div>
                    <div className="mt-1 font-mono text-xs text-slate-800">
                      B {displayValue(transaction?.buys)} · S {displayValue(transaction?.sells)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <details className="group rounded-lg border border-slate-200 bg-slate-50/50">
          <summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-slate-700">
            Provenance and inspection details
            <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
          </summary>
          <div className="space-y-4 border-t border-slate-200 px-4 py-4 text-sm">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Pair address</div>
              <div className="mt-1 break-all font-mono text-xs text-slate-700">{displayValue(pair.pairAddress)}</div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Source pair created at</div>
              <div className="mt-1 font-mono text-xs text-slate-700">{displayValue(pair.inspection.source_pair_created_at)}</div>
            </div>
            <div className="grid gap-4 border-t border-slate-200 pt-4 sm:grid-cols-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Source observation time</div>
                <div className="mt-1 text-sm text-slate-700">Unavailable</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Source freshness</div>
                <div className="mt-1 text-sm text-slate-700">{temporalRecord?.source_freshness.status ?? "Unknown"}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Data received at</div>
                <div className="mt-1 font-mono text-xs text-slate-700">{formatReceivedAt(temporalRecord?.received_at ?? null)}</div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Receipt age at evaluation</div>
                <div className="mt-1 text-sm text-slate-700">
                  {temporalRecord ? `${temporalRecord.receipt_recency.age_seconds} seconds` : "Unavailable"}
                </div>
              </div>
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Token-origin age</div>
                <div className="mt-1 text-sm text-slate-700">Unavailable</div>
              </div>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Findings</div>
              <pre className="mt-2 max-h-48 overflow-auto rounded-md bg-slate-950 p-3 text-xs text-slate-200">{JSON.stringify(pair.inspection.findings, null, 2)}</pre>
            </div>
          </div>
        </details>
      </CardContent>
    </Card>
  );
}

function CandidateListingPanel({
  listing,
  isPending,
  isError,
  errorMessage,
  onLoad,
  onSelect,
}: {
  listing: CandidateListingResponse | undefined;
  isPending: boolean;
  isError: boolean;
  errorMessage: string;
  onLoad: () => void;
  onSelect: (candidate: CandidateListingEntry) => void;
}) {
  return (
    <Card className="border-slate-200 shadow-sm">
      <CardHeader className="pb-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <CardTitle className="text-lg">Provider candidate listing</CardTitle>
            <CardDescription>
              Load one bounded list from DexScreener's documented latest token-profiles endpoint.
            </CardDescription>
          </div>
          <Button
            type="button"
            onClick={onLoad}
            disabled={isPending}
            variant="outline"
            className="min-h-10 border-emerald-200 text-emerald-800 hover:bg-emerald-50"
          >
            {isPending ? <LoaderCircle className="animate-spin" /> : <Database />}
            {isPending ? "Loading candidates…" : "Load candidates"}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50/70 px-4 py-3 text-sm leading-6 text-amber-950">
          <div className="font-semibold">Provider listing only</div>
          <div>
            Origin: DexScreener latest token profiles · selection basis: provider order ·
            canonical discovery admission: <span className="font-semibold">NOT_ADMITTED</span>.
            This is not comprehensive discovery, ranking, approval, or investment quality.
          </div>
        </div>

        {isError && (
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
            <div className="font-semibold">Candidate listing unavailable</div>
            <div className="mt-1">{errorMessage}</div>
          </div>
        )}

        {!listing && !isPending && !isError && (
          <div className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
            No provider listing loaded. Loading candidates is always explicit.
          </div>
        )}

        {listing && !isPending && (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
              <span>
                {listing.candidates.length} provider entries · {listing.selectable_count} selectable ·{" "}
                {listing.invalid_count} unavailable or invalid
              </span>
              <span>Received {formatReceivedAt(listing.received_at)}</span>
            </div>
            {listing.candidates.length === 0 ? (
              <div className="rounded-lg border border-dashed border-slate-300 px-4 py-8 text-center text-sm text-slate-500">
                The provider returned an empty listing.
              </div>
            ) : (
              <div className="grid gap-2">
                {listing.candidates.map((candidate) => {
                  const identity =
                    candidate.chainId && candidate.tokenAddress
                      ? `${candidate.chainId} · ${candidate.tokenAddress}`
                      : "Chain or token identity unavailable";
                  const label =
                    candidate.description ||
                    candidate.tokenAddress ||
                    `Provider entry ${candidate.provider_index + 1}`;
                  const canInspect = candidate.inspectable && candidate.chainId && candidate.tokenAddress;
                  return (
                    <div
                      key={candidate.provider_index}
                      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3"
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-xs font-semibold uppercase tracking-[0.12em] text-slate-400">
                            #{candidate.provider_index + 1}
                          </span>
                          <span
                            className={
                              candidate.status === "SELECTABLE" || candidate.status === "DUPLICATE"
                                ? "rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-800"
                                : "rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600"
                            }
                          >
                            {candidate.status}
                          </span>
                        </div>
                        <div className="mt-1 truncate text-sm font-semibold text-slate-900">{label}</div>
                        <div className="mt-1 break-all font-mono text-xs text-slate-500">{identity}</div>
                        {candidate.issues.length > 0 && (
                          <div className="mt-1 text-xs text-slate-500">
                            {candidate.issues.join(" · ")}
                          </div>
                        )}
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        disabled={!canInspect}
                        onClick={() => onSelect(candidate)}
                        className="shrink-0"
                      >
                        Select for inspection
                      </Button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function InspectionPage() {
  const [chainId, setChainId] = useState("ethereum");
  const [tokenAddress, setTokenAddress] = useState("");
  const [result, setResult] = useState<InspectionWithTemporalEvidence | null>(null);
  const [safetyResult, setSafetyResult] = useState<TokenSafetyAssessment | null>(null);
  const [opportunityResult, setOpportunityResult] = useState<OpportunityEvaluation | null>(null);
  const [activeRequestKey, setActiveRequestKey] = useState<string | null>(null);
  const [activeSafetyRequestKey, setActiveSafetyRequestKey] = useState<string | null>(null);
  const [activeEvaluationKey, setActiveEvaluationKey] = useState<string | null>(null);
  const inputKeyRef = useRef("");
  const requestSequenceRef = useRef(0);
  const safetyRequestSequenceRef = useRef(0);
  const evaluationRequestSequenceRef = useRef(0);
  const inputKey = `${chainId.trim()}\u0000${tokenAddress.trim()}`;
  inputKeyRef.current = inputKey;
  const inspection = useInspectToken();
  const safety = useAssessTokenSafety();
  const opportunity = useEvaluateOpportunity();
  const candidateListing = useMutation({
    mutationFn: () => listCandidateTokens(),
  });

  function updateChainId(value: string) {
    requestSequenceRef.current += 1;
    safetyRequestSequenceRef.current += 1;
    evaluationRequestSequenceRef.current += 1;
    setChainId(value);
    setResult(null);
    setSafetyResult(null);
    setOpportunityResult(null);
    setActiveRequestKey(null);
    setActiveSafetyRequestKey(null);
    setActiveEvaluationKey(null);
  }

  function updateTokenAddress(value: string) {
    requestSequenceRef.current += 1;
    safetyRequestSequenceRef.current += 1;
    evaluationRequestSequenceRef.current += 1;
    setTokenAddress(value);
    setResult(null);
    setSafetyResult(null);
    setOpportunityResult(null);
    setActiveRequestKey(null);
    setActiveSafetyRequestKey(null);
    setActiveEvaluationKey(null);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inspection.isPending) return;
    const nextChainId = chainId.trim();
    const nextTokenAddress = tokenAddress.trim();
    const requestKey = `${nextChainId}\u0000${nextTokenAddress}`;
    const requestSequence = ++requestSequenceRef.current;
    safetyRequestSequenceRef.current += 1;
    evaluationRequestSequenceRef.current += 1;
    setResult(null);
    setSafetyResult(null);
    setOpportunityResult(null);
    setActiveRequestKey(requestKey);
    setActiveSafetyRequestKey(null);
    setActiveEvaluationKey(null);
    inspection.mutate(
      { data: { chainId: nextChainId, tokenAddress: nextTokenAddress } },
      {
        onSuccess: (nextResult) => {
          if (
            requestSequenceRef.current === requestSequence &&
            inputKeyRef.current === requestKey
          ) {
            setResult(nextResult);
          }
        },
      },
    );
  }

  function checkTokenSafety() {
    if (safety.isPending || !report) return;
    const nextChainId = chainId.trim();
    const nextTokenAddress = tokenAddress.trim();
    const requestKey = `${nextChainId}\u0000${nextTokenAddress}`;
    const requestSequence = ++safetyRequestSequenceRef.current;
    evaluationRequestSequenceRef.current += 1;
    setSafetyResult(null);
    setOpportunityResult(null);
    setActiveSafetyRequestKey(requestKey);
    setActiveEvaluationKey(null);
    safety.mutate(
      { data: { chainId: nextChainId, tokenAddress: nextTokenAddress } },
      {
        onSuccess: (nextResult) => {
          if (
            safetyRequestSequenceRef.current === requestSequence &&
            inputKeyRef.current === requestKey &&
            nextResult.identity.chain_id === nextChainId &&
            nextResult.identity.token_address === nextTokenAddress
          ) {
            setSafetyResult(nextResult);
          }
        },
      },
    );
  }

  function evaluatePair(pairIndex: number) {
    if (!report || !safetyResult || opportunity.isPending) return;
    const nextChainId = chainId.trim();
    const nextTokenAddress = tokenAddress.trim();
    const requestKey = `${nextChainId}\u0000${nextTokenAddress}\u0000${pairIndex}`;
    const requestSequence = ++evaluationRequestSequenceRef.current;
    setOpportunityResult(null);
    setActiveEvaluationKey(requestKey);
    opportunity.mutate(
      {
        data: {
          chainId: nextChainId,
          tokenAddress: nextTokenAddress,
          pairIndex,
          inspection: result,
          safety: safetyResult,
        },
      },
      {
        onSuccess: (nextResult) => {
          if (
            evaluationRequestSequenceRef.current === requestSequence &&
            inputKeyRef.current === `${nextChainId}\u0000${nextTokenAddress}` &&
            nextResult.identity.pair_index === pairIndex &&
            nextResult.identity.chain_id === nextChainId &&
            nextResult.identity.token_identity === nextTokenAddress
          ) {
            setOpportunityResult(nextResult);
          }
        },
      },
    );
  }

  function selectCandidate(candidate: CandidateListingEntry) {
    if (!candidate.chainId || !candidate.tokenAddress) return;
    requestSequenceRef.current += 1;
    safetyRequestSequenceRef.current += 1;
    evaluationRequestSequenceRef.current += 1;
    setChainId(candidate.chainId);
    setTokenAddress(candidate.tokenAddress);
    setResult(null);
    setSafetyResult(null);
    setOpportunityResult(null);
    setActiveRequestKey(null);
    setActiveSafetyRequestKey(null);
    setActiveEvaluationKey(null);
  }

  const errorMessage =
    inspection.error instanceof Error
      ? inspection.error.message
      : "The inspection could not be completed. Check the inputs and try again.";
  const safetyErrorMessage =
    safety.error instanceof Error
      ? safety.error.message
      : "The token safety assessment could not be completed. Check the provider and try again.";
  const opportunityErrorMessage =
    opportunity.error instanceof Error
      ? opportunity.error.message
      : "The selected pair could not be evaluated. The reports may no longer match.";
  const report = result?.report;
  const temporalEvidence = result?.temporal_evidence;

  return (
    <main className="min-h-screen bg-[#f5f8f7] text-slate-950">
      <header className="border-b border-slate-200/80 bg-[#102a2b] text-white">
        <div className="mx-auto max-w-6xl px-5 py-8 sm:px-8 lg:py-10">
          <div className="flex items-start justify-between gap-6">
            <div className="max-w-3xl">
              <div className="mb-4 flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">
                <Database className="h-4 w-4" />
                Read-only market intelligence
              </div>
              <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">Memecoin inspection</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-emerald-50/75 sm:text-base">
                Inspect every pair returned for one token. Values stay source-shaped and precise; this workspace does not rank, approve, or trade.
              </p>
            </div>
            <div className="hidden rounded-full border border-emerald-200/20 bg-white/5 px-3 py-1.5 text-xs font-medium text-emerald-100 sm:block">
              P08 acceptance: not attempted
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-6xl space-y-6 px-5 py-7 sm:px-8 lg:py-10">
        <CandidateListingPanel
          listing={candidateListing.data}
          isPending={candidateListing.isPending}
          isError={candidateListing.isError}
          errorMessage={
            candidateListing.error instanceof Error
              ? candidateListing.error.message
              : "The provider listing could not be loaded. Try the explicit action again."
          }
          onLoad={() => {
            if (!candidateListing.isPending) candidateListing.mutate();
          }}
          onSelect={selectCandidate}
        />
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Start an inspection</CardTitle>
            <CardDescription>Enter a chain and token address, then submit once to request the current source response.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="grid gap-4 lg:grid-cols-[180px_1fr_auto] lg:items-end">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Chain</span>
                <Input value={chainId} onChange={(event) => updateChainId(event.target.value)} required maxLength={64} pattern="[A-Za-z0-9._~-]+" placeholder="ethereum" />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Token address</span>
                <Input value={tokenAddress} onChange={(event) => updateTokenAddress(event.target.value)} required maxLength={128} pattern="[A-Za-z0-9._~-]+" placeholder="0x..." />
              </label>
              <Button type="submit" disabled={inspection.isPending || !chainId.trim() || !tokenAddress.trim()} className="min-h-10 px-8 bg-[#0f766e] hover:bg-[#0d665f]">
                {inspection.isPending ? <LoaderCircle className="animate-spin" /> : <Search />}
                {inspection.isPending ? "Inspecting…" : "Inspect token"}
              </Button>
            </form>
            {report && (
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-amber-950">Safety is always explicit</div>
                  <div className="mt-1 text-xs leading-5 text-amber-900/80">
                    Request bounded GoPlus evidence for this inspected token. No safety request runs automatically.
                  </div>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  onClick={checkTokenSafety}
                  disabled={safety.isPending}
                  className="min-h-10 border-amber-300 bg-white text-amber-900 hover:bg-amber-100"
                >
                  {safety.isPending ? <LoaderCircle className="animate-spin" /> : <Search />}
                  {safety.isPending ? "Checking safety…" : "Check token safety"}
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {inspection.isPending && (
          <Card className="border-emerald-200 bg-emerald-50/70">
            <CardContent className="flex items-center gap-3 py-5 text-sm text-emerald-900">
              <LoaderCircle className="h-5 w-5 animate-spin" />
              Fetching the source response and preserving its provenance…
            </CardContent>
          </Card>
        )}

        {inspection.isError && !inspection.isPending && activeRequestKey === inputKey && (
          <Card className="border-rose-200 bg-rose-50">
            <CardContent className="flex items-start gap-3 py-5 text-rose-950">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
              <div>
                <div className="font-semibold">Inspection unavailable</div>
                <div className="mt-1 text-sm text-rose-800">{errorMessage}</div>
              </div>
            </CardContent>
          </Card>
        )}

        {safety.isPending && activeSafetyRequestKey === inputKey && (
          <Card className="border-amber-200 bg-amber-50/70">
            <CardContent className="flex items-center gap-3 py-5 text-sm text-amber-950">
              <LoaderCircle className="h-5 w-5 animate-spin" />
              Fetching bounded safety evidence and applying the P03 evaluator…
            </CardContent>
          </Card>
        )}

        {safety.isError && !safety.isPending && activeSafetyRequestKey === inputKey && (
          <Card className="border-rose-200 bg-rose-50">
            <CardContent className="flex items-start gap-3 py-5 text-rose-950">
              <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
              <div>
                <div className="font-semibold">Token safety unavailable</div>
                <div className="mt-1 text-sm text-rose-800">{safetyErrorMessage}</div>
              </div>
            </CardContent>
          </Card>
        )}

        {!inspection.isPending && !inspection.isError && !report && (
          <Card className="border-dashed border-slate-300 bg-white/60">
            <CardContent className="flex flex-col items-center justify-center px-6 py-16 text-center">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-emerald-700">
                <Search className="h-5 w-5" />
              </div>
              <h2 className="mt-5 text-lg font-semibold text-slate-900">No inspection yet</h2>
              <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">Submit a token above to see every returned pair, source window, unavailable value, and provenance detail.</p>
            </CardContent>
          </Card>
        )}

        {report && !inspection.isPending && (
          <section className="space-y-5" aria-live="polite">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">Inspection result</div>
                <h2 className="mt-1 text-2xl font-semibold tracking-tight text-slate-950">
                  {report.payload.pair_count} pair{report.payload.pair_count === 1 ? "" : "s"} returned
                </h2>
              </div>
              <div className="text-right text-sm text-slate-500">
                 <div>Data received at</div>
                 <div className="font-medium text-slate-700">{formatReceivedAt(report.receipt.received_at)}</div>
              </div>
            </div>
             <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3"><div className="text-xs text-slate-500">Source</div><div className="mt-1 font-medium">{report.source}</div></div>
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3"><div className="text-xs text-slate-500">Response size</div><div className="mt-1 font-medium">{report.receipt.response_bytes.toLocaleString()} bytes</div></div>
              <div className="rounded-xl border border-slate-200 bg-white px-4 py-3"><div className="text-xs text-slate-500">Attempts</div><div className="mt-1 font-medium">{report.request.attempts} · {report.request.retry_count} retry</div></div>
               <div className="rounded-xl border border-slate-200 bg-white px-4 py-3"><div className="text-xs text-slate-500">P08 acceptance</div><div className="mt-1 font-medium">{report.evidence.p08_acceptance}</div></div>
            </div>
             <Card className="border-amber-200 bg-amber-50/70">
               <CardContent className="space-y-2 py-4 text-sm text-amber-950">
                 <div className="font-semibold">Temporal evidence</div>
                 <div>Source observation time: <span className="font-medium">Unavailable</span> · Source freshness: <span className="font-medium">Unknown</span></div>
                 <div className="text-amber-900/80">A recent receipt confirms when this response arrived, not when the source last observed the market. Rolling volume labels remain source windows, not exact UTC boundaries.</div>
               </CardContent>
             </Card>
             {safetyResult && !safety.isPending && (
               <SafetyAssessmentPanel result={safetyResult} />
             )}
              {opportunity.isError &&
                !opportunity.isPending &&
                activeEvaluationKey?.startsWith(`${inputKey}\u0000`) && (
               <Card className="border-rose-200 bg-rose-50">
                 <CardContent className="py-4 text-sm text-rose-900">
                   <div className="font-semibold">Opportunity evaluation unavailable</div>
                   <div className="mt-1">{opportunityErrorMessage}</div>
                 </CardContent>
               </Card>
             )}
             {opportunityResult && !opportunity.isPending && (
               <OpportunityEvaluationPanel result={opportunityResult} />
             )}
            {report.payload.pairs.length === 0 ? (
               <Card className="border-dashed border-slate-300 bg-white/60"><CardContent className="py-12 text-center text-sm text-slate-500"><div className="font-medium text-slate-700">No pairs returned</div><div className="mt-2">The source returned no pair-level temporal records for this token.</div></CardContent></Card>
            ) : (
               report.payload.pairs.map((pair: InspectionPair, index: number) => (
                 <PairCard
                   key={`${pair.pairAddress ?? "pair"}-${index}`}
                   pair={pair}
                   index={index}
                   temporalRecord={temporalEvidence?.records[index]}
                   onEvaluate={evaluatePair}
                   canEvaluate={Boolean(safetyResult) && !safety.isPending}
                   isEvaluating={
                     opportunity.isPending &&
                     activeEvaluationKey === `${inputKey}\u0000${index}`
                   }
                 />
               ))
            )}
            <details className="rounded-xl border border-slate-200 bg-white">
              <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold text-slate-700">Report provenance</summary>
              <div className="border-t border-slate-200 px-5 py-4 text-sm">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div><div className="text-xs text-slate-500">Raw payload SHA-256</div><div className="mt-1 break-all font-mono text-xs">{displayValue(report.payload.raw_payload_sha256)}</div></div>
                  <div><div className="text-xs text-slate-500">P08 observed at</div><div className="mt-1 font-mono text-xs">{displayValue(report.evidence.p08_observed_at)}</div></div>
                   <div><div className="text-xs text-slate-500">Evaluation timestamp</div><div className="mt-1 font-mono text-xs">{formatReceivedAt(result?.evaluation_time ?? null)}</div></div>
                   <div><div className="text-xs text-slate-500">Temporal records</div><div className="mt-1 font-medium">{temporalEvidence?.records.length ?? 0}</div></div>
                </div>
              </div>
            </details>
          </section>
        )}
      </div>
    </main>
  );
}

function Router() {
  const [location] = useLocation();
  return (
    <ErrorBoundary resetKey={location}>
      <Switch>
        <Route path="/" component={InspectionPage} />
        <Route component={NotFound} />
      </Switch>
    </ErrorBoundary>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}