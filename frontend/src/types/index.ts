export interface AdminUser {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: "super_admin" | "admin" | "viewer";
  is_active: boolean;
  last_login_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  expires_at: string;
  user: AdminUser;
}

export interface PublicExamination {
  id: number;
  title: string;
  exam_code: string;
  subject_name?: string | null;
  subject_code?: string | null;
  exam_date: string;
  shift: string;
  start_time?: string | null;
  end_time?: string | null;
  academic_session?: string | null;
  semester?: string | null;
  department?: string | null;
  status: string;
}

export interface Examination extends PublicExamination {
  instructions?: string | null;
  created_by?: number | null;
  total_seated_students: number;
  active_dataset_id?: number | null;
  active_dataset_filename?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExaminationCreatePayload {
  title: string;
  exam_code: string;
  subject_name?: string;
  subject_code?: string;
  exam_date: string;
  shift: string;
  start_time?: string;
  end_time?: string;
  academic_session?: string;
  semester?: string;
  department?: string;
  status: "draft" | "published" | "completed" | "archived";
  instructions?: string;
}

export interface StudentSeatingAllocation {
  seating_id: number;
  examination_id: number;
  examination_title: string;
  exam_code: string;
  exam_date: string;
  shift: string;
  start_time?: string | null;
  end_time?: string | null;
  academic_session?: string | null;
  roll_number: string;
  student_name: string;
  registration_number?: string | null;
  department?: string | null;
  branch?: string | null;
  semester?: string | null;
  subject_code?: string | null;
  subject_name?: string | null;
  building_name?: string | null;
  floor_number?: string | null;
  room_number: string;
  bench_number?: string | null;
  seat_number: string;
  row_number?: string | null;
  column_number?: string | null;
  instructions?: string | null;
}

export interface StudentSearchResponse {
  query_roll_number: string;
  student_name?: string | null;
  department?: string | null;
  total_allocations: number;
  allocations: StudentSeatingAllocation[];
}

export interface DatasetItem {
  id: number;
  examination_id: number;
  examination_title?: string | null;
  examination_code?: string | null;
  original_filename: string;
  storage_bucket: string;
  storage_path: string;
  processing_storage_path?: string | null;
  file_size_bytes: number;
  mime_type: string;
  file_checksum: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  is_active: boolean;
  version: number;
  uploaded_by?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SignedUrlResponse {
  dataset_id: number;
  original_filename: string;
  storage_bucket: string;
  storage_path: string;
  signed_url: string;
  expires_in_seconds: number;
}

export interface ImportRecordPreview {
  row_number: number;
  roll_number: string;
  student_name: string;
  registration_number?: string | null;
  department?: string | null;
  branch?: string | null;
  semester?: string | null;
  subject_code?: string | null;
  subject_name?: string | null;
  building_name?: string | null;
  floor_number?: string | null;
  room_number: string;
  bench_number?: string | null;
  seat_number: string;
  grid_row?: string | null;
  grid_column?: string | null;
  shift?: string | null;
}

export interface DuplicateRecordInfo {
  row_number: number;
  roll_number: string;
  student_name?: string | null;
  first_seen_row?: number | null;
  source: "within_excel" | "existing_database" | "seat_collision";
  reason: string;
}

export interface InvalidRecordInfo {
  row_number: number;
  raw_roll_number?: string | null;
  raw_student_name?: string | null;
  errors: string[];
}

export interface ImportPreviewResponse {
  job_token: string;
  job_id: number;
  dataset_id: number;
  examination_id: number;
  examination_title: string;
  examination_code: string;
  original_filename: string;
  storage_path: string;
  replace_existing: boolean;
  existing_records_count: number;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  detected_columns: Record<string, string>;
  preview_records: ImportRecordPreview[];
  duplicates: DuplicateRecordInfo[];
  invalid_records: InvalidRecordInfo[];
  can_confirm: boolean;
  status: string;
  warnings: string[];
}

export interface ImportConfirmResponse {
  job_token: string;
  job_id: number;
  dataset_id: number;
  examination_id: number;
  status: string;
  inserted_rows: number;
  replaced_previous_rows: number;
  completed_at: string;
  message: string;
}

export interface ImportJobItem {
  id: number;
  job_token: string;
  examination_id: number;
  examination_title?: string | null;
  examination_code?: string | null;
  dataset_id?: number | null;
  original_filename?: string | null;
  initiated_by?: number | null;
  status: string;
  replace_existing: boolean;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  inserted_rows: number;
  error_message?: string | null;
  started_at: string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SeatingRecordAdmin {
  id: number;
  examination_id: number;
  dataset_id: number;
  roll_number: string;
  student_name: string;
  registration_number?: string | null;
  department?: string | null;
  branch?: string | null;
  semester?: string | null;
  subject_code?: string | null;
  subject_name?: string | null;
  building_name?: string | null;
  floor_number?: string | null;
  room_number: string;
  bench_number?: string | null;
  seat_number: string;
  row_number?: string | null;
  column_number?: string | null;
  shift?: string | null;
  created_at: string;
}

export interface DashboardStats {
  total_examinations: number;
  published_examinations: number;
  active_datasets: number;
  total_datasets: number;
  total_seating_records: number;
  total_unique_students: number;
  recent_imports: ImportJobItem[];
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  database: {
    connected: boolean;
    dialect: string;
    latency_ms: number;
    pool_status?: string;
    error?: string;
  };
  storage: {
    provider: string;
    bucket: string;
    private: boolean;
    configured: boolean;
  };
}
