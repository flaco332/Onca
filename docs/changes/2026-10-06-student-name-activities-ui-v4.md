# Ajustes de alumnos y actividades — 2026-10-06

El bloque inicial registra la primera entrega de v4 y su EXE validado.
La ampliación al final de este documento mantiene esa rama y **no genera build**;
sus cambios nuevos se revisan desde source.

## Motivo y contexto

Continuación de v3 desde `e43db13`, tras revisar status, rama, log, diff y
`2026-10-05-ui-data-quality-v3.md`. El árbol inicial estaba limpio. La fase v3
estaba cerrada: se creó `feat/student-name-activities-ui-v4` desde ese HEAD.
Baseline real: **127 tests aprobados**, incluyendo los 19 de escritorio,
con Python 3.11.17. No se reinició el proyecto ni se cambió su arquitectura.

La arquitectura sigue siendo Tkinter/ttk → servicios → repositorios → SQLite.
Se conservan verificación médica, validación inline, selección por ID,
calendario, formularios desplazables, pagos, adjuntos, backups y multiselección.

## Nombre, Apellidos y presentación

El esquema original ya almacenaba `first_name` y `last_name`. El error estaba
en el formulario único y en `partition(" ")` al guardar, que separaba nombres
compuestos por su primer espacio. Ahora el formulario muestra **Nombre \*** y
**Apellidos** en filas separadas y guarda las partes explícitas. Apellidos es
opcional; no se muestra un diálogo por dejarlo vacío.

Ambos campos usan validación inline compartida: espacios, acentos españoles,
Ñ/ñ, apóstrofes y guiones; nombres y apellidos compuestos intactos. Se conservan
los límites de 200 caracteres por parte y el rechazo de números/símbolos de la
validación existente. No se cambia el contacto de emergencia.

`display_name(first_name, last_name)` es la única composición para presentar
las partes. Omite apellidos ausentes y espacios exteriores, sin `None`, `NULL`
ni marcadores. `join_name` sigue como alias de compatibilidad. El servicio
devuelve las partes y el campo derivado `name`, usado por tabla principal,
título del alumno y selector grupal. Identidad y relaciones siguen por
`student_id`; las participaciones usan `student_activity_id`.

Los clientes antiguos con un borrador que solo contiene `name` guardan ese
texto completo en `first_name`, sin inferir apellidos. Al editar por ID con
el mismo nombre visible antiguo, se conserva la separación existente. Para
cambiar partes explícitas debe enviarse `first_name`/`last_name`. Los helpers
antiguos de separación no se usan en el nuevo guardado ni en la migración.

## Migración y compatibilidad

Schema actual **4**, registrado mediante la infraestructura de `user_version`
y savepoints existente. `004_student_names.sql` queda incluido en PyInstaller.

- Instalaciones normales v0–v3 con `first_name`/`last_name`: se conservan sus
  valores exactos; no se intenta corregir una separación histórica ambigua.
- Tabla antigua compatible con un único `name`: `ALTER TABLE ... RENAME COLUMN`
  conserva el texto íntegro como `first_name`; se añade `last_name TEXT NOT NULL
  DEFAULT ''`. No se reconstruye la tabla ni se modifican los IDs.
- La adopción de esa forma antigua precede los índices de v1/v2 dentro del
  savepoint del upgrade; la versión final se marca en 4. Un fallo revierte
  también el renombrado y la nueva columna.
- La verificación del respaldo admite esa forma antigua únicamente para
  versiones anteriores a 4, exigiendo las demás columnas/tipos/FK del proyecto.
  No se aceptan esquemas arbitrarios o parcialmente separados.
- `init_db()` mantiene el respaldo completo verificado previo a migrar.
  Archivos, pagos, participaciones y verificación médica siguen conservados.

No se abrió ni migró ninguna instalación con datos reales durante este trabajo.
Pruebas y smoke usan exclusivamente bases/archivos sintéticos temporales.

## Búsquedas

No había buscador visual ni una consulta SQL de búsqueda que modificar.
`load_students_from_db(search=...)` ofrece un filtro reutilizable sobre el
nombre de presentación: permite buscar Nombre, Apellidos o Nombre completo
sin distinguir mayúsculas, mediante `casefold()`. Mantiene sensibilidad a los
acentos. El texto no se interpola en SQL: sigue habiendo una sola consulta
para cargar el listado, sin N+1. No se añade un buscador visual en esta fase.

## Actividades extras

La implementación anterior era un `tk.Listbox` con texto concatenado y selección
por posición. Se sustituye por `ttk.Treeview`: **Fecha, Tipo, Lugar, Costo,
Pagado, Estado**. Fecha y estado centrados, importes a la derecha, lugar
expandible, encabezados legibles y selección con el estilo claro/oscuro común.

Scroll vertical para muchos registros; horizontal solo cuando las columnas
exceden el espacio disponible. La tabla se expande con el panel. Una actividad
sin lugar deja la celda vacía; sin pago muestra `$0.00`. Los importes antiguos
NULL se presentan como cero. No hay filas falsas seleccionables para el estado
vacío. Título y notas de actividad/alumno aparecen debajo al seleccionar una
fila, en un área de solo lectura con ajuste de línea y scroll para notas largas.
No se abre otra ventana para consultar esos datos básicos.

La sección incluye historial y futuros. Se conserva el orden explícito existente
`ORDER BY ea.activity_date DESC, sa.student_activity_id DESC`: fechas mayores
primero y desempate estable por participación. La selección sobrevive a recargas
por ID, aunque cambie la posición. Se conservan agregar, doble clic/ver-editar,
quitar y actividad grupal. El indicador principal de próxima actividad mantiene
su consulta/reglas separadas sin cambios.

**Estado sigue mostrando participación/asistencia**, como en el sistema previo:
Pendiente, Confirmado, Asistió, No asistió, Cancelado. Costo y Pagado muestran
los importes reales; no se introduce un estado de pago inferido que confunda
asistencia con saldo. El ejemplo inicial de Pagado se adaptó a estos datos.

## V med

El encabezado es exactamente `V med`. Encabezado y celda están centrados, la
columna no se expande y su ancho mínimo se adapta a la fuente del encabezado
(58 px como base). El indicador sigue siendo exactamente **✓ o vacío**, con
la misma expresión sobre `has_medical` persistido. No hay lógica médica nueva.

## Archivos modificados

- Modelo/servicios: `app/models.py`, `app/student_service.py`.
- Repositorio/migración: `app/students_repository.py`,
  `app/migrations/__init__.py`, `app/migrations/004_student_names.sql`.
- Interfaz/estilo: `app/ui.py`, `app/theme.py`.
- Empaquetado: `OncaAlumnos.spec`.
- Tests: `test_student_names.py`, `test_activity_list.py`, `test_gui.py`,
  `test_migrations.py`, `test_hardening.py`.
- Docs: README, CHANGELOG, architecture, development y este registro.

No se modifican dependencias, workflows, versión interna, datos, assets,
snapshots previos o remotes. El build nuevo queda en el workspace privado.

## Validación de la entrega inicial

**VERIFIED AUTOMATICALLY:** **156 passed / 0 failed / 0 skipped** con
`ONCA_GUI_TESTS=1`, Python 3.11.17, SQLite 3.53.1 y Tcl/Tk 8.6.15 en Windows x64.
Son 129 pruebas de lógica y 27 de escritorio; incremento de 29 sobre la baseline.
Se ajustan dos expectativas antiguas que asumían dividir nombres por espacios,
conservando las comprobaciones de identidad y homónimos. El test de quitar una
actividad usa ahora la selección del Treeview.

Cobertura nueva: partes/nombres compuestos/opcionalidad, validación y
`display_name`, guardar/editar y conservar IDs/historial, búsquedas por las
tres formas con una consulta, adopción de nombre único, conservación de schema
3, respaldo previo y rollback, `V med`, actividad única/múltiple/sin lugar/sin
pago, orden y desempate, scroll vertical y horizontal ante redimensionado,
detalle de notas, selección estable y tema oscuro.

Comandos ejecutados con los intérpretes locales 3.11.17:

```powershell
$env:ONCA_GUI_TESTS = '1'
python -m unittest discover -s tests
python -m compileall -q app run.py tools tests
python -m pip check
python tools/check_query_plans.py
python tools/smoke_test.py
python build_release.py --output .private/v4-work/build-final
python tools/smoke_test.py .private/v4-work/build-final/OncaAlumnos.exe
git diff --check
```

Suite completa, compile, pip check de runtime/build, planes SQL y smoke source:
OK. Build final con PyInstaller **6.20.0** y hooks **2026.5**: OK.
El manifest marca schema 4. Binario final local:
`.private/v4-work/build-final/OncaAlumnos.exe`, **13 481 148 bytes**.
SHA-256: `404362cb9450bd0f426fbfce56c886c91250d5f066e1482bb95d01c2b52dfa8a`.
Smoke EXE de inicio/base vacía/cierre: OK. Comprobación adicional del binario:
SQL 002/003/004 y schema presentes en el archive, checksum del manifest correcto,
apertura/migración de instalaciones sintéticas schema 0 con nombre único y
schema 3 con partes separadas/verificación médica. Ambas llegan a 4 conservando
ID/nombres/verificación, integridad/FK y respaldo de la versión anterior.
Esto verifica el camino empaquetado de migración, no todos los formularios del EXE.

**VERIFIED MANUALLY:** ninguna revisión humana realizada.
**NOT VERIFIED:** DPI reales, uso humano de formularios y todos los recorridos
del EXE. **NOT EXECUTED:** CI remoto (sin push), auditoría online de dependencias
(no cambiaron), lint/type checking/pytest (sin configuración en el proyecto).

## Riesgos y pruebas manuales pendientes

- Los registros históricamente divididos por el primer espacio se conservan;
  revisar y corregir sus partes conscientemente desde el formulario.
- Un schema 4 no debe abrirse con un ejecutable antiguo de schema 3.
- El listado y filtro siguen cargando los alumnos completos; no se introduce
  paginación ni se afirma una mejora asintótica.
- Revisar campos nuevos a DPI 100%, 125% y 150%, en modo claro/oscuro y con teclado.
- Crear/editar nombres compuestos y apellidos, vaciar apellidos, guardar y reiniciar.
- Verificar `V med`: en la ampliación, la casilla actualiza el indicador al clic;
  adjuntar por sí solo no verifica.
- Probar muchas actividades, ventanas estrechas, notas largas, selección,
  doble clic, agregar, editar, quitar y asignación grupal.
- Revisar el orden descendente del historial y el indicador de próxima actividad.
- En una copia sintética antigua: abrir, comprobar respaldo/migración y restaurar
  en una carpeta nueva; nunca reemplazar una instalación activa para esta prueba.

Licencia, revisión pública del snapshot, firma del EXE y revisión del historial
siguen pendientes de las fases anteriores. Esta iteración no publica material.

## Git

Commits locales de implementación y tests:

- `24c4b1e`: `feat(students): persist separate names and migrate legacy records`.
- `e932204`: `feat(ui): structure student activities and separate name fields`.

Este documento, README, CHANGELOG, architecture y development se cierran en
un commit documental separado. Rama v3 y sus commits conservados; sin push,
publicación, modificación de visibilidad, cambios de remoto o reescritura
de historial. Los outputs de build están ignorados por `.gitignore`.

## Ampliación de v4 — 2026-10-06

Inicio en `6764687`, rama `feat/student-name-activities-ui-v4`, árbol limpio.
Se ejecutaron status, rama, log y diff antes de editar. Baseline de esta
ampliación: **156 tests aprobados** con GUI habilitada. No se creó otra rama.

## Selector de fechas

Se amplía el selector previo como `DatePicker`; `BirthDatePicker` y
`birth_date_from_parts()` permanecen como wrappers compatibles. `InlineDateEntry`
integra fecha textual visible y botón Elegir; clic en el campo, botón, F4 o
Alt+Abajo abre el mismo popup compacto cerca de la entrada. No se abren
duplicados para un campo. Año/Mes/Día se eligen sin escribir ISO; confirmar
devuelve YYYY-MM-DD y cierra, Escape/Cancelar conserva el valor anterior.

Se utiliza en nacimiento, fecha de actividad, fecha de certificado y fecha de
pago. Se retiran las instrucciones que presentaban teclear YYYY-MM-DD como
método principal; la entrada manual se conserva con validación inline.
Los estilos ttk se comparten; el popup inicia con la paleta del tema actual.

`parse_date_field()` centraliza la regla según tipo: nacimiento opcional y no
futuro, certificado requerido al verificar/adjuntar y no futuro, actividades
y pagos con pasado/futuro según la lógica previa. El año comienza normalmente
en 1900 y conserva años anteriores si el registro ya los contiene; actividades
y pagos ofrecen 20 años futuros, ampliando el rango si el valor existente lo
necesita. Cambiar mes/año ajusta el día al máximo válido, incluidos bisiestos.

## Finanzas

`parse_amount()` devuelve `Decimal` con dos decimales. Rechaza negativos,
texto, vacío, más de dos decimales, notación científica, NaN/infinito y montos
mayores de 1 000 000 000. Cero es válido para costo/pagado de actividad;
un pago mensual conserva la obligación de ser positivo. Los campos nuevos
inician con cero explícito; vaciar un importe exige corregirlo antes de guardar.

`activity_amounts()` valida ambos campos y usa `remaining_balance()` para
calcular costo menos pagado. Pagado mayor al costo produce el error inline
exacto **El monto pagado no puede ser mayor al costo total.** y bloquea alta/
edición, tanto en UI como por servicio. Restante es de solo lectura, se actualiza
en vivo desde StringVar y muestra moneda, por ejemplo `$800.00` o `$0.00`.
Entradas inválidas dejan el saldo vacío, nunca negativo. El detalle de la
actividad seleccionada muestra también el saldo sin añadir otra columna ancha.

Estado continúa indicando participación/asistencia. No se cambia a Pagado
automáticamente ni se confunde cancelación/asistencia con saldo financiero.

Compatibilidad: se conserva el almacenamiento SQLite REAL histórico, sin
reescribir datos. Los repositorios enlazan texto decimal como parámetro; los
servicios convierten lecturas a Decimal mediante su representación textual.
No se suma/resta dinero con floats en aplicación o SQL. `MoneyInput` admite
floats únicamente como entrada de clientes antiguos, convertida a texto antes
de validar; formularios/cálculos usan Decimal. Migrar el almacenamiento a
centavos enteros queda fuera de esta ampliación. Un sobrepago o precisión
histórica anómala se conserva, muestra revisión en detalle y exige corrección
al editar; no se recorta ni se elimina automáticamente.

## Certificado médico

Se elimina Guardar verificación. El comando del checkbox llama al servicio
`set_medical_verification()` por ID y guarda inmediatamente estado y fecha
en una transacción. `medical_indicator()` compone ✓/vacío para la carga de
tabla y la actualización de V med. La actualización puntual conserva selección,
pestaña y teléfono/nombres/otros cambios sin guardar; no ejecuta un guardado
general del alumno.

Al marcar se exige fecha válida no futura. Si está vacía, se muestra
**Selecciona la fecha del certificado.** y se restaura el checkbox; no se
inventa una fecha de emisión. Se mantiene Usar fecha de hoy como atajo útil.
La fecha elegida se usa también al adjuntar PNG/PDF, sin reemplazarla por hoy.
Un alumno todavía no guardado muestra una indicación inline: primero debe
existir su student_id para poder verificarlo.

Sin archivo, la fecha explícita se conserva en `medical_certificates` con
`file_path=''`, posibilidad que ya admite el esquema/repositorio. Es metadato
del certificado declarado, no un archivo adjunto inventado. El primer adjunto
completa ese registro para que una fecha de adjunto anterior no quede oculta
por el metadato sin archivo. Se conservan archivos existentes y los backups
omiten referencias vacías, como antes.

Desmarcar no requiere corregir la fecha y conserva metadatos/archivos.
Desvincular sigue desmarcando y conserva archivos físicos. Cambios programáticos
del BooleanVar durante cargar/limpiar no disparan autosave. Ante fallo SQLite,
se revierte la transacción, la UI vuelve al estado anterior y muestra un error
técnico mediante el sistema de logging/diálogo existente. Errores normales se
muestran inline.

## Ubicación

**MAP: RESEARCHED ONLY.** [Evaluación técnica completa](../map-location-evaluation.md)
de Google Maps Platform, OSM, Leaflet y TkinterMapView: claves, precios/límites,
offline, empaquetado, tamaño, dependencias, mantenimiento, privacidad y marcador.
Se recomienda evaluar un adaptador opcional TkinterMapView con cartografía
regional autorizada/local y catálogo de lugares, sujeto a auditoría/pruebas de
la release y sus dependencias. No hay prototipo ni columnas latitud/longitud.
Lugar sigue opcional y offline; no se instalan dependencias ni se añaden claves,
geocodificación automática o llamadas externas con datos de alumnos.

## Regresión

**VERIFIED AUTOMATICALLY:** suite completa **194 passed / 0 failed / 0 skipped**,
Python 3.11.17/SQLite 3.53.1/Tk 8.6.15, con `ONCA_GUI_TESTS=1`: 156 pruebas de
lógica y 38 de GUI. Se añaden 38 respecto de la baseline 156; no se omite la
regresión anterior. El test médico previo se renombra para aclarar que modificar
la variable programáticamente no equivale al clic del usuario.

Cobertura integral: crear/editar alumno, nombres/apellidos y student_id,
teléfonos locales/internacionales, nacimiento, pagos y precisión, certificado/
V med, actividades individuales/grupales/múltiples y selección múltiple,
backups/restore, migraciones, consultas únicas, rutas relativas y modo oscuro.
Se comprueba autosave en ambos sentidos, metadatos sin archivo, fecha vacía/
futura, rollback SQL/UI, formulario sin guardar preservado y adjunto posterior.

Problemas encontrados y corregidos: dos tests nuevos detectaron que leer
Entry.get() dentro del trace devolvía el valor anterior. Se usan StringVar para
el saldo inmediato y el error cruzado. La revisión añadió un test para que
adjuntar después de verificar sin archivo conserve la visibilidad del adjunto.

Otros checks: **15 tests de migraciones aprobados**, pip check, compileall,
planes SQL y smoke source de inicio/cierre: OK. Se mantiene schema 4: no hay
nuevas columnas y no hace falta otra migración. Migraciones anteriores y
backups/restauración siguen cubiertos con datos sintéticos.

Archivos de esta ampliación: `date_picker.py`, `form_widgets.py`, `validation.py`,
`activity_form.py`, `activity_service.py`, `activities_repository.py`,
`payment_service.py`, `payments_repository.py`, `certificate_service.py`,
`medical_repository.py`, `student_service.py`, `ui.py`; tests GUI y nuevo
`test_dates_money_autosave.py`; README, CHANGELOG, architecture, development,
manual-validation, este registro y map-location-evaluation. No se cambian
dependencias, empaquetado, versión, esquema, datos reales o remotes.

**VERIFIED MANUALLY:** ninguna revisión humana.
**NOT VERIFIED:** DPI y monitores reales, todos los recorridos humanos, mapa/
coordenadas y empaquetado de estos cambios. **NOT EXECUTED:** CI remoto,
auditoría online de dependencias y nuevo build.

**BUILD: NOT EXECUTED — waiting for user approval.** No se ejecutó PyInstaller
ni se generó/reemplazó un EXE. La prueba existente de seguridad del build solo
comprueba el rechazo de un destino ya existente, antes de empaquetar. El EXE
validado anterior conserva su SHA-256:
`404362cb9450bd0f426fbfce56c886c91250d5f066e1482bb95d01c2b52dfa8a`.
Ese ejecutable no contiene esta ampliación; revisar source hasta autorizar build.

Checklist de usuario: [manual-validation.md](../manual-validation.md#checklist-de-la-ampliación-v4).
Sin push, publicación ni cambios de visibilidad. Árbol final y commits locales
se comprueban al cerrar; la rama continúa siendo v4.

Commits locales de la ampliación:

- `07a2e7d`: componentes de fecha comunes y validación monetaria Decimal.
- `36db901`: formulario con saldo en vivo, fechas y autosave médico.
- `db54392`: regresión de fechas, finanzas y autosave.
- `569499f`: investigación de proveedores de mapas.
- Documentación y checklist se cierran en un quinto commit separado.
