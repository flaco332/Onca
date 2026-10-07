import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
from datetime import date

from app.paths import APP_NAME
from app import database
from pathlib import Path
from app.theme import apply_theme
from app.activity_form import ActivityFormMixin
from app.background_tasks import BackgroundTasks
from app.errors import ValidationError, BackupError, FieldValidationError
from app.form_widgets import InlineEntry, InlineDateEntry
from app.student_options import BELT_RANKS
from app.logging_config import log_event
from app.version import __version__
from app.student_service import load_students_from_db, save_student_to_db, delete_student_from_db, validate_student_field, medical_indicator
from app.certificate_service import attach_certificate, certificate_path, remove_certificates, set_medical_verification
from app.payment_service import (
    add_payment,
    get_payments_by_student,
    update_payment,
    delete_payment,
)
from app.activity_service import (
    get_activities_by_student,
    delete_student_activity,
)
from app.logic import days_until_payment, pending_or_overdue_students
from app.validation import (
    activity_status_label,
    parse_amount,
    parse_iso_date,
    parse_certificate_date,
    format_money,
    remaining_balance,
)


class StudentApp(ActivityFormMixin):
    """Tk presentation and state. Services own validation and persistence."""
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)

        self.dark_mode = False
        self.style = ttk.Style()

        self.style.theme_use("clam")

        self.status = tk.StringVar(value="Listo")
        self.tasks = BackgroundTasks(root, self.status, self.set_busy)
        self.root.protocol("WM_DELETE_WINDOW", self.request_close)
        self.students = load_students_from_db()
        self.visible_students = []
        self.visible_payments = []
        self.activities_by_id = {}
        self.current_cert_path = ""
        self.cert_preview_image = None
        self.selected_student_id = None

        self.inline_fields = {}
        self.create_widgets()
        self.apply_theme()
        self.clear_form()
        self.refresh_listbox()
        self.show_pending_reminder()
        self.create_menu()

    def create_widgets(self):
        main = ttk.Frame(self.root, padding=12, style="Main.TFrame")
        main.grid(row=0, column=0, sticky="nsew")

        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(main, text="Alumnos", padding=14, style="Card.TLabelframe")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16), pady=(0, 6))

        self.listbox = ttk.Treeview(list_frame, columns=("id", "name", "due", "medical", "activity"), show="headings", selectmode="browse")
        for column, title, width in (("id", "ID", 45), ("name", "Alumno", 160), ("due", "Pago", 85), ("medical", "V med", 58), ("activity", "Actividad", 90)):
            self.listbox.heading(column, text=title, anchor="center")
            self.listbox.column(column, width=width, minwidth=58 if column == "medical" else 40, stretch=column == "name", anchor="center" if column == "medical" else "w")
        self.listbox.grid(row=0, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
        self.listbox.bind("<<TreeviewSelect>>", self.on_student_selected)
        self.listbox.bind("<Button-1>", self.on_listbox_click)

        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 4), pady=(0, 6))
        self.listbox.config(yscrollcommand=scroll.set)

        horizontal = ttk.Scrollbar(list_frame, orient="horizontal", command=self.listbox.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.listbox.configure(xscrollcommand=horizontal.set)

        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        right_frame = ttk.Frame(main, style="Main.TFrame")
        right_frame.grid(row=0, column=1, sticky="nsew")

        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)

        top_bar = ttk.Frame(right_frame, style="Main.TFrame")
        top_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_bar.columnconfigure(0, weight=1)
        top_bar.columnconfigure(1, weight=0)

        self.label_selected_student = ttk.Label(
            top_bar,
            text="Nuevo alumno",
            style="Title.TLabel"
        )
        self.label_selected_student.grid(row=0, column=0, sticky="w")
        
        self.button_dark_mode = ttk.Button(
            top_bar,
            text="Modo oscuro",
            command=self.toggle_dark_mode,
            style="Accent.TButton"
        )
        self.button_dark_mode.grid(row=0, column=1, sticky="e")

        self.notebook = ttk.Notebook(right_frame, style="Custom.TNotebook")
        self.notebook.grid(row=1, column=0, sticky="nsew")

        self.tab_general = ttk.Frame(self.notebook, padding=12)
        self.tab_payments = ttk.Frame(self.notebook, padding=12)
        self.tab_medical = ttk.Frame(self.notebook, padding=12)
        self.tab_activities = ttk.Frame(self.notebook, padding=12)

        self.notebook.add(self.tab_general, text="Datos generales")
        self.notebook.add(self.tab_payments, text="Pagos")
        self.notebook.add(self.tab_medical, text="Médico")
        self.notebook.add(self.tab_activities, text="Actividades")

        self.create_general_tab()
        self.create_payments_tab()
        self.create_medical_tab()
        self.create_activities_tab()

        main.columnconfigure(0, weight=1, minsize=260)
        main.columnconfigure(1, weight=4, minsize=560)
        main.rowconfigure(0, weight=1)
        ttk.Label(main, textvariable=self.status, style="Status.TLabel").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def create_inline_entry(self, parent, field, validator=None):
        control = InlineEntry(parent, validator or (lambda value: validate_student_field(field, value)))
        self.inline_fields[field] = control
        return control.entry

    def create_general_tab(self):
        self.tab_general.columnconfigure(0, weight=1)
        self.tab_general.rowconfigure(2, weight=1)

        student_frame = ttk.LabelFrame(
            self.tab_general,
            text="Información del alumno",
            padding=10
        )
        student_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        student_frame.columnconfigure(1, weight=1)
        student_frame.columnconfigure(3, weight=1)

        ttk.Label(student_frame, text="Nombre *:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_name = self.create_inline_entry(student_frame, "first_name")
        self.inline_fields["first_name"].grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(student_frame, text="Apellidos:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_last_name = self.create_inline_entry(student_frame, "last_name")
        self.inline_fields["last_name"].grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(student_frame, text="Teléfono:").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_phone = self.create_inline_entry(student_frame, "phone")
        self.inline_fields["phone"].grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(student_frame, text="Fecha de Nacimiento:").grid(
            row=3, column=0, sticky="w", padx=(0, 8), pady=(0, 4)
        )
        self.entry_birth_date = self.create_date_entry(student_frame, "birth_date", "birth", optional=True)
        self.inline_fields["birth_date"].grid(
            row=3, column=1, columnspan=3, sticky="ew", pady=(0, 4)
        )

        emergency_frame = ttk.LabelFrame(
            self.tab_general,
            text="Contacto de emergencia",
            padding=10
        )
        emergency_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        emergency_frame.columnconfigure(1, weight=1)
        emergency_frame.columnconfigure(3, weight=1)

        ttk.Label(emergency_frame, text="Nombre:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_emergency_contact_name = self.create_inline_entry(emergency_frame, "emergency_contact_name")
        self.inline_fields["emergency_contact_name"].grid(
            row=0, column=1, sticky="ew", padx=(0, 14), pady=(0, 8)
        )

        ttk.Label(emergency_frame, text="Teléfono:").grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_emergency_contact_phone = self.create_inline_entry(emergency_frame, "emergency_contact_phone")
        self.inline_fields["emergency_contact_phone"].grid(
            row=0, column=3, sticky="ew", pady=(0, 8)
        )

        sport_frame = ttk.LabelFrame(
            self.tab_general,
            text="Taekwondo y observaciones",
            padding=15
        )
        sport_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        sport_frame.columnconfigure(1, weight=1)
        sport_frame.rowconfigure(1, weight=1)

        ttk.Label(sport_frame, text="Cinta/grado:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )

        self.combo_belt_rank = ttk.Combobox(
            sport_frame,
            values=BELT_RANKS,
            state="readonly"
        )
        self.combo_belt_rank.grid(
            row=0, column=1, sticky="ew", pady=(0, 8)
        )

        ttk.Label(sport_frame, text="Notas:").grid(
            row=1, column=0, sticky="nw", padx=(0, 8)
        )

        notes_frame = ttk.Frame(sport_frame)
        notes_frame.grid(row=1, column=1, sticky="nsew")

        notes_frame.columnconfigure(0, weight=1)
        notes_frame.rowconfigure(0, weight=1)

        self.text_notes = tk.Text(notes_frame, height=5, wrap="word")
        self.text_notes.grid(row=0, column=0, sticky="nsew")

        notes_scroll = ttk.Scrollbar(
            notes_frame,
            orient="vertical",
            command=self.text_notes.yview
        )
        notes_scroll.grid(row=0, column=1, sticky="ns")
        self.text_notes.config(yscrollcommand=notes_scroll.set)
        self.notes_error = tk.StringVar(self.root)
        ttk.Label(notes_frame, textvariable=self.notes_error, style="Error.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")
        self.text_notes.bind("<KeyRelease>", self.validate_notes)
        self.text_notes.bind("<FocusOut>", self.validate_notes)

        button_frame = ttk.Frame(self.tab_general)
        button_frame.grid(row=3, column=0, sticky="ew")

        button_frame.columnconfigure((0, 1), weight=1)

        self.button_save = ttk.Button(
            button_frame,
            text="Agregar alumno",
            command=self.add_or_update
        )
        self.button_save.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(
            button_frame,
            text="Eliminar alumno",
            command=self.delete
        ).grid(row=0, column=1, sticky="ew")

    def validate_notes(self, event=None):
        try:
            validate_student_field("notes", self.text_notes.get("1.0", tk.END))
            self.notes_error.set("")
        except ValidationError as error:
            self.notes_error.set(str(error))

    def open_birth_date_picker(self):
        return self.inline_fields["birth_date"].open_picker()

    def create_date_entry(self, parent, field, kind, *, optional=False):
        control = InlineDateEntry(parent, kind=kind, optional=optional)
        self.inline_fields[field] = control
        return control.entry

    def create_payments_tab(self):
        self.tab_payments.columnconfigure(0, weight=1)
        self.tab_payments.rowconfigure(1, weight=1)

        payment_frame = ttk.LabelFrame(
            self.tab_payments,
            text="Registrar pago",
            padding=10
        )
        payment_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        payment_frame.columnconfigure(1, weight=1)
        payment_frame.columnconfigure(3, weight=1)

        ttk.Label(payment_frame, text="Fecha pago:").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_last_payment = self.create_date_entry(payment_frame, "last_payment", "payment")
        self.inline_fields["last_payment"].grid(
            row=0, column=1, sticky="ew", padx=(0, 14), pady=(0, 8)
        )

        ttk.Label(payment_frame, text="Monto:").grid(
            row=0, column=2, sticky="w", padx=(0, 8), pady=(0, 8)
        )
        self.entry_payment_amount = self.create_inline_entry(payment_frame, "payment_amount", parse_amount)
        self.inline_fields["payment_amount"].grid(
            row=0, column=3, sticky="ew", pady=(0, 8)
        )

        ttk.Label(payment_frame, text="Método:").grid(
            row=1, column=0, sticky="w", padx=(0, 8)
        )
        self.combo_payment_method = ttk.Combobox(
            payment_frame,
            values=["Efectivo", "Transferencia", "Tarjeta", "Otro"],
            state="readonly"
        )
        self.combo_payment_method.grid(
            row=1, column=1, sticky="ew", padx=(0, 14)
        )
        self.combo_payment_method.set("Efectivo")

        self.label_pay = ttk.Label(
            payment_frame,
            text="Días para siguiente pago: -",
            foreground="blue"
        )
        self.label_pay.grid(row=1, column=2, columnspan=2, sticky="w")

        ttk.Button(
            payment_frame,
            text="Registrar pago",
            command=self.register_payment
        ).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(10, 0))

        history_frame = ttk.LabelFrame(
            self.tab_payments,
            text="Historial de pagos",
            padding=10
        )
        history_frame.grid(row=1, column=0, sticky="nsew")

        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)

        self.payments_listbox = tk.Listbox(history_frame, height=8)
        self.payments_listbox.grid(row=0, column=0, sticky="nsew")
        self.payments_listbox.bind("<<ListboxSelect>>", self.on_payment_selected)

        payments_scroll = ttk.Scrollbar(
            history_frame,
            orient="vertical",
            command=self.payments_listbox.yview
        )
        payments_scroll.grid(row=0, column=1, sticky="ns")
        self.payments_listbox.config(yscrollcommand=payments_scroll.set)

        payment_buttons = ttk.Frame(history_frame)
        payment_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        payment_buttons.columnconfigure((0, 1), weight=1)

        ttk.Button(
            payment_buttons,
            text="Modificar pago seleccionado",
            command=self.modify_selected_payment
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(
            payment_buttons,
            text="Eliminar pago seleccionado",
            command=self.delete_selected_payment
        ).grid(row=0, column=1, sticky="ew")

    def create_medical_tab(self):
        self.tab_medical.columnconfigure(0, weight=1)
        self.tab_medical.rowconfigure(0, weight=1)

        medical_frame = ttk.LabelFrame(
            self.tab_medical,
            text="Certificado médico",
            padding=10
        )
        medical_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        medical_frame.columnconfigure(1, weight=1)
        medical_frame.rowconfigure(6, weight=1)

        self.has_medical_var = tk.BooleanVar()

        self.medical_checkbox = ttk.Checkbutton(
            medical_frame,
            text="Verificado médico",
            variable=self.has_medical_var, command=self.autosave_medical_verification
        )
        self.medical_checkbox.grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.verification_error = tk.StringVar(self.root)
        ttk.Label(medical_frame, textvariable=self.verification_error, style="Error.TLabel", wraplength=280).grid(row=0, column=1, sticky="w")

        ttk.Label(medical_frame, text="Fecha certificado:").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )

        self.entry_medical_date = self.create_date_entry(medical_frame, "medical_date", "certificate")
        self.inline_fields["medical_date"].grid(row=1, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(
            medical_frame,
            text="Usar fecha de hoy",
            command=self.set_today_medical_date
        ).grid(row=3, column=1, sticky="w", pady=(0, 8))

        ttk.Label(medical_frame, text="Archivo:").grid(
            row=4, column=0, sticky="w", padx=(0, 8), pady=(0, 8)
        )

        ttk.Button(
            medical_frame,
            text="Seleccionar PNG/PDF...",
            command=self.attach_certificate
        ).grid(row=4, column=1, sticky="ew", pady=(0, 8))

        self.label_cert = ttk.Label(
            medical_frame,
            text="(ningún archivo seleccionado)",
            foreground="gray"
        )
        self.label_cert.grid(row=5, column=0, columnspan=2, sticky="w", pady=(0, 8))

        preview_frame = ttk.LabelFrame(
            medical_frame,
            text="Vista previa",
            padding=10
        )
        preview_frame.grid(row=6, column=0, columnspan=2, sticky="nsew")

        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        self.label_cert_preview = ttk.Label(
            preview_frame,
            text="Sin vista previa disponible",
            foreground="gray",
            anchor="center"
        )
        self.label_cert_preview.grid(row=0, column=0, sticky="nsew")

    def create_activities_tab(self):
        self.tab_activities.columnconfigure(0, weight=1)
        self.tab_activities.rowconfigure(0, weight=1)

        activities_frame = ttk.LabelFrame(
            self.tab_activities,
            text="Actividades extras del alumno",
            padding=10
        )
        activities_frame.grid(row=0, column=0, sticky="nsew")

        activities_frame.columnconfigure(0, weight=1)
        activities_frame.columnconfigure(1, weight=1)
        activities_frame.columnconfigure(2, weight=1)
        activities_frame.rowconfigure(0, weight=1)

        self.activities_tree = ttk.Treeview(
            activities_frame, columns=("date", "type", "location", "cost", "paid", "status"),
            show="headings", selectmode="browse", height=8
        )
        for column, title, width, anchor in (
            ("date", "Fecha", 105, "center"), ("type", "Tipo", 80, "w"),
            ("location", "Lugar", 130, "w"), ("cost", "Costo", 80, "e"),
            ("paid", "Pagado", 80, "e"), ("status", "Estado", 100, "center")
        ):
            self.activities_tree.heading(column, text=title, anchor="center")
            self.activities_tree.column(column, width=width, minwidth=width, anchor=anchor, stretch=column == "location")
        self.activities_tree.grid(
            row=0,
            column=0,
            columnspan=3,
            sticky="nsew",
            pady=(0, 8)
        )
        self.activities_tree.bind("<Double-Button-1>", self.open_selected_activity_window)
        self.activities_tree.bind("<<TreeviewSelect>>", self.show_activity_detail)

        activities_scroll = ttk.Scrollbar(
            activities_frame,
            orient="vertical",
            command=self.activities_tree.yview
        )
        activities_scroll.grid(row=0, column=3, sticky="ns")
        self.activities_tree.config(yscrollcommand=activities_scroll.set)
        self.activities_horizontal = ttk.Scrollbar(activities_frame, orient="horizontal", command=self.activities_tree.xview)
        self.activities_horizontal.grid(row=1, column=0, columnspan=3, sticky="ew")
        self.activities_tree.configure(xscrollcommand=self.update_activities_horizontal)

        self.activity_detail_title = tk.StringVar(value="Selecciona un alumno para ver sus actividades.")
        ttk.Label(activities_frame, textvariable=self.activity_detail_title).grid(row=2, column=0, columnspan=3, sticky="w", pady=(8, 4))
        self.activity_detail = tk.Text(activities_frame, height=4, width=1, wrap="word", state="disabled")
        self.activity_detail.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        detail_scroll = ttk.Scrollbar(activities_frame, orient="vertical", command=self.activity_detail.yview)
        detail_scroll.grid(row=3, column=3, sticky="ns", pady=(0, 8))
        self.activity_detail.configure(yscrollcommand=detail_scroll.set)

        ttk.Button(
            activities_frame,
            text="Agregar actividad",
            command=self.open_add_activity_window
        ).grid(row=4, column=0, sticky="ew", padx=(0, 8))

        ttk.Button(
            activities_frame,
            text="Ver / editar actividad",
            command=self.open_selected_activity_window
        ).grid(row=4, column=1, sticky="ew", padx=(0, 8))

        ttk.Button(
            activities_frame,
            text="Quitar actividad",
            command=self.remove_student_activity
        ).grid(row=4, column=2, sticky="ew", padx=(0, 8))

        ttk.Button(
            activities_frame,
            text="Actividad grupal",
            command=self.open_group_activity_selection
        ).grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))

    def refresh_listbox(self):
        """Keep identity stable across sorting; compute remaining days once."""
        selection = self.selected_student_id
        self.listbox.delete(*self.listbox.get_children())
        self.students_by_id = {student["student_id"]: student for student in self.students}
        ordered = sorted(((days_until_payment(student["last_payment_date"]), student) for student in self.students), key=lambda item: (item[0] is None, item[0] or 0))
        self.visible_students = [student for _, student in ordered]
        for remaining, student in ordered:
            state = "" if remaining is None else (f"Vencido {abs(remaining)} d" if remaining < 0 else f"{remaining} días")
            self.listbox.insert("", "end", iid=str(student["student_id"]), values=(student["student_id"], student["name"], state, medical_indicator(student), student["next_activity_date"]))
        if selection in self.students_by_id:
            self.listbox.selection_set(str(selection))

    def on_listbox_click(self, event):
        if not self.tasks.busy and not self.listbox.identify_row(event.y):
            self.listbox.selection_remove(self.listbox.selection())
            self.reset_form_for_new_student()
            return "break"
    
    def on_student_selected(self, event):
        selected = self.listbox.selection()
        if selected and not self.tasks.busy:
            student = self.students_by_id.get(int(selected[0]))
            if student is not None:
                self.load_student_into_form(student)

    def load_student_into_form(self, student):
        self.selected_student_id = student["student_id"]
        self.label_selected_student.config(text=student["name"])

        self.entry_name.delete(0, tk.END)
        self.entry_name.insert(0, student["first_name"])
        self.entry_last_name.delete(0, tk.END)
        self.entry_last_name.insert(0, student["last_name"])

        self.entry_phone.delete(0, tk.END)
        self.entry_phone.insert(0, student["phone"])

        self.entry_birth_date.delete(0, tk.END)
        self.entry_birth_date.insert(0, student.get("birth_date", ""))

        self.entry_emergency_contact_name.delete(0, tk.END)
        self.entry_emergency_contact_name.insert(0, student.get("emergency_contact_name", ""))

        self.entry_emergency_contact_phone.delete(0, tk.END)
        self.entry_emergency_contact_phone.insert(0, student.get("emergency_contact_phone", ""))

        self.combo_belt_rank.set(student.get("belt_rank", ""))

        self.text_notes.delete("1.0", tk.END)
        self.text_notes.insert("1.0", student.get("notes", ""))

        self.entry_last_payment.delete(0, tk.END)
        self.entry_last_payment.insert(0, student["last_payment_date"].isoformat() if student["last_payment_date"] else "")

        self.entry_medical_date.delete(0, tk.END)
        self.entry_medical_date.insert(0, student["medical_cert_date"].strftime("%Y-%m-%d"))

        self.has_medical_var.set(student["has_medical"])
        self.verification_error.set("")
        self.current_cert_path = student.get("medical_cert_path", "")

        if self.current_cert_path:
            self.label_cert.config(
                text=os.path.basename(self.current_cert_path),
                foreground="black"
            )
        else:
            self.label_cert.config(
                text="(ningún archivo seleccionado)",
                foreground="gray"
            )

        self.update_certificate_preview()

        remaining = days_until_payment(student["last_payment_date"])
        self.label_pay.config(text=f"Días para siguiente pago: {remaining if remaining is not None else '-'}")

        self.refresh_payment_history(student["student_id"])
        self.refresh_student_activities(student["student_id"])

        # Ensure save button reflects update mode
        self.button_save.config(text="Actualizar alumno")

    def refresh_payment_history(self, student_id: int):
        self.payments_listbox.delete(0, tk.END)
        self.visible_payments = []

        payments = get_payments_by_student(student_id)

        if not payments:
            self.payments_listbox.insert(tk.END, "Sin pagos registrados.")
            return

        for payment in payments:
            self.visible_payments.append(payment)

            line = (
                f"{payment['payment_date']} | "
                f"{format_money(payment['amount'])} | "
                f"{payment['method'] or 'Sin método'}"
            )

            self.payments_listbox.insert(tk.END, line)

    def get_selected_payment(self, show_warning=True):
        if not self.payments_listbox.curselection():
            if show_warning:
                messagebox.showwarning(APP_NAME, "Primero selecciona un pago del historial.")
            return None

        index = self.payments_listbox.curselection()[0]

        if index >= len(self.visible_payments):
            if show_warning:
                messagebox.showwarning(APP_NAME, "Selecciona un pago válido.")
            return None

        return self.visible_payments[index]

    def on_payment_selected(self, event):
        payment = self.get_selected_payment(show_warning=False)

        if payment is None:
            return

        self.entry_last_payment.delete(0, tk.END)
        self.entry_last_payment.insert(0, payment["payment_date"])

        self.entry_payment_amount.delete(0, tk.END)
        self.entry_payment_amount.insert(0, str(payment["amount"]))

        method = payment["method"] or "Efectivo"

        if method in ["Efectivo", "Transferencia", "Tarjeta", "Otro"]:
            self.combo_payment_method.set(method)
        else:
            self.combo_payment_method.set("Otro")

    def modify_selected_payment(self):
        payment = self.get_selected_payment()

        if payment is None:
            return

        payment_date = self.entry_last_payment.get().strip()
        amount_raw = self.entry_payment_amount.get().strip()
        method = self.combo_payment_method.get().strip()

        valid = [self.inline_fields[field].validate() for field in ("last_payment", "payment_amount")]
        if not all(valid):
            self.status.set("Revisa los campos del pago.")
            return
        parsed_date = date.fromisoformat(parse_iso_date(payment_date))
        amount = parse_amount(amount_raw)

        payment_month = parsed_date.strftime("%Y-%m")

        confirm = messagebox.askyesno(
            APP_NAME,
            "¿Seguro que deseas modificar este pago?"
        )

        if not confirm:
            return

        try:
            update_payment(
                payment_id=payment["payment_id"],
                amount=amount,
                payment_date=payment_date,
                payment_month=payment_month,
                method=method,
                notes=payment["notes"] or ""
            )
        except Exception as error:
            self.show_operation_error(error)
            return

        self.students = load_students_from_db()
        self.refresh_listbox()
        self.refresh_payment_history(self.selected_student_id)

        self.entry_payment_amount.delete(0, tk.END)

        remaining = days_until_payment(parsed_date)
        self.label_pay.config(text=f"Días para siguiente pago: {remaining if remaining is not None else '-'}")

        messagebox.showinfo(APP_NAME, "Pago modificado correctamente.")

    def delete_selected_payment(self):
        payment = self.get_selected_payment()

        if payment is None:
            return

        confirm = messagebox.askyesno(
            APP_NAME,
            f"¿Seguro que deseas eliminar el pago de {format_money(payment['amount'])} del {payment['payment_date']}?"
        )

        if not confirm:
            return

        try:
            delete_payment(payment["payment_id"])
        except Exception as error:
            self.show_operation_error(error)
            return

        self.students = load_students_from_db()
        self.refresh_listbox()
        self.refresh_payment_history(self.selected_student_id)

        self.entry_payment_amount.delete(0, tk.END)

        messagebox.showinfo(APP_NAME, "Pago eliminado correctamente.")

    def refresh_student_activities(self, student_id: int):
        selected = self.activities_tree.selection()
        self.activities_tree.delete(*self.activities_tree.get_children())
        activities = get_activities_by_student(student_id)
        self.activities_by_id = {str(activity["student_activity_id"]): activity for activity in activities}
        for activity in activities:
            self.activities_tree.insert("", "end", iid=str(activity["student_activity_id"]), values=(
                activity["activity_date"], activity["activity_type"], activity["location"] or "",
                format_money(activity["cost"]), format_money(activity["paid_amount"]),
                activity_status_label(activity["attendance_status"])
            ))
        # La selección sigue la participación por ID aunque cambie el orden del listado.
        if selected and selected[0] in self.activities_by_id:
            self.activities_tree.selection_set(selected[0])
        self.show_activity_detail()

    def update_activities_horizontal(self, first, last):
        self.activities_horizontal.set(first, last)
        if float(first) > 0 or float(last) < 1:
            self.activities_horizontal.grid()
        else:
            self.activities_horizontal.grid_remove()

    def show_activity_detail(self, event=None):
        activity = self.get_selected_activity(show_warning=False)
        self.activity_detail_title.set("Detalle de la actividad" if activity is not None else (
            "Selecciona una actividad para ver su título y notas." if self.activities_by_id else "Todavía no hay actividades registradas."
        ))
        lines = []
        if activity is not None:
            lines.append(f"Título: {activity['title']}")
            try:
                lines.append(f"Restante: {format_money(remaining_balance(activity['cost'] or 0, activity['paid_amount'] or 0))}")
            except ValidationError:
                lines.append("Saldo histórico: revisa los importes al editar.")
            for field, label in (("activity_notes", "Notas de actividad"), ("student_activity_notes", "Notas del alumno")):
                if activity[field]:
                    lines.append(f"{label}: {activity[field]}")
        self.activity_detail.configure(state="normal")
        self.activity_detail.delete("1.0", tk.END)
        self.activity_detail.insert("1.0", "\n".join(lines))
        self.activity_detail.configure(state="disabled")

    def get_selected_activity(self, show_warning=True):
        selection = self.activities_tree.selection()
        activity = self.activities_by_id.get(selection[0]) if selection else None
        if activity is None:
            if show_warning:
                messagebox.showwarning(APP_NAME, "Primero selecciona una actividad.")
            return None

        return activity

    def update_certificate_preview(self):
        self.cert_preview_image = None

        if not self.current_cert_path:
            self.label_cert_preview.config(
                text="Sin vista previa disponible",
                image="",
                foreground="gray"
            )
            return

        try:
            preview_path = certificate_path(self.current_cert_path)
        except ValidationError as error:
            self.show_operation_error(error)
            return
        if not preview_path.is_file():
            self.label_cert_preview.config(
                text="El archivo no existe o fue movido.",
                image="",
                foreground="red"
            )
            return

        ext = os.path.splitext(self.current_cert_path)[1].lower()

        if ext != ".png":
            self.label_cert_preview.config(
                text="Vista previa solo disponible para archivos PNG.",
                image="",
                foreground="gray"
            )
            return

        try:
            image = tk.PhotoImage(file=str(preview_path))

            max_width = 520
            max_height = 300

            width = image.width()
            height = image.height()

            scale_w = max(1, (width + max_width - 1) // max_width)
            scale_h = max(1, (height + max_height - 1) // max_height)
            scale = max(scale_w, scale_h)

            if scale > 1:
                image = image.subsample(scale, scale)

            self.cert_preview_image = image

            self.label_cert_preview.config(
                image=self.cert_preview_image,
                text=""
            )

        except Exception as error:
            log_event("unexpected_exception", error)
            self.label_cert_preview.config(
                text="No fue posible previsualizar este archivo.",
                image="",
                foreground="red"
            )

    def build_student_from_form(self):
        from app.student_service import validate_student
        needs_medical_date = self.current_cert_path or self.has_medical_var.get()
        if needs_medical_date and not self.inline_fields["medical_date"].validate():
            raise ValidationError("Revisa la fecha del certificado.")
        return validate_student({
            "student_id": self.selected_student_id,
            "first_name": self.entry_name.get(), "last_name": self.entry_last_name.get(), "phone": self.entry_phone.get(),
            "birth_date": self.entry_birth_date.get(),
            "emergency_contact_name": self.entry_emergency_contact_name.get(),
            "emergency_contact_phone": self.entry_emergency_contact_phone.get(),
            "belt_rank": self.combo_belt_rank.get(), "notes": self.text_notes.get("1.0", tk.END),
            "has_medical": self.has_medical_var.get(),
            "medical_cert_date": date.fromisoformat(parse_certificate_date(self.entry_medical_date.get().strip())) if needs_medical_date else date.today(),
            "medical_cert_path": self.current_cert_path,
        })

    def add_or_update(self):
        try:
            student = self.build_student_from_form()
        except FieldValidationError as error:
            for field, message in error.errors.items():
                if field in self.inline_fields:
                    self.inline_fields[field].show_error(message)
                elif field == "notes":
                    self.notes_error.set(message)
            self.status.set("Revisa los campos indicados.")
            return
        except ValidationError as error:
            self.status.set(str(error))
            return

        try:
            save_student_to_db(student)
        except Exception as error:
            self.show_operation_error(error)
            return

        self.students = load_students_from_db()
        self.refresh_listbox()
        self.clear_form()

        self.status.set("Alumno guardado")

    def attach_certificate(self):
        if self.selected_student_id is None:
            messagebox.showwarning(APP_NAME, "Guarda y selecciona al alumno antes de adjuntar un certificado.")
            return
        if not self.inline_fields["medical_date"].validate():
            return
        source = filedialog.askopenfilename(title="Seleccionar certificado", filetypes=[("PNG / PDF", "*.png *.pdf")])
        if not source:
            return
        student_id = self.selected_student_id
        issued = parse_certificate_date(self.entry_medical_date.get())
        def complete(reference):
            self.current_cert_path = reference
            self.inline_fields["medical_date"].value.set(issued)
            self.label_cert.config(text=os.path.basename(reference))
            self.students = load_students_from_db()
            self.refresh_listbox()
            self.update_certificate_preview()
            self.status.set("Certificado guardado")
        self.tasks.start("Guardando certificado…", lambda: attach_certificate(student_id, source, issued), complete, self.show_operation_error)

    def delete(self):
        if self.selected_student_id is None:
            return
        if not messagebox.askyesno(APP_NAME, "¿Dar de baja al alumno seleccionado? Su historial se conservará."):
            return
        try:
            delete_student_from_db(self.selected_student_id)
        except Exception as error:
            self.show_operation_error(error)
            return
        self.clear_form()
        self.students = load_students_from_db()
        self.refresh_listbox()
        self.status.set("Alumno dado de baja")

    def autosave_medical_verification(self):
        """Sincroniza solo la verificación, conservando pestaña y ediciones sin guardar."""
        student = self.students_by_id.get(self.selected_student_id)
        previous = student["has_medical"] if student is not None else False
        target = self.has_medical_var.get()
        self.verification_error.set("")
        if student is None or self.tasks.busy:
            self.has_medical_var.set(previous)
            self.verification_error.set("Guarda y selecciona el alumno antes de verificar." if student is None else "Espera a que termine la operación.")
            return
        if target and not self.inline_fields["medical_date"].validate():
            self.has_medical_var.set(previous)
            return
        issued = self.entry_medical_date.get() if target else ""
        try:
            set_medical_verification(self.selected_student_id, target, issued)
        except ValidationError as error:
            self.has_medical_var.set(previous)
            self.verification_error.set(str(error))
            return
        except Exception as error:
            self.has_medical_var.set(previous)
            self.show_operation_error(error)
            return
        student["has_medical"] = target
        if target:
            student["medical_cert_date"] = date.fromisoformat(issued)
        self.listbox.set(str(self.selected_student_id), "medical", medical_indicator(student))
        self.status.set("Verificación médica guardada")

    def clear_form(self):
        today = date.today().strftime("%Y-%m-%d")

        self.selected_student_id = None
        self.listbox.selection_remove(self.listbox.selection())
        self.button_save.configure(text="Agregar alumno")
        self.visible_payments = []
        self.activities_by_id = {}
        self.label_selected_student.config(text="Nuevo alumno")

        self.entry_name.delete(0, tk.END)
        self.entry_last_name.delete(0, tk.END)
        self.entry_phone.delete(0, tk.END)
        self.entry_birth_date.delete(0, tk.END)
        self.entry_emergency_contact_name.delete(0, tk.END)
        self.entry_emergency_contact_phone.delete(0, tk.END)
        self.combo_belt_rank.set("")
        self.text_notes.delete("1.0", tk.END)

        self.entry_last_payment.delete(0, tk.END)

        self.entry_payment_amount.delete(0, tk.END)
        self.combo_payment_method.set("Efectivo")

        self.entry_medical_date.delete(0, tk.END)
        self.entry_medical_date.insert(0, today)

        self.has_medical_var.set(False)
        self.verification_error.set("")
        self.current_cert_path = ""

        self.label_pay.config(text="Días para siguiente pago: -")
        self.label_cert.config(
            text="(ningún archivo seleccionado)",
            foreground="gray"
        )

        self.update_certificate_preview()

        self.payments_listbox.delete(0, tk.END)
        self.activities_tree.delete(*self.activities_tree.get_children())
        self.show_activity_detail()
        self.activity_detail_title.set("Selecciona un alumno para ver sus actividades.")
        for control in self.inline_fields.values():
            control.show_error("")
        self.notes_error.set("")

    def reset_form_for_new_student(self):
        """Reset identity and editable fields through one deterministic path."""
        if self.tasks.busy:
            return
        self.listbox.selection_remove(self.listbox.selection())
        self.clear_form()
        self.button_save.configure(text="Agregar alumno")
        self.entry_name.focus_set()

    def set_today_medical_date(self):
        self.entry_medical_date.delete(0, tk.END)
        self.entry_medical_date.insert(0, date.today().strftime("%Y-%m-%d"))

    def register_payment(self):
        if self.selected_student_id is None:
            messagebox.showwarning(APP_NAME, "Primero selecciona un alumno.")
            return

        payment_date = self.entry_last_payment.get().strip()
        amount_raw = self.entry_payment_amount.get().strip()
        method = self.combo_payment_method.get().strip()

        valid = [self.inline_fields[field].validate() for field in ("last_payment", "payment_amount")]
        if not all(valid):
            self.status.set("Revisa los campos del pago.")
            return
        parsed_date = date.fromisoformat(parse_iso_date(payment_date))
        amount = parse_amount(amount_raw)

        payment_month = parsed_date.strftime("%Y-%m")

        try:
            add_payment(
                student_id=self.selected_student_id,
                amount=amount,
                payment_date=payment_date,
                payment_month=payment_month,
                method=method,
                notes=""
            )
        except Exception as error:
            self.show_operation_error(error)
            return

        self.students = load_students_from_db()
        self.refresh_listbox()
        self.refresh_payment_history(self.selected_student_id)

        self.entry_payment_amount.delete(0, tk.END)

        remaining = days_until_payment(parsed_date)
        self.label_pay.config(text=f"Días para siguiente pago: {remaining if remaining is not None else '-'}")

        messagebox.showinfo(APP_NAME, "Pago registrado correctamente.")

    def open_add_activity_window(self):
        if self.selected_student_id is None:
            messagebox.showwarning(APP_NAME, "Primero selecciona un alumno.")
            return

        self.open_activity_form(mode="create")

    def open_group_activity_selection(self):
        if not self.students:
            messagebox.showwarning(APP_NAME, "No hay alumnos registrados.")
            return

        selection_window = tk.Toplevel(self.root)
        selection_window.title("Seleccionar alumnos")
        selection_window.geometry("420x460")
        selection_window.minsize(360, 400)

        ttk.Label(
            selection_window,
            text="Haz clic para marcar/desmarcar. Teclado: flechas y Espacio.", wraplength=340
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 8))

        listbox = tk.Listbox(
            selection_window,
            # El modo nativo alterna cada clic; Espacio y flechas siguen funcionando.
            selectmode="multiple",
            exportselection=False,
            height=18,
            width=42,
            font=("Segoe UI", 10)
        )
        listbox.grid(row=1, column=0, padx=12, pady=(0, 10), sticky="nsew")

        scrollbar = ttk.Scrollbar(selection_window, orient="vertical", command=listbox.yview)
        scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        listbox.config(yscrollcommand=scrollbar.set)

        selectable_students = list(self.students)
        for student in selectable_students:
            listbox.insert(tk.END, f"#{student['student_id']} · {student['name']}")

        selection_window.columnconfigure(0, weight=1)
        selection_window.rowconfigure(1, weight=1)

        def confirm_selection():
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning(APP_NAME, "Selecciona al menos un alumno.")
                return

            selected_student_ids = [selectable_students[index]["student_id"] for index in selected_indices]
            selection_window.destroy()
            self.open_activity_form(mode="create", selected_student_ids=selected_student_ids)

        ttk.Button(selection_window, text="Continuar", command=confirm_selection).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12)
        )

    def open_selected_activity_window(self, event=None):
        if self.selected_student_id is None:
            messagebox.showwarning(APP_NAME, "Primero selecciona un alumno.")
            return

        activity = self.get_selected_activity(show_warning=True)

        if activity is None:
            return

        self.open_activity_form(mode="edit", activity=activity)


    def remove_student_activity(self):
        if self.selected_student_id is None:
            messagebox.showwarning(APP_NAME, "Primero selecciona un alumno.")
            return

        activity = self.get_selected_activity(show_warning=True)

        if activity is None:
            return

        confirm = messagebox.askyesno(
            APP_NAME,
            f"¿Seguro que deseas quitar la actividad '{activity['title']}'?"
        )

        if not confirm:
            return

        try:
            delete_student_activity(activity["student_activity_id"])
        except Exception as error:
            self.show_operation_error(error)
            return

        self.students = load_students_from_db()
        self.refresh_listbox()
        self.refresh_student_activities(self.selected_student_id)
        self.status.set("Actividad quitada")

    def show_pending_reminder(self):
        pending = pending_or_overdue_students(self.students, warn_days=3)
        if pending:
            log_event("payment_reminder")
            self.status.set(f"{len(pending)} alumnos con pagos próximos o vencidos")

    def toggle_dark_mode(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()


    def apply_theme(self):
        apply_theme(self.root, self.style, self.dark_mode, vars(self))
        heading_font = tkfont.Font(root=self.root, font=self.style.lookup("Treeview.Heading", "font"))
        medical_width = max(58, heading_font.measure("V med") + 12)
        self.listbox.column("medical", width=medical_width, minwidth=medical_width)

    def show_operation_error(self, error: BaseException) -> None:
        """Keep sensitive technical exception values out of dialogs and logs."""
        log_event("unexpected_exception", error)
        self.status.set("No fue posible completar la operación")
        message = str(error) if isinstance(error, (ValidationError, BackupError)) else "No fue posible guardar los cambios. Intenta nuevamente."
        messagebox.showerror(APP_NAME, message)

    def set_busy(self, busy: bool) -> None:
        """Disable mutable widgets while a worker holds the data-operation lock."""
        if busy:
            self._disabled_widgets = []
            def disable(widget):
                if isinstance(widget, (ttk.Entry, ttk.Combobox, ttk.Button, ttk.Checkbutton, ttk.Treeview)):
                    self._disabled_widgets.append((widget, widget.state()))
                    widget.state(["disabled"])
                elif isinstance(widget, (tk.Text, tk.Listbox)):
                    self._disabled_widgets.append((widget, widget.cget("state")))
                    widget.configure(state="disabled")
                for child in widget.winfo_children():
                    disable(child)
            disable(self.root)
        else:
            for widget, original in getattr(self, "_disabled_widgets", []):
                if isinstance(widget, ttk.Widget):
                    widget.state(["!disabled"])
                    widget.state(original)
                else:
                    widget.configure(state=original)
            self._disabled_widgets = []

    def request_close(self) -> None:
        """Never abandon an active backup/restore/certificate operation."""
        if self.tasks.busy:
            self.status.set("Espera a que termine la operación antes de cerrar")
            return
        self.tasks.close()
        self.root.destroy()

    def create_menu(self) -> None:
        menu = tk.Menu(self.root)
        data = tk.Menu(menu, tearoff=False)
        data.add_command(label="Crear respaldo", command=self.backup_data)
        data.add_command(label="Validar respaldo", command=self.validate_data_backup)
        data.add_command(label="Restaurar en carpeta nueva…", command=self.restore_data)
        data.add_separator()
        data.add_command(label="Abrir certificado", command=self.open_certificate)
        data.add_command(label="Desvincular certificados", command=self.unlink_certificates)
        menu.add_cascade(label="Datos", menu=data)
        menu.add_command(label="Acerca de", command=lambda: messagebox.showinfo(APP_NAME, f"ONCA Alumnos {__version__}\nAplicación local de escritorio"))
        self.root.configure(menu=menu)

    def backup_data(self) -> None:
        from app.backups import create_backup
        self.tasks.start("Creando respaldo…", lambda: create_backup(Path(database.DB_PATH).parent),
                         lambda result: self.status.set("Respaldo completado y verificado"), self.show_operation_error)

    def validate_data_backup(self) -> None:
        if self.tasks.busy:
            return
        from app.backups import validate_backup
        folder = filedialog.askdirectory(title="Seleccionar respaldo")
        if folder:
            self.tasks.start("Validando respaldo…", lambda: validate_backup(folder),
                             lambda result: self.status.set("Respaldo válido"), self.show_operation_error)

    def restore_data(self) -> None:
        if self.tasks.busy:
            return
        from app.backups import restore_backup
        from datetime import datetime
        from uuid import uuid4
        folder = filedialog.askdirectory(title="Seleccionar respaldo a restaurar")
        if not folder or not messagebox.askyesno(APP_NAME, "Se respaldarán los datos actuales y se restaurará en una carpeta nueva. ¿Continuar?"):
            return
        root = Path(database.DB_PATH).parent
        destination = root.parent / ("OncaAlumnos-restored-" + datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid4().hex[:8])
        def complete(result):
            self.status.set("Respaldo restaurado; instalación actual conservada")
            messagebox.showinfo(APP_NAME, "Restauración verificada. Para usarla, inicia ONCA_DATA_DIR con esta carpeta:\n" + str(result))
        self.tasks.start("Restaurando respaldo…", lambda: restore_backup(folder, root, destination), complete, self.show_operation_error)

    def open_certificate(self) -> None:
        if self.tasks.busy or not self.current_cert_path:
            return
        try:
            path = certificate_path(self.current_cert_path)
            if not path.is_file():
                raise ValidationError("El archivo no está disponible.")
            # Supported desktop platform only. Path is validated, never a shell command.
            os.startfile(str(path))
        except Exception as error:
            self.show_operation_error(error)

    def unlink_certificates(self) -> None:
        if self.tasks.busy or self.selected_student_id is None:
            return
        if not messagebox.askyesno(APP_NAME, "¿Desvincular los certificados del alumno seleccionado? Los archivos se conservarán."):
            return
        try:
            remove_certificates(self.selected_student_id)
            self.current_cert_path = ""
            self.has_medical_var.set(False)
            self.label_cert.configure(text="Sin certificado")
            self.students = load_students_from_db()
            self.refresh_listbox()
            self.update_certificate_preview()
            self.status.set("Certificados desvinculados")
        except Exception as error:
            self.show_operation_error(error)
