"""Database health check and backup verification CLI utility."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select
from app.core.database import SessionLocal, verify_database_connection
from app.models.models import (
    AdminUser,
    Dataset,
    Examination,
    ImportJob,
    SeatingRecord,
    Student,
)
from app.services.storage_service import storage_service


def main() -> None:
    db_health = verify_database_connection()
    storage_health = storage_service.get_storage_health()

    if not db_health.get("connected"):
        print(json.dumps({"status": "FAILED", "database": db_health}, indent=2))
        sys.exit(1)

    with SessionLocal() as db:
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "OK",
            "database": db_health,
            "storage": storage_health,
            "counts": {
                "admin_users": int(db.scalar(select(func.count(AdminUser.id))) or 0),
                "examinations": int(db.scalar(select(func.count(Examination.id))) or 0),
                "datasets": int(db.scalar(select(func.count(Dataset.id))) or 0),
                "students": int(db.scalar(select(func.count(Student.id))) or 0),
                "seating_records": int(db.scalar(select(func.count(SeatingRecord.id))) or 0),
                "import_jobs": int(db.scalar(select(func.count(ImportJob.id))) or 0),
            },
        }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
