# Ajustes de UI y calidad de datos — 2026-10-05

## 1. Objetivo

Corregir campos y estados de alumnos, mejorar formularios y conservar los datos.
Continuar v2 sin reimplementar persistencia, backups ni arquitectura.
Estado: **READY FOR PUBLIC SNAPSHOT REVIEW**, con licencia y revisión humana pendientes.
No autoriza publicar el historial original ni una Release.

## 2. Estado inicial

Base `refactor/pre-public-hardening-v2`, HEAD `878c91f390f92860b09a1fe83ffb80e86fbcffa0`.
Working tree limpio, cinco commits v2, baseline 78 tests. Se revisaron status,
diff, log, remoto y reporte anterior antes de modificar. Rama nueva desde ese HEAD:
`feat/ui-data-quality-v3`. Rama base y snapshot v2 conservados.

## 3. Arquitectura encontrada

```text
run.py                         arranque y preparación
app/ui.py, activity_form.py     Tkinter/ttk, selección y formularios
app/*_service.py                validación y coordinación de operaciones
app/*_repository.py             SQL parametrizado
app/database.py                 conexiones, transacciones y foreign keys
app/migrations/                 schema mediante user_version
app/paths.py, certificates.py   recursos y archivos administrados
app/certificate_service.py     adjuntos y compensación ante fallos
app/backups.py, data_access.py  backup/restore y locks
app/theme.py                    estilos compartidos
tests/                         unittest, datos sintéticos y GUI optativa
tools/                         smoke, planes SQL y exportación sin historial
.github/workflows/              tests y build manual
docs/                          documentación técnica
```

UI → servicios → repositorios → SQLite; sin SQL desde widgets. Información médica:
estado de alumno y referencias en `medical_certificates`, no un módulo clínico.
`models.py` contiene `StudentDraft`. Persisten UI grande, estados en diccionarios
y configuración global de rutas. Se conserva la estructura; controles nuevos
justificados por reutilización, sin framework adicional.

## 4. Archivos modificados

Nuevos: `app/form_widgets.py`, `app/date_picker.py`, `app/student_options.py`,
`app/migrations/003_medical_verification.sql`, `tests/test_data_quality.py` y este documento.

Aplicación: `app/errors.py`, `validation.py`, `student_service.py`,
`students_repository.py`, `medical_repository.py`, `logic.py`, `theme.py`, `ui.py`,
`activity_service.py`, `activity_form.py`, `migrations/__init__.py`, `OncaAlumnos.spec`.
Tests: `test_validation.py`, `test_gui.py`, `test_migrations.py`, `test_hardening.py`.
Docs: README, CHANGELOG, architecture, development, deployment, data-and-privacy,
performance-and-complexity y manual-validation. Eliminados: ninguno.
Requirements, workflows, assets, datos y snapshots no se modificaron.
Total frente a v2: 30 archivos (6 nuevos y 24 modificados), aproximadamente
1 200 líneas añadidas y 200 retiradas, incluidas pruebas y documentación.

## 5. Teléfonos

`phone_error()` acepta dígitos ASCII, espacios, +, guiones y paréntesis. Valida
7–15 dígitos, + solo al inicio y paréntesis equilibrados, sin imponer país.
Conserva formato; un límite adicional de 80 caracteres evita separadores ilimitados.
Vacío opcional. Principal/emergencia comparten reglas al editar y guardar.
Letras, saltos de línea y símbolos arbitrarios se rechazan. Sin reescritura histórica.

## 6. Cintas/grados

Causa: concatenación de literales Python por dos comas faltantes. `BELT_RANKS`
contiene 15 opciones independientes, incluidas Marrón, Marrón avanzada, Roja y
Roja avanzada. Test de cantidad/unicidad/opciones. Grados históricos incorrectos
se conservan: no se puede inferir cuál de los concatenados correspondía al alumno.

## 7. Pagos

Fecha ausente/inválida → `None`, celda Pago → `""`. Antes se sustituía por hoy,
inventando 30 días. Recordatorios omiten esos casos y conservan cálculos reales.
Entrada nueva vacía; guardar datos generales no registra pagos. Fecha/monto
muestran errores inline con `parse_iso_date()` y `parse_amount()` compartidos.

## 8. Certificado médico

Schema 3: `students.medical_verified INTEGER NOT NULL DEFAULT 0 CHECK (...0,1)`.
La casilla histórica no estaba persistida: un archivo no prueba verificación.
Migración conservadora inicia desmarcada, sin tocar adjuntos, con transacción
y respaldo previo de instalaciones antiguas. Columnas/FK siguen verificándose.

Columna estrecha ✓ desde estado persistido. Adjuntar PNG/PDF no verifica.
**Guardar verificación** persiste la casilla y recarga la tabla. Cambios pendientes
del widget no alteran el indicador. Puede confirmarse sin archivo adjunto.
Desvincular desmarca y conserva archivos. Ediciones programáticas que omiten el
booleano lo preservan. Backup/restore conserva el estado; no se interpreta contenido médico.

## 9. Actividades

`ScrollableFrame`: scrollbar, rueda y desplazamiento por foco, mínimo 420×280,
altura inicial ajustada a pantalla. Enlaces locales, sin `bind_all`. Text conserva
su scroll; el foco de Guardar revela el botón. Revisión humana de DPI aún pendiente.

Columna Actividad: menor fecha ISO válida desde hoy para participación Pendiente/
Confirmado (`registered`, `pending`, `confirmed`). Cancelado/Asistió/No asistió y
fechas pasadas se omiten; sin coincidencias, vacío. Agregado por ID en una consulta.
Crear/editar/quitar recargan indicadores. Reglas de campos compartidas con servicios;
destinatarios fijados al abrir el diálogo, como en v2.

## 10. Fecha de nacimiento

`BirthDatePicker`: selector Año → Mes → Día, no cuadrícula mensual; facilita años
históricos sin navegar cientos de meses. Entrada ISO manual conservada. Abrir o
cancelar no modifica datos. Ajusta días al cambiar mes/año; rechaza futuro al confirmar.
Lista años desde 1900 y permite años anteriores de registros existentes; entrada
manual admite otras fechas históricas válidas de Python. `parse_birth_date()` y
`birth_date_from_parts()` validan ISO/bisiestos/futuro. Sin dependencia ni migración de nacimiento.

## 11. Selección múltiple

Listbox `selectmode="multiple"`, `exportselection=False`: clic añade, repetir
desmarca sin Ctrl; flechas y Espacio nativos. Sin lógica basada en coordenadas
absolutas. Los tests simulan clic usando bbox y comprueban selección/teclado.

## 12. Validación inline

`InlineEntry` actualiza mensaje rojo mediante StringVar. `FieldValidationError`
separa errores por campo de presentación. Datos generales, nacimiento, teléfonos,
pagos y campos principales de actividad usan reglas centrales. Notas de alumno
se validan al escribir/perder foco/guardar; notas de actividad al guardar.
Fecha médica inválida bloquea guardado con error inline. Se conservan diálogos
técnicos, de selección requerida y destructivos; éxito de actividad usa barra de estado.

## 13. Mejoras de rendimiento

Antes no había indicador de actividad; no se inventa benchmark comparativo.
Nuevo agregado SQL sin n consultas Python por n alumnos; test de trace verifica
un SELECT para el listado. Estado médico sin acceso al filesystem por fila.
Agrupar r participaciones puede costar O(r log r), según plan SQLite. El ordenamiento
de UI sigue O(n log n); teléfono O(L). No se afirma mejora asintótica del listado
ni se añaden índices. Se eliminan bloques de validación modal duplicada en pagos
y actividades. `tools/check_query_plans.py` pasó con datos sintéticos; últimos
pagos/certificados conservan índices compuestos sin ordenamientos temporales.

## 14. Tests añadidos

78 → **127**, incremento de 49: 108 de lógica y 19 de GUI. Nuevos casos de
teléfono, fechas, cintas, pagos ausentes/incompletos, verificación/constraints,
migración 2→3 y rollback, backup/restore, próximas actividades por ID/consulta
única, inline, selector, PNG/PDF sintéticos, tabla, scroll/foco y multiselección.
No se retiró cobertura funcional v2 ni se introdujeron datos reales.

## 15. Resultados automáticos

**VERIFIED AUTOMATICALLY:** Windows x64, Python 3.11.17, Tcl/Tk 8.6.15, SQLite
3.53.1. Venv nuevo de runtime e instalación de requirements sin paquetes externos.
Build con herramientas fijadas existentes: PyInstaller 6.20.0 y hooks 2026.5.

```powershell
$env:ONCA_GUI_TESTS = '1'
python -m unittest discover -s tests -v
python -m compileall -q app run.py tools tests
python -m pip check
python tools/check_query_plans.py
python tools/smoke_test.py
python build_release.py --output CARPETA_NUEVA
python tools/smoke_test.py CARPETA_NUEVA/OncaAlumnos.exe
git diff --check
```

127 passed / 0 failed / 0 skipped. Compile, pip check, planes SQL y ambos smoke: OK.
EXE: `.private/v3-work/build-validated/OncaAlumnos.exe`, 13 469 900 bytes.
SHA-256: `ce0f938b51ace6685486e16437f5af0193c3120fb3d0428803aff37704443f94`.
Checksum, manifest schema 3 y avisos de terceros generados. Archive inspeccionado:
schema.sql, migraciones 002/003; sin rutas personales en co_filename de aplicación.
`work/` excluido de distribución. Smoke EXE cubre arranque/base vacía/cierre,
no todos los formularios del binario.

pytest, lint y type checking: **NOT EXECUTED**, sin configuración en este proyecto
de unittest. Auditoría online de vulnerabilidades: **NOT EXECUTED** en v3;
dependencias no cambian respecto al inventario/auditoría v2. CI real: **NOT EXECUTED**,
sin push. No se equiparan controles automáticos con revisión visual/DPI humana.

## 16. Pruebas manuales pendientes

**VERIFIED MANUALLY: ninguna. NOT VERIFIED:** revisión humana y escalas Windows.
Usar instalación y archivos sintéticos; registrar resultados sin datos personales.

- [ ] Teléfono mexicano.
- [ ] Teléfono internacional.
- [ ] Errores inline se actualizan/desaparecen sin modal.
- [ ] Fecha de nacimiento manual ISO, histórica y rechazo de futuro.
- [ ] Calendario/selector Año → Mes → Día, bisiestos y cancelar.
- [ ] Cintas separadas: Marrón, Marrón avanzada, Roja, Roja avanzada.
- [ ] Alumno sin pago: celda completamente vacía.
- [ ] Alumno con pago: cálculo, editar/eliminar.
- [ ] Certificado médico: marcar/desmarcar y guardar.
- [ ] Indicador ✓ persiste; adjuntar no marca automáticamente.
- [ ] PNG certificado: adjuntar, preview, abrir, desvincular.
- [ ] PDF certificado: adjuntar, abrir con visor, desvincular.
- [ ] Agregar actividad, editar/quitar; conservar destinatarios.
- [ ] Scrollbar/rueda actividad en pantalla pequeña; Guardar accesible.
- [ ] Actividad en tabla: solo próxima fecha; cancelada/pasada excluida.
- [ ] Selección múltiple sin Ctrl: añadir/desmarcar.
- [ ] Modo oscuro y contraste de controles nuevos.
- [ ] DPI 100%.
- [ ] DPI 125%.
- [ ] DPI 150%.
- [ ] Navegación con teclado, foco, flechas y Espacio.
- [ ] Source: guardar/cerrar/reiniciar.
- [ ] EXE empaquetado: formularios, guardar/cerrar/reiniciar.
- [ ] Backup/restore conserva adjuntos/verificación en carpeta nueva.

## 17. Evaluación del minimapa

No implementado; lugar textual offline conservado. Fuentes oficiales consultadas
el 2026-10-05. La integración propuesta no está validada en ONCA.

| Alternativa | Integración y límites offline |
| --- | --- |
| OpenStreetMap | Cartografía, no widget Tk. Requiere atribución; el servidor público raster prohíbe offline/prefetch. Necesita tiles propios o proveedor que permita distribución offline. [Política OSM](https://operations.osmfoundation.org/policies/tiles/) |
| Leaflet/HTML | Biblioteca JS con clics, marcadores/coordenadas. En Tk requiere motor de navegador y puente de selección, aumentando packaging (evaluación arquitectónica). JS/HTML local no incluye cartografía; necesita tiles autorizados. [Leaflet](https://leafletjs.com/reference.html) |
| TkinterMapView | Widget Tk con marcadores/base offline; repositorio con librerías de imagen/red/geocodificación. Auditar dependencias de una versión concreta. Caché offline no concede derechos sobre tiles. [Repositorio](https://github.com/TomSchimansky/TkinterMapView), [requirements](https://github.com/TomSchimansky/TkinterMapView/blob/main/requirements.txt) |

Propuesta: mantener lugar textual; latitud/longitud opcionales mediante migración
independiente, finitas y en -90..90/-180..180. Selector optativo, sin impedir guardar
sin Internet/mapas. Definir área/zoom/tamaño/derechos de mapas locales antes de elegir
widget; probar Windows/PyInstaller y privacidad de red. No enviar datos de alumnos
a proveedores ni añadir claves, servidores, descargas de mapas o costos ahora.

## 18. Riesgos o deuda técnica restante

- Licencia propia pendiente; no se crea LICENSE ni se presumen permisos de assets.
- Historial original conserva riesgos documentados en v2; revisar copia sin .git.
- UI grande, dicts, CRUD/listados síncronos y completos; medir antes de más refactor.
- Sin corrección automática de grados concatenados o inferencia médica histórica.
- Actividad próxima se recalcula al cargar/refrescar, sin timer de medianoche.
- Adjuntos faltantes bloquean backup/migración segura; backups sin cifrado/autenticación.
- EXE sin firma; formularios completos/DPI/CI real pendientes.
- Python 3.12 y otros sistemas no validados ni declarados soportados en esta fase.

## 19. Estado Git

Rama `feat/ui-data-quality-v3`, sin upstream. `origin` conserva el repositorio
privado original. Lectura `git ls-remote --heads origin`: solamente `master` en
`c5716c213c2bddcc68935a539fd2c2d566833ae0`. Sin fetch, push, Release, cambio de
visibilidad o remotes. Commits locales de código/pruebas:

- `4cf30d7`: teléfonos y validación inline.
- `ad26667`: estados, cintas, migración médica y actividad próxima.
- `4009c76`: selector, actividad desplazable y multiselección.
- `f294560`: conservación médica en backup/restore.

Un quinto commit documental cierra la fase. Tras él: working tree limpio,
sin untracked, 11 ahead / 0 behind frente a `origin/master` (no es upstream).
Ready to push: YES solo al remoto privado tras autorización; ready for public
review: YES para material revisable sin historial, no autorización de publicación.

`.gitignore` conserva exclusiones de bases, adjuntos, logs, backups, exports,
config local, builds, venvs y workspace privado. Escaneo de archivos versionados:
palabras/formatos de credenciales, rutas personales, archivos privados y tamaños;
sin valores sensibles nuevos. No garantiza ausencia de toda información sensible
posible en el historial. No se tocaron datos privados ni se sobrescribieron snapshots.

## 20. Recomendación para siguiente iteración

Completar checklist con datos sintéticos/DPI reales, decidir licencia y revisar CI
cuando se autorice enviar trabajo. Después crear otra copia desde HEAD revisado,
sin historial/workspace privado, preservando v2. Mantener minimapa separado y
priorizar evidencia de uso antes de dependencias o reorganizaciones mayores.
