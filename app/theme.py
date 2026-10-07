"""Neutral ttk design tokens shared by the main window and dialogs."""
from tkinter import ttk

FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 13, "bold")
SPACE = 8
PANEL_PADDING = 12
WINDOW_SIZE = "1120x700"
MIN_WINDOW_SIZE = (880, 620)


def apply_theme(root, style: ttk.Style, dark: bool, widgets: dict) -> None:
    """Configure one neutral palette; native point fonts honor Tk scaling."""
    bg, panel, field, fg, muted, selected = (
        ("#242424", "#303030", "#383838", "#f0f0f0", "#b5b5b5", "#505050") if dark
        else ("#f3f3f3", "#fafafa", "#ffffff", "#202020", "#656565", "#d7d7d7")
    )
    style.theme_use("clam")
    root.configure(bg=bg)
    style.configure(".", background=bg, foreground=fg, font=FONT)
    for name in ("TFrame", "Main.TFrame"):
        style.configure(name, background=bg)
    for name in ("TLabel", "TLabelframe.Label", "Card.TLabelframe.Label"):
        style.configure(name, background=panel, foreground=fg)
    style.configure("Title.TLabel", font=TITLE_FONT, background=bg)
    style.configure("Error.TLabel", foreground="#f28b82" if dark else "#b00020", font=(FONT[0], 9))
    for name in ("TLabelframe", "Card.TLabelframe"):
        style.configure(name, background=panel, bordercolor=muted)
    for name in ("TButton", "Outline.TButton", "Accent.TButton"):
        style.configure(name, padding=(12, 6), background=panel, foreground=fg)
        style.map(name, background=[("active", selected)], foreground=[("disabled", muted)])
    style.configure("Accent.TButton", font=(FONT[0], FONT[1], "bold"))
    for name in ("TEntry", "TCombobox"):
        style.configure(name, fieldbackground=field, foreground=fg, background=panel)
        style.map(name, fieldbackground=[("readonly", field)], foreground=[("readonly", fg)])
    for name in ("TNotebook", "Custom.TNotebook"):
        style.configure(name, background=bg)
    for name in ("TNotebook.Tab", "Custom.TNotebook.Tab"):
        style.configure(name, padding=(12, 8), background=panel)
        style.map(name, background=[("selected", selected)])
    style.configure("Treeview", rowheight=28, fieldbackground=field, background=field, foreground=fg)
    style.configure("Treeview.Heading", font=(FONT[0], FONT[1], "bold"), padding=6)
    style.map("Treeview", background=[("selected", selected)], foreground=[("selected", fg)])
    options = dict(bg=field, fg=fg, selectbackground=selected, selectforeground=fg, font=FONT)
    for name in ("payments_listbox",):
        if name in widgets:
            widgets[name].configure(**options)
    for name in ("text_notes", "activity_detail"):
        if name in widgets:
            widgets[name].configure(**options, insertbackground=fg)
    if "label_cert_preview" in widgets:
        widgets["label_cert_preview"].configure(background=panel, foreground=muted)
    if "button_dark_mode" in widgets:
        widgets["button_dark_mode"].configure(text="Modo claro" if dark else "Modo oscuro")
