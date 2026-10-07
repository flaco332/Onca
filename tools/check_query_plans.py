"""Compare baseline/current query plans on synthetic in-memory data, no timing."""
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.migrations import migrate_database
from tests.fixtures.query_plan_data import populate_query_plan_fixture


def main() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript((Path(__file__).resolve().parents[1] / "app/schema.sql").read_text())
        populate_query_plan_fixture(conn)
        queries = {
            "latest_payment": "SELECT payment_date FROM payments WHERE student_id=1 ORDER BY payment_date DESC,payment_id DESC LIMIT 1",
            "latest_certificate": "SELECT file_path FROM medical_certificates WHERE student_id=1 ORDER BY issue_date DESC,certificate_id DESC LIMIT 1",
            "participations": "SELECT student_activity_id FROM student_activities WHERE student_id=1",
            "shared_activity": "SELECT count(*) FROM student_activities WHERE activity_id=1",
        }
        for label in ("BEFORE", "AFTER"):
            if label == "AFTER":
                migrate_database(conn)
            for name, sql in queries.items():
                plan = " | ".join(row[3] for row in conn.execute("EXPLAIN QUERY PLAN " + sql))
                print(f"{label} {name}: {plan}")
                if label == "AFTER" and name.startswith("latest_"):
                    assert "TEMP B-TREE" not in plan
    finally:
        conn.close()


if __name__ == "__main__":
    main()
