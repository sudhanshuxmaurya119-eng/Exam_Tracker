"""CLI script to provision or update an administrator user in PostgreSQL."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, or_, select
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.models import AdminUser


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update an Examination Portal Administrator")
    parser.add_argument("--username", required=True, help="Admin username")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password (>= 8 chars)")
    parser.add_argument("--full-name", default="Examination Controller", help="Full name")
    parser.add_argument(
        "--role",
        choices=["super_admin", "admin", "viewer"],
        default="super_admin",
        help="Role assignment",
    )
    args = parser.parse_args()

    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        existing = db.scalar(
            select(AdminUser).where(
                or_(
                    func.lower(AdminUser.username) == args.username.lower(),
                    func.lower(AdminUser.email) == args.email.lower(),
                )
            )
        )
        if existing:
            existing.username = args.username.strip()
            existing.email = args.email.strip().lower()
            existing.full_name = args.full_name.strip()
            existing.hashed_password = hash_password(args.password)
            existing.role = args.role
            existing.is_active = True
            db.commit()
            print(f"Updated existing administrator '{existing.username}' ({existing.email}) with role '{existing.role}'.")
        else:
            admin = AdminUser(
                username=args.username.strip(),
                email=args.email.strip().lower(),
                full_name=args.full_name.strip(),
                hashed_password=hash_password(args.password),
                role=args.role,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"Created administrator '{admin.username}' ({admin.email}) with role '{admin.role}'.")


if __name__ == "__main__":
    main()
