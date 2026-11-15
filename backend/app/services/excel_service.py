"""Excel validation, parsing, duplicate detection, and template generation service."""

import hashlib
import io
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import pandas as pd
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.schemas.schemas import (
    DuplicateRecordInfo,
    ImportRecordPreview,
    InvalidRecordInfo,
)

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
ALLOWED_MIME_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel",
    "text/csv",
    "application/csv",
    "application/octet-stream",
}

COLUMN_ALIASES: Dict[str, List[str]] = {
    "roll_number": [
        "roll_number",
        "rollnumber",
        "roll_no",
        "rollno",
        "roll",
        "student_roll",
        "enrollment_no",
        "enrollment_number",
        "university_roll_no",
    ],
    "student_name": [
        "student_name",
        "studentname",
        "name",
        "candidate_name",
        "full_name",
        "student",
    ],
    "room_number": [
        "room_number",
        "roomnumber",
        "room_no",
        "roomno",
        "room",
        "hall_no",
        "hall_number",
        "hall",
        "exam_hall",
    ],
    "seat_number": [
        "seat_number",
        "seatnumber",
        "seat_no",
        "seatno",
        "seat",
        "chair_no",
        "desk_no",
    ],
    "registration_number": [
        "registration_number",
        "registration_no",
        "reg_no",
        "regno",
        "reg_number",
    ],
    "department": [
        "department",
        "dept",
        "programme",
        "program",
        "school",
    ],
    "branch": [
        "branch",
        "specialization",
        "stream",
        "discipline",
    ],
    "semester": [
        "semester",
        "sem",
        "year_sem",
        "term",
    ],
    "subject_code": [
        "subject_code",
        "subjectcode",
        "course_code",
        "paper_code",
        "sub_code",
    ],
    "subject_name": [
        "subject_name",
        "subjectname",
        "course_name",
        "paper_name",
        "subject",
    ],
    "building_name": [
        "building_name",
        "building",
        "block",
        "block_name",
        "wing",
        "academic_block",
    ],
    "floor_number": [
        "floor_number",
        "floor",
        "floor_no",
        "level",
    ],
    "bench_number": [
        "bench_number",
        "bench",
        "bench_no",
        "table_no",
    ],
    "row_number": [
        "row_number",
        "row",
        "row_no",
        "grid_row",
    ],
    "column_number": [
        "column_number",
        "column",
        "col",
        "col_no",
        "grid_column",
    ],
    "shift": [
        "shift",
        "exam_shift",
        "session_shift",
        "slot",
    ],
}

REQUIRED_CANONICAL_COLUMNS = ["roll_number", "student_name", "room_number", "seat_number"]
ROLL_NUMBER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9/_-]{1,63}$")


def normalize_header(raw_header: Any) -> str:
    """Normalize an Excel column header to snake_case alphanumeric tokens."""
    text = str(raw_header or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def clean_cell(val: Any) -> Optional[str]:
    """Convert cell value to clean string or None if empty/NaN."""
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "null", "n/a", "-"}:
        return None
    # Strip trailing .0 produced if Excel stored an integer as float
    if re.match(r"^\d+\.0$", s):
        s = s[:-2]
    return s


def validate_upload_file_metadata(
    filename: str,
    content_type: Optional[str],
    file_bytes: bytes,
) -> Tuple[str, str]:
    """Validate file extension, size, magic bytes, and compute SHA-256 checksum."""
    settings = get_settings()
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a valid filename.",
        )

    lower_name = filename.lower().strip()
    ext = ""
    for candidate in ALLOWED_EXTENSIONS:
        if lower_name.endswith(candidate):
            ext = candidate
            break

    if not ext:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{filename}'. Allowed formats: .xlsx, .xls, .csv",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if len(file_bytes) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
        )

    # Verify magic bytes for .xlsx (PK\x03\x04 ZIP container) and .xls (OLE2 header)
    if ext == ".xlsx" and not file_bytes.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .xlsx file signature. Please upload a valid Excel (.xlsx) workbook.",
        )
    if ext == ".xls" and not (
        file_bytes.startswith(b"\xd0\xcf\x11\xe0") or file_bytes.startswith(b"PK\x03\x04")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid .xls file signature. Please upload a valid Excel workbook.",
        )

    checksum = hashlib.sha256(file_bytes).hexdigest()
    normalized_mime = content_type or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return ext, checksum


def parse_and_validate_excel(
    file_bytes: bytes,
    filename: str,
    existing_roll_numbers: Set[str],
    replace_existing: bool,
    default_shift: Optional[str] = None,
) -> Dict[str, Any]:
    """Read Excel with Pandas/OpenPyXL, validate schema, detect duplicates & invalid rows."""
    lower_name = filename.lower().strip()
    try:
        buffer = io.BytesIO(file_bytes)
        if lower_name.endswith(".csv"):
            df = pd.read_csv(buffer, dtype=str, keep_default_na=False)
        else:
            df = pd.read_excel(buffer, engine="openpyxl", dtype=str, keep_default_na=False)
    except Exception as exc:
        logger.error("Failed to parse uploaded Excel file '%s': %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to read Excel file '{filename}'. Ensure the workbook is not corrupted or password-protected.",
        ) from exc

    # Drop completely empty rows
    df = df.dropna(how="all")
    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded Excel sheet contains no data rows.",
        )

    # Map headers
    raw_columns = list(df.columns)
    normalized_to_raw: Dict[str, str] = {}
    for col in raw_columns:
        norm = normalize_header(col)
        if norm and norm not in normalized_to_raw:
            normalized_to_raw[norm] = str(col)

    detected_columns: Dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized_to_raw:
                detected_columns[canonical] = normalized_to_raw[alias]
                break

    missing_required = [
        req for req in REQUIRED_CANONICAL_COLUMNS if req not in detected_columns
    ]
    if missing_required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Missing required columns: {', '.join(missing_required)}. "
                f"Detected headers in file: {', '.join(str(c) for c in raw_columns)}"
            ),
        )

    seen_rolls_in_sheet: Dict[str, int] = {}
    seen_room_seats: Dict[Tuple[str, str, str], int] = {}

    valid_staged_records: List[Dict[str, Any]] = []
    preview_records: List[ImportRecordPreview] = []
    duplicates: List[DuplicateRecordInfo] = []
    invalid_records: List[InvalidRecordInfo] = []
    warnings: List[str] = []

    total_rows = 0

    for idx, row in df.iterrows():
        # Excel row number (1-based header + 1-based data row = idx + 2)
        excel_row_num = int(idx) + 2

        def get_field(canonical_name: str) -> Optional[str]:
            raw_col = detected_columns.get(canonical_name)
            if not raw_col:
                return None
            return clean_cell(row.get(raw_col))

        raw_roll = get_field("roll_number")
        raw_name = get_field("student_name")
        raw_room = get_field("room_number")
        raw_seat = get_field("seat_number")

        # Skip completely blank trailing lines
        if not any([raw_roll, raw_name, raw_room, raw_seat]):
            continue

        total_rows += 1
        row_errors: List[str] = []

        if not raw_roll:
            row_errors.append("Missing roll_number")
        else:
            norm_roll = raw_roll.strip().upper()
            if not ROLL_NUMBER_PATTERN.match(norm_roll):
                row_errors.append(
                    f"Invalid roll_number format '{raw_roll}' (use alphanumeric, '-', '_', or '/')"
                )

        if not raw_name:
            row_errors.append("Missing student_name")
        if not raw_room:
            row_errors.append("Missing room_number")
        if not raw_seat:
            row_errors.append("Missing seat_number")

        if row_errors:
            invalid_records.append(
                InvalidRecordInfo(
                    row_number=excel_row_num,
                    raw_roll_number=raw_roll,
                    raw_student_name=raw_name,
                    errors=row_errors,
                )
            )
            continue

        assert raw_roll is not None and raw_name is not None and raw_room is not None and raw_seat is not None
        norm_roll = raw_roll.strip().upper()
        norm_room = raw_room.strip().upper()
        norm_seat = raw_seat.strip().upper()
        norm_building = (get_field("building_name") or "").strip().upper()

        # 1. Check duplicate roll_number within the Excel sheet
        if norm_roll in seen_rolls_in_sheet:
            first_row = seen_rolls_in_sheet[norm_roll]
            duplicates.append(
                DuplicateRecordInfo(
                    row_number=excel_row_num,
                    roll_number=norm_roll,
                    student_name=raw_name,
                    first_seen_row=first_row,
                    source="within_excel",
                    reason=f"Duplicate roll number '{norm_roll}' in Excel (first appeared at row {first_row}).",
                )
            )
            continue

        # 2. Check existing database records if replace_existing is False
        if not replace_existing and norm_roll in existing_roll_numbers:
            duplicates.append(
                DuplicateRecordInfo(
                    row_number=excel_row_num,
                    roll_number=norm_roll,
                    student_name=raw_name,
                    first_seen_row=None,
                    source="existing_database",
                    reason=f"Roll number '{norm_roll}' already exists in this examination (enable Replace Dataset to overwrite).",
                )
            )
            continue

        # 3. Check seat collision inside the same building + room
        seat_key = (norm_building, norm_room, norm_seat)
        if seat_key in seen_room_seats:
            first_seat_row = seen_room_seats[seat_key]
            duplicates.append(
                DuplicateRecordInfo(
                    row_number=excel_row_num,
                    roll_number=norm_roll,
                    student_name=raw_name,
                    first_seen_row=first_seat_row,
                    source="seat_collision",
                    reason=f"Seat '{norm_seat}' in room '{norm_room}' is already assigned at row {first_seat_row}.",
                )
            )
            continue

        seen_rolls_in_sheet[norm_roll] = excel_row_num
        seen_room_seats[seat_key] = excel_row_num

        record_dict: Dict[str, Any] = {
            "row_number": excel_row_num,
            "roll_number": norm_roll,
            "student_name": raw_name.strip(),
            "registration_number": get_field("registration_number"),
            "department": get_field("department"),
            "branch": get_field("branch"),
            "semester": get_field("semester"),
            "subject_code": get_field("subject_code"),
            "subject_name": get_field("subject_name"),
            "building_name": get_field("building_name"),
            "floor_number": get_field("floor_number"),
            "room_number": raw_room.strip(),
            "bench_number": get_field("bench_number"),
            "seat_number": norm_seat,
            "grid_row": get_field("row_number"),
            "grid_column": get_field("column_number"),
            "shift": get_field("shift") or default_shift,
        }
        valid_staged_records.append(record_dict)

        if len(preview_records) < 50:
            preview_records.append(ImportRecordPreview(**record_dict))

    if total_rows == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No non-empty student seating rows were found in the uploaded Excel file.",
        )

    if invalid_records:
        warnings.append(
            f"{len(invalid_records)} invalid row(s) detected and excluded from staging."
        )
    if duplicates:
        warnings.append(
            f"{len(duplicates)} duplicate/conflicting row(s) detected and excluded from staging."
        )
    if replace_existing and existing_roll_numbers:
        warnings.append(
            f"Confirming this import will atomically replace {len(existing_roll_numbers)} existing seating record(s) for this examination."
        )

    return {
        "total_rows": total_rows,
        "valid_rows": len(valid_staged_records),
        "invalid_rows": len(invalid_records),
        "duplicate_rows": len(duplicates),
        "detected_columns": detected_columns,
        "preview_records": preview_records,
        "staged_records": valid_staged_records,
        "duplicates": duplicates,
        "invalid_records": invalid_records,
        "can_confirm": len(valid_staged_records) > 0,
        "warnings": warnings,
    }


def generate_sample_excel_template() -> bytes:
    """Generate a clean Excel (.xlsx) template file with canonical columns for administrators."""
    columns = [
        "roll_number",
        "student_name",
        "registration_number",
        "department",
        "branch",
        "semester",
        "subject_code",
        "subject_name",
        "building_name",
        "floor_number",
        "room_number",
        "bench_number",
        "seat_number",
        "row_number",
        "column_number",
        "shift",
    ]
    sample_rows = [
        {
            "roll_number": "2026CS1001",
            "student_name": "Aarav Sharma",
            "registration_number": "REG2026001",
            "department": "Computer Science & Engineering",
            "branch": "CSE",
            "semester": "Semester V",
            "subject_code": "CS501",
            "subject_name": "Database Management Systems",
            "building_name": "Academic Block A",
            "floor_number": "2nd Floor",
            "room_number": "A-204",
            "bench_number": "B-01",
            "seat_number": "S-01",
            "row_number": "Row 1",
            "column_number": "Col 1",
            "shift": "Morning (09:30 AM - 12:30 PM)",
        },
        {
            "roll_number": "2026CS1002",
            "student_name": "Diya Verma",
            "registration_number": "REG2026002",
            "department": "Computer Science & Engineering",
            "branch": "CSE",
            "semester": "Semester V",
            "subject_code": "CS501",
            "subject_name": "Database Management Systems",
            "building_name": "Academic Block A",
            "floor_number": "2nd Floor",
            "room_number": "A-204",
            "bench_number": "B-01",
            "seat_number": "S-02",
            "row_number": "Row 1",
            "column_number": "Col 2",
            "shift": "Morning (09:30 AM - 12:30 PM)",
        },
    ]
    df = pd.DataFrame(sample_rows, columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="SeatingPlan")
    output.seek(0)
    return output.getvalue()
