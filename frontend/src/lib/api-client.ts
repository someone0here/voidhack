/**
 * api-client.ts — Typed fetch wrapper for the Cyber Fraud Correlator backend.
 *
 * Every interface here mirrors a backend Pydantic schema 1:1 so the frontend
 * and API can never silently drift apart. Source of truth per type is noted
 * above each block.
 *
 * Base URL resolution: `VITE_API_URL` (see .env.example), falling back to the
 * local dev default. Routes are called at the root mount (`app.include_router
 * (api_router)` in main.py mirrors every `/cases/...` route at root for
 * frontend compatibility), so no `/api/v1` prefix is used here.
 */

const API_BASE_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/+$/, '') ??
  'http://localhost:8000';

// ── Enums — mirror app/db/models.py ─────────────────────────────────────────

export type SourceType = 'cdr' | 'ipdr' | 'bank_upi' | 'email' | 'android_log';

export type EntityType =
  'phone' | 'account' | 'device_imei' | 'ip_address' | 'mac_address' | 'email_address';

export type LinkType =
  | 'shared_imei'
  | 'shared_upi_handle'
  | 'shared_mac'
  | 'shared_ip_subnet'
  | 'co_occurrence'
  | 'direct_communication'
  | 'transaction';

export type CaseStatus = 'active' | 'closed' | 'archived';

// ── Case — mirror app/schemas/case.py ───────────────────────────────────────

export interface CaseCreate {
  name: string;
  status?: CaseStatus;
}

export interface CaseRead {
  id: number;
  name: string;
  status: CaseStatus;
  created_at: string;
}

// ── Ingestion — mirror app/services/ingestion/models.py::IngestionSummary ──

export interface IngestionSummary {
  rows_processed: number;
  rows_skipped: number;
  entities_created: number;
  entity_links_created: number;
  skipped_reasons: string[];
}

// ── Graph — mirror app/services/correlation/graph_serializer.py ────────────

export interface SerializedNode {
  id: number;
  entity_type: string;
  value: string;
  cluster_id: number;
}

export interface SerializedEdge {
  source: number;
  target: number;
  confidence: number;
  link_type: string;
  confidence_label: string;
}

export interface SerializedGraph {
  nodes: SerializedNode[];
  edges: SerializedEdge[];
}

// ── Risk — mirror RankedEntityRiskRead in app/api/v1/cases.py ──────────────

export interface RankedEntityRiskRead {
  entity_id: number;
  entity_type: string;
  value: string;
  score: number;
  reason_codes: string[];
  reason_descriptions: string[];
  recommendation: string;
}

// ── Brief — mirror app/services/brief/json_exporter.py ─────────────────────

export interface CaseSummary {
  case_id: number;
  name: string;
  status: string;
  created_at: string;
  total_evidence_files: number;
  total_entities: number;
  total_links: number;
  total_clusters: number;
}

export interface RankedEntityExport {
  entity_id: number;
  entity_type: string;
  identifier: string;
  score: number;
  reason_codes: string[];
  reason_descriptions: string[];
  recommendation: string;
}

export interface ClusterSummaryExport {
  cluster_id: number;
  node_count: number;
  entity_types: string[];
  high_risk_entity_count: number;
}

export interface CustodyIntegrityStatement {
  is_valid: boolean;
  total_entries: number;
  head_hash: string | null;
  statutory_statement: string;
  broken_reason: string | null;
  details: Record<string, unknown>;
}

export interface BriefExport {
  classification: string;
  generated_at: string;
  case_summary: CaseSummary;
  custody_chain: CustodyIntegrityStatement;
  top_entities: RankedEntityExport[];
  clusters: ClusterSummaryExport[];
}

// ── Integrity — mirror app/services/integrity/custody_chain.py ─────────────

export interface ChainVerificationResult {
  is_valid: boolean;
  total_entries: number;
  broken_entry_id: number | null;
  broken_index: number | null;
  reason: string | null;
  details: Record<string, unknown>;
}

// ── Error handling ───────────────────────────────────────────────────────────
//
// Backend error shapes (see main.py exception handlers):
//   - IngestionError / ValueError  -> 400 { error, detail: string, request_id }
//   - HTTPException (404, etc.)    -> N   { detail: string }
//   - FastAPI validation error     -> 422 { detail: [{ loc, msg, type }, ...] }
// ApiError normalizes all three into a single readable `detail`/`message`.

interface RawErrorBody {
  error?: string;
  detail?: unknown;
  request_id?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function formatErrorDetail(detail: unknown): string | undefined {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item: unknown) => {
        if (isRecord(item) && typeof item.msg === 'string') {
          return item.msg;
        }
        return null;
      })
      .filter((msg): msg is string => msg !== null);
    return messages.length > 0 ? messages.join('; ') : undefined;
  }
  return undefined;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail?: string;
  readonly errorCode?: string;
  readonly requestId?: string;

  constructor(status: number, body: unknown, requestIdHeader: string | null) {
    const raw: RawErrorBody = isRecord(body) ? (body as RawErrorBody) : {};
    const detail = formatErrorDetail(raw.detail);
    super(detail ?? `Request failed with status ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.errorCode = typeof raw.error === 'string' ? raw.error : undefined;
    this.requestId =
      typeof raw.request_id === 'string'
        ? raw.request_id
        : (requestIdHeader ?? undefined);
  }
}

// ── Core request helper ──────────────────────────────────────────────────────

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      {
        detail: 'Unable to reach the correlator service. Confirm the backend is running.',
      },
      null,
    );
  }

  const requestIdHeader = response.headers.get('X-Request-ID');

  if (!response.ok) {
    let body: unknown = null;
    try {
      body = await response.json();
    } catch {
      // Non-JSON error body (rare) — ApiError falls back to a generic message.
    }
    throw new ApiError(response.status, body, requestIdHeader);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

const JSON_HEADERS = { 'Content-Type': 'application/json' };

// ── Public API surface — mirror app/api/v1/cases.py ─────────────────────────

async function uploadEvidence(
  caseId: number,
  file: File,
  sourceType: SourceType,
): Promise<IngestionSummary> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_type', sourceType);
  // Deliberately no Content-Type header — the browser sets the multipart
  // boundary automatically when the body is a FormData instance.
  return request<IngestionSummary>(`/cases/${caseId}/evidence`, {
    method: 'POST',
    body: formData,
  });
}

function getBriefPdfUrl(caseId: number, maskPii = true): string {
  return `${API_BASE_URL}/cases/${caseId}/brief.pdf?mask_pii=${String(maskPii)}`;
}

export const apiClient = {
  cases: {
    list: (): Promise<CaseRead[]> => request<CaseRead[]>('/cases'),

    create: (payload: CaseCreate): Promise<CaseRead> =>
      request<CaseRead>('/cases', {
        method: 'POST',
        headers: JSON_HEADERS,
        body: JSON.stringify(payload),
      }),

    get: (caseId: number): Promise<CaseRead> => request<CaseRead>(`/cases/${caseId}`),

    uploadEvidence,

    getGraph: (caseId: number): Promise<SerializedGraph> =>
      request<SerializedGraph>(`/cases/${caseId}/graph`),

    getRiskScores: (caseId: number): Promise<RankedEntityRiskRead[]> =>
      request<RankedEntityRiskRead[]>(`/cases/${caseId}/risk`),

    getBriefJson: (caseId: number, maskPii = true): Promise<BriefExport> =>
      request<BriefExport>(`/cases/${caseId}/brief.json?mask_pii=${String(maskPii)}`),

    getBriefPdfUrl,

    getIntegrity: (caseId: number): Promise<ChainVerificationResult> =>
      request<ChainVerificationResult>(`/cases/${caseId}/integrity`),
  },
};
