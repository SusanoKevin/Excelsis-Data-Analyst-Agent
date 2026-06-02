#!/usr/bin/env python3
"""
Set all 20 class sections to a spread of attendance rates that
showcases the full spectrum around the 75% threshold.

Distribution:
  Excellent  (90%+)  : 9-B 92%  10-A 95%  11-A 91%  12-A 94%
  Good       (80-89%): 9-D 85%  10-B 83%  11-D 82%  12-D 87%
  Borderline (75-79%): 9-C 78%  10-E 76%  11-B 79%  12-C 75%
  At-risk    (65-74%): 9-E 70%  11-C 66%  10-D 72%  12-B 68%
  Critical   (<65%) : 9-A 50%  10-C 58%  11-E 63%  12-E 55%
"""
from __future__ import annotations

from urllib.parse import quote_plus

from sqlalchemy import create_engine, text

SERVER   = "localhost,1433"
USERNAME = "sa"
PASSWORD = "ExcelsisTest_2024!"
DRIVER   = "{ODBC Driver 18 for SQL Server}"

SECTION_TARGETS = [
    # Excellent — well above threshold
    {"section": "9-B",  "target_rate": 0.92},
    {"section": "10-A", "target_rate": 0.95},
    {"section": "11-A", "target_rate": 0.91},
    {"section": "12-A", "target_rate": 0.94},
    # Good — comfortably passing
    {"section": "9-D",  "target_rate": 0.85},
    {"section": "10-B", "target_rate": 0.83},
    {"section": "11-D", "target_rate": 0.82},
    {"section": "12-D", "target_rate": 0.87},
    # Borderline — just above threshold
    {"section": "9-C",  "target_rate": 0.78},
    {"section": "10-E", "target_rate": 0.76},
    {"section": "11-B", "target_rate": 0.79},
    {"section": "12-C", "target_rate": 0.75},
    # At-risk — just below threshold
    {"section": "9-E",  "target_rate": 0.70},
    {"section": "11-C", "target_rate": 0.66},
    {"section": "10-D", "target_rate": 0.72},
    {"section": "12-B", "target_rate": 0.68},
    # Critical — well below threshold
    {"section": "9-A",  "target_rate": 0.50},
    {"section": "10-C", "target_rate": 0.58},
    {"section": "11-E", "target_rate": 0.63},
    {"section": "12-E", "target_rate": 0.55},
]


def _engine():
    dsn = (
        f"DRIVER={DRIVER};SERVER={SERVER};DATABASE=education_db;"
        f"UID={USERNAME};PWD={PASSWORD};TrustServerCertificate=yes;"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={quote_plus(dsn)}")


def _set_rate(conn, sec: str, target: float) -> None:
    row = conn.execute(
        text(
            "SELECT COUNT(*) AS total,"
            " SUM(CASE WHEN status='present' THEN 1 ELSE 0 END) AS present_count,"
            " SUM(CASE WHEN status='absent'  THEN 1 ELSE 0 END) AS absent_count"
            " FROM attendance WHERE class_section = :sec"
        ),
        {"sec": sec},
    ).fetchone()

    total, present, absent = row.total, row.present_count, row.absent_count
    if total == 0:
        print(f"  {sec}: no rows found, skipping")
        return

    target_present = int(total * target)
    delta = target_present - present

    if abs(delta) <= 1:
        print(f"  {sec}: already at {present/total*100:.1f}%, target {target*100:.0f}% — skip")
        return

    if delta > 0:
        # need MORE present: flip absent → present
        to_flip = min(delta, absent)
        conn.execute(
            text(
                f"UPDATE TOP ({to_flip}) attendance"
                " SET status = 'present'"
                " WHERE class_section = :sec AND status = 'absent'"
            ),
            {"sec": sec},
        )
        actual = (present + to_flip) / total * 100
        print(f"  {sec}: +{to_flip:,} absent→present → ~{actual:.0f}%  (was {present/total*100:.0f}%)")
    else:
        # need FEWER present: flip present → absent
        to_flip = -delta
        conn.execute(
            text(
                f"UPDATE TOP ({to_flip}) attendance"
                " SET status = 'absent'"
                " WHERE class_section = :sec AND status = 'present'"
            ),
            {"sec": sec},
        )
        actual = (present - to_flip) / total * 100
        print(f"  {sec}: -{to_flip:,} present→absent → ~{actual:.0f}%  (was {present/total*100:.0f}%)")


def main() -> None:
    engine = _engine()
    print("Setting attendance rates across all 20 sections...\n")

    categories = [
        ("Excellent  (90%+) ", ["9-B", "10-A", "11-A", "12-A"]),
        ("Good       (80-89%)", ["9-D", "10-B", "11-D", "12-D"]),
        ("Borderline (75-79%)", ["9-C", "10-E", "11-B", "12-C"]),
        ("At-risk    (65-74%)", ["9-E", "11-C", "10-D", "12-B"]),
        ("Critical   (<65%) ", ["9-A", "10-C", "11-E", "12-E"]),
    ]

    target_map = {p["section"]: p["target_rate"] for p in SECTION_TARGETS}

    with engine.begin() as conn:
        for label, sections in categories:
            print(f"{label}:")
            for sec in sections:
                _set_rate(conn, sec, target_map[sec])
            print()

    print("Done")
    engine.dispose()


if __name__ == "__main__":
    main()
