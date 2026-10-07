"""Orden explícito del historial y datos opcionales de actividades sintéticas."""
from app import activity_service as activities
from test_hardening import IsolatedDatabase


class ActivityListTests(IsolatedDatabase):
    def test_mixed_history_and_future_descending_with_stable_tie_breaker(self):
        for day in ("2026-01-01", "2026-12-01", "2026-10-01", "2026-12-01"):
            activities.create_activity_for_students([self.student], "Actividad Demo", "Otro", day)
        rows = activities.get_activities_by_student(self.student)
        self.assertEqual([r["activity_date"] for r in rows], ["2026-12-01", "2026-12-01", "2026-10-01", "2026-01-01"])
        self.assertGreater(rows[0]["student_activity_id"], rows[1]["student_activity_id"])

    def test_missing_location_and_payment_remain_optional(self):
        activities.create_activity_for_students([self.student], "Actividad Demo", "Otro", "2026-10-05")
        row = activities.get_activities_by_student(self.student)[0]
        self.assertEqual(row["location"], "")
        self.assertEqual(row["paid_amount"], 0)

    def test_listing_uses_one_select_for_many_activities(self):
        from unittest.mock import patch
        from app import database
        for index in range(12):
            activities.create_activity_for_students([self.student], "Actividad Demo", "Otro", "2026-10-05")
        connection = database.get_connection()
        statements = []
        connection.set_trace_callback(statements.append)
        with patch("app.activities_repository.get_connection", return_value=connection):
            self.assertEqual(len(activities.get_activities_by_student(self.student)), 12)
        self.assertEqual(sum(s.lstrip().upper().startswith("SELECT") for s in statements), 1)
