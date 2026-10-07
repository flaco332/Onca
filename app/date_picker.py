"""Selector reutilizable Año → Mes → Día, sin dependencias externas."""
import calendar
from datetime import date
import tkinter as tk
from tkinter import ttk

from app.errors import ValidationError
from app.validation import parse_date_field


def date_from_parts(year: int, month: int, day: int, *, kind: str = "activity", today: date | None = None) -> str:
    """Valida también años bisiestos y conserva el formato usado por SQLite."""
    try:
        value = date(year, month, day).isoformat()
    except (ValueError, TypeError):
        raise ValidationError("Selecciona un año, mes y día válidos.") from None
    return parse_date_field(value, kind, today=today)


def birth_date_from_parts(year: int, month: int, day: int, *, today: date | None = None) -> str:
    return date_from_parts(year, month, day, kind="birth", today=today)


class DatePicker(tk.Toplevel):
    """Selector compacto; no cambia la entrada hasta confirmar una fecha válida."""

    def __init__(self, parent, current: str, on_selected, *, kind: str = "activity", anchor=None):
        super().__init__(parent)
        self.kind = kind
        self.title({"birth": "Fecha de nacimiento", "activity": "Fecha de actividad", "certificate": "Fecha de certificado", "payment": "Fecha de pago"}[kind])
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        today = date.today()
        try:
            initial = date.fromisoformat(parse_date_field(current, kind))
        except (ValidationError, ValueError):
            initial = date(2000, 1, 1) if kind == "birth" else today
        form = ttk.Frame(self, padding=16)
        form.pack(fill="both", expand=True)
        maximum_year = today.year if kind in {"birth", "certificate"} else min(9999, max(today.year + 20, initial.year))
        self.year = ttk.Combobox(form, width=8, values=tuple(range(maximum_year, min(1900, initial.year) - 1, -1)), state="readonly")
        self.month = ttk.Combobox(form, width=6, values=tuple(range(1, 13)), state="readonly")
        self.day = ttk.Combobox(form, width=6, state="readonly")
        for column, (label, control, value) in enumerate((("Año", self.year, initial.year), ("Mes", self.month, initial.month), ("Día", self.day, initial.day))):
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=4)
            control.grid(row=1, column=column, padx=4, pady=(4, 8))
            control.set(value)
        self.error = tk.StringVar(self)
        ttk.Label(form, textvariable=self.error, style="Error.TLabel", wraplength=280).grid(row=2, column=0, columnspan=3, sticky="w")
        self.year.bind("<<ComboboxSelected>>", self.update_days)
        self.month.bind("<<ComboboxSelected>>", self.update_days)
        self.day.bind("<<ComboboxSelected>>", lambda _: self.error.set(""))
        self.on_selected = on_selected
        ttk.Button(form, text="Usar fecha", command=self.confirm).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(form, text="Cancelar", command=self.destroy).grid(row=3, column=2, pady=(8, 0))
        self.bind("<Escape>", lambda _: self.destroy())
        self.bind("<Return>", lambda _: self.confirm())
        self.update_days()
        self.update_idletasks()
        self.configure(background=ttk.Style(self).lookup("TFrame", "background"))
        anchor = anchor or parent
        x, y = anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height()
        if y + self.winfo_reqheight() > self.winfo_screenheight():
            y = anchor.winfo_rooty() - self.winfo_reqheight()
        self.geometry(f"+{max(0, min(x, self.winfo_screenwidth() - self.winfo_reqwidth()))}+{max(0, y)}")
        self.year.focus_set()

    def update_days(self, event=None):
        maximum = calendar.monthrange(int(self.year.get()), int(self.month.get()))[1]
        self.day.configure(values=tuple(range(1, maximum + 1)))
        # Cambiar de mes/año ajusta el día, sin crear fechas como 31 de febrero.
        self.day.set(min(int(self.day.get()), maximum))
        self.error.set("")

    def confirm(self):
        try:
            value = date_from_parts(int(self.year.get()), int(self.month.get()), int(self.day.get()), kind=self.kind)
        except (ValidationError, ValueError) as error:
            self.error.set(str(error))
            return
        self.on_selected(value)
        self.destroy()


class BirthDatePicker(DatePicker):
    """Alias compatible del selector previo, con las mismas reglas de nacimiento."""

    def __init__(self, parent, current: str, on_selected, *, anchor=None):
        super().__init__(parent, current, on_selected, kind="birth", anchor=anchor)
