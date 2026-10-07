# Deployment y distribución

## Estado y tipos de entrega

**BUILD: NOT EXECUTED — waiting for final user approval.**
Esta RC prepara fuente/configuración; los comandos de compilación de esta guía
no se han ejecutado para la RC. No reemplazar ejecutables o releases anteriores.

- SOURCE RELEASE: app, documentación pública, tests/fixtures sintéticas,
  herramientas, requirements, licencias y configuración; sin .git ni datos.
- WINDOWS APPLICATION: EXE nuevo, manifest, SHA256SUMS y avisos originales;
  nunca tests, fixtures, SQLite precreada, logs, backups, work o entornos.

Versión única: app/version.py. La RC usa SemVer con sufijo rc; la metadata Windows
usa cuatro enteros y flag de prerelease. No se prometen bytes idénticos entre builds,
sí un procedimiento verificable con herramientas/runtime fijados.

## 1. Requisitos

Windows x64 y entorno Python 3.11.17/Tk validado. Destino de salida nuevo.
Revisar [licencias](dependencies-and-licenses.md), [decisión Apache-2.0](../LICENSE-DECISION.md)
y [checklist](release-checklist.md). No incluir branding de procedencia pendiente.

## 2. Preparar entorno limpio

Desde la fuente revisada, con Python compatible:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.venv\Scripts\python.exe -m pip check
```

Para preparar exactamente Python 3.11.17 con uv, seguir [developer guide](developer-guide.md).
El runtime no necesita paquetes PyPI; los siete pins corresponden al build.

## 3. Tests y verificación de datos

```powershell
$env:ONCA_GUI_TESTS = '1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q app run.py tools tests
.venv\Scripts\python.exe tools/public_snapshot.py --check
.venv\Scripts\python.exe tools/check_query_plans.py
.venv\Scripts\python.exe tools/smoke_test.py
```

El smoke usa un directorio temporal y comprueba alumnos/pagos/certificados/
actividades/participaciones vacíos tras dos aperturas. No usa bases de desarrollo.
Los tests de primer inicio comprueban carpetas, schema, idempotencia y conservación
de registros del usuario al reiniciar. Las migraciones 0–4 se prueban con datos sintéticos.

## 4. Limpieza y snapshot

No borrar instalaciones ni distribuciones previas para limpiar. Preparar una
carpeta nueva desde commits revisados:

```powershell
$rcVersion = .venv\Scripts\python.exe -c "from app.version import __version__; print(__version__)"
.venv\Scripts\python.exe tools/public_snapshot.py --output ("release-candidate/source-v" + $rcVersion)
```

Excluye docs/changes internos, .git, .private, bases, adjuntos, backups/logs,
caché y binarios. Archivos inesperados bloquean exportación. Revisar la copia
resultante; no adjuntar la carpeta original ni copiar archivos locales a mano.
No se sobrescribe un destino existente. Si hay correcciones, usar otro destino
de revisión sin destruir la candidata anterior.

## 5. Construir Windows — solo después de aprobación

```powershell
.venv\Scripts\python.exe build_release.py --output ("dist-v" + $rcVersion)
.venv\Scripts\python.exe tools/smoke_test.py ("dist-v" + $rcVersion + "/OncaAlumnos.exe")
```

Alternativa: build_release.ps1 con OutputDirectory nuevo. OncaAlumnos.spec incluye
schema y SQL 002/003/004; módulos por imports. No incluye tests, data o assets.
El builder nunca fusiona ni limpia una distribución existente.

## 6. Avisos, checksums y revisión

Resultado futuro: OncaAlumnos.exe, build-manifest.json, SHA256SUMS.txt,
THIRD_PARTY_NOTICES.md, carpeta THIRD_PARTY_NOTICES, LICENSE y NOTICE.
work contiene diagnóstico/rutas del constructor: no distribuirlo.

```powershell
Get-FileHash ("dist-v" + $rcVersion + "/OncaAlumnos.exe") -Algorithm SHA256
Get-Content ("dist-v" + $rcVersion + "/SHA256SUMS.txt")
Get-Content ("dist-v" + $rcVersion + "/build-manifest.json")
```

El builder conserva textos originales de Python/Tcl/Tk y herramientas/vendor
NOTICE. Verificar el inventario real de DLL/hook incluido antes de publicar;
este control binario queda pendiente porque no hay un nuevo EXE.
No distribuir datos, certificado o log de una instalación de prueba.

## 7. Primer inicio y permisos

Por defecto se crean en %LOCALAPPDATA%/OncaAlumnos:
onca.db, certificados/, backups/, logs/ y el lock de operaciones.
No hay carpeta de configuración secreta ni lectura .env.
No se escribe en Program Files, junto al EXE o dentro de sys._MEIPASS.
ONCA_DATA_DIR permite una ruta absoluta alternativa con permisos de escritura.

Primer inicio aplica migraciones y no crea alumnos/pagos/actividades/certificados.
El backup diario de una base nueva es una copia vacía, creada en el perfil,
nunca un backup preincluido. Evitar directorios compartidos en red.

## 8. Actualización, reinstalación y restauración

1. Cerrar ONCA, crear/verificar backup y conservar la aplicación anterior.
2. Instalar/descomprimir el ejecutable nuevo sin reemplazar los datos del perfil.
3. Abrir: una migración pendiente exige respaldo completo antes del upgrade.
4. Revisar con datos sintéticos en Windows limpio antes de instalar sobre datos reales.

Reinstalar la app no debe borrar el directorio de datos. Para recuperar,
usar Datos → Restaurar en carpeta nueva y activar la carpeta indicada con
ONCA_DATA_DIR tras cerrar. No copiar una SQLite abierta con herramientas de archivos.
Un downgrade no admite schema futuro; utilizar un backup compatible en otra carpeta.

## 9. CI y publicación futura

tests.yml valida instalación, tests/GUI, pip check, source scan, compile y smoke.
build-windows.yml solo se ejecuta manualmente tras aprobación y entrega un artifact
de revisión; no publica Releases. CI remoto verde aún no verificado en esta RC.

Apache-2.0 está incorporada. La publicación requiere revisión humana, CI observada,
build nuevo/checksum/avisos y autorización explícita. Historial original contiene
datos privados: usar fuente sin .git y una publicación nueva revisada. No generar
tags, push, Release o cambio de visibilidad como parte de la preparación.
Pasos concretos para el propietario: [guía de publicación](publication-guide.md).
