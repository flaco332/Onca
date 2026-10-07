"""Export reviewed committed files, without Git history or local data.
This is a preparation tool, not a publication command.
"""
import argparse
import io
import subprocess
import re
import stat
import zipfile
from pathlib import Path, PurePosixPath

ALLOWED_ROOTS = {"app", "docs", "tests", "tools", ".github", "third_party_licenses"}
ALLOWED_FILES = {"README.md", "CHANGELOG.md", "LICENSE", "NOTICE", ".gitignore", "requirements.txt",
                 "requirements-dev.txt", "run.py", "OncaAlumnos.spec",
                 "build_release.py", "build_release.ps1", "BUILD_INSTRUCTIONS.md",
                 "LICENSE-DECISION.md", "THIRD_PARTY_NOTICES.md"}
EXCLUDED_PREFIXES = ("docs/changes/",)
PRIVATE_PARTS = {".git", ".private", ".venv", "__pycache__", "data", "backups", "exports", "certificados", "logs", "build", "dist", "release"}
PRIVATE_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".pyc", ".log", ".exe", ".zip", ".pem", ".key", ".pfx", ".p12", ".dll", ".pyd", ".pdf", ".png", ".ico", ".jpg", ".bak", ".tmp", ".csv", ".tsv", ".json", ".txt", ".xlsx", ".xls"}
PATTERNS = (
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})",
    rb"AKIA[0-9A-Z]{16}", rb"AIza[0-9A-Za-z_-]{35}",
    rb"[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9_. -]+[\\/]",
)


def validate_source_file(name: str, data: bytes, *, mode: int = 0) -> None:
    """Bloquea rutas privadas, binarios y patrones sensibles sin imprimir sus valores."""
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name or not path.parts:
        raise ValueError(f"Ruta insegura: {name}")
    if path.parts[0] not in ALLOWED_ROOTS and name not in ALLOWED_FILES:
        raise ValueError(f"Archivo no revisado: {name}")
    fixture_text = path.parts[:2] == ("tests", "fixtures") and path.suffix.lower() in {".json", ".csv", ".tsv", ".txt"}
    requirement = name in {"requirements.txt", "requirements-dev.txt"}
    if stat.S_ISLNK(mode) or any(part in PRIVATE_PARTS for part in path.parts) or (path.suffix.lower() in PRIVATE_SUFFIXES and not fixture_text and not requirement) or path.name.startswith(".env"):
        raise ValueError(f"Archivo privado/generado: {name}")
    if len(data) > 4_000_000 or b"\x00" in data or any(re.search(pattern, data) for pattern in PATTERNS):
        raise ValueError(f"Contenido requiere revisión: {name}")


def export_snapshot(root: Path, output: Path) -> int:
    """Exporta HEAD limpio con lista permitida; conserva cualquier destino existente."""
    if subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=root).returncode:
        raise ValueError("Guarda los cambios revisados en commits antes de exportar HEAD.")
    archive = subprocess.check_output(["git", "archive", "--format=zip", "HEAD"], cwd=root)
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        files = [item for item in source.infolist() if not item.is_dir() and not item.filename.startswith(EXCLUDED_PREFIXES)]
        for item in files:
            validate_source_file(item.filename, source.read(item), mode=item.external_attr >> 16)
        output.mkdir(parents=True, exist_ok=False)
        for item in files:
            source.extract(item, output)
    return len(files)


def check_source(root: Path) -> int:
    """Revisa la fuente seleccionada; las evidencias internas no forman parte de la RC."""
    files = []
    for name in ALLOWED_FILES:
        if (root / name).is_file():
            files.append(root / name)
    for name in ALLOWED_ROOTS:
        files.extend(p for p in (root / name).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    checked = 0
    for path in files:
        name = path.relative_to(root).as_posix()
        if name.startswith(EXCLUDED_PREFIXES):
            continue
        validate_source_file(name, path.read_bytes(), mode=path.lstat().st_mode)
        checked += 1
    return checked


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--output", help="New directory; refuses to overwrite")
    options.add_argument("--check", action="store_true", help="Validate current source without exporting")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.check:
        print(f"Fuente revisada: {check_source(root)} archivos; sin patrones bloqueados.")
    else:
        output = Path(args.output).resolve()
        print(f"Snapshot sin historial: {output} ({export_snapshot(root, output)} archivos)")


if __name__ == "__main__":
    main()
