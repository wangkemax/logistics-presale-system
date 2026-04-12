/**
 * API Client — typed wrapper around fetch for backend communication.
 */

// In production: NEXT_PUBLIC_API_URL is empty → relative paths → proxied via Next.js rewrites
// In development: NEXT_PUBLIC_API_URL = "http://localhost:8000" → direct backend calls
export const API_BASE = typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL !== undefined
  ? process.env.NEXT_PUBLIC_API_URL
  : "http://localhost:8000";

// WebSocket base URL — derives from API_BASE
export const WS_BASE = API_BASE ? API_BASE.replace(/^http/, "ws") : `ws://${typeof window !== "undefined" ? window.location.host : "localhost:8000"}`;

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(body.detail || "Request failed", res.status);
  }

  // Handle 204 No Content or empty responses
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  if (!text) return undefined as T;
  return JSON.parse(text);
}

// ── Auth ──

export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  register: (email: string, name: string, password: string, role = "consultant") =>
    request<any>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, name, password, role }),
    }),
};

// ── Projects ──

export interface Project {
  id: string;
  name: string;
  description: string | null;
  client_name: string | null;
  industry: string | null;
  status: string;
  tender_file_url: string | null;
  created_at: string;
  updated_at: string;
  assumptions?: Record<string, any>;
  stages?: Stage[];
  quotations?: Quotation[];
}

export interface Stage {
  id: string;
  stage_number: number;
  stage_name: string;
  agent_name: string;
  status: string;
  output_data: Record<string, any> | null;
  qa_result: string | null;
  confidence: number | null;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  execution_time_seconds: number | null;
}

export interface Quotation {
  id: string;
  version: number;
  scheme_name: string;
  cost_breakdown: Record<string, any> | null;
  total_cost: number | null;
  total_price: number | null;
  roi: number | null;
  irr: number | null;
  npv: number | null;
  payback_months: number | null;
  status: string;
}

export interface QAIssue {
  id: string;
  stage_number: number;
  severity: string;
  category: string | null;
  description: string;
  suggestion: string | null;
  resolution: string | null;
  status: string;
}

export const projects = {
  list: () => request<Project[]>("/api/v1/projects"),

  get: (id: string) => request<Project>(`/api/v1/projects/${id}`),

  create: (data: { name: string; description?: string; client_name?: string; industry?: string }) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  uploadTender: async (projectId: string, files: File | File[]) => {
    const token = localStorage.getItem("token");
    const formData = new FormData();
    const fileArray = Array.isArray(files) ? files : [files];
    for (const file of fileArray) {
      formData.append("files", file);
    }

    const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/upload-tender`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });

    if (!res.ok) throw new ApiError("Upload failed", res.status);
    return res.json();
  },

  runPipeline: (projectId: string, language: string = "zh", provider: string = "", model: string = "") => {
    const params = new URLSearchParams({ language });
    if (provider) params.set("provider", provider);
    if (model) params.set("model", model);
    return request<{ message: string }>(`/api/v1/projects/${projectId}/run-pipeline?${params}`, {
      method: "POST",
    });
  },

  resumePipeline: (projectId: string) =>
    request<{ message: string; resume_from: number }>(`/api/v1/projects/${projectId}/resume-pipeline`, {
      method: "POST",
    }),

  delete: (projectId: string) =>
    request<{ message: string }>(`/api/v1/projects/${projectId}`, {
      method: "DELETE",
    }),

  clone: (projectId: string) =>
    request<Project>(`/api/v1/projects/${projectId}/clone`, {
      method: "POST",
    }),

  runStage: (projectId: string, stageNumber: number) =>
    request<{ stage_number: number; status: string }>(
      `/api/v1/projects/${projectId}/run-stage`,
      {
        method: "POST",
        body: JSON.stringify({ stage_number: stageNumber, override_input: {} }),
      }
    ),

  analyzeQuality: (projectId: string) =>
    request<{
      project_id: string;
      overall_score: number;
      verdict: "PASS" | "CONDITIONAL_PASS" | "FAIL";
      summary: { p0_count: number; p1_count: number; p2_count: number; total_issues: number };
      stage_scores: Array<{
        stage: number;
        name: string;
        score: number;
        metrics: Record<string, any>;
        issues: Array<{ severity: string; msg: string }>;
      }>;
      consistency_issues: Array<{ severity: string; type: string; msg: string }>;
    }>(`/api/v1/projects/${projectId}/quality/analyze`),

  getStages: (projectId: string) =>
    request<Stage[]>(`/api/v1/projects/${projectId}/stages`),

  getQuotations: (projectId: string) =>
    request<Quotation[]>(`/api/v1/projects/${projectId}/quotations`),

  getQAIssues: (projectId: string) =>
    request<QAIssue[]>(`/api/v1/projects/${projectId}/qa-issues`),

  resolveQAIssue: (projectId: string, issueId: string, resolution: string) =>
    request<QAIssue>(`/api/v1/projects/${projectId}/qa-issues/${issueId}`, {
      method: "PATCH",
      body: JSON.stringify({ resolution, status: "resolved" }),
    }),
};

// ── Quotations ──

export const quotations = {
  generateFromPipeline: (projectId: string) =>
    request<Quotation>(`/api/v1/projects/${projectId}/quotations/generate-from-pipeline`, {
      method: "POST",
    }),

  exportExcel: async (projectId: string, quotationId: string) => {
    const token = localStorage.getItem("token");
    if (!token) throw new ApiError("请先登录", 401);
    const res = await fetch(
      `${API_BASE}/api/v1/projects/${projectId}/quotations/${quotationId}/export-excel`,
      {
        headers: { Authorization: `Bearer ${token}` },
        credentials: "include",
      }
    );
    if (!res.ok) {
      const errText = await res.text().catch(() => "");
      throw new ApiError(`Export failed: ${res.status} ${errText}`, res.status);
    }
    const blob = await res.blob();
    const correctBlob = new Blob([blob], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    });
    const url = URL.createObjectURL(correctBlob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `quotation_${quotationId}.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  },

  update: (projectId: string, quotationId: string, data: Partial<Quotation>) =>
    request<Quotation>(`/api/v1/projects/${projectId}/quotations/${quotationId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
};

// ── Knowledge Base ──

export interface KnowledgeEntry {
  id: string;
  category: string;
  title: string;
  content: string;
  tags: string[] | null;
  is_active: boolean;
  file_name?: string | null;
  has_file?: boolean;
}

export interface SearchResult {
  id: string;
  title: string;
  content: string;
  score: number;
  category: string;
  tags: string;
}

export const knowledge = {
  list: (category?: string) =>
    request<KnowledgeEntry[]>(`/api/v1/knowledge${category ? `?category=${category}` : ""}`),

  search: (query: string, category?: string, topK = 5) =>
    request<SearchResult[]>("/api/v1/knowledge/search", {
      method: "POST",
      body: JSON.stringify({ query, category, top_k: topK }),
    }),

  create: (data: { category: string; title: string; content: string; tags?: string[] }) =>
    request<KnowledgeEntry>("/api/v1/knowledge", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  batchImport: (entries: Array<{ category: string; title: string; content: string; tags?: string[] }>) =>
    request<{ imported: number }>("/api/v1/knowledge/batch-import", {
      method: "POST",
      body: JSON.stringify({ entries }),
    }),

  delete: (id: string) =>
    request<void>(`/api/v1/knowledge/${id}`, { method: "DELETE" }),

  downloadUrl: (id: string) =>
    `${API_BASE}/api/v1/knowledge/${id}/download`,
};

// ── LLM Providers ──

export interface LLMModel {
  id: string;
  name: string;
}

export interface LLMProvider {
  id: string;
  label: string;
  models: LLMModel[];
  default_model: string;
  available: boolean;
}

export const llmProviders = {
  list: () => request<LLMProvider[]>("/api/v1/llm/providers"),
};
