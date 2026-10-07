"""Desktop launcher, safe error boundary and isolated UI smoke validation."""
import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from app.database import init_db, DB_PATH
from app.ui import StudentApp
from app.theme import WINDOW_SIZE, MIN_WINDOW_SIZE
from app.paths import APP_NAME, managed_path
from app.background_tasks import BackgroundTasks
from app.backups import ensure_daily_backup
from app.logging_config import configure_logging, log_event
from app.version import __version__
from app.errors import BackupError


def prepare_data(*, smoke: bool = False) -> bool:
    """Primer inicio sin seeds; las carpetas y migraciones viven fuera del ejecutable."""
    data_root = Path(DB_PATH).parent
    configure_logging(data_root)
    for folder in ("certificados", "backups"):
        managed_path(data_root, folder).mkdir(parents=True, exist_ok=True)
    init_db()
    if not smoke:
        try:
            ensure_daily_backup(data_root)
        except BackupError:
            return False
    return True


def main() -> None:
    """Prepare data on a worker, then construct all widgets on the Tk thread."""
    smoke = "--smoke-test" in sys.argv
    if smoke and not os.environ.get("ONCA_DATA_DIR"):
        raise ValueError("La validación requiere ONCA_DATA_DIR aislado.")
    root = tk.Tk()
    root.title(f"{APP_NAME} {__version__}")
    root.geometry(WINDOW_SIZE)
    root.minsize(*MIN_WINDOW_SIZE)
    state = {"exit_code": 0, "app": None}
    status = tk.StringVar(value="Preparando datos…")
    splash = ttk.Label(root, textvariable=status, padding=24)
    splash.pack(expand=True)
    bootstrap = BackgroundTasks(root, status, lambda busy: None)

    def fatal(error):
        log_event("unexpected_exception", error)
        state["exit_code"] = 1
        if not smoke:
            messagebox.showerror(APP_NAME, "No fue posible abrir los datos. Revisa los permisos, el respaldo y la compatibilidad de la base.")
        bootstrap.close()
        if state["app"] is not None:
            state["app"].tasks.close()
        root.destroy()

    def callback_error(exc_type, exc_value, traceback):
        if smoke:
            fatal(exc_value)
        else:
            log_event("unexpected_exception", exc_value)
            messagebox.showerror(APP_NAME, "No fue posible completar la operación. Intenta nuevamente.")
    root.report_callback_exception = callback_error

    def prepare():
        return prepare_data(smoke=smoke)

    def ready(result):
        bootstrap.close()
        splash.destroy()
        app = StudentApp(root)
        state["app"] = app
        root.title(f"{APP_NAME} {__version__}")
        if result is False:
            app.status.set("Respaldo diario pendiente: revisa los adjuntos y crea un respaldo")
            messagebox.showwarning(APP_NAME, "No se pudo crear un respaldo diario completo. Revisa archivos faltantes y espacio disponible; después usa Datos → Crear respaldo.")
        if smoke:
            # Exercise navigation and a secondary form without creating records.
            root.withdraw()
            for tab in app.notebook.tabs():
                app.notebook.select(tab)
                root.update_idletasks()
            app.open_activity_form("create")
            forms = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
            if not forms:
                raise RuntimeError("Activity form did not open")
            for form in forms:
                form.destroy()
            root.after(500, app.request_close)

    root.protocol("WM_DELETE_WINDOW", lambda: status.set("Espera a que termine la preparación") if bootstrap.busy else root.destroy())
    bootstrap.start("Preparando datos y respaldo…", prepare, ready, fatal)
    root.mainloop()
    raise SystemExit(state["exit_code"])


if __name__ == "__main__":
    main()
