import React, { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  Archive,
  CalendarPlus,
  CheckCircle2,
  Database,
  Download,
  Eye,
  FileSpreadsheet,
  HardDrive,
  History,
  Loader2,
  Plus,
  RefreshCw,
  Trash2,
  UploadCloud,
  Users,
  XCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { apiClient, ApiClientError, API_BASE_URL } from "../api/client";
import {
  DashboardStats,
  DatasetItem,
  Examination,
  ExaminationCreatePayload,
  HealthStatus,
  ImportJobItem,
  ImportPreviewResponse,
  SeatingRecordAdmin,
} from "../types";
import { StatusBanner } from "../components/StatusBanner";

type DashboardTab =
  | "overview"
  | "examinations"
  | "excel-import"
  | "datasets"
  | "history";

export const AdminDashboard: React.FC = () => {
  const { admin, loading: authLoading } = useAuth();
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");

  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [examinations, setExaminations] = useState<Examination[]>([]);
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);
  const [importJobs, setImportJobs] = useState<ImportJobItem[]>([]);

  const [loadingData, setLoadingData] = useState<boolean>(true);
  const [banner, setBanner] = useState<{
    type: "error" | "connection-error" | "success" | "info";
    title?: string;
    message: string;
  } | null>(null);

  // Examination creation state
  const [creatingExam, setCreatingExam] = useState(false);
  const [examForm, setExamForm] = useState<ExaminationCreatePayload>({
    title: "",
    exam_code: "",
    subject_name: "",
    subject_code: "",
    exam_date: new Date().toISOString().slice(0, 10),
    shift: "Morning (09:30 AM - 12:30 PM)",
    start_time: "09:30 AM",
    end_time: "12:30 PM",
    academic_session: "2026-2027",
    semester: "Semester V",
    department: "Computer Science & Engineering",
    status: "published",
    instructions:
      "Candidates must report 30 minutes prior to commencement with their University Identity Card.",
  });

  // Examination seating inspector modal state
  const [inspectingExam, setInspectingExam] = useState<Examination | null>(null);
  const [examSeatingRecords, setExamSeatingRecords] = useState<SeatingRecordAdmin[]>([]);
  const [seatingFilterQuery, setSeatingFilterQuery] = useState("");
  const [loadingSeating, setLoadingSeating] = useState(false);

  // Excel Import Pipeline state
  const [importExamId, setImportExamId] = useState<string>("");
  const [replaceExisting, setReplaceExisting] = useState<boolean>(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadingExcel, setUploadingExcel] = useState<boolean>(false);
  const [confirmingImport, setConfirmingImport] = useState<boolean>(false);
  const [importPreview, setImportPreview] = useState<ImportPreviewResponse | null>(null);

  const refreshAll = useCallback(async () => {
    setLoadingData(true);
    try {
      const [statsRes, healthRes, examsRes, dsRes, jobsRes] = await Promise.all([
        apiClient.getDashboardStats(),
        apiClient.getHealth(),
        apiClient.listExaminations(),
        apiClient.listDatasets(),
        apiClient.listImportJobs(),
      ]);
      setStats(statsRes);
      setHealth(healthRes);
      setExaminations(examsRes);
      setDatasets(dsRes);
      setImportJobs(jobsRes);
      if (!importExamId && examsRes.length > 0) {
        setImportExamId(String(examsRes[0].id));
      }
    } catch (err: unknown) {
      if (err instanceof ApiClientError) {
        setBanner({
          type: err.isConnectionError ? "connection-error" : "error",
          title: "Failed to Load Dashboard Data",
          message: err.message,
        });
      }
    } finally {
      setLoadingData(false);
    }
  }, [importExamId]);

  useEffect(() => {
    if (admin) {
      refreshAll();
    }
  }, [admin, refreshAll]);

  if (authLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center gap-2 text-slate-600">
        <Loader2 className="w-5 h-5 animate-spin" />
        Verifying administrator session...
      </div>
    );
  }

  if (!admin) {
    return <Navigate to="/admin/login" replace />;
  }

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreatingExam(true);
    setBanner(null);
    try {
      const created = await apiClient.createExamination(examForm);
      setBanner({
        type: "success",
        title: "Examination Created",
        message: `Created '${created.title}' (${created.exam_code}) for shift '${created.shift}'.`,
      });
      setExamForm((prev) => ({
        ...prev,
        title: "",
        exam_code: "",
        subject_name: "",
        subject_code: "",
      }));
      setImportExamId(String(created.id));
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        title: "Examination Creation Failed",
        message: err instanceof Error ? err.message : "Failed to create examination.",
      });
    } finally {
      setCreatingExam(false);
    }
  };

  const handleToggleExamStatus = async (exam: Examination) => {
    const nextStatus = exam.status === "published" ? "draft" : "published";
    try {
      await apiClient.updateExamination(exam.id, { status: nextStatus });
      setBanner({
        type: "success",
        message: `Updated '${exam.exam_code}' status to '${nextStatus}'.`,
      });
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to update examination.",
      });
    }
  };

  const handleDeleteExam = async (exam: Examination) => {
    if (
      !window.confirm(
        `Delete examination '${exam.title}' (${exam.exam_code}), all seating records, and associated Supabase Storage objects?`
      )
    ) {
      return;
    }
    try {
      await apiClient.deleteExamination(exam.id);
      setBanner({
        type: "info",
        message: `Deleted examination '${exam.exam_code}' and cleaned up associated datasets.`,
      });
      if (inspectingExam?.id === exam.id) {
        setInspectingExam(null);
      }
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to delete examination.",
      });
    }
  };

  const handleInspectSeating = async (exam: Examination, query = "") => {
    setInspectingExam(exam);
    setLoadingSeating(true);
    try {
      const rows = await apiClient.listExaminationSeating(exam.id, query);
      setExamSeatingRecords(rows);
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to load seating records.",
      });
    } finally {
      setLoadingSeating(false);
    }
  };

  const handleUploadAndValidateExcel = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!importExamId) {
      setBanner({ type: "error", message: "Please select a target examination first." });
      return;
    }
    if (!selectedFile) {
      setBanner({ type: "error", message: "Please choose an Excel (.xlsx/.xls) or .csv file." });
      return;
    }

    setUploadingExcel(true);
    setBanner(null);
    setImportPreview(null);

    try {
      const preview = await apiClient.uploadAndValidateExcel(
        Number(importExamId),
        selectedFile,
        replaceExisting
      );
      setImportPreview(preview);
      setBanner({
        type: preview.can_confirm ? "info" : "error",
        title: "Excel Validation & Storage Upload Complete",
        message: preview.can_confirm
          ? `Validated ${preview.total_rows} row(s): ${preview.valid_rows} valid, ${preview.duplicate_rows} duplicate(s), ${preview.invalid_rows} invalid. Review the summary below and click 'Confirm & Commit Import'.`
          : "No valid rows found to import. Please review the invalid/duplicate rows below.",
      });
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        title: "Excel Upload / Validation Failed",
        message: err instanceof Error ? err.message : "Failed to validate Excel file.",
      });
    } finally {
      setUploadingExcel(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!importPreview) return;
    setConfirmingImport(true);
    setBanner(null);
    try {
      const res = await apiClient.confirmExcelImport(importPreview.job_token);
      setBanner({
        type: "success",
        title: "PostgreSQL Transaction Committed",
        message: res.message,
      });
      setImportPreview(null);
      setSelectedFile(null);
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        title: "Import Transaction Rolled Back",
        message: err instanceof Error ? err.message : "Failed to commit import job.",
      });
    } finally {
      setConfirmingImport(false);
    }
  };

  const handleCancelImport = async () => {
    if (!importPreview) return;
    try {
      const res = await apiClient.cancelExcelImport(importPreview.job_token);
      setBanner({
        type: "info",
        title: "Staged Import Cancelled",
        message: res.message,
      });
      setImportPreview(null);
      setSelectedFile(null);
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to cancel import job.",
      });
    }
  };

  const handleDownloadSignedDataset = async (ds: DatasetItem) => {
    try {
      const signed = await apiClient.getDatasetSignedUrl(ds.id);
      const url = signed.signed_url.startsWith("http")
        ? signed.signed_url
        : signed.signed_url.startsWith("/api")
        ? `${API_BASE_URL.replace(/\/api\/v1$/, "")}${signed.signed_url}`
        : signed.signed_url;
      window.open(url, "_blank", "noopener,noreferrer");
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to generate signed URL.",
      });
    }
  };

  const handleDeleteDataset = async (ds: DatasetItem) => {
    if (
      !window.confirm(
        `Delete dataset '${ds.original_filename}' (v${ds.version}), its seating records, and its object in 'seating-datasets'?`
      )
    ) {
      return;
    }
    try {
      await apiClient.deleteDataset(ds.id);
      setBanner({
        type: "info",
        message: `Deleted dataset '${ds.original_filename}' from PostgreSQL and 'seating-datasets' bucket.`,
      });
      await refreshAll();
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to delete dataset.",
      });
    }
  };

  const handleDownloadBackupManifest = async () => {
    try {
      const manifest = await apiClient.getBackupManifest();
      const blob = new Blob([JSON.stringify(manifest, null, 2)], {
        type: "application/json",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `exam_portal_backup_manifest_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setBanner({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to export backup manifest.",
      });
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
        <div>
          <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
            Examination Controller Workspace
          </span>
          <h1 className="text-2xl font-extrabold text-slate-900 mt-0.5">
            Production Database & Seating Management
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Signed in as <strong>{admin.full_name}</strong> ({admin.email}) • Role:{" "}
            <span className="uppercase font-semibold text-indigo-700">{admin.role}</span>
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={() => apiClient.downloadExcelTemplate()}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs sm:text-sm font-semibold transition"
          >
            <Download className="w-4 h-4 text-indigo-600" />
            Excel Template (.xlsx)
          </button>

          <button
            type="button"
            onClick={refreshAll}
            disabled={loadingData}
            className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs sm:text-sm font-semibold transition"
          >
            <RefreshCw className={`w-4 h-4 ${loadingData ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Global Notification Banner */}
      {banner && (
        <StatusBanner
          type={banner.type}
          title={banner.title}
          message={banner.message}
          onDismiss={() => setBanner(null)}
        />
      )}

      {/* Navigation Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {[
          { id: "overview", label: "Overview & Health", icon: Activity },
          { id: "examinations", label: "Examinations & Shifts", icon: CalendarPlus },
          { id: "excel-import", label: "Excel Import Pipeline", icon: UploadCloud },
          { id: "datasets", label: "Storage Datasets (seating-datasets)", icon: HardDrive },
          { id: "history", label: "Import History & Backup", icon: History },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id as DashboardTab)}
              className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs sm:text-sm font-semibold whitespace-nowrap transition ${
                active
                  ? "bg-indigo-600 text-white shadow-sm"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              <Icon className="w-4 h-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: OVERVIEW & SYSTEM HEALTH */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Examinations (Published)
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-slate-900">
                  {stats?.total_examinations ?? 0}
                </span>
                <span className="text-xs font-semibold text-emerald-600">
                  ({stats?.published_examinations ?? 0} live)
                </span>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Total Seated Allocations
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-indigo-600">
                  {stats?.total_seating_records ?? 0}
                </span>
                <span className="text-xs text-slate-500">records</span>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Unique Students
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-slate-900">
                  {stats?.total_unique_students ?? 0}
                </span>
                <span className="text-xs text-slate-500">candidates</span>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Datasets in Storage
              </span>
              <div className="mt-2 flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-slate-900">
                  {stats?.total_datasets ?? 0}
                </span>
                <span className="text-xs font-semibold text-indigo-600">
                  ({stats?.active_datasets ?? 0} active)
                </span>
              </div>
            </div>
          </div>

          {/* Database & Supabase Storage Health Panel */}
          {health && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <Database className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-bold text-slate-900">
                      PostgreSQL Database Connectivity
                    </h3>
                  </div>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      health.database.connected
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-rose-100 text-rose-800"
                    }`}
                  >
                    {health.database.connected ? "CONNECTED" : "DISCONNECTED"}
                  </span>
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:text-sm">
                  <div>
                    <dt className="text-slate-500">Engine Dialect</dt>
                    <dd className="font-semibold text-slate-900 uppercase">
                      {health.database.dialect}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Query Latency</dt>
                    <dd className="font-semibold text-slate-900">
                      {health.database.latency_ms} ms
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-slate-500">Connection Pool Status</dt>
                    <dd className="font-mono text-xs text-slate-700 mt-0.5">
                      {health.database.pool_status || "Active Pool"}
                    </dd>
                  </div>
                </dl>
              </div>

              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <HardDrive className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-bold text-slate-900">
                      Supabase Private Storage Bucket
                    </h3>
                  </div>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-indigo-100 text-indigo-800">
                    PRIVATE BUCKET
                  </span>
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs sm:text-sm">
                  <div>
                    <dt className="text-slate-500">Bucket Name</dt>
                    <dd className="font-mono font-semibold text-slate-900">
                      {health.storage.bucket}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">Access Policy</dt>
                    <dd className="font-semibold text-slate-900">
                      Signed URLs Only (Service-Role Protected)
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-slate-500">Storage Provider</dt>
                    <dd className="font-mono text-xs text-slate-700 mt-0.5">
                      {health.storage.provider} (env: {health.environment})
                    </dd>
                  </div>
                </dl>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 2: EXAMINATIONS & SHIFTS */}
      {activeTab === "examinations" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Create Examination Form */}
          <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm h-fit">
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2 mb-4">
              <Plus className="w-4 h-4 text-indigo-600" />
              Create New Examination Session / Shift
            </h2>

            <form onSubmit={handleCreateExam} className="space-y-3.5 text-sm">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Examination Title *
                </label>
                <input
                  type="text"
                  value={examForm.title}
                  onChange={(e) => setExamForm({ ...examForm, title: e.target.value })}
                  placeholder="e.g. End Semester Examination - Fall 2026"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Unique Exam Code *
                  </label>
                  <input
                    type="text"
                    value={examForm.exam_code}
                    onChange={(e) =>
                      setExamForm({ ...examForm, exam_code: e.target.value.toUpperCase() })
                    }
                    placeholder="e.g. ESE-2026-CS501-S1"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 font-mono uppercase focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Exam Date *
                  </label>
                  <input
                    type="date"
                    value={examForm.exam_date}
                    onChange={(e) =>
                      setExamForm({ ...examForm, exam_date: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Subject Name
                  </label>
                  <input
                    type="text"
                    value={examForm.subject_name || ""}
                    onChange={(e) =>
                      setExamForm({ ...examForm, subject_name: e.target.value })
                    }
                    placeholder="Database Systems"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Subject Code
                  </label>
                  <input
                    type="text"
                    value={examForm.subject_code || ""}
                    onChange={(e) =>
                      setExamForm({
                        ...examForm,
                        subject_code: e.target.value.toUpperCase(),
                      })
                    }
                    placeholder="CS501"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Examination Shift *
                </label>
                <input
                  type="text"
                  value={examForm.shift}
                  onChange={(e) => setExamForm({ ...examForm, shift: e.target.value })}
                  placeholder="Morning (09:30 AM - 12:30 PM) or Afternoon (02:00 PM - 05:00 PM)"
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Department
                  </label>
                  <input
                    type="text"
                    value={examForm.department || ""}
                    onChange={(e) =>
                      setExamForm({ ...examForm, department: e.target.value })
                    }
                    placeholder="Computer Science"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Publication Status
                  </label>
                  <select
                    value={examForm.status}
                    onChange={(e) =>
                      setExamForm({
                        ...examForm,
                        status: e.target.value as ExaminationCreatePayload["status"],
                      })
                    }
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                  >
                    <option value="published">Published (Visible to Students)</option>
                    <option value="draft">Draft (Admin Only)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">
                  Candidate Instructions
                </label>
                <textarea
                  rows={2}
                  value={examForm.instructions || ""}
                  onChange={(e) =>
                    setExamForm({ ...examForm, instructions: e.target.value })
                  }
                  className="w-full px-3 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-600 focus:outline-none"
                />
              </div>

              <button
                type="submit"
                disabled={creatingExam}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold text-sm shadow-sm transition"
              >
                {creatingExam ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Creating Examination...
                  </>
                ) : (
                  <>
                    <Plus className="w-4 h-4" />
                    Create Examination Session
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Examinations List & Seating Inspector */}
          <div className="lg:col-span-7 space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
              <h2 className="text-base font-bold text-slate-900 mb-4">
                Configured Examinations ({examinations.length})
              </h2>

              {examinations.length === 0 ? (
                <p className="text-sm text-slate-500 py-6 text-center">
                  No examinations created yet. Create one using the form on the left.
                </p>
              ) : (
                <div className="space-y-3">
                  {examinations.map((exam) => (
                    <div
                      key={exam.id}
                      className="rounded-xl border border-slate-200 p-4 hover:border-slate-300 transition flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3"
                    >
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-800">
                            {exam.exam_code}
                          </span>
                          <span
                            className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase ${
                              exam.status === "published"
                                ? "bg-emerald-100 text-emerald-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {exam.status}
                          </span>
                          <span className="text-xs font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded">
                            {exam.shift}
                          </span>
                        </div>
                        <h3 className="font-bold text-slate-900 mt-1.5">{exam.title}</h3>
                        <p className="text-xs text-slate-500 mt-0.5">
                          Date: <strong>{exam.exam_date}</strong> • Seated Students:{" "}
                          <strong className="text-indigo-700">
                            {exam.total_seated_students}
                          </strong>
                          {exam.active_dataset_filename
                            ? ` • Active File: ${exam.active_dataset_filename}`
                            : ""}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 flex-wrap">
                        <button
                          type="button"
                          onClick={() => {
                            setImportExamId(String(exam.id));
                            setActiveTab("excel-import");
                          }}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold"
                        >
                          <UploadCloud className="w-3.5 h-3.5" />
                          Import Excel
                        </button>

                        <button
                          type="button"
                          onClick={() => handleInspectSeating(exam)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Seating ({exam.total_seated_students})
                        </button>

                        <button
                          type="button"
                          onClick={() => handleToggleExamStatus(exam)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold"
                        >
                          <Archive className="w-3.5 h-3.5" />
                          {exam.status === "published" ? "Unpublish" : "Publish"}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleDeleteExam(exam)}
                          className="p-1.5 rounded-lg text-rose-600 hover:bg-rose-50"
                          title="Delete Examination"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Seating Inspector Panel */}
            {inspectingExam && (
              <div className="bg-white rounded-2xl border border-indigo-200 p-5 shadow-sm">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                  <div>
                    <h3 className="font-bold text-slate-900 flex items-center gap-2">
                      <Users className="w-4 h-4 text-indigo-600" />
                      Seating Records — {inspectingExam.title} ({inspectingExam.exam_code})
                    </h3>
                    <p className="text-xs text-slate-500">
                      Protected Admin Inspection View • Showing up to 100 matching rows
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={seatingFilterQuery}
                      onChange={(e) => {
                        setSeatingFilterQuery(e.target.value);
                        handleInspectSeating(inspectingExam, e.target.value);
                      }}
                      placeholder="Filter roll, name, room..."
                      className="px-3 py-1.5 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-600"
                    />
                    <button
                      type="button"
                      onClick={() => setInspectingExam(null)}
                      className="text-xs font-semibold text-slate-500 hover:text-slate-800"
                    >
                      Close
                    </button>
                  </div>
                </div>

                {loadingSeating ? (
                  <div className="py-6 text-center text-xs text-slate-500">
                    Loading seating records...
                  </div>
                ) : examSeatingRecords.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500 bg-slate-50 rounded-xl">
                    No seating records found for this examination.
                  </div>
                ) : (
                  <div className="overflow-x-auto max-h-80">
                    <table className="min-w-full text-xs text-left border-collapse">
                      <thead>
                        <tr className="border-b border-slate-200 text-slate-500 uppercase bg-slate-50">
                          <th className="py-2 px-3">Roll No</th>
                          <th className="py-2 px-3">Student Name</th>
                          <th className="py-2 px-3">Building</th>
                          <th className="py-2 px-3">Room</th>
                          <th className="py-2 px-3">Bench</th>
                          <th className="py-2 px-3">Seat</th>
                          <th className="py-2 px-3">Shift</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {examSeatingRecords.map((rec) => (
                          <tr key={rec.id} className="hover:bg-slate-50">
                            <td className="py-2 px-3 font-mono font-bold text-indigo-700">
                              {rec.roll_number}
                            </td>
                            <td className="py-2 px-3 font-medium text-slate-900">
                              {rec.student_name}
                            </td>
                            <td className="py-2 px-3 text-slate-600">
                              {rec.building_name || "-"}
                            </td>
                            <td className="py-2 px-3 font-semibold text-slate-900">
                              {rec.room_number}
                            </td>
                            <td className="py-2 px-3 text-slate-600">
                              {rec.bench_number || "-"}
                            </td>
                            <td className="py-2 px-3 font-bold text-emerald-700">
                              {rec.seat_number}
                            </td>
                            <td className="py-2 px-3 text-slate-500">{rec.shift}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: EXCEL IMPORT PIPELINE (11-STEP WORKFLOW) */}
      {activeTab === "excel-import" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-5">
              <div>
                <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-indigo-600" />
                  Excel Seating Dataset Upload & Transactional Validation Pipeline
                </h2>
                <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                  Uploads original Excel to private bucket{" "}
                  <code className="px-1.5 py-0.5 rounded bg-slate-100 font-mono text-xs">
                    seating-datasets
                  </code>
                  , parses with Pandas/OpenPyXL, detects duplicate roll numbers & invalid
                  rows, and commits atomically only after your confirmation.
                </p>
              </div>
            </div>

            <form
              onSubmit={handleUploadAndValidateExcel}
              className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end bg-slate-50 p-4 rounded-xl border border-slate-200"
            >
              <div className="md:col-span-4">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  1. Target Examination *
                </label>
                <select
                  value={importExamId}
                  onChange={(e) => setImportExamId(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-xl border border-slate-300 bg-white text-sm font-medium focus:outline-none focus:ring-2 focus:ring-indigo-600"
                  required
                >
                  <option value="">-- Select Examination --</option>
                  {examinations.map((exam) => (
                    <option key={exam.id} value={exam.id}>
                      {exam.exam_code} — {exam.title} ({exam.shift}) [
                      {exam.total_seated_students} seated]
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-4">
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  2. Excel / CSV Dataset File (.xlsx, .xls, .csv) *
                </label>
                <input
                  type="file"
                  accept=".xlsx,.xls,.csv"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-slate-700 file:mr-3 file:py-2 file:px-3.5 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 bg-white border border-slate-300 rounded-xl p-1"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-700 py-2.5">
                  <input
                    type="checkbox"
                    checked={replaceExisting}
                    onChange={(e) => setReplaceExisting(e.target.checked)}
                    className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                  />
                  Safe Replace Dataset
                </label>
              </div>

              <div className="md:col-span-2">
                <button
                  type="submit"
                  disabled={uploadingExcel}
                  className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white font-semibold text-xs sm:text-sm shadow-sm transition"
                >
                  {uploadingExcel ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Validating...
                    </>
                  ) : (
                    <>
                      <UploadCloud className="w-4 h-4" />
                      Upload & Validate
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>

          {/* Step 6-11: Import Validation Summary, Duplicate Detection, Invalid Rows & Confirmation */}
          {importPreview && (
            <div className="bg-white rounded-2xl border-2 border-indigo-600 p-6 shadow-lg space-y-6">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-4">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-indigo-600">
                    Step 9 & 10: Validation Summary & Confirmation Required
                  </span>
                  <h3 className="text-xl font-bold text-slate-900 mt-0.5">
                    {importPreview.original_filename} → {importPreview.examination_title} (
                    {importPreview.examination_code})
                  </h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    Supabase Storage Object: {importPreview.storage_path}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleCancelImport}
                    disabled={confirmingImport}
                    className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl border border-rose-300 hover:bg-rose-50 text-rose-700 font-semibold text-xs sm:text-sm transition"
                  >
                    <XCircle className="w-4 h-4" />
                    Cancel & Discard
                  </button>

                  {importPreview.can_confirm && (
                    <button
                      type="button"
                      onClick={handleConfirmImport}
                      disabled={confirmingImport}
                      className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-60 text-white font-bold text-xs sm:text-sm shadow-md transition"
                    >
                      {confirmingImport ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Committing Transaction...
                        </>
                      ) : (
                        <>
                          <CheckCircle2 className="w-4 h-4" />
                          Confirm & Commit {importPreview.valid_rows} Record(s)
                        </>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Summary Counts */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-200">
                  <span className="text-xs font-semibold text-slate-500 block">
                    Total Rows Scanned
                  </span>
                  <span className="text-2xl font-extrabold text-slate-900">
                    {importPreview.total_rows}
                  </span>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3.5 border border-emerald-200">
                  <span className="text-xs font-semibold text-emerald-700 block">
                    Valid Staged Records
                  </span>
                  <span className="text-2xl font-extrabold text-emerald-900">
                    {importPreview.valid_rows}
                  </span>
                </div>
                <div className="bg-amber-50 rounded-xl p-3.5 border border-amber-200">
                  <span className="text-xs font-semibold text-amber-700 block">
                    Duplicate Roll / Seat Rows
                  </span>
                  <span className="text-2xl font-extrabold text-amber-900">
                    {importPreview.duplicate_rows}
                  </span>
                </div>
                <div className="bg-rose-50 rounded-xl p-3.5 border border-rose-200">
                  <span className="text-xs font-semibold text-rose-700 block">
                    Invalid / Malformed Rows
                  </span>
                  <span className="text-2xl font-extrabold text-rose-900">
                    {importPreview.invalid_rows}
                  </span>
                </div>
              </div>

              {/* Warnings */}
              {importPreview.warnings.length > 0 && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-1">
                  {importPreview.warnings.map((w, idx) => (
                    <p
                      key={idx}
                      className="text-xs sm:text-sm text-amber-900 flex items-center gap-2 font-medium"
                    >
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                      {w}
                    </p>
                  ))}
                </div>
              )}

              {/* Duplicate Roll Numbers Detected */}
              {importPreview.duplicates.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-amber-900 mb-2">
                    Duplicate Roll Numbers & Conflicts Detected ({importPreview.duplicates.length})
                  </h4>
                  <div className="overflow-x-auto max-h-48 border border-amber-200 rounded-xl">
                    <table className="min-w-full text-xs text-left">
                      <thead className="bg-amber-50 text-amber-900 uppercase">
                        <tr>
                          <th className="py-2 px-3">Excel Row #</th>
                          <th className="py-2 px-3">Roll Number</th>
                          <th className="py-2 px-3">Student Name</th>
                          <th className="py-2 px-3">Conflict Type</th>
                          <th className="py-2 px-3">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-amber-100">
                        {importPreview.duplicates.map((dup, i) => (
                          <tr key={i}>
                            <td className="py-2 px-3 font-mono font-bold">
                              Row {dup.row_number}
                            </td>
                            <td className="py-2 px-3 font-mono font-bold text-amber-900">
                              {dup.roll_number}
                            </td>
                            <td className="py-2 px-3">{dup.student_name || "-"}</td>
                            <td className="py-2 px-3 uppercase font-semibold">
                              {dup.source}
                            </td>
                            <td className="py-2 px-3 text-slate-700">{dup.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Invalid Records Detected */}
              {importPreview.invalid_records.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-rose-900 mb-2">
                    Invalid Rows Excluded ({importPreview.invalid_records.length})
                  </h4>
                  <div className="overflow-x-auto max-h-48 border border-rose-200 rounded-xl">
                    <table className="min-w-full text-xs text-left">
                      <thead className="bg-rose-50 text-rose-900 uppercase">
                        <tr>
                          <th className="py-2 px-3">Excel Row #</th>
                          <th className="py-2 px-3">Raw Roll No</th>
                          <th className="py-2 px-3">Raw Student Name</th>
                          <th className="py-2 px-3">Validation Errors</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-rose-100">
                        {importPreview.invalid_records.map((inv, i) => (
                          <tr key={i}>
                            <td className="py-2 px-3 font-mono font-bold">
                              Row {inv.row_number}
                            </td>
                            <td className="py-2 px-3 font-mono">
                              {inv.raw_roll_number || "(empty)"}
                            </td>
                            <td className="py-2 px-3">{inv.raw_student_name || "(empty)"}</td>
                            <td className="py-2 px-3 text-rose-700 font-medium">
                              {inv.errors.join("; ")}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Valid Preview Records Table */}
              {importPreview.preview_records.length > 0 && (
                <div>
                  <h4 className="text-sm font-bold text-slate-900 mb-2">
                    Preview of Validated Records (Showing {importPreview.preview_records.length} of{" "}
                    {importPreview.valid_rows})
                  </h4>
                  <div className="overflow-x-auto max-h-64 border border-slate-200 rounded-xl">
                    <table className="min-w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-600 uppercase">
                        <tr>
                          <th className="py-2 px-3">Row #</th>
                          <th className="py-2 px-3">Roll Number</th>
                          <th className="py-2 px-3">Student Name</th>
                          <th className="py-2 px-3">Department</th>
                          <th className="py-2 px-3">Building</th>
                          <th className="py-2 px-3">Room</th>
                          <th className="py-2 px-3">Bench</th>
                          <th className="py-2 px-3">Seat</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {importPreview.preview_records.map((rec) => (
                          <tr key={rec.row_number} className="hover:bg-slate-50">
                            <td className="py-2 px-3 font-mono text-slate-500">
                              {rec.row_number}
                            </td>
                            <td className="py-2 px-3 font-mono font-bold text-indigo-700">
                              {rec.roll_number}
                            </td>
                            <td className="py-2 px-3 font-medium text-slate-900">
                              {rec.student_name}
                            </td>
                            <td className="py-2 px-3 text-slate-600">
                              {rec.department || "-"}
                            </td>
                            <td className="py-2 px-3 text-slate-600">
                              {rec.building_name || "-"}
                            </td>
                            <td className="py-2 px-3 font-semibold text-slate-900">
                              {rec.room_number}
                            </td>
                            <td className="py-2 px-3 text-slate-600">
                              {rec.bench_number || "-"}
                            </td>
                            <td className="py-2 px-3 font-bold text-emerald-700">
                              {rec.seat_number}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: DATASETS & SUPABASE PRIVATE STORAGE */}
      {activeTab === "datasets" && (
        <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Supabase Storage Bucket:{" "}
                <code className="text-indigo-600 font-mono">seating-datasets</code>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                All dataset files are private. Use Signed URLs to download original Excel
                workbooks or delete datasets and their storage objects.
              </p>
            </div>
          </div>

          {datasets.length === 0 ? (
            <p className="text-sm text-slate-500 py-8 text-center">
              No datasets have been uploaded to storage yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500 uppercase bg-slate-50">
                    <th className="py-2.5 px-3">ID / Ver</th>
                    <th className="py-2.5 px-3">Examination</th>
                    <th className="py-2.5 px-3">Filename</th>
                    <th className="py-2.5 px-3">Storage Path</th>
                    <th className="py-2.5 px-3">Rows (Valid/Dup/Inv)</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {datasets.map((ds) => (
                    <tr key={ds.id} className="hover:bg-slate-50">
                      <td className="py-3 px-3 font-mono font-bold">
                        #{ds.id} (v{ds.version})
                      </td>
                      <td className="py-3 px-3">
                        <span className="font-bold text-slate-900 block">
                          {ds.examination_code || `Exam #${ds.examination_id}`}
                        </span>
                        <span className="text-slate-500">{ds.examination_title}</span>
                      </td>
                      <td className="py-3 px-3 font-medium text-slate-900">
                        {ds.original_filename}
                        <span className="block text-[11px] text-slate-400">
                          {(ds.file_size_bytes / 1024).toFixed(1)} KB • SHA256:{" "}
                          {ds.file_checksum.slice(0, 10)}…
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-[11px] text-slate-600 max-w-xs truncate">
                        {ds.storage_path}
                      </td>
                      <td className="py-3 px-3">
                        <span className="text-emerald-700 font-bold">{ds.valid_rows}</span> /{" "}
                        <span className="text-amber-700">{ds.duplicate_rows}</span> /{" "}
                        <span className="text-rose-700">{ds.invalid_rows}</span>
                      </td>
                      <td className="py-3 px-3">
                        {ds.is_active ? (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold uppercase text-[10px]">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold uppercase text-[10px]">
                            Superseded / Staged
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-right space-x-2 whitespace-nowrap">
                        <button
                          type="button"
                          onClick={() => handleDownloadSignedDataset(ds)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 font-semibold"
                        >
                          <Download className="w-3.5 h-3.5" />
                          Signed URL
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteDataset(ds)}
                          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 font-semibold"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 5: IMPORT HISTORY & BACKUP MANIFEST */}
      {activeTab === "history" && (
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Database Backup Verification & Recovery Manifest
              </h2>
              <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
                Export a signed JSON snapshot of all table counts, examination metadata, and
                Supabase Storage SHA-256 checksums to verify backups before or after maintenance.
              </p>
            </div>
            <button
              type="button"
              onClick={handleDownloadBackupManifest}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs sm:text-sm font-semibold shadow-sm transition shrink-0"
            >
              <Download className="w-4 h-4" />
              Export Backup Manifest (.json)
            </button>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <h3 className="text-base font-bold text-slate-900 mb-4">
              Dataset Import Job Audit Log ({importJobs.length})
            </h3>

            {importJobs.length === 0 ? (
              <p className="text-sm text-slate-500 py-6 text-center">
                No import jobs recorded yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-xs text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 uppercase bg-slate-50">
                      <th className="py-2.5 px-3">Job ID</th>
                      <th className="py-2.5 px-3">Examination</th>
                      <th className="py-2.5 px-3">File</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3">Total / Valid / Inserted</th>
                      <th className="py-2.5 px-3">Duplicates / Invalid</th>
                      <th className="py-2.5 px-3">Started At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {importJobs.map((job) => (
                      <tr key={job.id} className="hover:bg-slate-50">
                        <td className="py-2.5 px-3 font-mono font-bold">
                          #{job.id} ({job.job_token.slice(0, 8)})
                        </td>
                        <td className="py-2.5 px-3 font-medium text-slate-900">
                          {job.examination_code || `Exam #${job.examination_id}`}
                        </td>
                        <td className="py-2.5 px-3 text-slate-600">
                          {job.original_filename || "-"}
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${
                              job.status === "completed"
                                ? "bg-emerald-100 text-emerald-800"
                                : job.status === "awaiting_confirmation"
                                ? "bg-amber-100 text-amber-800"
                                : job.status === "cancelled"
                                ? "bg-slate-100 text-slate-700"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {job.status}
                          </span>
                          {job.error_message && (
                            <span className="block text-[11px] text-rose-600 mt-0.5">
                              {job.error_message}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {job.total_rows} / {job.valid_rows} /{" "}
                          <strong className="text-emerald-700">{job.inserted_rows}</strong>
                        </td>
                        <td className="py-2.5 px-3 font-mono">
                          {job.duplicate_rows} dup / {job.invalid_rows} inv
                        </td>
                        <td className="py-2.5 px-3 text-slate-500">
                          {new Date(job.started_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
