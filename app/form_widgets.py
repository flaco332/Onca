"""Controles pequeños reutilizables; las reglas de datos permanecen en servicios."""
from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from app.errors import ValidationError


class InlineEntry(ttk.Frame):
    """Entrada con error junto al campo, actualizado también al editar con teclado."""

    def __init__(self, parent, validator: Callable[[str], object]):
        super().__init__(parent)
        self.validator = validator
        self.on_change = None
        self.value = tk.StringVar(self)
        self.error = tk.StringVar(self)
        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill="x")
        self.entry = ttk.Entry(self.input_frame, textvariable=self.value)
        self.entry.pack(fill="x")
        self.label = ttk.Label(self, textvariable=self.error, style="Error.TLabel", wraplength=280)
        self.value.trace_add("write", self.value_changed)

    def value_changed(self, *_):
        self.validate()
        if self.on_change is not None:
            self.on_change()

    def show_error(self, message: str) -> None:
        self.error.set(message)
        if message:
            self.label.pack(fill="x", pady=(2, 0))
        else:
            self.label.pack_forget()

    def validate(self) -> bool:
        try:
            self.validator(self.value.get())
        except ValidationError as error:
            self.show_error(str(error))
            return False
        self.show_error("")
        return True


class InlineDateEntry(InlineEntry):
    """Fecha visible con selector por clic, botón o teclado; entrada manual validada."""

    def __init__(self, parent, *, kind: str, optional: bool = False):
        from app.validation import parse_date_field
        super().__init__(parent, lambda value: parse_date_field(value, kind, optional=optional))
        self.kind = kind
        self.picker = None
        self.entry.pack_configure(side="left", expand=True)
        self.button = ttk.Button(self.input_frame, text="Elegir…", width=8, command=self.open_picker)
        self.button.pack(side="right", padx=(4, 0))
        self.entry.bind("<Button-1>", lambda _: self.open_picker())
        self.entry.bind("<F4>", lambda _: self.open_picker())
        self.entry.bind("<Alt-Down>", lambda _: self.open_picker())

    def open_picker(self):
        from app.date_picker import DatePicker, BirthDatePicker
        if self.entry.instate(["disabled"]):
            return
        if self.picker is not None and self.picker.winfo_exists():
            self.picker.lift()
            return self.picker
        options = {"anchor": self.entry}
        picker_type = BirthDatePicker if self.kind == "birth" else DatePicker
        if self.kind != "birth":
            options["kind"] = self.kind
        self.picker = picker_type(self.winfo_toplevel(), self.value.get(), self.value.set, **options)
        return self.picker


class ScrollableFrame(ttk.Frame):
    """Formulario vertical; enlaces locales evitan capturar la rueda de otras ventanas."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0, takefocus=True)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.content = ttk.Frame(self.canvas, padding=14)
        self.item = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda _: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.item, width=event.width))
        self.bind("<<ThemeChanged>>", self.update_theme)
        self.update_theme()
        for key, units in (("<Prior>", -1), ("<Next>", 1)):
            self.canvas.bind(key, lambda _, step=units: self.canvas.yview_scroll(step, "pages"))
        self.canvas.bind("<Home>", lambda _: self.canvas.yview_moveto(0))
        self.canvas.bind("<End>", lambda _: self.canvas.yview_moveto(1))
        self.canvas.bind("<MouseWheel>", self.on_wheel)

    def update_theme(self, event=None):
        style = ttk.Style(self)
        self.canvas.configure(background=style.lookup("TFrame", "background") or "#f3f3f3")
        def visit(widget):
            if isinstance(widget, tk.Text):
                widget.configure(background=style.lookup("TEntry", "fieldbackground"), foreground=style.lookup("TEntry", "foreground"), insertbackground=style.lookup("TEntry", "foreground"))
            for child in widget.winfo_children():
                visit(child)
        visit(self.content)

    def bind_content(self):
        """Se enlaza una vez, después de construir los controles del formulario."""
        def visit(widget):
            if not isinstance(widget, (tk.Text, tk.Listbox)):
                widget.bind("<MouseWheel>", self.on_wheel, add="+")
                widget.bind("<Button-4>", lambda _: self.scroll(-1), add="+")
                widget.bind("<Button-5>", lambda _: self.scroll(1), add="+")
            widget.bind("<FocusIn>", self.reveal, add="+")
            for child in widget.winfo_children():
                visit(child)
        visit(self.content)
        self.update_theme()

    def scroll(self, units: int):
        self.canvas.yview_scroll(units, "units")
        return "break"

    def on_wheel(self, event):
        return self.scroll(-max(1, abs(event.delta) // 120) if event.delta > 0 else max(1, abs(event.delta) // 120))

    def reveal(self, event):
        height = self.content.winfo_height()
        if height <= self.canvas.winfo_height():
            return
        top = event.widget.winfo_rooty() - self.content.winfo_rooty()
        bottom = top + event.widget.winfo_height()
        visible_top = self.canvas.canvasy(0)
        visible_bottom = visible_top + self.canvas.winfo_height()
        if top < visible_top:
            self.canvas.yview_moveto(top / height)
        elif bottom > visible_bottom:
            self.canvas.yview_moveto((bottom - self.canvas.winfo_height()) / height)
