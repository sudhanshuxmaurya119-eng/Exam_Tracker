"""Official Examination Seating Slip and Room Seating Plan PDF generator."""

import io
from datetime import datetime, timezone
from typing import List
from app.schemas.schemas import StudentSeatingAllocation


def _escape_pdf_text(text: str) -> str:
    """Escape characters for PDF literal strings."""
    cleaned = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(text or ""))
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_native_pdf(lines_per_page: List[List[tuple[str, int, int, int, bool]]]) -> bytes:
    """Generate a standards-compliant PDF-1.4 document with Helvetica/Helvetica-Bold fonts."""
    objects: List[bytes] = []

    def add_obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    # 1: Catalog, 2: Pages placeholder, 3: Font Regular, 4: Font Bold
    add_obj(b"<< /Type /Catalog /Pages 2 0 R >>")
    add_obj(b"")  # placeholder for /Pages
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    page_obj_ids: List[int] = []

    for page_items in lines_per_page:
        stream_lines = [
            "q",
            "0.12 0.23 0.54 rg",
            "36 765 540 42 re f",
            "0.95 0.96 0.98 rg",
            "36 695 540 58 re f",
            "0.80 0.84 0.90 RG",
            "1 w",
            "36 60 540 747 re S",
            "Q",
        ]
        for text, x, y, size, bold in page_items:
            font_ref = "/F2" if bold else "/F1"
            color_cmd = "1 1 1 rg" if y >= 775 else "0.1 0.14 0.22 rg"
            escaped = _escape_pdf_text(text)
            stream_lines.append(
                f"BT {color_cmd} {font_ref} {size} Tf {x} {y} Td ({escaped}) Tj ET"
            )

        stream_data = "\n".join(stream_lines).encode("latin-1", errors="replace")
        content_id = add_obj(
            f"<< /Length {len(stream_data)} >>\nstream\n".encode("ascii")
            + stream_data
            + b"\nendstream"
        )
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_id} 0 R >>"
        ).encode("ascii")
        page_id = add_obj(page_dict)
        page_obj_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode("ascii")

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: List[int] = []
    for idx, obj_bytes in enumerate(objects, start=1):
        offsets.append(buf.tell())
        buf.write(f"{idx} 0 obj\n".encode("ascii"))
        buf.write(obj_bytes)
        buf.write(b"\nendobj\n")

    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    buf.write(b"0000000000 65535 f \n")
    for off in offsets:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))

    buf.write(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return buf.getvalue()


def generate_student_seating_slip_pdf(
    roll_number: str,
    allocations: List[StudentSeatingAllocation],
) -> bytes:
    """Generate an official printable PDF seating slip for a student across one or more examinations."""
    generated_ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    first = allocations[0]
    pages: List[List[tuple[str, int, int, int, bool]]] = []

    items: List[tuple[str, int, int, int, bool]] = [
        ("EXAMINATION SEATING PLAN PORTAL - OFFICIAL SEATING SLIP", 50, 782, 13, True),
        (f"Candidate Name: {first.student_name}", 50, 730, 12, True),
        (f"Roll Number: {first.roll_number}", 360, 730, 12, True),
        (
            f"Department / Branch: {first.department or 'N/A'} ({first.branch or 'General'})",
            50,
            710,
            10,
            False,
        ),
        (f"Registration No: {first.registration_number or 'N/A'}", 360, 710, 10, False),
        (f"Allocated Examinations ({len(allocations)}):", 50, 672, 12, True),
    ]

    y = 648
    for idx, alloc in enumerate(allocations, start=1):
        if y < 140:
            items.append((f"Generated on: {generated_ts}", 50, 72, 8, False))
            pages.append(items)
            items = [
                ("EXAMINATION SEATING PLAN PORTAL - OFFICIAL SEATING SLIP (CONT.)", 50, 782, 13, True),
                (f"Candidate: {first.student_name} ({first.roll_number})", 50, 725, 11, True),
            ]
            y = 665

        items.append(
            (
                f"{idx}. {alloc.examination_title} [{alloc.exam_code}]",
                50,
                y,
                11,
                True,
            )
        )
        y -= 16
        items.append(
            (
                f"   Date: {alloc.exam_date.isoformat()}   |   Shift: {alloc.shift}"
                + (f" ({alloc.start_time} - {alloc.end_time})" if alloc.start_time else ""),
                50,
                y,
                10,
                False,
            )
        )
        y -= 15
        items.append(
            (
                f"   Subject: {alloc.subject_name or 'Allotted Paper'} ({alloc.subject_code or '-'})",
                50,
                y,
                10,
                False,
            )
        )
        y -= 16
        items.append(
            (
                f"   HALL / ROOM: {alloc.room_number}   |   SEAT NO: {alloc.seat_number}"
                + (f"   |   BENCH: {alloc.bench_number}" if alloc.bench_number else ""),
                50,
                y,
                11,
                True,
            )
        )
        y -= 15
        items.append(
            (
                f"   Building: {alloc.building_name or 'Main Block'}   |   Floor: {alloc.floor_number or 'Ground'}"
                + (
                    f"   |   Row/Col: {alloc.row_number or '-'} / {alloc.column_number or '-'}"
                    if (alloc.row_number or alloc.column_number)
                    else ""
                ),
                50,
                y,
                10,
                False,
            )
        )
        y -= 15
        if alloc.instructions:
            items.append((f"   Note: {alloc.instructions[:95]}", 50, y, 9, False))
            y -= 15
        y -= 10

    items.append(
        (
            "IMPORTANT: Carry your University ID Card and this Seating Slip to the Examination Hall.",
            50,
            92,
            9,
            True,
        )
    )
    items.append((f"Generated on: {generated_ts} | Verified by Examination Controller Portal", 50, 74, 8, False))
    pages.append(items)

    return _build_native_pdf(pages)
