# Onca Alumnos

Aplicación de escritorio para gestionar alumnos, pagos, actividades y certificados
médicos adjuntos. Funciona localmente con Python, Tkinter/ttk y SQLite, sin servidor
ni servicios externos obligatorios.

Esta entrega es una **Release Candidate para revisión**, no una release publicada.
La versión se define únicamente en `app/version.py`. El nuevo EXE está pendiente
de autorización; los ejecutables anteriores no representan necesariamente esta RC.

## Características

- Crear, editar y dar de baja alumnos por ID; Nombre y Apellidos separados.
- Validación inline de teléfonos nacionales/internacionales y fechas.
- Selector visual Año/Mes/Día para nacimiento, actividades, certificados y pagos.
- Registrar, modificar y eliminar pagos; cálculo de vencimiento.
- Actividades individuales/grupales, asistencia y saldo restante con Decimal.
- Certificados PNG/PDF, vista previa PNG y apertura con el visor del sistema.
- Verificación médica automática al marcar/desmarcar y columna `V med`.
- Backups verificados y restauración en una carpeta nueva, sin sobrescribir datos.
- Tema claro/oscuro y tablas con desplazamiento.

No se incluyen capturas ni assets de procedencia pendiente. La aplicación no
implementa mapas, geocodificación ni interpretación clínica de documentos.

## Arquitectura y estructura

```text
UI → servicios/validación → repositorios → SQLite
                         → archivos administrados y backups
```

| Ruta | Contenido |
| --- | --- |
| `app/` | UI, servicios, validación, persistencia y rutas |
| `app/migrations/` | Actualizaciones SQLite ordenadas y transaccionales |
| `run.py` | Arranque y preparación del directorio de datos |
| `tests/`, `tests/fixtures/` | Pruebas y ejemplos exclusivamente sintéticos |
| `tools/` | Smoke, planes SQL y exportación de fuente sin historial |
| `docs/` | Arquitectura, desarrollo, deployment y checklists |
| `OncaAlumnos.spec`, `build_release.py` | Configuración y proceso Windows |

Consulta [arquitectura](docs/architecture.md), [desarrollo](docs/developer-guide.md)
y [deployment](docs/deployment.md).

## Requisitos

Windows x64 y **Python 3.11.17 con Tcl/Tk** para el entorno validado. Se comprobaron
Tcl/Tk 8.6.15 y SQLite 3.53.1. Otras versiones/sistemas requieren validación.
El runtime utiliza solo la biblioteca estándar; `requirements.txt` no instala
paquetes externos. Las herramientas de build se fijan en `requirements-dev.txt`.

## Ejecutar desde código fuente

Descomprime la fuente y abre PowerShell en su carpeta. Con Python compatible:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe run.py
```

Para preparar el intérprete validado con uv, consulta la [guía de desarrollo](docs/developer-guide.md).
No necesitas activar el venv ni permisos de administrador para ejecutar ONCA.

## Ejecutar tests

```powershell
$env:ONCA_GUI_TESTS = '1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m compileall -q app run.py tools tests
.venv\Scripts\python.exe tools/check_query_plans.py
.venv\Scripts\python.exe tools/smoke_test.py
.venv\Scripts\python.exe tools/public_snapshot.py --check
```

GUI requiere escritorio. Sin `ONCA_GUI_TESTS=1` se omiten esas pruebas. Tests y
smoke usan SQLite temporal/en memoria, sin conectar con instalaciones privadas.

## Generar aplicación Windows

**No hay un nuevo build autorizado en esta RC.** El procedimiento siguiente es
para ejecutarse después de revisión/aprobación:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe build_release.py --output dist-reviewed
.venv\Scripts\python.exe tools/smoke_test.py dist-reviewed/OncaAlumnos.exe
```

El destino debe ser nuevo. Se generan EXE, manifest, checksum y avisos de terceros.
Se distribuyen juntos, excluyendo `work/`. El workflow Windows es manual y no publica.

## Datos y almacenamiento

Por defecto se escribe en `%LOCALAPPDATA%\OncaAlumnos\`: `onca.db`, `certificados/`,
`backups/` y `logs/technical.log`. No se escribe junto al EXE ni en Program Files.
No hay configuración secreta ni lectura automática de `.env`. `ONCA_DATA_DIR`
puede seleccionar otra carpeta absoluta y escribible antes de arrancar.

El primer inicio crea carpetas y schema 4 con **cero alumnos, pagos, certificados,
actividades y participaciones**. No hay seeds. Reiniciar no crea registros.
Los catálogos de cintas y opciones se definen en código.

## Backups

Menú Datos: crear, validar y restaurar. Hay backup diario al arrancar y antes de
migrar una instalación anterior. Se verifican SQLite, FK, adjuntos y SHA-256.
Restore publica una carpeta nueva; el usuario la activa tras cerrar ONCA.
Un primer inicio normal puede crear un backup de la base vacía, no datos de ejemplo.
Más detalles en [datos y privacidad](docs/data-and-privacy.md).

## Privacidad y seguridad

La fuente candidata excluye bases, adjuntos, backups, logs, secretos y datos reales.
Los ejemplos sintéticos quedan en tests y no se incorporan al paquete Windows.
Nunca adjuntes datos personales a issues, PR, capturas o logs de diagnóstico.
El historial original conserva información privada: publicar solamente la copia
revisada sin `.git`, después de completar la [checklist](docs/release-checklist.md).

El almacenamiento y los backups no tienen cifrado/autenticación propios. Protege
el perfil de Windows y usa copias privadas. Los logs registran eventos/tipos de
error, sin valores personales. SHA-256 detecta corrupción, no autoría.

## Limitaciones conocidas

- Sin revisión humana completa de DPI, formularios y EXE de esta RC.
- Sin firma digital, instalador o actualización automática.
- Listados completos, sin paginación; no es una base multiusuario en red.
- Dinero calculado con Decimal, conservando columnas REAL históricas en SQLite.
- Certificados se verifican por el usuario; la firma básica del archivo no es antivirus.
- No importa automáticamente TXT antiguos ni elimina respaldos por retención.

## Contribuir

Usa una rama de trabajo, datos sintéticos y pruebas para cambios de persistencia.
Describe problema, comportamiento y verificaciones. No publiques historial ni
material privado. Las contribuciones originales se reciben bajo Apache-2.0.

## Licencia

El código y la documentación originales están bajo [Apache-2.0](LICENSE),
con atribución en [NOTICE](NOTICE). Permite uso comercial y modificaciones privadas,
conservando licencia/avisos y señalando cambios al redistribuir.
Consulta [la decisión](LICENSE-DECISION.md); las dependencias conservan sus
[avisos de terceros](THIRD_PARTY_NOTICES.md) y [licencias propias](docs/dependencies-and-licenses.md).
La publicación de esta RC sigue pendiente de revisión; sigue la
[guía de publicación](docs/publication-guide.md).
