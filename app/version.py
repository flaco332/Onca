"""Versión única de ONCA; la metadata de Windows se deriva sin compilar."""
import re

__version__ = "0.9.0-rc1"


def windows_version(version: str = __version__) -> tuple[int, int, int, int]:
    """Windows exige cuatro enteros; el sufijo RC permanece en la versión textual."""
    match = re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc[1-9]\d*)?", version)
    if match is None:
        raise ValueError("Versión SemVer o RC inválida.")
    parts = tuple(int(part) for part in match.groups())
    if any(part > 65535 for part in parts):
        raise ValueError("La versión excede los límites de metadata Windows.")
    return (*parts, 0)
