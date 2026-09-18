import { FormEvent, useRef, useState } from "react";
import { useInspectToken } from "@workspace/api-client-react";
import type {
  InspectionPair,
  InspectionWithTemporalEvidence,
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
}: {
  pair: InspectionPair;
  index: number;
  temporalRecord: TemporalEvidenceRecord | undefined;
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

function InspectionPage() {
  const [chainId, setChainId] = useState("ethereum");
  const [tokenAddress, setTokenAddress] = useState("");
  const [result, setResult] = useState<InspectionWithTemporalEvidence | null>(null);
  const [activeRequestKey, setActiveRequestKey] = useState<string | null>(null);
  const inputKeyRef = useRef("");
  const requestSequenceRef = useRef(0);
  const inputKey = `${chainId.trim()}\u0000${tokenAddress.trim()}`;
  inputKeyRef.current = inputKey;
  const inspection = useInspectToken();

  function updateChainId(value: string) {
    requestSequenceRef.current += 1;
    setChainId(value);
    setResult(null);
    setActiveRequestKey(null);
  }

  function updateTokenAddress(value: string) {
    requestSequenceRef.current += 1;
    setTokenAddress(value);
    setResult(null);
    setActiveRequestKey(null);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (inspection.isPending) return;
    const nextChainId = chainId.trim();
    const nextTokenAddress = tokenAddress.trim();
    const requestKey = `${nextChainId}\u0000${nextTokenAddress}`;
    const requestSequence = ++requestSequenceRef.current;
    setResult(null);
    setActiveRequestKey(requestKey);
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

  const errorMessage =
    inspection.error instanceof Error
      ? inspection.error.message
      : "The inspection could not be completed. Check the inputs and try again.";
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
        <Card className="border-slate-200 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="text-lg">Start an inspection</CardTitle>
            <CardDescription>Enter a chain and token address, then submit once to request the current source response.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} className="grid gap-4 lg:grid-cols-[180px_1fr_auto] lg:items-end">
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Chain</span>
                <Input value={chainId} onChange={(event) => setChainId(event.target.value)} required maxLength={64} pattern="[A-Za-z0-9._~-]+" placeholder="ethereum" />
              </label>
              <label className="space-y-2">
                <span className="text-sm font-medium text-slate-700">Token address</span>
                <Input value={tokenAddress} onChange={(event) => setTokenAddress(event.target.value)} required maxLength={128} pattern="[A-Za-z0-9._~-]+" placeholder="0x..." />
              </label>
              <Button type="submit" disabled={inspection.isPending || !chainId.trim() || !tokenAddress.trim()} className="min-h-10 px-8 bg-[#0f766e] hover:bg-[#0d665f]">
                {inspection.isPending ? <LoaderCircle className="animate-spin" /> : <Search />}
                {inspection.isPending ? "Inspecting…" : "Inspect token"}
              </Button>
            </form>
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
            {report.payload.pairs.length === 0 ? (
               <Card className="border-dashed border-slate-300 bg-white/60"><CardContent className="py-12 text-center text-sm text-slate-500"><div className="font-medium text-slate-700">No pairs returned</div><div className="mt-2">The source returned no pair-level temporal records for this token.</div></CardContent></Card>
            ) : (
               report.payload.pairs.map((pair: InspectionPair, index: number) => <PairCard key={`${pair.pairAddress ?? "pair"}-${index}`} pair={pair} index={index} temporalRecord={temporalEvidence?.records[index]} />)
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