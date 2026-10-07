"""Opt-in desktop tests, separated from headless data-layer coverage."""
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch
from app import database
from app.student_service import save_student_to_db, load_students_from_db
from app.ui import StudentApp
from app.date_picker import BirthDatePicker
from app.activity_service import create_activity_for_students, get_activities_by_student
from datetime import date


@unittest.skipUnless(os.environ.get("ONCA_GUI_TESTS") == "1", "Requires desktop; set ONCA_GUI_TESTS=1")
class GuiTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(prefix="onca-gui-test-")
        self.addCleanup(folder.cleanup)
        for key, value in (("DATA_FOLDER", folder.name), ("DB_PATH", str(Path(folder.name) / "onca.db"))):
            mocked = patch.object(database, key, value)
            mocked.start()
            self.addCleanup(mocked.stop)
        database.init_db()
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = StudentApp(self.root)
        self.addCleanup(self.root.destroy)
        self.addCleanup(self.app.tasks.close)
        self.errors = []
        self.root.report_callback_exception = lambda kind, value, trace: self.errors.append(kind)

    def test_navigation_form_theme_and_resize(self):
        for tab in self.app.notebook.tabs():
            self.app.notebook.select(tab)
            self.root.update()
        self.app.open_activity_form("create")
        forms = [child for child in self.root.winfo_children() if isinstance(child, tk.Toplevel)]
        self.assertEqual(len(forms), 1)
        forms[0].destroy()
        self.app.toggle_dark_mode()
        self.root.geometry("1120x760")
        self.root.update()
        self.assertEqual(self.errors, [])

    def test_activity_form_keeps_original_single_recipient(self):
        first = save_student_to_db({"name": "Alumno Prueba Uno"})
        second = save_student_to_db({"name": "Alumno Prueba Dos"})
        self.app.selected_student_id = first
        self.app.open_activity_form("create", selected_student_ids=[first])
        form = next(child for child in self.root.winfo_children() if isinstance(child, tk.Toplevel))
        form.inline_fields["title"].entry.insert(0, "Actividad Demo")
        self.app.selected_student_id = second
        button = next(child for child in form.activity_form.winfo_children() if isinstance(child, ttk.Button))
        with patch("app.ui.messagebox.showerror") as error:
            button.invoke()
            error.assert_not_called()
        from app.activity_service import get_activities_by_student
        self.assertEqual(len(get_activities_by_student(first)), 1)
        self.assertEqual(get_activities_by_student(second), [])

    def test_homonym_selection_and_save_by_id(self):
        first = save_student_to_db({"name": "Alumno Prueba"})
        second = save_student_to_db({"name": "Alumno Prueba"})
        self.app.students = load_students_from_db()
        self.app.refresh_listbox()
        self.app.listbox.selection_set(str(second))
        self.app.on_student_selected(None)
        self.assertEqual(self.app.selected_student_id, second)
        self.app.entry_name.delete(0, tk.END)
        self.app.entry_name.insert(0, "Alumno Editado")
        with patch("app.ui.messagebox.showerror") as error, patch("app.ui.messagebox.showwarning") as warning:
            self.app.add_or_update()
            error.assert_not_called()
            warning.assert_not_called()
        rows = {row["student_id"]: row["name"] for row in load_students_from_db()}
        self.assertEqual(rows[first], "Alumno Prueba")
        self.assertEqual(rows[second], "Alumno Editado")
        self.assertEqual(self.errors, [])

    def select_demo(self):
        student_id = save_student_to_db({"name": "Alumno Prueba"})
        self.app.students = load_students_from_db()
        self.app.refresh_listbox()
        self.app.load_student_into_form(self.app.students_by_id[student_id])
        return student_id

    def activity_window(self):
        return next(child for child in self.root.winfo_children() if isinstance(child, tk.Toplevel))

    def test_phone_errors_inline_and_live(self):
        self.app.entry_name.insert(0, "Alumno Prueba")
        for field in ("phone", "emergency_contact_phone"):
            control = self.app.inline_fields[field]
            control.value.set("abc")
            self.assertIn("Usa solo", control.error.get())
        with patch("app.ui.messagebox.showwarning") as warning, patch("app.ui.messagebox.showerror") as error:
            self.app.add_or_update()
            warning.assert_not_called()
            error.assert_not_called()
        self.assertEqual(load_students_from_db(), [])
        for field in ("phone", "emergency_contact_phone"):
            self.app.inline_fields[field].value.set("+1 (202) 555-0123")
            self.assertEqual(self.app.inline_fields[field].error.get(), "")
        self.app.add_or_update()
        self.assertEqual(len(load_students_from_db()), 1)

    def test_birth_date_error_inline(self):
        self.app.inline_fields["birth_date"].value.set("20010912")
        self.assertTrue(self.app.inline_fields["birth_date"].error.get())
        self.app.inline_fields["birth_date"].value.set("2001-09-12")
        self.assertEqual(self.app.inline_fields["birth_date"].error.get(), "")

    def test_new_student_payment_cell_empty(self):
        student_id = self.select_demo()
        self.assertEqual(self.app.listbox.set(str(student_id), "due"), "")
        self.assertEqual(self.app.entry_last_payment.get(), "")

    def test_programmatic_medical_value_waits_for_explicit_form_save(self):
        student_id = self.select_demo()
        self.app.has_medical_var.set(True)
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")
        self.app.add_or_update()
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "✓")
        self.app.load_student_into_form(self.app.students_by_id[student_id])
        self.app.has_medical_var.set(False)
        self.app.add_or_update()
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")

    def test_medical_header_and_centered_check(self):
        self.assertEqual(self.app.listbox.heading("medical", "text"), "V med")
        self.assertEqual(str(self.app.listbox.heading("medical", "anchor")), "center")
        self.assertEqual(str(self.app.listbox.column("medical", "anchor")), "center")
        self.assertFalse(self.app.listbox.column("medical", "stretch"))

    def test_separate_name_fields_save_and_edit(self):
        self.app.entry_name.insert(0, "Alumno Compuesto")
        self.app.entry_last_name.insert(0, "Ensayo Sintético")
        self.app.add_or_update()
        student = load_students_from_db()[0]
        student_id = student["student_id"]
        self.assertEqual(self.app.listbox.set(str(student_id), "name"), "Alumno Compuesto Ensayo Sintético")
        self.app.load_student_into_form(student)
        self.assertEqual(self.app.entry_name.get(), "Alumno Compuesto")
        self.assertEqual(self.app.entry_last_name.get(), "Ensayo Sintético")
        self.app.entry_last_name.delete(0, tk.END)
        self.app.add_or_update()
        self.assertEqual(load_students_from_db()[0]["student_id"], student_id)
        self.assertEqual(self.app.listbox.set(str(student_id), "name"), "Alumno Compuesto")

    def test_surname_validation_inline(self):
        self.app.inline_fields["last_name"].value.set("Prueba2")
        self.assertTrue(self.app.inline_fields["last_name"].error.get())
        self.app.inline_fields["last_name"].value.set("")
        self.assertEqual(self.app.inline_fields["last_name"].error.get(), "")

    def test_single_activity_columns_and_inline_detail(self):
        student_id = self.select_demo()
        create_activity_for_students([student_id], "Torneo Demo", "Torneo", "2026-10-05", "Lugar Prueba", 200, 122, "confirmed", "Nota general")
        activity = get_activities_by_student(student_id)[0]
        with database.get_connection() as conn:
            conn.execute("UPDATE student_activities SET notes='Nota personal' WHERE student_activity_id=?", (activity["student_activity_id"],))
        self.app.refresh_student_activities(student_id)
        iid = self.app.activities_tree.get_children()[0]
        self.assertEqual(self.app.activities_tree.item(iid, "values"), ("2026-10-05", "Torneo", "Lugar Prueba", "$200.00", "$122.00", "Confirmado"))
        self.app.activities_tree.selection_set(iid)
        self.app.show_activity_detail()
        detail = self.app.activity_detail.get("1.0", "end-1c")
        for value in ("Torneo Demo", "Nota general", "Nota personal"):
            self.assertIn(value, detail)
        self.assertEqual(self.app.get_selected_activity()["student_activity_id"], int(iid))
        self.assertEqual(str(self.app.activities_tree.column("date", "anchor")), "center")
        self.assertEqual(str(self.app.activities_tree.column("paid", "anchor")), "e")

    def test_activity_without_location_or_payment(self):
        student_id = self.select_demo()
        create_activity_for_students([student_id], "Examen Demo", "Examen", "2026-11-02")
        self.app.refresh_student_activities(student_id)
        iid = self.app.activities_tree.get_children()[0]
        self.assertEqual(self.app.activities_tree.set(iid, "location"), "")
        self.assertEqual(self.app.activities_tree.set(iid, "paid"), "$0.00")
        self.assertEqual(self.app.activities_tree.set(iid, "status"), "Pendiente")

    def test_activity_empty_state_not_selectable(self):
        self.select_demo()
        self.assertEqual(self.app.activities_tree.get_children(), ())
        self.assertIsNone(self.app.get_selected_activity(show_warning=False))
        self.assertIn("no hay actividades", self.app.activity_detail_title.get())

    def test_many_activities_scroll_and_stable_selection(self):
        student_id = self.select_demo()
        for index in range(35):
            create_activity_for_students([student_id], "Actividad Demo", "Otro", "2026-10-05")
        self.app.refresh_student_activities(student_id)
        self.app.notebook.select(self.app.tab_activities)
        self.root.deiconify()
        self.root.geometry("1120x700")
        self.root.update()
        self.assertEqual(len(self.app.activities_tree.get_children()), 35)
        self.assertLess(self.app.activities_tree.yview()[1], 1)
        iid = self.app.activities_tree.get_children()[12]
        self.app.activities_tree.selection_set(iid)
        self.app.refresh_student_activities(student_id)
        self.assertEqual(self.app.get_selected_activity()["student_activity_id"], int(iid))
        self.app.activities_tree.yview_moveto(1)
        self.root.update()
        self.assertAlmostEqual(self.app.activities_tree.yview()[1], 1, places=2)

    def test_activity_horizontal_only_on_overflow_and_dark_theme(self):
        self.app.notebook.select(self.app.tab_activities)
        self.root.deiconify()
        self.root.geometry("1600x700")
        self.root.update()
        self.assertEqual(self.app.activities_horizontal.winfo_manager(), "")
        self.root.geometry("880x620")
        self.root.update()
        self.assertEqual(self.app.activities_horizontal.winfo_manager(), "grid")
        self.app.toggle_dark_mode()
        self.assertEqual(self.app.activity_detail.cget("bg"), self.app.text_notes.cget("bg"))
        self.assertEqual(self.app.style.lookup("Treeview", "foreground"), "#f0f0f0")

    def test_activity_save_refreshes_main_date(self):
        student_id = self.select_demo()
        self.app.open_activity_form("create")
        window = self.activity_window()
        window.inline_fields["title"].value.set("Actividad Demo")
        button = next(child for child in window.activity_form.winfo_children() if isinstance(child, ttk.Button))
        button.invoke()
        self.assertEqual(self.app.listbox.set(str(student_id), "activity"), date.today().isoformat())
        self.assertEqual(self.errors, [])

    def test_activity_validation_inline(self):
        self.select_demo()
        self.app.open_activity_form("create")
        window = self.activity_window()
        window.inline_fields["activity_date"].value.set("20010912")
        window.inline_fields["cost"].value.set("abc")
        button = next(child for child in window.activity_form.winfo_children() if isinstance(child, ttk.Button))
        with patch("app.ui.messagebox.showerror") as error:
            button.invoke()
            error.assert_not_called()
        for field in ("title", "activity_date", "cost"):
            self.assertTrue(window.inline_fields[field].error.get())
        self.assertTrue(window.winfo_exists())

    def test_payment_validation_inline(self):
        self.select_demo()
        self.app.inline_fields["last_payment"].value.set("20261005")
        self.app.inline_fields["payment_amount"].value.set("abc")
        with patch("app.ui.messagebox.showwarning") as warning:
            self.app.register_payment()
            warning.assert_not_called()
        for field in ("last_payment", "payment_amount"):
            self.assertTrue(self.app.inline_fields[field].error.get())

    def test_activity_delete_refreshes_main_date(self):
        student_id = self.select_demo()
        create_activity_for_students([student_id], "Actividad Demo", "Otro", date.today().isoformat())
        self.app.students = load_students_from_db()
        self.app.refresh_listbox()
        self.app.refresh_student_activities(student_id)
        self.app.activities_tree.selection_set(self.app.activities_tree.get_children()[0])
        with patch("app.ui.messagebox.askyesno", return_value=True):
            self.app.remove_student_activity()
        self.assertEqual(self.app.listbox.set(str(student_id), "activity"), "")

    def test_activity_edit_refreshes_main_date(self):
        from datetime import timedelta
        student_id = self.select_demo()
        create_activity_for_students([student_id], "Actividad Demo", "Otro", date.today().isoformat())
        self.app.open_activity_form("edit", activity=get_activities_by_student(student_id)[0])
        window = self.activity_window()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        window.inline_fields["activity_date"].value.set(tomorrow)
        next(child for child in window.activity_form.winfo_children() if isinstance(child, ttk.Button)).invoke()
        self.assertEqual(self.app.listbox.set(str(student_id), "activity"), tomorrow)

    def test_png_certificate_preview_does_not_verify(self):
        from app.certificate_service import attach_certificate
        student_id = self.select_demo()
        source = Path(database.DATA_FOLDER) / "synthetic.png"
        image = tk.PhotoImage(width=2, height=2)
        image.put("white", to=(0, 0, 2, 2))
        image.write(str(source), format="png")
        attach_certificate(student_id, str(source), "2026-01-01")
        self.app.students = load_students_from_db()
        self.app.refresh_listbox()
        self.app.load_student_into_form(self.app.students_by_id[student_id])
        self.assertIsNotNone(self.app.cert_preview_image)
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")

    def test_pdf_certificate_preserves_unverified_state(self):
        import time
        student_id = self.select_demo()
        source = Path(database.DATA_FOLDER) / "synthetic.pdf"
        source.write_bytes(b"%PDF-1.4\n% Synthetic test only\n%%EOF\n")
        with patch("app.ui.filedialog.askopenfilename", return_value=str(source)):
            self.app.attach_certificate()
        deadline = time.monotonic() + 5
        while self.app.tasks.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertFalse(self.app.tasks.busy)
        self.assertTrue(self.app.current_cert_path.endswith(".pdf"))
        self.assertFalse(self.app.has_medical_var.get())
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")
        self.assertIsNone(self.app.cert_preview_image)

    def test_activity_scroll_small_window_and_wheel(self):
        self.app.open_activity_form("create")
        window = self.activity_window()
        window.geometry("480x280")
        self.root.update()
        canvas = window.scroll_form.canvas
        self.assertLess(canvas.yview()[1], 1)
        entry = window.inline_fields["title"].entry
        entry.event_generate("<MouseWheel>", delta=-120)
        self.root.update()
        self.assertGreater(canvas.yview()[0], 0)
        window.scroll_form.scrollbar.set(*canvas.yview())
        canvas.yview_moveto(1)
        self.root.update()
        self.assertAlmostEqual(canvas.yview()[1], 1, places=2)
        self.assertEqual(self.errors, [])

    def test_activity_keyboard_focus_reveals_save_button(self):
        self.app.open_activity_form("create")
        window = self.activity_window()
        window.geometry("480x280")
        self.root.update()
        button = next(child for child in window.activity_form.winfo_children() if isinstance(child, ttk.Button))
        button.focus_force()
        self.root.update()
        self.assertGreater(window.scroll_form.canvas.yview()[0], 0)
        self.assertEqual(self.errors, [])

    def test_picker_confirm_and_leap_year(self):
        self.app.open_birth_date_picker()
        picker = next(child for child in self.root.winfo_children() if isinstance(child, BirthDatePicker))
        self.assertEqual(self.app.entry_birth_date.get(), "")
        picker.year.set(2000)
        picker.month.set(2)
        picker.day.set(29)
        picker.update_days()
        picker.confirm()
        self.assertEqual(self.app.entry_birth_date.get(), "2000-02-29")

    def test_picker_rejects_future_and_cancel_preserves_value(self):
        picker = BirthDatePicker(self.root, "1900-01-01", self.app.inline_fields["birth_date"].value.set)
        picker.year.set(date.today().year + 1)
        picker.confirm()
        self.assertIn("futura", picker.error.get())
        self.assertEqual(self.app.entry_birth_date.get(), "")
        picker.destroy()

    def test_multiselect_click_toggle_and_keyboard(self):
        save_student_to_db({"name": "Alumno Prueba Uno"})
        save_student_to_db({"name": "Alumno Prueba Dos"})
        self.app.students = load_students_from_db()
        self.app.open_group_activity_selection()
        window = self.activity_window()
        selector = next(child for child in window.winfo_children() if isinstance(child, tk.Listbox))
        self.root.update()
        def click(index):
            x, y, width, height = selector.bbox(index)
            selector.event_generate("<ButtonPress-1>", x=x + 2, y=y + height // 2)
            selector.event_generate("<ButtonRelease-1>", x=x + 2, y=y + height // 2)
            self.root.update()
        click(0)
        click(1)
        self.assertEqual(selector.curselection(), (0, 1))
        click(0)
        self.assertEqual(selector.curselection(), (1,))
        selector.focus_force()
        selector.activate(0)
        selector.event_generate("<KeyPress-space>")
        self.root.update()
        self.assertEqual(selector.curselection(), (0, 1))
        selector.event_generate("<KeyPress-Down>")
        self.root.update()
        self.assertEqual(selector.index("active"), 1)
        self.assertEqual(self.errors, [])

    def test_all_main_dates_share_picker_and_click(self):
        from app.date_picker import DatePicker
        from app.form_widgets import InlineDateEntry
        for field in ("birth_date", "last_payment", "medical_date"):
            control = self.app.inline_fields[field]
            self.assertIsInstance(control, InlineDateEntry)
            control.entry.event_generate("<Button-1>", x=2, y=2)
            self.assertIsInstance(control.picker, DatePicker)
            same = control.open_picker()
            self.assertIs(same, control.picker)
            same.destroy()

    def test_activity_date_picker_changes_value_and_month_navigation(self):
        self.app.open_activity_form("create")
        window = self.activity_window()
        control = window.inline_fields["activity_date"]
        control.button.invoke()
        picker = control.picker
        picker.year.set(2030)
        picker.month.set(2)
        picker.day.set(28)
        picker.update_days()
        picker.confirm()
        self.assertEqual(control.value.get(), "2030-02-28")
        self.assertFalse(picker.winfo_exists())

    def test_picker_clamps_leap_day_and_certificate_future(self):
        control = self.app.inline_fields["medical_date"]
        original = control.value.get()
        picker = control.open_picker()
        picker.year.set(2000)
        picker.month.set(2)
        picker.day.set(29)
        picker.update_days()
        self.assertEqual(picker.day.get(), "29")
        picker.year.set(1900)
        picker.update_days()
        self.assertEqual(picker.day.get(), "28")
        picker.year.set(date.today().year + 1)
        picker.confirm()
        self.assertIn("futura", picker.error.get())
        self.assertEqual(control.value.get(), original)
        picker.year.set(2000)
        picker.day.set(29)
        picker.confirm()
        self.assertEqual(control.value.get(), "2000-02-29")

    def test_live_remaining_and_overpayment_blocks_save(self):
        self.select_demo()
        self.app.open_activity_form("create")
        window = self.activity_window()
        window.inline_fields["title"].value.set("Actividad Demo")
        window.inline_fields["cost"].value.set("1200")
        window.inline_fields["paid_amount"].value.set("400")
        self.assertEqual(window.remaining_balance.get(), "$800.00")
        self.assertTrue(window.remaining_entry.instate(["readonly"]))
        window.inline_fields["paid_amount"].value.set("1200")
        self.assertEqual(window.remaining_balance.get(), "$0.00")
        window.inline_fields["paid_amount"].value.set("1400")
        self.assertEqual(window.remaining_balance.get(), "")
        self.assertEqual(window.inline_fields["paid_amount"].error.get(), "El monto pagado no puede ser mayor al costo total.")
        button = next(child for child in window.activity_form.winfo_children() if isinstance(child, ttk.Button))
        with patch("app.ui.messagebox.showerror") as error:
            button.invoke()
            error.assert_not_called()
        self.assertTrue(window.winfo_exists())
        self.assertEqual(get_activities_by_student(self.app.selected_student_id), [])
        window.inline_fields["cost"].value.set("1400")
        self.assertEqual(window.inline_fields["paid_amount"].error.get(), "")
        self.assertEqual(window.remaining_balance.get(), "$0.00")
        button.invoke()
        saved = get_activities_by_student(self.app.selected_student_id)[0]
        self.assertEqual(saved["cost"], 1400)
        self.assertEqual(saved["paid_amount"], 1400)
        self.assertEqual(saved["attendance_status"], "registered")

    def test_invalid_money_inline_and_decimal_balance(self):
        self.app.open_activity_form("create")
        window = self.activity_window()
        for field, value in (("cost", "-20"), ("paid_amount", "-20"), ("cost", "abc"), ("paid_amount", "12.999"), ("cost", "")):
            window.inline_fields["cost"].value.set("1200")
            window.inline_fields["paid_amount"].value.set("0")
            window.inline_fields[field].value.set(value)
            self.assertTrue(window.inline_fields[field].error.get())
            self.assertEqual(window.remaining_balance.get(), "")
        window.inline_fields["cost"].value.set("0.30")
        window.inline_fields["paid_amount"].value.set("0.10")
        self.assertEqual(window.remaining_balance.get(), "$0.20")

    def test_medical_autosave_refreshes_immediately_and_preserves_draft(self):
        student_id = self.select_demo()
        self.app.listbox.selection_set(str(student_id))
        self.root.update()
        self.app.notebook.select(self.app.tab_medical)
        self.app.inline_fields["medical_date"].value.set("2026-10-01")
        self.app.entry_phone.insert(0, "+1 (202) 555-0123")
        self.app.medical_checkbox.invoke()
        self.root.update()
        self.assertTrue(load_students_from_db()[0]["has_medical"])
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "✓")
        self.assertEqual(self.app.entry_phone.get(), "+1 (202) 555-0123")
        self.assertEqual(load_students_from_db()[0]["phone"], "")
        self.assertEqual(self.app.notebook.select(), str(self.app.tab_medical))
        self.app.medical_checkbox.invoke()
        self.assertFalse(load_students_from_db()[0]["has_medical"])
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")

    def test_medical_autosave_rolls_back_checkbox_on_sql_failure(self):
        import sqlite3
        student_id = self.select_demo()
        with patch("app.ui.set_medical_verification", side_effect=sqlite3.OperationalError("synthetic failure")), patch("app.ui.messagebox.showerror") as error, patch("app.ui.log_event") as logged:
            self.app.medical_checkbox.invoke()
            error.assert_called_once()
            logged.assert_called_once()
        self.assertFalse(self.app.has_medical_var.get())
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "")
        self.assertFalse(load_students_from_db()[0]["has_medical"])

    def test_medical_empty_or_future_date_inline(self):
        self.select_demo()
        for value in ("", "2999-01-01"):
            self.app.inline_fields["medical_date"].value.set(value)
            with patch("app.ui.messagebox.showerror") as error:
                self.app.medical_checkbox.invoke()
                error.assert_not_called()
            self.assertFalse(self.app.has_medical_var.get())
            self.assertTrue(self.app.inline_fields["medical_date"].error.get())
            self.assertFalse(load_students_from_db()[0]["has_medical"])

    def test_medical_new_student_and_programmatic_load_do_not_autosave(self):
        with patch("app.ui.set_medical_verification") as save:
            self.app.medical_checkbox.invoke()
            self.assertFalse(self.app.has_medical_var.get())
            self.assertTrue(self.app.verification_error.get())
            self.select_demo()
            save.assert_not_called()

    def test_unverify_with_invalid_date_and_failure_restores_checked(self):
        import sqlite3
        student_id = self.select_demo()
        self.app.medical_checkbox.invoke()
        self.app.inline_fields["medical_date"].value.set("")
        with patch("app.ui.set_medical_verification", side_effect=sqlite3.OperationalError("synthetic failure")), patch("app.ui.messagebox.showerror"):
            self.app.medical_checkbox.invoke()
        self.assertTrue(self.app.has_medical_var.get())
        self.assertEqual(self.app.listbox.set(str(student_id), "medical"), "✓")
        self.app.medical_checkbox.invoke()
        self.assertFalse(load_students_from_db()[0]["has_medical"])

    def test_picker_uses_dark_palette_and_compact_window(self):
        self.app.toggle_dark_mode()
        picker = self.app.inline_fields["medical_date"].open_picker()
        self.assertEqual(picker.cget("bg"), self.app.style.lookup("TFrame", "background"))
        self.assertLess(picker.winfo_reqwidth(), 500)
        self.assertLess(picker.winfo_reqheight(), 400)
