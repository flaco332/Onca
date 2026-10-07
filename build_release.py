"""Build a fresh, local-only distribution without copying user data."""
import argparse
import hashlib
import json
import shutil
from importlib.metadata import distribution
import subprocess
import sys
from pathlib import Path
from app.version import __version__
from app.migrations import CURRENT_SCHEMA_VERSION


def copy_third_party_notices(root: Path, output: Path) -> None:
    """Conserva textos originales y NOTICE vendorizados, sin copiar paquetes o datos."""
    notices = output / "THIRD_PARTY_NOTICES"
    notices.mkdir()
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", notices / "Python-LICENSE.txt")
    for name in ("PyInstaller", "pyinstaller-hooks-contrib", "altgraph", "packaging", "setuptools", "pefile", "pywin32-ctypes"):
        dist = distribution(name)
        for file in dist.files or []:
            if file.name.lower().startswith(("license", "copying", "notice")):
                relative = Path(str(file))
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Ruta inválida en avisos instalados.")
                target = notices / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(Path(dist.locate_file(file)), target)
    for license_file in (Path(sys.base_prefix) / "tcl").rglob("license.terms"):
        target = notices / "Tcl-Tk" / license_file.relative_to(Path(sys.base_prefix) / "tcl")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(license_file, target)
    for license_file in (root / "third_party_licenses").iterdir():
        if license_file.is_file():
            shutil.copyfile(license_file, notices / license_file.name)
    shutil.copyfile(root / "THIRD_PARTY_NOTICES.md", output / "THIRD_PARTY_NOTICES.md")
    for name in ("LICENSE", "NOTICE"):
        if (root / name).is_file():
            shutil.copyfile(root / name, output / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="dist", help="New output directory (must not exist)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    output = Path(args.output).resolve()
    # Refuse to merge with stale distributions or overwrite anything.
    output.mkdir(parents=True, exist_ok=False)
    subprocess.run([sys.executable, "-m", "PyInstaller",
                    str(root / "OncaAlumnos.spec"), "--distpath", str(output),
                    "--workpath", str(output / "work")], cwd=root, check=True)
    exe = output / "OncaAlumnos.exe"
    digest = hashlib.sha256(exe.read_bytes()).hexdigest()
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {exe.name}\n", encoding="utf-8")
    (output / "build-manifest.json").write_text(json.dumps({
        "app_version": __version__, "schema_version": CURRENT_SCHEMA_VERSION,
        "python_version": sys.version.split()[0],
        "executable": exe.name, "sha256": digest,
    }, indent=2) + "\n", encoding="utf-8")
    copy_third_party_notices(root, output)
    print(f"Build local: {exe}")


if __name__ == "__main__":
    main()
