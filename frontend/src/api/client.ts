import {
  AdminUser,
  DashboardStats,
  DatasetItem,
  Examination,
  ExaminationCreatePayload,
  HealthStatus,
  ImportConfirmResponse,
  ImportJobItem,
  ImportPreviewResponse,
  PublicExamination,
  SeatingRecordAdmin,
  SignedUrlResponse,
  StudentSearchResponse,
  TokenResponse,
} from "../types";

const rawBase = (import.meta.env.VITE_API_BASE_URL || "/api/v1").trim().replace(/\/+$/, "");
export const API_BASE_URL = rawBase.endsWith("/api/v1")
  ? rawBase
  : rawBase.startsWith("http")
  ? `${rawBase}/api/v1`
  : rawBase;

const TOKEN_STORAGE_KEY = "exam_portal_admin_jwt";
const USER_STORAGE_KEY = "exam_portal_admin_user";

export class ApiClientError extends Error {
  status: number;
  isConnectionError: boolean;

  constructor(message: string, status = 0, isConnectionError = false) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.isConnectionError = isConnectionError;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredSession(token: string, user: AdminUser): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredSession(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  localStorage.removeItem(USER_STORAGE_KEY);
}

export function getStoredUser(): AdminUser | null {
  const raw = localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AdminUser;
  } catch {
    return null;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  requiresAuth = false
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (requiresAuth) {
    const token = getStoredToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch {
    throw new ApiClientError(
      "Unable to reach the Examination Portal Backend Server. Please check your internet connection or verify that the backend service is online.",
      0,
      true
    );
  }

  if (response.status === 401 && requiresAuth) {
    clearStoredSession();
  }

  if (!response.ok) {
    let detail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson && typeof errJson.detail === "string") {
        detail = errJson.detail;
      }
    } catch {
      // Fallback to status text
      if (response.statusText) {
        detail = `${detail}: ${response.statusText}`;
      }
    }
    throw new ApiClientError(detail, response.status, false);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  // Health Check
  getHealth(): Promise<HealthStatus> {
    return request<HealthStatus>("/health");
  },

  // Public Student Search & Examinations
  getPublicExaminations(shift?: string): Promise<PublicExamination[]> {
    const params = new URLSearchParams();
    if (shift) params.set("shift", shift);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<PublicExamination[]>(`/examinations/public${qs}`);
  },

  searchStudentSeating(
    rollNumber: string,
    examinationId?: number,
    shift?: string
  ): Promise<StudentSearchResponse> {
    const params = new URLSearchParams({ roll_number: rollNumber.trim() });
    if (examinationId) params.set("examination_id", String(examinationId));
    if (shift) params.set("shift", shift);
    return request<StudentSearchResponse>(`/search/student?${params.toString()}`);
  },

  getSeatingSlipPdfUrl(rollNumber: string, examinationId?: number, shift?: string): string {
    const params = new URLSearchParams({ roll_number: rollNumber.trim() });
    if (examinationId) params.set("examination_id", String(examinationId));
    if (shift) params.set("shift", shift);
    return `${API_BASE_URL}/search/seating-slip/pdf?${params.toString()}`;
  },

  // Authentication
  login(username: string, password: string): Promise<TokenResponse> {
    return request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
  },

  getMe(): Promise<AdminUser> {
    return request<AdminUser>("/auth/me", {}, true);
  },

  // Admin Dashboard & Maintenance
  getDashboardStats(): Promise<DashboardStats> {
    return request<DashboardStats>("/maintenance/dashboard", {}, true);
  },

  getBackupManifest(): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>("/maintenance/backup-manifest", {}, true);
  },

  // Admin Examinations Management
  listExaminations(statusFilter?: string, shift?: string): Promise<Examination[]> {
    const params = new URLSearchParams();
    if (statusFilter) params.set("status", statusFilter);
    if (shift) params.set("shift", shift);
    const qs = params.toString() ? `?${params.toString()}` : "";
    return request<Examination[]>(`/examinations${qs}`, {}, true);
  },

  createExamination(payload: ExaminationCreatePayload): Promise<Examination> {
    return request<Examination>(
      "/examinations",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      true
    );
  },

  updateExamination(
    examinationId: number,
    payload: Partial<ExaminationCreatePayload>
  ): Promise<Examination> {
    return request<Examination>(
      `/examinations/${examinationId}`,
      {
        method: "PUT",
        body: JSON.stringify(payload),
      },
      true
    );
  },

  deleteExamination(examinationId: number): Promise<{ deleted: boolean }> {
    return request<{ deleted: boolean }>(
      `/examinations/${examinationId}`,
      { method: "DELETE" },
      true
    );
  },

  listExaminationSeating(
    examinationId: number,
    query?: string,
    limit = 100
  ): Promise<SeatingRecordAdmin[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (query) params.set("query", query);
    return request<SeatingRecordAdmin[]>(
      `/examinations/${examinationId}/seating?${params.toString()}`,
      {},
      true
    );
  },

  // Excel Import Pipeline
  async downloadExcelTemplate(): Promise<void> {
    const token = getStoredToken();
    const res = await fetch(`${API_BASE_URL}/imports/template`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) {
      throw new ApiClientError("Failed to download Excel template.", res.status);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "Examination_Seating_Template.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  },

  uploadAndValidateExcel(
    examinationId: number,
    file: File,
    replaceExisting: boolean
  ): Promise<ImportPreviewResponse> {
    const formData = new FormData();
    formData.append("examination_id", String(examinationId));
    formData.append("replace_existing", String(replaceExisting));
    formData.append("file", file);

    return request<ImportPreviewResponse>(
      "/imports/upload",
      {
        method: "POST",
        body: formData,
      },
      true
    );
  },

  confirmExcelImport(jobToken: string): Promise<ImportConfirmResponse> {
    return request<ImportConfirmResponse>(
      `/imports/${jobToken}/confirm`,
      {
        method: "POST",
        body: JSON.stringify({ skip_invalid_and_duplicates: true }),
      },
      true
    );
  },

  cancelExcelImport(jobToken: string): Promise<{ status: string; message: string }> {
    return request<{ status: string; message: string }>(
      `/imports/${jobToken}/cancel`,
      {
        method: "POST",
      },
      true
    );
  },

  listImportJobs(examinationId?: number): Promise<ImportJobItem[]> {
    const qs = examinationId ? `?examination_id=${examinationId}` : "";
    return request<ImportJobItem[]>(`/imports/jobs${qs}`, {}, true);
  },

  // Datasets & Private Storage ('seating-datasets')
  listDatasets(examinationId?: number): Promise<DatasetItem[]> {
    const qs = examinationId ? `?examination_id=${examinationId}` : "";
    return request<DatasetItem[]>(`/datasets${qs}`, {}, true);
  },

  getDatasetSignedUrl(datasetId: number): Promise<SignedUrlResponse> {
    return request<SignedUrlResponse>(`/datasets/${datasetId}/signed-url`, {}, true);
  },

  deleteDataset(datasetId: number): Promise<{ deleted: boolean }> {
    return request<{ deleted: boolean }>(
      `/datasets/${datasetId}`,
      { method: "DELETE" },
      true
    );
  },
};
