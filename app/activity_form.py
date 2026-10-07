"""Formulario desplazable de actividades; validación y persistencia en servicios."""
import tkinter as tk
from tkinter import ttk
from datetime import date
from app.activity_service import create_activity_for_students, update_student_activity, validate_activity_field, activity_amounts
from app.form_widgets import InlineEntry, InlineDateEntry, ScrollableFrame
from app.errors import ValidationError, FieldValidationError
from app.student_service import load_students_from_db
from app.validation import activity_status_label, activity_status_options, format_money, bounded_text


class ActivityFormMixin:
    """Separa el diálogo de actividades del diseño de la ventana principal."""
    def open_activity_form(self, mode: str, activity=None, selected_student_ids=None):
        is_edit = mode == "edit"
        is_group = selected_student_ids is not None and len(selected_student_ids) > 1
        # Los destinatarios quedan fijados aunque cambie la selección de la ventana principal.
        recipients = tuple(selected_student_ids) if selected_student_ids is not None else (self.selected_student_id,)

        window = tk.Toplevel(self.root)
        window.title("Editar actividad" if is_edit else ("Actividad grupal" if is_group else "Agregar actividad"))
        window.geometry(f"580x{min(620, max(280, self.root.winfo_screenheight() - 120))}")
        window.minsize(420, 280)
        window.resizable(True, True)

        scroll = ScrollableFrame(window)
        scroll.grid(row=0, column=0, sticky="nsew")
        form = scroll.content
        window.activity_form = form
        window.scroll_form = scroll
        controls = {}
        window.inline_fields = controls

        def field(name):
            control = InlineDateEntry(form, kind="activity") if name == "activity_date" else InlineEntry(form, lambda value: validate_activity_field(name, value))
            controls[name] = control
            return control.entry

        window.columnconfigure(0, weight=1)
        window.rowconfigure(0, weight=1)

        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="Título:").grid(row=0, column=0, sticky="w", pady=(0, 8))
        entry_title = field("title")
        controls["title"].grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Tipo:").grid(row=1, column=0, sticky="w", pady=(0, 8))
        combo_type = ttk.Combobox(
            form,
            values=["Torneo", "Convivio", "Examen", "Seminario", "Campamento", "Otro"],
            state="readonly"
        )
        combo_type.grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Fecha:").grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 8)
        )
        entry_date = field("activity_date")
        controls["activity_date"].grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Lugar:").grid(row=4, column=0, sticky="w", pady=(0, 8))
        entry_location = field("location")
        controls["location"].grid(row=4, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Costo total:").grid(row=5, column=0, sticky="w", pady=(0, 8))
        entry_cost = field("cost")
        controls["cost"].grid(row=5, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Monto pagado:").grid(row=6, column=0, sticky="w", pady=(0, 8))
        entry_paid = field("paid_amount")
        controls["paid_amount"].grid(row=6, column=1, sticky="ew", pady=(0, 8))

        window.remaining_balance = tk.StringVar(window)
        ttk.Label(form, text="Restante:").grid(row=7, column=0, sticky="w", pady=(0, 8))
        window.remaining_entry = ttk.Entry(form, textvariable=window.remaining_balance, state="readonly")
        window.remaining_entry.grid(row=7, column=1, sticky="ew", pady=(0, 8))

        def update_balance():
            for name in ("cost", "paid_amount"):
                controls[name].show_error("")
            try:
                amounts = activity_amounts(controls["cost"].value.get(), controls["paid_amount"].value.get())
            except FieldValidationError as error:
                window.remaining_balance.set("")
                for name, message in error.errors.items():
                    controls[name].show_error(message)
                return None
            window.remaining_balance.set(format_money(amounts[2]))
            return amounts

        controls["cost"].on_change = controls["paid_amount"].on_change = update_balance

        ttk.Label(form, text="Estado:").grid(row=8, column=0, sticky="w", pady=(0, 8))
        combo_status = ttk.Combobox(
            form,
            values=[label for label, _ in activity_status_options()],
            state="readonly"
        )
        combo_status.grid(row=8, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="Notas:").grid(row=9, column=0, sticky="nw", pady=(0, 8))
        text_notes = tk.Text(form, height=5, wrap="word")
        text_notes.grid(row=9, column=1, sticky="ew", pady=(0, 8))

        note_error = tk.StringVar(window)
        ttk.Label(form, textvariable=note_error, style="Error.TLabel", wraplength=300).grid(row=10, column=1, sticky="w")

        if is_edit and activity is not None:
            entry_title.insert(0, activity["title"] or "")
            combo_type.set(activity["activity_type"] or "Torneo")
            entry_date.insert(0, activity["activity_date"] or date.today().strftime("%Y-%m-%d"))
            entry_location.insert(0, activity["location"] or "")
            entry_cost.insert(0, str(activity["cost"] or 0))
            entry_paid.insert(0, str(activity["paid_amount"] or 0))
            combo_status.set(activity_status_label(activity["attendance_status"]))

            note_value = activity["student_activity_notes"] or activity["activity_notes"] or ""
            text_notes.insert("1.0", note_value)
        else:
            combo_type.set("Torneo")
            entry_date.insert(0, date.today().strftime("%Y-%m-%d"))
            entry_cost.insert(0, "0")
            entry_paid.insert(0, "0")
            combo_status.set("Pendiente")

        def save_activity():
            title = entry_title.get().strip()
            activity_type = combo_type.get().strip()
            activity_date = entry_date.get().strip()
            location = entry_location.get().strip()
            status_label = combo_status.get().strip()
            notes = text_notes.get("1.0", tk.END).strip()
            status = next((value for label, value in activity_status_options() if label == status_label), "registered")

            valid = [control.validate() for control in controls.values()]
            amounts = update_balance()
            try:
                bounded_text(notes, "Notas")
                note_error.set("")
            except ValidationError as error:
                note_error.set(str(error))
                return
            if not all(valid) or amounts is None:
                return
            cost, paid_amount, _ = amounts

            try:
                if is_edit:
                    update_student_activity(
                        student_activity_id=activity["student_activity_id"],
                        title=title,
                        activity_type=activity_type,
                        activity_date=activity_date,
                        location=location,
                        cost=cost,
                        paid_amount=paid_amount,
                        attendance_status=status,
                        notes=notes
                    )
                else:
                    create_activity_for_students(
                        student_ids=list(recipients), title=title,
                        activity_type=activity_type, activity_date=activity_date,
                        location=location, cost=cost, paid_amount=paid_amount,
                        attendance_status=status, notes=notes)

            except FieldValidationError as error:
                for name, message in error.errors.items():
                    controls[name].show_error(message)
                return
            except Exception as error:
                self.show_operation_error(error)
                return

            self.students = load_students_from_db()
            self.refresh_listbox()
            if self.selected_student_id is not None:
                self.refresh_student_activities(self.selected_student_id)
            self.status.set("Actividad actualizada" if is_edit else "Actividad guardada")

            window.destroy()

        ttk.Button(
            form,
            text="Guardar cambios" if is_edit else "Guardar actividad",
            command=save_activity
        ).grid(row=11, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        scroll.bind_content()
