# Dependencias y licencias

Revisión de metadatos/textos instalados y fuentes oficiales, 2026-10-06.
Runtime sin paquetes PyPI externos. Versiones de build fijadas en
requirements-dev.txt; entorno validado Python 3.11.17/Tk 8.6.15/SQLite 3.53.1.

## RUNTIME

| Dependencia | Versión validada | Uso | Licencia | URL/proyecto |
| --- | --- | --- | --- | --- |
| CPython y biblioteca estándar | 3.11.17 | Intérprete, Decimal, archivos, concurrencia | PSF-2.0 y avisos de componentes incluidos | [Python](https://docs.python.org/3.11/license.html) |
| tkinter | incluida en CPython | Wrapper UI | PSF para wrapper; Tcl/Tk por separado | [Python tkinter](https://docs.python.org/3.11/library/tkinter.html) |
| Tcl/Tk | 8.6.15 | UI nativa | Licencia permisiva Tcl/Tk, textos propios | [Tcl](https://github.com/tcltk/tcl/blob/core-8-6-15/license.terms), [Tk](https://github.com/tcltk/tk/blob/core-8-6-15/license.terms) |
| SQLite / sqlite3 | 3.53.1 / incluida en CPython | Base local | SQLite dominio público; wrapper PSF | [SQLite](https://www.sqlite.org/copyright.html) |

No se utilizan Pillow, tkcalendar, tkintermapview, Leaflet ni Google Maps.
No se añaden paquetes por la investigación de mapas. No se distribuyen fonts o
assets locales; invocar un visor PDF del sistema no incorpora su licencia al paquete.

## BUILD

| Dependencia | Versión | Uso | Licencia verificada | URL/proyecto |
| --- | --- | --- | --- | --- |
| PyInstaller | 6.20.0 | EXE / bootloader | GPL-2.0-or-later con excepción de empaquetado; ciertos archivos Apache-2.0 | [Licencia](https://pyinstaller.org/en/v6.20.0/license.html) |
| pyinstaller-hooks-contrib | 2026.5 | Hooks | GPL-2.0-or-later build; Apache-2.0 runtime hooks | [Proyecto](https://github.com/pyinstaller/pyinstaller-hooks-contrib) |
| altgraph | 0.17.5 | Grafo de imports | MIT | [Proyecto](https://github.com/ronaldoussoren/altgraph) |
| packaging | 26.2 | Versiones/metadata | Apache-2.0 OR BSD-2-Clause | [Proyecto](https://github.com/pypa/packaging) |
| setuptools | 83.0.0 | Soporte de build | MIT; vendor components conservan avisos propios | [Proyecto](https://github.com/pypa/setuptools) |
| pefile | 2024.8.26 | PE Windows | MIT | [Proyecto](https://github.com/erocarrera/pefile) |
| pywin32-ctypes | 0.2.3 | APIs Windows | BSD-3-Clause | [Proyecto](https://github.com/enthought/pywin32-ctypes) |

Los siete pins se conservan: se verificaron versiones, dependencias y pip check
del entorno de herramientas, no se eliminan por ausencia de imports del runtime.
La excepción de PyInstaller permite licenciar el programa independientemente;
no sustituye obligaciones de otras bibliotecas o modificaciones al bootloader.

## DEVELOPMENT y preparación

| Dependencia | Versión | Uso | Licencia | URL/proyecto |
| --- | --- | --- | --- | --- |
| unittest / compileall | CPython 3.11.17 | Tests / check sintáctico | PSF | [Python](https://docs.python.org/3.11/license.html) |
| uv | 0.12.23, opcional y en CI | Preparar intérprete/venv | MIT OR Apache-2.0 | [uv](https://github.com/astral-sh/uv#license) |
| pip-audit | 2.10.1 en entorno separado, no requerido por la app | Auditoría puntual | Apache-2.0, según metadata instalada | [Proyecto](https://github.com/pypa/pip-audit) |

No hay pytest/linter/type checker configurados. No entran en el EXE herramientas
de desarrollo por copiar el venv. La descarga administrada de Python incluye
componentes nativos: hay que verificar los avisos de DLL reales después del build.

## Avisos y auditoría

Ver [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md). Fuente conserva términos
Tcl/Tk originales. El futuro builder copia LICENSE de Python y textos instalados
LICENSE/COPYING/NOTICE, incluidos vendor notices; no es suficiente enlazar una web
si un componente exige entregar su texto completo.

pip-audit 2.10.1 revisó los siete pins con --no-deps --disable-pip: **sin
vulnerabilidades conocidas encontradas** a la fecha. Revisión limitada a esos
paquetes/avisos publicados; no audita Python/Tcl/Tk/SQLite/DLL ni código propio.
El runtime y todas las transitivas del EXE final requieren revisión binaria.
No se afirma que las versiones sean las más recientes.

La licencia propia es [Apache-2.0](../LICENSE), con [NOTICE](../NOTICE).
La selección fue autorizada por el propietario; no cambia las licencias de
dependencias ni concede derechos sobre marcas o datos de usuarios.
