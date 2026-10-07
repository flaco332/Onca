"""Verified database/attachment snapshots and non-destructive restoration.

Backups use SQLite's online API under the same application lock as all writes.
Absolute legacy references are normalized only in the backup copy. Restoration
always publishes a new directory: the active installation is never replaced.
Checksums detect corruption, not authenticity against a malicious publisher.
"""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid

from app.data_access import data_operation
from app.errors import BackupError, DatabaseError
from app.logging_config import log_event
from app.migrations import CURRENT_SCHEMA_VERSION, get_schema_version, validate_schema
from app.paths import managed_path, resolve_certificate_path, is_link
from app.version import __version__


def sha256_file(path: Path) -> str:
    """Hash in bounded memory, including large databases/attachments."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _check_database(path: Path) -> int:
    with closing(_readonly(path)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise BackupError("La base de datos del respaldo no es válida.")
        version = get_schema_version(conn)
        if not 0 <= version <= CURRENT_SCHEMA_VERSION:
            raise BackupError("El respaldo requiere otra versión de la aplicación.")
        validate_schema(conn)
        return version


def _attachment_files(root: Path):
    """Walk managed attachment trees only; never recurse into logs/backups."""
    for folder in ("certificados", "control_alumnos/certificados"):
        start = managed_path(root, folder)
        if not start.exists():
            continue
        for parent, directories, files in os.walk(start, followlinks=False):
            for name in directories + files:
                candidate = Path(parent) / name
                if is_link(candidate):
                    raise BackupError("No se permiten enlaces en los adjuntos.")
            for name in files:
                yield Path(parent) / name


def validate_backup(backup_dir: Path | str) -> dict:
    """Validate exact file inventory, paths, hashes, schema and all references."""
    root = Path(backup_dir).resolve()
    try:
        manifest_path = managed_path(root, "manifest.json")
        if manifest_path.stat().st_size > 4 * 1024 * 1024:
            raise BackupError("Manifest demasiado grande.")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format_version") != 1 or not isinstance(manifest.get("files"), dict):
            raise BackupError("Formato de respaldo no reconocido.")
        if not isinstance(manifest.get("app_version"), str) or not isinstance(manifest.get("created_at"), str):
            raise BackupError("Metadatos de respaldo incompletos.")
        files = manifest["files"]
        if "onca.db" not in files or len(files) > 100_000:
            raise BackupError("Inventario de respaldo inválido.")
        for name, digest in files.items():
            if name != "onca.db" and not name.startswith("certificados/"):
                raise BackupError("Archivo inesperado en respaldo.")
            path = managed_path(root, name)
            if not isinstance(digest, str) or len(digest) != 64 or sha256_file(path) != digest:
                raise BackupError("El checksum del respaldo no coincide.")
        actual = set()
        for parent, directories, filenames in os.walk(root, followlinks=False):
            for name in directories + filenames:
                if is_link(Path(parent) / name):
                    raise BackupError("Enlace inesperado en respaldo.")
            actual.update((Path(parent) / name).relative_to(root).as_posix() for name in filenames)
        if actual != set(files) | {"manifest.json"}:
            raise BackupError("El inventario del respaldo no coincide.")
        version = _check_database(managed_path(root, "onca.db"))
        if manifest.get("schema_version") != version:
            raise BackupError("Versión de schema incorrecta.")
        with closing(_readonly(root / "onca.db")) as conn:
            for (value,) in conn.execute("SELECT file_path FROM medical_certificates WHERE file_path != ''"):
                # Backups must be portable, even if their source used legacy paths.
                if value not in files or not value.startswith("certificados/"):
                    raise BackupError("Referencia de adjunto incompleta.")
        return manifest
    except BackupError:
        raise
    except (OSError, ValueError, TypeError, AttributeError, sqlite3.Error, DatabaseError) as error:
        raise BackupError("No fue posible validar el respaldo.") from error


def create_backup(data_root: Path | str) -> Path:
    """Create a complete snapshot in staging; publish only after validation."""
    root = Path(data_root).resolve()
    stage = None
    try:
        with data_operation(root):
            db = managed_path(root, "onca.db")
            if not db.is_file():
                raise BackupError("No hay una base de datos para respaldar.")
            directory = managed_path(root, "backups")
            directory.mkdir(exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".pending-", dir=directory))
            with closing(_readonly(db)) as source, closing(sqlite3.connect(stage / "onca.db")) as target:
                source.backup(target)
            files: dict[str, str] = {}
            copied: dict[Path, str] = {}

            def copy_attachment(source: Path) -> str:
                if is_link(source):
                    raise BackupError("No se permiten enlaces en los adjuntos.")
                source = source.resolve()
                if source in copied:
                    return copied[source]
                if not source.is_file() or is_link(source):
                    raise BackupError("Falta un adjunto del respaldo.")
                relative = f"certificados/{uuid.uuid4().hex}{source.suffix.lower()}"
                destination = managed_path(stage, relative)
                destination.parent.mkdir(exist_ok=True)
                # Exclusive file creation and content only: no external metadata.
                with source.open("rb") as incoming, destination.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
                files[relative] = sha256_file(destination)
                # External viewers/editors do not participate in our lock. A
                # changed source must fail validation rather than hide a race.
                if sha256_file(source) != files[relative]:
                    raise BackupError("Un adjunto cambió durante el respaldo. Intenta nuevamente.")
                copied[source] = relative
                return relative

            with closing(sqlite3.connect(stage / "onca.db")) as conn:
                with conn:
                    refs = conn.execute("SELECT certificate_id, file_path FROM medical_certificates WHERE file_path != ''").fetchall()
                    for certificate_id, value in refs:
                        source = resolve_certificate_path(value, root)
                        relative = copy_attachment(source)
                        conn.execute("UPDATE medical_certificates SET file_path=?, file_hash=? WHERE certificate_id=?",
                                     (relative, files[relative], certificate_id))
                    # Also retain managed files not yet referenced by a row.
                    for source in _attachment_files(root):
                        copy_attachment(source)
                version = get_schema_version(conn)
            files["onca.db"] = sha256_file(stage / "onca.db")
            manifest = {"format_version": 1, "app_version": __version__,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "schema_version": version, "files": files}
            (stage / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            validate_backup(stage)
            final = directory / (datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S_") + uuid.uuid4().hex[:8])
            stage.rename(final)
            stage = None
            log_event("backup_created")
            return final
    except Exception as error:
        log_event("backup_failed", error)
        raise BackupError("No fue posible crear un respaldo completo. No se modificaron los datos.") from error
    finally:
        if stage is not None:
            # Only the unique staging directory created above is eligible.
            shutil.rmtree(stage)


def restore_backup(backup_dir: Path | str, current_data_root: Path | str,
                   destination: Path | str) -> Path:
    """Back up current data, then restore into a NEW directory; never overwrite.

    The caller can activate the returned directory after closing the UI. Failed
    preparation leaves the current installation unchanged and removes only its
    own staging files. The pre-restore backup remains available on success/failure.
    """
    source, current, target = Path(backup_dir).resolve(), Path(current_data_root).resolve(), Path(destination).absolute()
    stage = None
    try:
        if target.exists() or target.is_symlink() or target.resolve().is_relative_to(current) or target.resolve().is_relative_to(source):
            raise BackupError("Selecciona una carpeta nueva fuera de los datos actuales.")
        log_event("restore_started")
        with data_operation(current):
            manifest = validate_backup(source)
            create_backup(current)
            target.parent.mkdir(parents=True, exist_ok=True)
            stage = Path(tempfile.mkdtemp(prefix=".onca-restore-", dir=target.parent))
            for name in manifest["files"]:
                original, restored = managed_path(source, name), managed_path(stage, name)
                restored.parent.mkdir(parents=True, exist_ok=True)
                with original.open("rb") as incoming, restored.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing)
            shutil.copyfile(source / "manifest.json", stage / "manifest.json")
            validate_backup(stage)
            # Compatible older snapshots are upgraded only in staging.
            from app.migrations import migrate_database
            with closing(sqlite3.connect(stage / "onca.db")) as conn:
                conn.execute("PRAGMA foreign_keys=ON")
                migrate_database(conn)
            _check_database(stage / "onca.db")
            # The backup manifest describes the pre-migration DB; restored data is
            # an installation, not a backup, so do not retain a stale manifest.
            (stage / "manifest.json").unlink()
            if target.exists():
                raise BackupError("La carpeta de destino ya existe.")
            stage.rename(target)
            stage = None
            log_event("restore_completed")
            return target
    except Exception as error:
        log_event("restore_failed", error)
        if isinstance(error, BackupError):
            raise
        raise BackupError("No fue posible restaurar. Los datos actuales se conservaron.") from error
    finally:
        if stage is not None:
            shutil.rmtree(stage)


def ensure_daily_backup(data_root: Path | str) -> Path | None:
    """Create one verified backup per UTC day; corrupted backups never count."""
    root = Path(data_root)
    directory = managed_path(root, "backups")
    prefix = datetime.now(timezone.utc).strftime("%Y-%m-%d_")
    with data_operation(root):
        if directory.exists():
            for backup in directory.glob(prefix + "*"):
                try:
                    validate_backup(backup)
                    return None
                except BackupError:
                    continue
        return create_backup(root)
