import os
import sys
import ntpath
from pathlib import Path, PurePosixPath
from datetime import date

APP_NAME = "Onca Alumnos"


def get_app_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS

    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


PROJECT_ROOT = get_app_base_dir()
RESOURCE_ROOT = get_resource_base_dir()

ASSETS_FOLDER = os.path.join(RESOURCE_ROOT, "assets")
APP_ICON_PATH = os.path.join(ASSETS_FOLDER, "onca.png")

def get_data_dir():
    """Choose user data independently of the source/executable location."""
    override = os.environ.get("ONCA_DATA_DIR")
    if override:
        if not os.path.isabs(override):
            raise ValueError("ONCA_DATA_DIR debe ser una ruta absoluta.")
        return os.path.abspath(override)
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~/AppData/Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "OncaAlumnos")


def is_link(path: Path) -> bool:
    """Include Windows junctions/reparse points, not just POSIX symlinks."""
    if not path.exists() and not path.is_symlink():
        return False
    return path.is_symlink() or bool(getattr(path.lstat(), "st_file_attributes", 0) & 0x400)


def managed_path(data_root: Path, relative: str) -> Path:
    """Resolve a portable path confined to data_root, rejecting traversal/links."""
    from app.errors import ValidationError
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValidationError("Ruta de archivo inválida.")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in relative.split("/")):
        raise ValidationError("Ruta de archivo inválida.")
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"{prefix}{n}" for prefix in ("COM", "LPT") for n in range(1, 10)}
    if any(part.endswith((" ", ".")) or part.split(".")[0].upper() in reserved
           or any(ord(c) < 32 or c in '<>"|?*' for c in part) for part in path.parts):
        raise ValidationError("Nombre de archivo inválido.")
    root = data_root.resolve()
    candidate = root.joinpath(*path.parts)
    current = root
    for part in path.parts:
        current = current / part
        if is_link(current):
            raise ValidationError("No se permiten enlaces en los archivos administrados.")
    if not candidate.resolve().is_relative_to(root):
        raise ValidationError("El archivo está fuera del directorio de datos.")
    return candidate


def resolve_certificate_path(value: str, data_root: Path | None = None) -> Path:
    """Resolve new relative references; read old absolute references unchanged."""
    from app.errors import ValidationError
    root = data_root or Path(DATA_FOLDER)
    if ntpath.isabs(value) or os.path.isabs(value):
        legacy = Path(value)
        if not legacy.is_absolute() or is_link(legacy):
            raise ValidationError("Ruta histórica no disponible en este sistema.")
        return legacy
    return managed_path(root, value)


DATA_FOLDER = get_data_dir()
BASE_FOLDER = os.path.join(DATA_FOLDER, "control_alumnos")
CERTS_FOLDER = os.path.join(DATA_FOLDER, "certificados")
BACKUPS_FOLDER = os.path.join(DATA_FOLDER, "backups")
LOG_PATH = os.path.join(BASE_FOLDER, "reminder_log.txt")

DB_PATH = os.path.join(DATA_FOLDER, "onca.db")
SCHEMA_PATH = os.path.join(RESOURCE_ROOT, "app", "schema.sql")

def ensure_base_folders():
    os.makedirs(DATA_FOLDER, exist_ok=True)
    os.makedirs(BASE_FOLDER, exist_ok=True)
    os.makedirs(CERTS_FOLDER, exist_ok=True)
    os.makedirs(BACKUPS_FOLDER, exist_ok=True)


def ensure_certs_month_folder():
    ensure_base_folders()

    month = date.today().strftime("%Y-%m")
    path = os.path.join(CERTS_FOLDER, month)
    os.makedirs(path, exist_ok=True)

    return path


def ensure_month_folder_and_file():
    ensure_base_folders()

    today = date.today()
    month_folder = today.strftime("%Y-%m")
    month_path = os.path.join(BASE_FOLDER, month_folder)
    os.makedirs(month_path, exist_ok=True)

    file_name = f"alumnos_{month_folder}.txt"
    file_path = os.path.join(month_path, file_name)

    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(
                "name|phone|has_medical|last_payment_date|medical_cert_date|medical_cert_path\n"
            )

    return file_path


def safe_filename(name: str) -> str:
    bad = '<>:"/\\|?*'
    out = "".join("_" if c in bad else c for c in name.strip())
    return out or "certificado"
