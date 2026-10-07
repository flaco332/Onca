"""Run the actual UI once against isolated empty data, then close it."""
from contextlib import closing
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

TABLES = ("students", "payments", "medical_certificates", "extra_activities", "student_activities")

def main():
    root = Path(__file__).resolve().parents[1]
    command = [str(Path(sys.argv[1]).resolve())] if len(sys.argv) > 1 else [sys.executable, str(root / "run.py")]
    with tempfile.TemporaryDirectory(prefix="onca-smoke-") as folder:
        env = dict(os.environ, ONCA_DATA_DIR=folder)
        for _ in range(2):
            subprocess.run(command + ["--smoke-test"], env=env, cwd=folder, check=True, timeout=60)
            with closing(sqlite3.connect(str(Path(folder) / "onca.db"))) as conn:
                assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                assert not conn.execute("PRAGMA foreign_key_check").fetchall()
                for table in TABLES:
                    assert conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0
        print("UI, cinco tablas vacías, reinicio y cierre ordenado: OK")


if __name__ == "__main__":
    main()
