import { useMemo, useState } from "react";
import {
  Archive,
  Bot,
  CheckCircle2,
  Database,
  Eye,
  FileClock,
  History,
  KeyRound,
  LoaderCircle,
  Play,
  RefreshCw,
  Save,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

type CaseReview = {
  contract_version: string;
  handle: string;
  case_digest: string;
  state: string;
  created_at: string;
  expires_at: string;
  candidate_id: string;
  chain_id: string;
  token_mint: string;
  pool_address: string;
  eligibility: string;
  pfx_outcome: string;
  pfs_outcome: string;
  cip_outcome: string;
  cip_digest: string;
  oci_outcome?: string | null;
  oci_digest?: string | null;
  osc_outcome?: string | null;
  osc_digest?: string | null;
  lifecycle_result_digest?: string | null;
  persistence_outcome?: string | null;
  persistence_digest?: string | null;
  persistence_artifact_count?: number | null;
  readback_path?: string | null;
  simulation_only: boolean;
  source_label: string;
};

type PrepareResponse = {
  handle: string;
  case_digest: string;
  state: string;
  review_path: string;
};

type RunResponse = {
  handle: string;
  case_digest: string;
  state: string;
  outcome: string;
  reason_codes: string[];
  oci_outcome: string | null;
  oci_digest: string | null;
  osc_outcome: string | null;
  osc_digest: string | null;
  lifecycle_result_digest: string | null;
  persist_eligible: boolean;
};

type PersistResponse = {
  handle: string;
  case_digest: string;
  state: string;
  outcome: string;
  reason_codes: string[];
  persistence_outcome: string | null;
  persistence_digest: string | null;
  lifecycle_result_digest: string | null;
  artifact_count: number | null;
  readback_path: string | null;
};

type LifecycleRead = {
  contract_version: string;
  outcome: string;
  reason_codes: string[];
  lifecycle_result_digest: string;
  result_digest: string;
  run: { artifact_count: number; outcome: string } | null;
  artifacts: Array<{
    artifact_kind: string;
    artifact_digest: string;
    payload_digest: string;
    owner_contract_version: string;
    canonical_payload: string;
    ordinal: number;
  }>;
};

type LifecycleCatalog = {
  contract_version: string;
  outcome: string;
  reason_codes: string[];
  limit: number;
  after_digest: string | null;
  lifecycle_result_digests: string[];
  next_after_digest: string | null;
  result_digest: string;
};

type PrepareValidation = {
  contract_version: string;
  status: "VALID";
  candidate_id: string;
  token_mint: string;
  chain_id: string;
  pool_address: string;
  pfx_invocation_id: string;
  cip_invocation_id: string;
  selected_observation_time: string;
  provider_connectivity_checked: boolean;
  mutates_case: boolean;
  simulation_only: boolean;
};

type OperatorReadiness = {
  contract_version: string;
  status: "READY" | "NOT_READY";
  environment: string;
  checks: Record<string, string>;
  process_local_registry: boolean;
  provider_connectivity_checked: boolean;
  simulation_only: boolean;
};

type ApiErrorPayload = {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
};

const TEMPLATE = {
  candidate_id: "",
  token_mint: "",
  target: {
    chain_id: "solana",
    token_mint: "",
    pool_address: "",
    base_mint: "",
    quote_mint: "",
    target_reference_id: "",
    target_reference_digest: "",
    target_contract_version: "",
  },
  processing_time: "",
  reference_time: "",
  evaluation_time: "",
  freshness_seconds: 120,
  max_top_holder_fraction: 0.2,
  rti11_timeout_seconds: 5,
  rti11_max_response_bytes: 262144,
  evaluation_id: "",
  paper_intent: {
    pfx_invocation_id: "",
    cip_invocation_id: "",
    decision_ruleset: {
      buy_score_threshold: "50",
      watch_score_threshold: "10",
      max_evidence_age_seconds: 120,
      version: "",
    },
    decision_time: "",
    policy_seed: {
      policy_snapshot_id: "",
      risk_governor_version: "",
      capital_authorization_version: "",
      evaluator_version: "",
      paper_lifecycle_id: "",
      paper_portfolio_id: "",
      simulation_reference_time: "",
      policy_cutoff_time: "",
      risk_state_max_age_seconds: "120",
      paper_capital_state_max_age_seconds: "120",
      paper_exposure_state_max_age_seconds: "120",
      valid_from: "",
      valid_until: "",
      risk_state: {
        status: "PASS",
        emergency_stop: false,
        risk_flags: [],
        as_of_time: "",
        available_at: "",
      },
      paper_capital_state: {
        unit: "USD",
        budget_total: "0",
        committed_before: "0",
        requested_entry: "0",
        max_single_entry: "0",
        as_of_time: "",
        available_at: "",
      },
      paper_exposure_state: {
        unit: "USD",
        exposure_before: "0",
        max_total_exposure: "0",
        as_of_time: "",
        available_at: "",
      },
      provenance_source: "operator",
    },
    execution_observation: {
      observation_id: "",
      subject_identity: {},
      observation_time: "",
      availability_time: "",
      quality: "VALID",
      market_context_digest: null,
      quote_context_digest: null,
      liquidity_context_digest: null,
      sellability_status: "AVAILABLE",
      source_contract_version: "",
      source_provenance: {},
      observation_replay_key: "",
    },
    simulation_configuration: {
      configuration_id: "",
      contract_version: "",
      simulation_version: "",
      fill_model_version: "",
      friction_model_version: "",
      failure_policy_version: "",
      seed_policy_version: "",
      configuration_provenance: {},
    },
    replay_identity: {
      replay_id: "",
      replay_schema_version: "",
      replay_seed_identity: "",
      parent_replay_id: null,
      replay_scope: {},
    },
    simulation_reference_time: "",
    paper_evaluation_time: "",
    selected_observation_time: "",
    target_asset_identity: {},
    simulation_policy: {
      policy_id: "",
      policy_version: "",
      mode: "FRESH_GENESIS",
      side: "BUY",
      requested_quantity: "0",
      quantity_unit: "TOKEN",
      price_unit: "USD_PER_TOKEN",
      fee_unit: "USD",
      quote_currency: "USD",
      reference_price_rule: "OBSERVED_CLOSE_PROXY",
      quantity_rounding_rule: "EXACT_DECIMAL_18",
      simulated_fill_time: "",
      simulated_capacity: "0",
      allow_partial_fill: false,
      friction_values: {},
      valuation_max_age_seconds: "120",
      accounting_fee: "0",
      accounting_priority_fee: "0",
      accounting_observed_at: "",
      accounting_contract_version: "",
      ledger_stream_identity: {},
      sequence_number: 1,
      previous_entry_digest: null,
      expectation_id: "",
      expectation_fields: [],
      fill_model_version: "",
      friction_model_version: "",
      provenance: {},
    },
    genesis: {
      state_id: "",
      state_version: "",
      portfolio_scope: {},
      target_asset_identity: {},
      as_of_time: "",
      zero_quantity: "0",
      zero_cost_basis: "0",
      provenance: {},
    },
  },
};

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

function short(value: string | null | undefined, size = 10) {
  if (!value) return "—";
  return value.length <= size * 2 + 3
    ? value
    : `${value.slice(0, size)}…${value.slice(-size)}`;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function artifactPayload(readback: LifecycleRead | null, kind: string): Record<string, unknown> | null {
  const artifact = readback?.artifacts.find((item) => item.artifact_kind === kind);
  if (!artifact) return null;
  try {
    return asRecord(JSON.parse(artifact.canonical_payload));
  } catch {
    return null;
  }
}

function displayCanonical(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string" || typeof value === "number") return String(value);
  if (typeof value === "boolean") return value ? "true" : "false";
  return null;
}

function displayIdentity(value: unknown): string | null {
  const record = asRecord(value);
  if (!record) return null;
  return JSON.stringify(record);
}

function stateTone(state: string | undefined) {
  if (!state) return "border-slate-700 bg-slate-900/70 text-slate-300";
  if (
    state.includes("TERMINAL") ||
    state === "REVIEW_READY" ||
    state === "STORED" ||
    state === "ALREADY_STORED"
  ) {
    return "border-emerald-500/40 bg-emerald-500/10 text-emerald-200";
  }
  if (state.includes("UNKNOWN") || state.includes("UNAVAILABLE")) {
    return "border-amber-500/40 bg-amber-500/10 text-amber-100";
  }
  if (state.includes("STOPPED") || state.includes("BLOCK")) {
    return "border-rose-500/40 bg-rose-500/10 text-rose-200";
  }
  return "border-sky-500/40 bg-sky-500/10 text-sky-100";
}

function AgentPod({
  name,
  role,
  status,
  icon: Icon,
}: {
  name: string;
  role: string;
  status: string;
  icon: typeof Bot;
}) {
  return (
    <div className="group relative rounded-2xl border border-white/10 bg-slate-950/65 p-3 shadow-[0_12px_35px_rgba(0,0,0,0.28)] backdrop-blur">
      <div className="flex items-center gap-3">
        <div className="relative grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-amber-300/25 bg-gradient-to-br from-slate-800 to-slate-950 shadow-inner">
          <div className="absolute -inset-px rounded-xl bg-[linear-gradient(135deg,rgba(245,158,11,.18),transparent_55%)]" />
          <Icon className="relative h-5 w-5 text-amber-200" />
          <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border border-slate-950 bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,.65)]" />
        </div>
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-amber-200/70">
            {role}
          </div>
          <div className="truncate text-sm font-semibold text-slate-50">{name}</div>
          <div className="mt-1 truncate text-[11px] text-slate-400">{status}</div>
        </div>
      </div>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.035] px-3 py-2.5">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
        {label}
      </div>
      <div className="mt-1 break-all font-mono text-xs text-slate-200">
        {value ?? "—"}
      </div>
    </div>
  );
}

async function decodeResponse<T>(response: Response): Promise<T> {
  const raw = await response.text();
  let parsed: unknown = null;
  if (raw) {
    try {
      parsed = JSON.parse(raw);
    } catch {
      parsed = raw;
    }
  }
  if (!response.ok) {
    const error = parsed as ApiErrorPayload;
    const detail = error?.error;
    throw new Error(
      [
        detail?.code || `HTTP_${response.status}`,
        detail?.message,
        detail?.request_id ? `request ${detail.request_id}` : undefined,
      ]
        .filter(Boolean)
        .join(" · "),
    );
  }
  return parsed as T;
}

export default function HunterRoom() {
  const [apiBase, setApiBase] = useState("");
  const [token, setToken] = useState("");
  const [prepareJson, setPrepareJson] = useState(() => formatJson(TEMPLATE));
  const [handleInput, setHandleInput] = useState("");
  const [activeHandle, setActiveHandle] = useState("");
  const [caseView, setCaseView] = useState<CaseReview | null>(null);
  const [lastRun, setLastRun] = useState<RunResponse | null>(null);
  const [lastPersist, setLastPersist] = useState<PersistResponse | null>(null);
  const [readback, setReadback] = useState<LifecycleRead | null>(null);
  const [history, setHistory] = useState<LifecycleCatalog | null>(null);
  const [readiness, setReadiness] = useState<OperatorReadiness | null>(null);
  const [prepareValidation, setPrepareValidation] = useState<PrepareValidation | null>(null);
  const [busy, setBusy] = useState<"prepare" | "validate" | "refresh" | "run" | "persist" | "readback" | "history" | "readiness" | null>(null);
  const [message, setMessage] = useState("No case loaded. Hunter Room is idle.");

  const base = useMemo(() => apiBase.trim().replace(/\/$/, ""), [apiBase]);

  const lifecycleDetail = useMemo(() => {
    if (!readback) return null;
    const fill = artifactPayload(readback, "FILL_OUTCOME");
    const transition = artifactPayload(readback, "STATE_TRANSITION");
    const resultingState = artifactPayload(readback, "RESULTING_PAPER_STATE");
    const accounting = asRecord(transition?.accounting_effect);
    const quantityEffect = asRecord(transition?.quantity_effect);
    const exposure = asRecord(resultingState?.exposure);
    const positions = Array.isArray(resultingState?.positions) ? resultingState.positions : [];
    const firstPosition = positions.length === 1 ? asRecord(positions[0]) : null;

    return {
      fillStatus: displayCanonical(fill?.status),
      side: displayCanonical(fill?.side),
      requestedQuantity: displayCanonical(fill?.requested_quantity),
      filledQuantity: displayCanonical(fill?.filled_quantity),
      remainingQuantity: displayCanonical(fill?.remaining_quantity),
      quantityUnit: displayCanonical(fill?.quantity_unit),
      effectivePrice: displayCanonical(fill?.effective_price),
      priceUnit: displayCanonical(fill?.price_unit),
      quoteCurrency: displayCanonical(fill?.quote_currency),
      fillTime: displayCanonical(fill?.fill_time),
      assetIdentity: displayIdentity(fill?.asset_identity),
      transitionStatus: displayCanonical(transition?.transition_status),
      transitionTime: displayCanonical(transition?.transition_reference_time),
      nextQuantity: displayCanonical(quantityEffect?.next_quantity),
      tradeValue: displayCanonical(accounting?.trade_value),
      acquisitionCost: displayCanonical(accounting?.acquisition_cost),
      removedCost: displayCanonical(accounting?.removed_cost),
      proceeds: displayCanonical(accounting?.proceeds),
      feeAmount: displayCanonical(accounting?.fee_amount),
      priorityFeeAmount: displayCanonical(accounting?.priority_fee_amount),
      accountingUnit: displayCanonical(accounting?.unit),
      stateQuality: displayCanonical(resultingState?.state_quality),
      stateAsOf: displayCanonical(resultingState?.as_of_time),
      positionQuantity: displayCanonical(firstPosition?.quantity),
      totalCostBasis: displayCanonical(firstPosition?.total_cost_basis),
      averageCost: displayCanonical(firstPosition?.average_cost),
      costBasisUnit: displayCanonical(firstPosition?.cost_basis_unit),
      valuationStatus: displayCanonical(exposure?.valuation_status),
      grossNotionalExposure: displayCanonical(exposure?.gross_notional_exposure),
    };
  }, [readback]);

  function authHeaders() {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token.trim()) headers.Authorization = `Bearer ${token.trim()}`;
    return headers;
  }

  async function api<T>(path: string, init: RequestInit = {}) {
    return decodeResponse<T>(
      await fetch(`${base}${path}`, {
        ...init,
        headers: {
          ...authHeaders(),
          ...(init.headers || {}),
        },
      }),
    );
  }

  async function checkReadiness() {
    if (!token.trim()) {
      setMessage("Operator bearer token is required for readiness.");
      return;
    }
    setBusy("readiness");
    try {
      const response = await fetch(`${base}/api/v1/operator/paper-cases/readiness`, {
        headers: authHeaders(),
      });
      const raw = await response.text();
      let parsed: unknown = null;
      if (raw) {
        try {
          parsed = JSON.parse(raw);
        } catch {
          parsed = raw;
        }
      }

      if (
        (response.status === 200 || response.status === 503) &&
        parsed &&
        typeof parsed === "object" &&
        "contract_version" in parsed &&
        "status" in parsed
      ) {
        const result = parsed as OperatorReadiness;
        setReadiness(result);
        setMessage(
          result.status === "READY"
            ? "Operator chain is configured for controlled-paper use."
            : "Operator chain is not ready; review the reported checks.",
        );
        return;
      }

      if (!response.ok) {
        const error = parsed as ApiErrorPayload;
        const detail = error?.error;
        throw new Error(
          [
            detail?.code || `HTTP_${response.status}`,
            detail?.message,
            detail?.request_id ? `request ${detail.request_id}` : undefined,
          ]
            .filter(Boolean)
            .join(" · "),
        );
      }
      throw new Error("Readiness response did not match the expected contract.");
    } catch (error) {
      setReadiness(null);
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function validatePreparePayload() {
    if (!token.trim()) {
      setMessage("Operator bearer token is required for payload validation.");
      return;
    }
    setBusy("validate");
    setPrepareValidation(null);
    try {
      const payload = JSON.parse(prepareJson);
      const result = await api<PrepareValidation>(
        "/api/v1/operator/paper-cases/validate",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setPrepareValidation(result);
      setMessage("Prepare payload is locally canonical. Provider/eligibility checks were not run.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function refreshCase(handle = activeHandle || handleInput.trim()) {
    if (!handle) {
      setMessage("Enter or create a case handle first.");
      return;
    }
    setBusy("refresh");
    try {
      const result = await api<CaseReview>(`/api/v1/operator/paper-cases/${encodeURIComponent(handle)}`);
      setCaseView(result);
      setActiveHandle(handle);
      setHandleInput(handle);
      setMessage(`Case refreshed: ${result.state}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function prepareCase() {
    setBusy("prepare");
    setReadback(null);
    setLastRun(null);
    setLastPersist(null);
    try {
      const payload = JSON.parse(prepareJson);
      const result = await api<PrepareResponse>("/api/v1/operator/paper-cases", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setActiveHandle(result.handle);
      setHandleInput(result.handle);
      setMessage(`Prepared case: ${result.state}`);
      await refreshCase(result.handle);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function runCase() {
    if (!caseView) return;
    setBusy("run");
    try {
      const result = await api<RunResponse>(
        `/api/v1/operator/paper-cases/${encodeURIComponent(caseView.handle)}/run`,
        {
          method: "POST",
          body: JSON.stringify({
            case_digest: caseView.case_digest,
            confirm_run: true,
          }),
        },
      );
      setLastRun(result);
      setMessage(`Run result: ${result.outcome}`);
      await refreshCase(caseView.handle);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function persistCase() {
    if (!caseView?.oci_digest || !caseView.osc_digest || !caseView.lifecycle_result_digest) return;
    setBusy("persist");
    try {
      const result = await api<PersistResponse>(
        `/api/v1/operator/paper-cases/${encodeURIComponent(caseView.handle)}/persist`,
        {
          method: "POST",
          body: JSON.stringify({
            case_digest: caseView.case_digest,
            oci_digest: caseView.oci_digest,
            osc_digest: caseView.osc_digest,
            lifecycle_result_digest: caseView.lifecycle_result_digest,
            confirm_persist: true,
          }),
        },
      );
      setLastPersist(result);
      setMessage(`Persistence result: ${result.persistence_outcome || result.outcome}`);
      await refreshCase(caseView.handle);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function readLifecycle() {
    const digest = caseView?.lifecycle_result_digest || lastPersist?.lifecycle_result_digest;
    if (!digest) return;
    setBusy("readback");
    try {
      const result = await api<LifecycleRead>(
        `/api/v1/paper-lifecycle-results/${encodeURIComponent(digest)}`,
      );
      setReadback(result);
      setMessage(`Readback: ${result.outcome}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function loadHistory(afterDigest?: string) {
    setBusy("history");
    try {
      const query = new URLSearchParams({ limit: "20" });
      if (afterDigest) query.set("after_digest", afterDigest);
      const result = await api<LifecycleCatalog>(
        `/api/v1/paper-lifecycle-results?${query.toString()}`,
      );
      setHistory(result);
      setMessage(
        result.lifecycle_result_digests.length
          ? `Loaded ${result.lifecycle_result_digests.length} persisted lifecycle identities.`
          : "Persisted lifecycle catalog is empty.",
      );
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  async function inspectHistoryDigest(digest: string) {
    setBusy("readback");
    try {
      const result = await api<LifecycleRead>(
        `/api/v1/paper-lifecycle-results/${encodeURIComponent(digest)}`,
      );
      setReadback(result);
      setMessage(`Readback: ${result.outcome}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(null);
    }
  }

  const state = caseView?.state || "IDLE";
  const canRun = state === "REVIEW_READY";
  const canPersist =
    state === "RUN_TERMINAL" &&
    Boolean(caseView?.oci_digest && caseView?.osc_digest && caseView?.lifecycle_result_digest);

  const agentStates = [
    {
      name: "Scout",
      role: "Trusted Source",
      status: caseView ? `${caseView.chain_id} evidence held` : "Awaiting explicit case",
      icon: ScanSearch,
    },
    {
      name: "Aegis",
      role: "Safety",
      status: caseView ? caseView.eligibility : "No eligibility result",
      icon: ShieldCheck,
    },
    {
      name: "Oracle",
      role: "Decision",
      status: caseView ? caseView.pfx_outcome : "No PFX result",
      icon: Sparkles,
    },
    {
      name: "Forge",
      role: "Paper Engine",
      status: caseView ? `${caseView.pfs_outcome} / ${caseView.cip_outcome}` : "No prepared simulation",
      icon: Bot,
    },
    {
      name: "Vault",
      role: "Persistence",
      status: caseView?.persistence_outcome || (caseView ? "Not persisted" : "Idle"),
      icon: Archive,
    },
  ];

  return (
    <div className="min-h-screen bg-[#050912] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_50%_18%,rgba(37,99,235,.14),transparent_32%),radial-gradient(circle_at_50%_58%,rgba(245,158,11,.08),transparent_35%)]" />
      <div className="relative mx-auto max-w-[1500px] p-3 sm:p-5 lg:p-7">
        <header className="mb-4 flex flex-col gap-3 rounded-2xl border border-white/8 bg-slate-950/75 px-4 py-3 backdrop-blur sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.22em] text-amber-200/75">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-300 shadow-[0_0_10px_rgba(252,211,77,.8)]" />
              MemeCoinHunterAI
            </div>
            <h1 className="mt-1 text-xl font-semibold tracking-tight text-white sm:text-2xl">
              Hunter Room
            </h1>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${stateTone(state)}`}>
              {state}
            </span>
            <span className="rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-xs text-sky-100">
              PAPER · SIMULATION ONLY
            </span>
          </div>
        </header>

        <section className="grid gap-4 xl:grid-cols-[310px_minmax(0,1fr)_330px]">
          <aside className="space-y-4">
            <Card className="border-white/10 bg-slate-950/75 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <KeyRound className="h-4 w-4 text-amber-300" />
                  Operator session
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs text-slate-400">API base</label>
                  <Input
                    value={apiBase}
                    onChange={(event) => setApiBase(event.target.value)}
                    placeholder="Same origin, or https://api.example"
                    className="border-white/10 bg-white/5 text-slate-100"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-xs text-slate-400">Bearer token</label>
                  <Input
                    type="password"
                    autoComplete="off"
                    value={token}
                    onChange={(event) => setToken(event.target.value)}
                    placeholder="Session only; never stored"
                    className="border-white/10 bg-white/5 text-slate-100"
                  />
                </div>
                <p className="text-[11px] leading-5 text-slate-500">
                  The token stays in browser memory only. Use TLS or a trusted same-origin proxy.
                </p>

                <div className="rounded-xl border border-white/8 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Operator readiness
                      </div>
                      <div className="mt-1 text-xs text-slate-300">
                        {readiness ? readiness.status : "Not checked"}
                      </div>
                    </div>
                    <span className={`rounded-full border px-2 py-1 text-[10px] font-semibold ${
                      readiness?.status === "READY"
                        ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100"
                        : readiness?.status === "NOT_READY"
                          ? "border-amber-400/30 bg-amber-400/10 text-amber-100"
                          : "border-white/10 bg-white/5 text-slate-400"
                    }`}>
                      {readiness?.environment || "manual"}
                    </span>
                  </div>

                  {readiness && (
                    <div className="mt-3 grid gap-1.5">
                      {Object.entries(readiness.checks).map(([name, value]) => (
                        <div
                          key={name}
                          className="flex items-center justify-between gap-3 text-[11px]"
                        >
                          <span className="text-slate-500">{name.replaceAll("_", " ")}</span>
                          <span className="font-mono text-slate-300">{value}</span>
                        </div>
                      ))}
                      <div className="mt-1 text-[10px] leading-4 text-slate-600">
                        Provider connectivity is not probed by this check.
                      </div>
                    </div>
                  )}

                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="mt-3 w-full border-emerald-300/20 bg-emerald-300/5 text-emerald-100"
                    disabled={busy !== null || !token.trim()}
                    onClick={() => void checkReadiness()}
                  >
                    {busy === "readiness" ? <LoaderCircle className="animate-spin" /> : <CheckCircle2 />}
                    Check readiness
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/75 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-base">
                  <Eye className="h-4 w-4 text-sky-300" />
                  Open case
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Input
                  value={handleInput}
                  onChange={(event) => setHandleInput(event.target.value)}
                  placeholder="Opaque case handle"
                  className="border-white/10 bg-white/5 font-mono text-xs text-slate-100"
                />
                <Button
                  type="button"
                  variant="outline"
                  className="w-full border-sky-300/25 bg-sky-300/5 text-sky-100"
                  disabled={busy !== null}
                  onClick={() => void refreshCase()}
                >
                  {busy === "refresh" ? <LoaderCircle className="animate-spin" /> : <RefreshCw />}
                  Refresh case
                </Button>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/75 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Exact prepare payload</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea
                  value={prepareJson}
                  onChange={(event) => {
                    setPrepareJson(event.target.value);
                    setPrepareValidation(null);
                  }}
                  className="min-h-[290px] border-white/10 bg-black/20 font-mono text-[11px] leading-5 text-slate-200"
                  spellCheck={false}
                />
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <Button
                    type="button"
                    variant="outline"
                    className="border-white/10 bg-white/5 text-slate-200"
                    onClick={() => {
                      setPrepareJson(formatJson(TEMPLATE));
                      setPrepareValidation(null);
                    }}
                  >
                    Reset template
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy !== null || !token.trim()}
                    className="border-emerald-300/20 bg-emerald-300/5 text-emerald-100"
                    onClick={() => void validatePreparePayload()}
                  >
                    {busy === "validate" ? <LoaderCircle className="animate-spin" /> : <CheckCircle2 />}
                    Validate
                  </Button>
                  <Button
                    type="button"
                    disabled={busy !== null || !token.trim()}
                    className="bg-amber-300 text-slate-950 hover:bg-amber-200"
                    onClick={() => void prepareCase()}
                  >
                    {busy === "prepare" ? <LoaderCircle className="animate-spin" /> : <ScanSearch />}
                    Prepare
                  </Button>
                </div>
                <p className="text-[11px] leading-5 text-slate-500">
                  No hidden defaults. The template is only a schema aid; every policy,
                  time, identity and simulation assumption must be explicitly reviewed.
                </p>

                {prepareValidation && (
                  <div className="rounded-xl border border-emerald-300/15 bg-emerald-300/5 p-3">
                    <div className="flex items-center justify-between gap-2">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-200/75">
                        Payload validation
                      </div>
                      <span className="rounded-full border border-emerald-300/20 px-2 py-1 text-[10px] font-semibold text-emerald-100">
                        {prepareValidation.status}
                      </span>
                    </div>
                    <div className="mt-2 grid gap-1 text-[11px] text-slate-400">
                      <div>Candidate: <span className="font-mono text-slate-300">{prepareValidation.candidate_id}</span></div>
                      <div>Pool: <span className="font-mono text-slate-300">{short(prepareValidation.pool_address, 8)}</span></div>
                      <div>Selected observation: <span className="font-mono text-slate-300">{prepareValidation.selected_observation_time}</span></div>
                    </div>
                    <div className="mt-2 text-[10px] leading-4 text-slate-500">
                      Local canonical decode only. No provider connectivity, eligibility, RTI-11,
                      PFX/PFS/CIP execution or case mutation was performed.
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </aside>

          <main className="space-y-4">
            <section className="relative overflow-hidden rounded-[28px] border border-amber-200/12 bg-[linear-gradient(180deg,rgba(11,18,32,.96),rgba(4,8,16,.98))] p-4 shadow-[0_30px_80px_rgba(0,0,0,.4)] sm:p-6">
              <div className="pointer-events-none absolute inset-0 opacity-40 [background-image:linear-gradient(rgba(148,163,184,.05)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,.05)_1px,transparent_1px)] [background-size:28px_28px]" />
              <div className="relative">
                <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-amber-200/65">
                      Central chamber
                    </div>
                    <h2 className="mt-1 text-xl font-semibold text-white">Case command floor</h2>
                  </div>
                  <div className="text-xs text-slate-500">
                    Actual server state only · no invented live activity
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-[1fr_1.2fr_1fr] md:items-center">
                  <div className="space-y-3">
                    <AgentPod {...agentStates[0]} />
                    <AgentPod {...agentStates[1]} />
                  </div>

                  <div className="relative mx-auto grid min-h-[270px] w-full max-w-[430px] place-items-center">
                    <div className="absolute h-60 w-60 rounded-full border border-sky-300/10 bg-sky-400/[0.025] shadow-[0_0_80px_rgba(56,189,248,.08)]" />
                    <div className="absolute h-44 w-44 rounded-full border border-amber-300/15" />
                    <div className="relative z-10 w-[190px] rounded-[24px] border border-amber-200/25 bg-slate-950/90 p-5 text-center shadow-[0_20px_70px_rgba(0,0,0,.5)]">
                      <div className="mx-auto mb-3 grid h-12 w-12 place-items-center rounded-2xl border border-amber-200/20 bg-amber-200/5">
                        <FileClock className="h-6 w-6 text-amber-200" />
                      </div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                        Case core
                      </div>
                      <div className="mt-2 text-sm font-semibold text-white">
                        {caseView ? short(caseView.handle, 7) : "No active case"}
                      </div>
                      <div className="mt-2 text-[11px] text-slate-400">
                        {caseView ? caseView.state : "Load or prepare one explicit paper case"}
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <AgentPod {...agentStates[2]} />
                    <AgentPod {...agentStates[3]} />
                    <AgentPod {...agentStates[4]} />
                  </div>
                </div>
              </div>
            </section>

            <Card className="border-white/10 bg-slate-950/75 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between gap-3 text-base">
                  <span>Case review</span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-white/10 bg-white/5 text-slate-200"
                    disabled={!caseView || busy !== null}
                    onClick={() => void refreshCase()}
                  >
                    <RefreshCw />
                    Manual refresh
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {caseView ? (
                  <div className="space-y-4">
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <KeyValue label="Candidate" value={caseView.candidate_id} />
                      <KeyValue label="Token mint" value={short(caseView.token_mint, 9)} />
                      <KeyValue label="Exact pool" value={short(caseView.pool_address, 9)} />
                      <KeyValue label="Eligibility" value={caseView.eligibility} />
                      <KeyValue label="PFX" value={caseView.pfx_outcome} />
                      <KeyValue label="PFS" value={caseView.pfs_outcome} />
                      <KeyValue label="CIP" value={caseView.cip_outcome} />
                      <KeyValue label="Case digest" value={short(caseView.case_digest, 9)} />
                    </div>

                    <div className="rounded-xl border border-sky-400/15 bg-sky-400/5 px-3 py-2 text-xs leading-5 text-sky-100/80">
                      Historical OHLCV is a simulation-only price proxy. Capacity, friction,
                      fee and replay values are explicit paper assumptions, not executable liquidity
                      or guaranteed fills.
                    </div>

                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                      <KeyValue label="OCI" value={caseView.oci_outcome || "Not run"} />
                      <KeyValue label="OSC" value={caseView.osc_outcome || "Not run"} />
                      <KeyValue label="Lifecycle" value={short(caseView.lifecycle_result_digest, 8)} />
                      <KeyValue label="Persistence" value={caseView.persistence_outcome || "Not persisted"} />
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-dashed border-white/10 px-4 py-10 text-center text-sm text-slate-500">
                    Review data appears here after an authenticated prepare or manual case lookup.
                  </div>
                )}
              </CardContent>
            </Card>
          </main>

          <aside className="space-y-4">
            <Card className="border-white/10 bg-slate-950/80 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Operator controls</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  type="button"
                  className="w-full bg-sky-300 text-slate-950 hover:bg-sky-200"
                  disabled={!canRun || busy !== null}
                  onClick={() => void runCase()}
                >
                  {busy === "run" ? <LoaderCircle className="animate-spin" /> : <Play />}
                  Run paper case once
                </Button>
                <Button
                  type="button"
                  className="w-full bg-amber-300 text-slate-950 hover:bg-amber-200"
                  disabled={!canPersist || busy !== null}
                  onClick={() => void persistCase()}
                >
                  {busy === "persist" ? <LoaderCircle className="animate-spin" /> : <Save />}
                  Persist exact lifecycle
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="w-full border-emerald-300/20 bg-emerald-300/5 text-emerald-100"
                  disabled={!caseView?.lifecycle_result_digest || busy !== null}
                  onClick={() => void readLifecycle()}
                >
                  {busy === "readback" ? <LoaderCircle className="animate-spin" /> : <Database />}
                  Read persisted lifecycle
                </Button>

                <div className="rounded-xl border border-white/8 bg-black/20 p-3 text-[11px] leading-5 text-slate-400">
                  <div className="font-semibold text-slate-200">No automatic retry</div>
                  Run and persist controls rely on the server state machine. Unknown outcomes stay
                  terminal until the controller resolves them.
                </div>
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/80 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Terminal detail</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <KeyValue label="OCI digest" value={short(caseView?.oci_digest, 8)} />
                <KeyValue label="OSC digest" value={short(caseView?.osc_digest, 8)} />
                <KeyValue label="Lifecycle digest" value={short(caseView?.lifecycle_result_digest, 8)} />
                <KeyValue label="RTI-03 digest" value={short(caseView?.persistence_digest, 8)} />
                <KeyValue
                  label="Stored artifacts"
                  value={caseView?.persistence_artifact_count ?? "—"}
                />
              </CardContent>
            </Card>

            <Card className="border-white/10 bg-slate-950/80 text-slate-100">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center justify-between gap-2 text-base">
                  <span className="flex items-center gap-2">
                    <History className="h-4 w-4 text-sky-300" />
                    Persisted lifecycle catalog
                  </span>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="border-white/10 bg-white/5 text-slate-200"
                    disabled={busy !== null}
                    onClick={() => void loadHistory()}
                  >
                    {busy === "history" ? <LoaderCircle className="animate-spin" /> : <RefreshCw />}
                    Load
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-[11px] leading-5 text-slate-500">
                  RTI-07 returns canonical digests in lexicographic order, not a profitability or
                  recency ranking. Detail is fetched only when you inspect one digest.
                </p>
                {history ? (
                  <>
                    {history.lifecycle_result_digests.length ? (
                      <div className="max-h-64 space-y-2 overflow-y-auto pr-1">
                        {history.lifecycle_result_digests.map((digest) => (
                          <button
                            key={digest}
                            type="button"
                            disabled={busy !== null}
                            onClick={() => void inspectHistoryDigest(digest)}
                            className="flex w-full items-center justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.035] px-3 py-2 text-left transition hover:border-sky-300/25 hover:bg-sky-300/5 disabled:opacity-50"
                          >
                            <span className="font-mono text-[11px] text-slate-300">
                              {short(digest, 10)}
                            </span>
                            <Eye className="h-3.5 w-3.5 shrink-0 text-sky-300" />
                          </button>
                        ))}
                      </div>
                    ) : (
                      <div className="rounded-xl border border-dashed border-white/10 px-3 py-5 text-center text-xs text-slate-500">
                        No persisted lifecycle identities in this catalog page.
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="border-white/10 bg-white/5 text-slate-200"
                        disabled={busy !== null || history.after_digest === null}
                        onClick={() => void loadHistory()}
                      >
                        First page
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="border-white/10 bg-white/5 text-slate-200"
                        disabled={busy !== null || !history.next_after_digest}
                        onClick={() => void loadHistory(history.next_after_digest || undefined)}
                      >
                        Next page
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="rounded-xl border border-dashed border-white/10 px-3 py-5 text-center text-xs text-slate-500">
                    Load the bounded persisted lifecycle catalog manually.
                  </div>
                )}
              </CardContent>
            </Card>

            {readback && (
              <Card className="border-emerald-400/20 bg-emerald-400/5 text-slate-100">
                <CardHeader className="pb-3">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                    Durable readback
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-xs">
                  <KeyValue label="Outcome" value={readback.outcome} />
                  <KeyValue label="Artifacts" value={readback.artifacts.length} />
                  <KeyValue label="Lifecycle digest" value={short(readback.lifecycle_result_digest, 8)} />
                  <KeyValue label="Result digest" value={short(readback.result_digest, 8)} />

                  {lifecycleDetail && (
                    <div className="space-y-3 rounded-xl border border-emerald-300/12 bg-black/20 p-3">
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-emerald-200/70">
                          Canonical paper detail
                        </div>
                        <div className="mt-1 text-[11px] leading-5 text-slate-500">
                          Direct projection of persisted canonical artifacts. No P&amp;L or profitability is inferred here.
                        </div>
                      </div>

                      <div className="grid gap-2 sm:grid-cols-2">
                        <KeyValue label="Fill status" value={lifecycleDetail.fillStatus} />
                        <KeyValue label="Side" value={lifecycleDetail.side} />
                        <KeyValue
                          label="Requested quantity"
                          value={
                            lifecycleDetail.requestedQuantity && lifecycleDetail.quantityUnit
                              ? `${lifecycleDetail.requestedQuantity} ${lifecycleDetail.quantityUnit}`
                              : lifecycleDetail.requestedQuantity
                          }
                        />
                        <KeyValue
                          label="Filled quantity"
                          value={
                            lifecycleDetail.filledQuantity && lifecycleDetail.quantityUnit
                              ? `${lifecycleDetail.filledQuantity} ${lifecycleDetail.quantityUnit}`
                              : lifecycleDetail.filledQuantity
                          }
                        />
                        <KeyValue
                          label="Effective price"
                          value={
                            lifecycleDetail.effectivePrice && lifecycleDetail.priceUnit
                              ? `${lifecycleDetail.effectivePrice} ${lifecycleDetail.priceUnit}`
                              : lifecycleDetail.effectivePrice
                          }
                        />
                        <KeyValue label="Fill time" value={lifecycleDetail.fillTime} />
                        <KeyValue label="Transition" value={lifecycleDetail.transitionStatus} />
                        <KeyValue label="Transition time" value={lifecycleDetail.transitionTime} />
                        <KeyValue
                          label="Trade value"
                          value={
                            lifecycleDetail.tradeValue && lifecycleDetail.accountingUnit
                              ? `${lifecycleDetail.tradeValue} ${lifecycleDetail.accountingUnit}`
                              : lifecycleDetail.tradeValue
                          }
                        />
                        <KeyValue
                          label="Fee amount"
                          value={
                            lifecycleDetail.feeAmount && lifecycleDetail.accountingUnit
                              ? `${lifecycleDetail.feeAmount} ${lifecycleDetail.accountingUnit}`
                              : lifecycleDetail.feeAmount
                          }
                        />
                        <KeyValue
                          label="Priority fee"
                          value={
                            lifecycleDetail.priorityFeeAmount && lifecycleDetail.accountingUnit
                              ? `${lifecycleDetail.priorityFeeAmount} ${lifecycleDetail.accountingUnit}`
                              : lifecycleDetail.priorityFeeAmount
                          }
                        />
                        <KeyValue label="Next quantity" value={lifecycleDetail.nextQuantity} />
                        <KeyValue label="State quality" value={lifecycleDetail.stateQuality} />
                        <KeyValue label="State as-of" value={lifecycleDetail.stateAsOf} />
                        <KeyValue label="Position quantity" value={lifecycleDetail.positionQuantity} />
                        <KeyValue
                          label="Total cost basis"
                          value={
                            lifecycleDetail.totalCostBasis && lifecycleDetail.costBasisUnit
                              ? `${lifecycleDetail.totalCostBasis} ${lifecycleDetail.costBasisUnit}`
                              : lifecycleDetail.totalCostBasis
                          }
                        />
                        <KeyValue
                          label="Average cost"
                          value={
                            lifecycleDetail.averageCost && lifecycleDetail.costBasisUnit
                              ? `${lifecycleDetail.averageCost} ${lifecycleDetail.costBasisUnit}`
                              : lifecycleDetail.averageCost
                          }
                        />
                        <KeyValue label="Valuation status" value={lifecycleDetail.valuationStatus} />
                        <KeyValue
                          label="Gross notional exposure"
                          value={lifecycleDetail.grossNotionalExposure}
                        />
                      </div>

                      {lifecycleDetail.assetIdentity && (
                        <KeyValue label="Canonical asset identity" value={lifecycleDetail.assetIdentity} />
                      )}
                    </div>
                  )}
                  {readback.artifacts.length > 0 && (
                    <div className="rounded-xl border border-white/8 bg-black/20 p-3">
                      <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">
                        Artifact kinds
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {readback.artifacts.map((artifact) => (
                          <span
                            key={artifact.artifact_digest}
                            className="rounded-full border border-emerald-300/15 bg-emerald-300/5 px-2 py-1 text-[10px] text-emerald-100"
                          >
                            {artifact.artifact_kind}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            <div className={`rounded-2xl border p-3 text-xs leading-5 ${message.includes("HTTP_") || message.includes("invalid") || message.includes("required") ? "border-rose-400/25 bg-rose-400/5 text-rose-100" : "border-white/10 bg-slate-950/70 text-slate-400"}`}>
              <div className="mb-1 flex items-center gap-2 font-semibold text-slate-200">
                {message.includes("HTTP_") ? <TriangleAlert className="h-4 w-4" /> : <FileClock className="h-4 w-4" />}
                Activity
              </div>
              {message}
            </div>
          </aside>
        </section>

        <footer className="mt-4 rounded-2xl border border-white/8 bg-slate-950/60 px-4 py-3 text-[11px] leading-5 text-slate-500">
          Hunter Room is an operator surface for controlled paper simulation. It does not sign,
          broadcast, route, settle, or execute live economic trades. G2/G3/G4/P09 remain outside
          this surface.
        </footer>
      </div>
    </div>
  );
}
