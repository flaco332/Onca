# Avisos de terceros

Estos avisos conservan las licencias de dependencias. El código propio usa
[Apache-2.0](LICENSE), con atribución en [NOTICE](NOTICE) y decisión en
[LICENSE-DECISION.md](LICENSE-DECISION.md).

## Runtime

- CPython/biblioteca estándar: Python Software Foundation y demás titulares
  identificados en su LICENSE original. [Texto oficial](https://docs.python.org/3.11/license.html).
- Tcl/Tk: Regents of the University of California, Sun Microsystems, Scriptics,
  ActiveState y demás titulares de sus avisos. Textos completos conservados en
  third_party_licenses/Tcl-license.terms y Tk-license.terms.
- SQLite: dominio público. [Declaración oficial](https://www.sqlite.org/copyright.html).
- Segoe UI: solicitada al sistema; no se distribuye un archivo de esa fuente.
  No se incluyen iconos/branding locales de procedencia pendiente.

## Build

PyInstaller (GPL con excepción de bootloader y archivos Apache), hooks contrib
(GPL para hooks de build/Apache para runtime hooks), altgraph (MIT), packaging
(Apache-2.0 OR BSD-2-Clause), setuptools (MIT y avisos vendorizados), pefile (MIT)
y pywin32-ctypes (BSD-3-Clause). Las versiones y fuentes verificadas están en
[el inventario](docs/dependencies-and-licenses.md).

## Cómo conservarlos en Windows

El builder copia el LICENSE original del intérprete, términos de Tcl/Tk,
LICENSE/COPYING/NOTICE instalados —incluidos vendor notices— a THIRD_PARTY_NOTICES/.
Añade este resumen, LICENSE y NOTICE del proyecto.
Distribuir los textos completos originales, no solamente enlaces o este resumen.

Antes de publicar el nuevo EXE, comparar sus DLL/runtime hooks efectivamente
incluidos con las licencias originales y completar cualquier aviso faltante del
runtime concreto, incluidos componentes vendorizados. Ese inventario binario
queda pendiente porque esta preparación no genera un nuevo EXE.
No modificar copyrights de terceros ni reemplazarlos por la licencia propia.
