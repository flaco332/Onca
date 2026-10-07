"""Content-only attachment copies with opaque names and bounded input files."""
from datetime import date
from pathlib import Path
import struct
import uuid
from app import database
from app.data_access import data_operation
from app.errors import FileOperationError, ValidationError
from app.logging_config import log_event
from app.paths import managed_path, is_link

MAX_ATTACHMENT_BYTES = 32 * 1024 * 1024


def validate_attachment(source: Path) -> None:
    """Allow PNG/PDF signatures only, with bounded size and PNG dimensions."""
    if not source.is_file() or is_link(source):
        raise ValidationError("Selecciona un archivo existente sin enlaces.")
    if source.suffix.lower() not in {".png", ".pdf"}:
        raise ValidationError("Solo se permiten certificados PNG o PDF.")
    if not 0 < source.stat().st_size <= MAX_ATTACHMENT_BYTES:
        raise ValidationError("El archivo está vacío o supera 32 MiB.")
    with source.open("rb") as handle:
        header = handle.read(32)
    if source.suffix.lower() == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise ValidationError("El contenido no corresponde a un PDF.")
    else:
        if not header.startswith(bytes.fromhex("89504e470d0a1a0a")) or header[12:16] != b"IHDR" or len(header) < 24:
            raise ValidationError("El contenido no corresponde a un PNG.")
        width, height = struct.unpack(">II", header[16:24])
        if not (0 < width <= 6000 and 0 < height <= 6000):
            raise ValidationError("La imagen excede las dimensiones permitidas.")


def copy_certificate(src_path: str, student_name: str = "", custom_name: str | None = None,
                     *, data_root: Path | None = None) -> str:
    """Copy to an exclusive opaque path; old name arguments are compatibility only.

    The result is POSIX-relative to data_root. Input names and filesystem
    metadata are never incorporated in the output filename or technical logs.
    """
    root = data_root or Path(database.DB_PATH).parent
    source, destination = Path(src_path), None
    created = False
    try:
        validate_attachment(source)
        relative = f"certificados/{date.today():%Y/%m}/{uuid.uuid4().hex}{source.suffix.lower()}"
        with data_operation(root):
            destination = managed_path(root, relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open("rb") as incoming, destination.open("xb") as outgoing:
                created = True
                total = 0
                for block in iter(lambda: incoming.read(1024 * 1024), b""):
                    total += len(block)
                    if total > MAX_ATTACHMENT_BYTES:
                        raise ValidationError("El archivo supera 32 MiB.")
                    outgoing.write(block)
            validate_attachment(destination)
        return relative
    except Exception as error:
        if created and destination is not None:
            # Compensation only for the unique file successfully created here.
            destination.unlink(missing_ok=True)
        log_event("certificate_copy_failed", error)
        if isinstance(error, ValidationError):
            raise
        raise FileOperationError("No fue posible copiar el certificado.") from error


def update_student_certificate(student: dict, cert_path: str) -> dict:
    """Update an in-memory draft, without persistence."""
    student.update(medical_cert_path=cert_path, medical_cert_date=date.today(), has_medical=True)
    return student
