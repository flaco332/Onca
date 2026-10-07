# Guía de desarrollo

## Entorno y preparación

Windows x64, Python 3.11.17 con Tk 8.6.15 y SQLite 3.53.1 son el entorno validado.
Usa un intérprete con Tk. No se afirma soporte de otros runtimes sin probarlos.

Con el intérprete compatible ya instalado:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pip check
```

Alternativa usada en CI para obtener esa versión Windows:

```powershell
python -m pip install uv==0.12.23
uv python install 3.11.17 --no-bin
uv venv .venv --python 3.11.17 --managed-python --seed
```

uv es herramienta de preparación, no dependencia runtime ni parte del EXE.

## Estructura y ejecución

Consulta [arquitectura](architecture.md). run.py inicia Tk y prepara datos en
worker; app contiene presentación, servicios, repositorios y schema.
tests contiene solo casos sintéticos; fixtures no son seeds de producción.

```powershell
.venv\Scripts\python.exe run.py
```

Para revisar sin acceder a la instalación habitual:

```powershell
$reviewData = Join-Path $env:TEMP ("Onca-review-" + [guid]::NewGuid().ToString('N'))
$env:ONCA_DATA_DIR = $reviewData
.venv\Scripts\python.exe run.py
```

Usa una carpeta escribible vacía y propia para cada revisión. Para volver al
directorio por defecto, quita ONCA_DATA_DIR de esa sesión. No hay lector .env.

## Tests y checks

```powershell
$env:ONCA_GUI_TESTS = '1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m compileall -q app run.py tools tests
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe tools/check_query_plans.py
.venv\Scripts\python.exe tools/smoke_test.py
.venv\Scripts\python.exe tools/public_snapshot.py --check
```

El smoke abre/cierra dos veces y comprueba las cinco tablas vacías. GUI requiere
escritorio; sin la variable se omite su cobertura. No hay pytest/lint/type checker
configurados. No presentes checks omitidos como ejecutados.

## Migraciones y campos nuevos

1. Añadir SQL numerado consecutivo en app/migrations y callback al registro.
2. Incrementar CURRENT_SCHEMA_VERSION y extender validación del nuevo schema.
3. No duplicar una columna en schema inicial y ALTER: nuevas bases recorren todas
   las versiones. Conservar el baseline y los contratos de versiones anteriores.
4. Añadir el SQL explícitamente a OncaAlumnos.spec.
5. Probar upgrade, rollback completo, respaldo previo y datos conservados.

No usar executescript en el upgrade transaccional ni inferir identidades/nombres
históricos. Agregar campos a StudentDraft/proyección/repositorio/servicio y después
al formulario. Validación central, errores por campo; no ejecutar SQL desde widgets.

## Servicios y tests

Operaciones de dinero usan Decimal, de fechas las reglas comunes y de alumnos ID.
Writes relacionados comparten una transacción; workers no reciben widgets/conexiones.
Adjuntos nuevos deben usar rutas administradas. Logs solo con eventos permitidos.

Cada test usa SQLite temporal/en memoria y archivos explícitamente sintéticos.
Reutiliza tests/fixtures para datos de herramientas. No exportes datos de usuarios
ni adaptes una base real como fixture. Prueba fallos de persistencia/rollback,
homónimos, selección y compatibilidad, no solo casos felices.

## Preparar una release

La versión se cambia exclusivamente en app/version.py; la metadata Windows y
About/manifest derivan de ella. Añade una entrada real a CHANGELOG.
Revisa licencias, checklist y fuente; haz commits pequeños antes del snapshot:

```powershell
$rcVersion = .venv\Scripts\python.exe -c "from app.version import __version__; print(__version__)"
.venv\Scripts\python.exe tools/public_snapshot.py --output ("release-candidate/source-v" + $rcVersion)
```

El exportador usa HEAD limpio, no historial. Excluye informes internos de
docs/changes, datos, binarios y entornos; rechaza patrones sensibles y destinos
existentes. La copia fuente conserva tests; el paquete Windows no los incorpora.
No publicar la rama original con su historial privado.
Ver [deployment](deployment.md) y [checklist](release-checklist.md).

## Troubleshooting

- Tk no importa: usar la distribución de Python con Tcl/Tk validada.
- Acceso denegado: revisar permisos y ONCA_DATA_DIR; no ejecutar como administrador
  para escribir junto al EXE.
- Migración bloqueada: verificar/restablecer adjuntos o un respaldo completo.
- Base de versión futura: no forzar downgrade; restaurar una copia compatible.
- Snapshot rechazado: revisar archivos señalados, hacer commit y elegir destino nuevo.
- Error de saldo: corregir costo/pagado; no ignorar el límite ni redondear datos inválidos.
- Fotos/PDF: revisar límites y formato; la app no valida seguridad clínica/documental.
