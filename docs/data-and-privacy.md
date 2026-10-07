# Datos y privacidad

## Almacenamiento

ONCA guarda nombres, fechas de nacimiento, teléfonos, contactos de emergencia,
rango, notas, pagos, fechas de certificados, rutas/hash de adjuntos, actividades,
lugares, costos, asistencia y participaciones. Son datos locales del usuario.
También guarda un estado explícito de verificación médica. No se calcula a partir
de la existencia de un adjunto; no constituye una evaluación médica automática.

Directorio por defecto: `%LOCALAPPDATA%\OncaAlumnos`. `ONCA_DATA_DIR` permite
seleccionar otro directorio absoluto antes de arrancar. No hay importación
silenciosa ni conexión a servidores.

```text
OncaAlumnos/
├── onca.db
├── certificados/YYYY/MM/<uuid>.png|pdf
├── logs/technical.log
├── .operation.lock
└── backups/<fecha-UTC>_<identificador>/
    ├── onca.db
    ├── certificados/<uuid>.png|pdf
    └── manifest.json
```

Los directorios heredados `control_alumnos/certificados` se incluyen como
adjuntos en backups. TXT/logs/exports de formatos antiguos no se importan ni
se incluyen en el respaldo: si necesitas conservarlos, gestiona una copia
privada separada con la aplicación cerrada.

## Respaldos

Menú **Datos → Crear respaldo**. También hay respaldo automático por día UTC
al iniciar (excepto smoke tests) y antes de migrar una instalación existente.
El proceso usa `sqlite3.Connection.backup()`; no copia una SQLite activa con
`shutil.copy`. La base y sus adjuntos se coordinan bajo un lock de aplicación.
Se conservan también archivos administrados no referenciados, para recuperación.

El manifest contiene formato, versión ONCA, fecha UTC, schema version e
inventario SHA-256. Se validan contenido, SQLite, FK, rutas y referencias antes
de publicar el directorio del backup. Las referencias históricas absolutas se
normalizan solo en la base de la copia; el original no se modifica.
Un adjunto faltante hace fallar un respaldo completo: revisa/restablece ese
archivo o desvincula conscientemente su referencia desde la UI.

Menú **Datos → Validar respaldo** verifica un directorio existente. No basta
con que exista `manifest.json`. SHA-256 detecta corrupción, no autenticidad:
solo restaura respaldos de procedencia confiable. No hay cifrado ni retención
con eliminación automática. Vigila espacio y conserva copias en otro dispositivo.
El backup diario refleja el momento del inicio, no todos los cambios de la sesión.

## Restauración sin sobrescritura

1. **Datos → Restaurar en carpeta nueva…** y selecciona el respaldo.
2. Confirma: se crea/verifica un respaldo de los datos activos antes de restaurar.
3. Se copian archivos a staging, se verifican y se migran allí si procede.
4. Solo tras completar la validación se publica una carpeta nueva hermana.
5. Cierra ONCA y usa la ruta indicada para activar esa instalación:

```powershell
$env:ONCA_DATA_DIR = (Resolve-Path .\OncaAlumnos-restored).Path
python run.py
# O, para el ejecutable:
.\OncaAlumnos.exe
```

Sustituye la carpeta del ejemplo por la **ruta real mostrada por la aplicación**.
No se reemplaza la base activa. Una falla conserva los datos actuales y el
respaldo previo; solo se limpia el staging creado por esa operación. Un destino
existente o dentro de los datos actuales/respaldo fuente se rechaza.
El directorio restaurado es una instalación, no otro backup: no conserva el
manifest que describía la base antes de migrarla.

## Certificados y traslado

PNG/PDF nuevos: tamaño máximo 32 MiB, firma básica y PNG hasta 6000×6000.
La firma no sustituye un decoder completo ni un análisis antimalware. Los
nombres nuevos no contienen alumnos ni el nombre del archivo de origen.
Se rechazan traversal, rutas nuevas absolutas, nombres reservados y enlaces.
Para mover una instalación nueva, cierra ONCA y traslada juntos base y
`certificados`; las rutas relativas permanecen válidas. Preferible: backup y
restore verificables. Rutas absolutas antiguas se leen si siguen disponibles;
no se reescriben automáticamente en producción. Un backup completo permite
restaurarlas como referencias relativas sin tocar el original.

**Desvincular certificados** borra sus referencias, conservando archivos. La
baja de alumno es lógica; no elimina pagos/certificados. No es una función de
borrado definitivo de información personal.
Desvincular certificados desmarca la verificación. En bases anteriores a schema 3
el estado inicia desmarcado, incluso si hay archivos: revisa y confirma cada caso.
La copia SQLite del backup y la restauración conservan los estados ya guardados.

## Protección

Logs rotados (512000 bytes, tres rotaciones) contienen eventos y clases de error;
no contienen nombres, teléfonos, rutas, montos, notas ni tracebacks. Los logs
no entran en los backups ni en el build.
No hay autenticación/cifrado propio. Usa permisos del sistema, protección del
equipo y copias privadas. Los locks coordinan ONCA, no editores externos;
cierra otros programas que modifiquen los adjuntos durante un respaldo.
No uses un directorio de datos compartido en red como base multiusuario.

El snapshot público excluye bases, certificados, exports, backups, logs,
configuración local y assets sin permisos documentados. Los nombres de pruebas
(incluidos homónimos) son inventados; nunca se extraen de registros privados.

Si falla el respaldo diario de una base ya actualizada, ONCA muestra un aviso
y mantiene la UI disponible para resolver el problema. La migración de una
base antigua sí se bloquea si no puede verificarse su respaldo previo; en ese
caso restablece los adjuntos faltantes o utiliza la versión anterior para
revisar conscientemente las referencias antes de volver a actualizar.
