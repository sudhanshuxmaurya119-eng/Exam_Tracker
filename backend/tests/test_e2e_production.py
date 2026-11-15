"""Comprehensive End-to-End Test Suite covering all 15 Phase 10 Production Test Scenarios."""

import io
import os
from pathlib import Path
import sys
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# Ensure backend root is in sys.path
BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

# Configure test environment before importing app
TEST_DB_FILE = BACKEND_ROOT / "tests" / "test_persistence.db"
os.environ["APP_ENV"] = "testing"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE.as_posix()}"
os.environ["INITIAL_ADMIN_USERNAME"] = "controller_admin"
os.environ["INITIAL_ADMIN_EMAIL"] = "controller@examportal.edu"
os.environ["INITIAL_ADMIN_PASSWORD"] = "StrongAdminPass#2026"
os.environ["JWT_SECRET_KEY"] = "test-super-secret-jwt-key-with-at-least-32-characters-long"

from app.core.config import Settings, get_settings
from app.core import database
from app.core.rate_limit import rate_limiter
from app.main import app, bootstrap_initial_admin


def make_excel_bytes(rows: list[dict]) -> bytes:
    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Seating")
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    get_settings.cache_clear()
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()
    database.reconfigure_database(f"sqlite:///{TEST_DB_FILE.as_posix()}")
    database.Base.metadata.create_all(bind=database.engine)
    bootstrap_initial_admin()
    rate_limiter.clear()
    yield
    database.engine.dispose()
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except OSError:
            pass


@pytest.fixture()
def client() -> TestClient:
    rate_limiter.clear()
    return TestClient(app)


def test_01_student_portal_and_health_accessibility(client: TestClient):
    """Test 1: Verify /health and public examination endpoints are accessible."""
    health_res = client.get("/health")
    assert health_res.status_code == 200
    body = health_res.json()
    assert body["status"] == "healthy"
    assert body["database"]["connected"] is True
    assert body["storage"]["bucket"] == "seating-datasets"

    pub_res = client.get("/api/v1/examinations/public")
    assert pub_res.status_code == 200
    assert isinstance(pub_res.json(), list)


def test_02_administrator_login(client: TestClient):
    """Test 2: Verify administrator authentication and rejection of invalid credentials."""
    bad_res = client.post(
        "/api/v1/auth/login",
        json={"username": "controller_admin", "password": "WrongPassword123"},
    )
    assert bad_res.status_code == 401

    ok_res = client.post(
        "/api/v1/auth/login",
        json={"username": "controller_admin", "password": "StrongAdminPass#2026"},
    )
    assert ok_res.status_code == 200
    data = ok_res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "controller_admin"
    assert data["user"]["role"] == "super_admin"


def get_auth_headers(client: TestClient) -> dict[str, str]:
    res = client.post(
        "/api/v1/auth/login",
        json={"username": "controller_admin", "password": "StrongAdminPass#2026"},
    )
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_03_examination_creation_and_multiple_shifts(client: TestClient):
    """Test 3, 9, 10: Create multiple examinations across Morning and Afternoon shifts."""
    headers = get_auth_headers(client)

    exam1_payload = {
        "title": "B.Tech End Semester Examination - Database Systems",
        "exam_code": "ESE-2026-CS501-M",
        "subject_name": "Database Management Systems",
        "subject_code": "CS501",
        "exam_date": "2026-12-10",
        "shift": "Morning (09:30 AM - 12:30 PM)",
        "start_time": "09:30 AM",
        "end_time": "12:30 PM",
        "academic_session": "2026-2027",
        "semester": "Semester V",
        "department": "Computer Science & Engineering",
        "status": "published",
        "instructions": "Bring University ID Card.",
    }
    r1 = client.post("/api/v1/examinations", json=exam1_payload, headers=headers)
    assert r1.status_code == 201, r1.text

    exam2_payload = {
        "title": "B.Tech End Semester Examination - Operating Systems",
        "exam_code": "ESE-2026-CS502-A",
        "subject_name": "Operating Systems",
        "subject_code": "CS502",
        "exam_date": "2026-12-12",
        "shift": "Afternoon (02:00 PM - 05:00 PM)",
        "start_time": "02:00 PM",
        "end_time": "05:00 PM",
        "academic_session": "2026-2027",
        "semester": "Semester V",
        "department": "Computer Science & Engineering",
        "status": "published",
        "instructions": "No programmable calculators allowed.",
    }
    r2 = client.post("/api/v1/examinations", json=exam2_payload, headers=headers)
    assert r2.status_code == 201, r2.text

    # Verify duplicate exam_code is rejected
    dup_res = client.post("/api/v1/examinations", json=exam1_payload, headers=headers)
    assert dup_res.status_code == 409


def test_04_to_07_excel_upload_processing_duplicate_detection_and_insertion(client: TestClient):
    """Test 4, 5, 6, 7: Upload Excel, detect duplicates & invalid rows, preview, and confirm transactional insert."""
    headers = get_auth_headers(client)
    exams = client.get("/api/v1/examinations", headers=headers).json()
    exam1 = next(e for e in exams if e["exam_code"] == "ESE-2026-CS501-M")

    excel_rows = [
        {
            "roll_number": "2026CS1001",
            "student_name": "Aarav Sharma",
            "department": "CSE",
            "building_name": "Block A",
            "floor_number": "1st Floor",
            "room_number": "A-101",
            "bench_number": "B-01",
            "seat_number": "S-01",
        },
        {
            "roll_number": "2026CS1002",
            "student_name": "Diya Verma",
            "department": "CSE",
            "building_name": "Block A",
            "floor_number": "1st Floor",
            "room_number": "A-101",
            "bench_number": "B-01",
            "seat_number": "S-02",
        },
        # Duplicate roll_number inside Excel sheet!
        {
            "roll_number": "2026CS1001",
            "student_name": "Aarav Sharma Duplicate",
            "department": "CSE",
            "building_name": "Block A",
            "floor_number": "1st Floor",
            "room_number": "A-101",
            "bench_number": "B-02",
            "seat_number": "S-03",
        },
        # Invalid row (missing room_number and seat_number)
        {
            "roll_number": "2026CS1003",
            "student_name": "Rohan Nair",
            "department": "CSE",
            "building_name": "Block A",
            "floor_number": "1st Floor",
            "room_number": "",
            "bench_number": "",
            "seat_number": "",
        },
    ]
    excel_bytes = make_excel_bytes(excel_rows)

    upload_res = client.post(
        "/api/v1/imports/upload",
        data={"examination_id": str(exam1["id"]), "replace_existing": "true"},
        files={
            "file": (
                "cs501_seating.xlsx",
                excel_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    )
    assert upload_res.status_code == 200, upload_res.text
    preview = upload_res.json()

    assert preview["total_rows"] == 4
    assert preview["valid_rows"] == 2
    assert preview["duplicate_rows"] == 1
    assert preview["invalid_rows"] == 1
    assert preview["can_confirm"] is True
    assert preview["duplicates"][0]["roll_number"] == "2026CS1001"
    assert preview["duplicates"][0]["source"] == "within_excel"

    # Confirm and commit into PostgreSQL / DB transaction
    job_token = preview["job_token"]
    confirm_res = client.post(f"/api/v1/imports/{job_token}/confirm", headers=headers)
    assert confirm_res.status_code == 200, confirm_res.text
    confirm_data = confirm_res.json()
    assert confirm_data["status"] == "completed"
    assert confirm_data["inserted_rows"] == 2


def test_08_to_11_multi_exam_multi_shift_search_and_pdf_generation(client: TestClient):
    """Test 8, 9, 10, 11: Same student in a second examination/shift (different room/seat), search, and PDF slip."""
    headers = get_auth_headers(client)
    exams = client.get("/api/v1/examinations", headers=headers).json()
    exam2 = next(e for e in exams if e["exam_code"] == "ESE-2026-CS502-A")

    # Student 2026CS1001 has a DIFFERENT room and seat in Exam 2 (Afternoon Shift)
    exam2_rows = [
        {
            "roll_number": "2026CS1001",
            "student_name": "Aarav Sharma",
            "department": "CSE",
            "building_name": "Block C",
            "floor_number": "3rd Floor",
            "room_number": "C-305",
            "bench_number": "B-12",
            "seat_number": "S-24",
        }
    ]
    up2 = client.post(
        "/api/v1/imports/upload",
        data={"examination_id": str(exam2["id"]), "replace_existing": "true"},
        files={
            "file": (
                "cs502_seating.xlsx",
                make_excel_bytes(exam2_rows),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    ).json()
    client.post(f"/api/v1/imports/{up2['job_token']}/confirm", headers=headers)

    # Search student across ALL examinations
    search_res = client.get("/api/v1/search/student", params={"roll_number": "2026cs1001"})
    assert search_res.status_code == 200
    s_data = search_res.json()
    assert s_data["total_allocations"] == 2
    rooms = {a["exam_code"]: (a["room_number"], a["seat_number"]) for a in s_data["allocations"]}
    assert rooms["ESE-2026-CS501-M"] == ("A-101", "S-01")
    assert rooms["ESE-2026-CS502-A"] == ("C-305", "S-24")

    # Filter search by Shift
    afternoon_res = client.get(
        "/api/v1/search/student",
        params={"roll_number": "2026CS1001", "shift": "Afternoon (02:00 PM - 05:00 PM)"},
    )
    assert afternoon_res.status_code == 200
    assert afternoon_res.json()["total_allocations"] == 1
    assert afternoon_res.json()["allocations"][0]["room_number"] == "C-305"

    # Test 11: Official PDF Seating Slip generation
    pdf_res = client.get("/api/v1/search/seating-slip/pdf", params={"roll_number": "2026CS1001"})
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-1.4")
    assert len(pdf_res.content) > 500


def test_12_and_13_safe_dataset_replacement_and_deletion(client: TestClient):
    """Test 12 & 13: Verify existing records are preserved during preview/cancel, replaced atomically on confirm, and deleted cleanly."""
    headers = get_auth_headers(client)
    exams = client.get("/api/v1/examinations", headers=headers).json()
    exam1 = next(e for e in exams if e["exam_code"] == "ESE-2026-CS501-M")

    # Upload replacement dataset but DO NOT confirm yet
    replacement_rows = [
        {
            "roll_number": "2026CS1001",
            "student_name": "Aarav Sharma",
            "department": "CSE",
            "building_name": "Block B",
            "floor_number": "2nd Floor",
            "room_number": "B-202",
            "bench_number": "B-05",
            "seat_number": "S-10",
        }
    ]
    preview = client.post(
        "/api/v1/imports/upload",
        data={"examination_id": str(exam1["id"]), "replace_existing": "true"},
        files={
            "file": (
                "cs501_v2.xlsx",
                make_excel_bytes(replacement_rows),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    ).json()

    # Before confirmation, old seating record (A-101) MUST still be intact!
    pre_check = client.get(
        "/api/v1/search/student",
        params={"roll_number": "2026CS1001", "examination_id": exam1["id"]},
    ).json()
    assert pre_check["allocations"][0]["room_number"] == "A-101"

    # Now confirm the replacement dataset
    confirm = client.post(f"/api/v1/imports/{preview['job_token']}/confirm", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["replaced_previous_rows"] == 2
    assert confirm.json()["inserted_rows"] == 1

    # Verify student search now reflects the new room B-202
    post_check = client.get(
        "/api/v1/search/student",
        params={"roll_number": "2026CS1001", "examination_id": exam1["id"]},
    ).json()
    assert post_check["allocations"][0]["room_number"] == "B-202"

    # Test signed download URL generation
    ds_id = preview["dataset_id"]
    signed_res = client.get(f"/api/v1/datasets/{ds_id}/signed-url", headers=headers)
    assert signed_res.status_code == 200
    signed_url = signed_res.json()["signed_url"]
    dl_res = client.get(signed_url)
    assert dl_res.status_code == 200
    assert dl_res.content.startswith(b"PK\x03\x04")

    # Test 13: Delete the old superseded dataset
    datasets = client.get(
        "/api/v1/datasets", params={"examination_id": exam1["id"]}, headers=headers
    ).json()
    superseded = next(d for d in datasets if not d["is_active"])
    del_res = client.delete(f"/api/v1/datasets/{superseded['id']}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


def test_14_database_persistence_across_restart_and_prod_guard(client: TestClient):
    """Test 14: Dispose engine (simulating server restart) and verify data persists; verify SQLite blocked in production."""
    database.engine.dispose()
    database.reconfigure_database(f"sqlite:///{TEST_DB_FILE.as_posix()}")

    res = client.get("/api/v1/search/student", params={"roll_number": "2026CS1001"})
    assert res.status_code == 200
    assert res.json()["total_allocations"] == 2

    # Verify production configuration strictly rejects SQLite
    with pytest.raises(ValueError, match="SQLite is prohibited in production"):
        Settings(
            APP_ENV="production",
            DATABASE_URL="sqlite:///./illegal.db",
            JWT_SECRET_KEY="a" * 64,
            SUPABASE_URL="https://example.supabase.co",
            SUPABASE_SERVICE_ROLE_KEY="service-role-secret",
        )


def test_15_unauthorized_api_access_and_security(client: TestClient):
    """Test 15: Verify unauthorized access to admin endpoints and wildcard scraping attempts are blocked."""
    assert client.get("/api/v1/examinations").status_code == 401
    assert client.get("/api/v1/datasets").status_code == 401
    assert client.get("/api/v1/imports/jobs").status_code == 401
    assert client.get("/api/v1/maintenance/dashboard").status_code == 401

    # Wildcard or SQL injection attempt on public student search must be rejected with 400
    inj_res = client.get("/api/v1/search/student", params={"roll_number": "% OR 1=1 --"})
    assert inj_res.status_code == 400
