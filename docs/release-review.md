# Revisión de Release Candidate — 2026-10-06

## Alcance

Preparación local de fuente desde v4, sin publicación, push, tag, cambio de visibilidad
o EXE nuevo. Se mantiene la arquitectura y se conserva la eliminación local del
informe de mapas encontrado al comenzar. Se retiran referencias públicas rotas.

Versión elegida: 0.9.0-rc1. No se declara 1.0 estable porque faltan pruebas humanas,
validación binaria RC y revisión en Windows limpio. Metadata Windows derivada de
app/version.py, numérica y con flag de prerelease.

## Privacidad y limpieza

La fuente candidata no incluye datos de alumnos, pagos, certificados, actividades,
SQLite precreada, backups, logs, archivos .env, claves, assets sin permisos,
entornos, caché, builds o releases previas. Las fixtures necesarias permanecen
en tests; la herramienta de planes SQL las importa desde tests/fixtures y solo
las utiliza en memoria. El runtime nunca las importa ni crea registros de ejemplo.

Las bases locales privadas y distribuciones anteriores con registros se conservaron
intactas: se comprobaron en modo de solo lectura y no se exportaron. Limpieza de
distribución significa exclusión, no borrado de información del usuario.

Se revisaron archivos actuales, rutas/extensiones, inventario local y 1933 blobs
del historial alcanzable inicial. Patrones de claves privadas/tokens conocidos:
sin candidatos detectados. Inspección de contenido limitada a blobs de hasta 2 MB;
no garantiza detectar todo secreto arbitrario, contenido médico de imágenes o
refs remotas/desconocidas. La fuente se comprueba además con el exportador.

El historial original contiene un log con nombres/fechas, un adjunto de procedencia
no acreditada y rutas personales de un entorno. **No publicar ese historial.**
No se reescribe ni purga; la candidata reutiliza el exportador sin .git.
La revisión no expone nombres, teléfonos, contenido médico o rutas personales
en este documento. Copyrights/avisos públicos de dependencias se preservan por licencia.

## Preparación

- Fuente y Windows Application documentados por separado.
- Primer inicio crea carpetas de usuario y aplica migraciones sin seeds.
- Snapshot bloquea archivos privados/binarios, symlinks y patrones sensibles.
- Metadata RC comprobable sin cargar Analysis/PyInstaller.
- Avisos originales/vendor NOTICE preparados; falta inventario del nuevo binario.
- CI valida fuente y tests; build sigue manual, con aprobación y sin publicación.
- Runtime sin paquetes externos; siete pins de build conservados y revisados.
- pip-audit 2.10.1 sobre los siete pins: sin vulnerabilidades conocidas encontradas.
- Apache-2.0 incorporada por delegación explícita del propietario, con LICENSE/NOTICE.

## Resultados de la candidata inicial

**VERIFIED AUTOMATICALLY:** 209 passed / 0 failed / 0 skipped en un venv nuevo
de Python 3.11.17, con GUI habilitada (171 de lógica y 38 de GUI). Migraciones:
15 tests aprobados. Pip check de runtime/build, compileall, planes SQL y smoke
source con dos aperturas/cinco tablas vacías: OK. Escaneo actual de 83 archivos
de fuente: sin patrones bloqueados.

La copia exportada sin historial también ejecutó los **209 tests**, todos aprobados
sin omisiones, desde su propia carpeta y con el venv limpio. Smoke de dos aperturas,
pip check y planes SQL: OK. Se verificaron sus 83 archivos y 28 enlaces locales de
documentación; no contiene caché, historial o datos privados. Los hashes de las
bases locales auditadas y del EXE validado anterior no cambiaron. Estos resultados
no se presentan como CI remoto o revisión humana. La candidata se prepara en
release-candidate/source-v0.9.0-rc1; se conserva fuera del índice Git.

**VERIFIED MANUALLY:** ninguna prueba humana realizada.
**CI: NOT VERIFIED** — no push ni ejecución remota de Actions.
**BUILD: NOT EXECUTED — waiting for final user approval.**
El EXE validado anterior conserva su checksum y no representa esta candidata.

## Bloqueos de publicación

Derechos sobre aportaciones ajenas, autorización de publicación, CI verde observado,
revisión humana y —para Windows— build/avisos/checksum/prueba limpia.
La rama original con historial privado no es un repositorio público preparado.
El snapshot de fuente es el material de revisión; no supone aprobación de deployment.

## Licencia y nueva copia de revisión

El propietario delegó la selección de licencia: Apache-2.0 elegida por su uso
comercial permitido, modificaciones privadas y concesión expresa de patentes.
Texto oficial íntegro en LICENSE; atribución colectiva en NOTICE sin inventar
un titular personal. Dependencias conservan sus licencias. La revisión de derechos
ajenos sigue correspondiendo al propietario; no se distribuyen assets de origen incierto.

La nueva candidata licenciada se prepara en release-candidate/source-v0.9.0-rc1-licensed,
sin reemplazar la copia anterior. La [guía](publication-guide.md) distingue pasos
de revisión local, CI privada y publicación de fuente de los del futuro EXE.

**VERIFIED AUTOMATICALLY, fuente licenciada:** suite completa repetida con GUI,
209 passed / 0 failed / 0 skipped, tanto en workspace como en copia exportada
sin historial. Se revisaron 86 archivos y 46 enlaces locales de documentación.
Pip check, planes SQL y smoke de dos aperturas/cinco tablas vacías: OK.
La prueba de avisos conserva LICENSE/NOTICE y no ejecuta PyInstaller.
Hashes de bases locales y EXE anterior sin cambios. No se afirma una nueva
auditoría online de vulnerabilidades: permanece el resultado de preparación anterior.

**READY FOR PUBLIC SOURCE RELEASE: NO** hasta checklist manual, derechos del
propietario, CI remoto y autorización final. **READY FOR SOURCE REVIEW: YES**.
CI y revisión humana siguen NOT VERIFIED; build sigue NOT EXECUTED.
