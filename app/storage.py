import csv
from datetime import datetime, date


FIELDNAMES = [
    "name",
    "phone",
    "has_medical",
    "last_payment_date",
    "medical_cert_date",
    "medical_cert_path",
]


def parse_date(value: str) -> date:
    value = (value or "").strip()

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return date.today()


def load_students(file_path):
    students = []

    try:
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f, delimiter="|")

            for row in reader:
                name = (row.get("name") or "").strip()

                if not name:
                    continue

                students.append({
                    "name": name,
                    "phone": (row.get("phone") or "").strip(),
                    "has_medical": ((row.get("has_medical") or "False").strip() == "True"),
                    "last_payment_date": parse_date(row.get("last_payment_date")),
                    "medical_cert_date": parse_date(row.get("medical_cert_date")),
                    "medical_cert_path": (row.get("medical_cert_path") or "").strip(),
                })

    except FileNotFoundError:
        pass

    return students


def save_students(file_path, students):
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter="|")
        writer.writeheader()

        for student in students:
            writer.writerow({
                "name": student["name"],
                "phone": student["phone"],
                "has_medical": str(student["has_medical"]),
                "last_payment_date": student["last_payment_date"].strftime("%Y-%m-%d"),
                "medical_cert_date": student["medical_cert_date"].strftime("%Y-%m-%d"),
                "medical_cert_path": student["medical_cert_path"],
            })