# Rendimiento y complejidad

Análisis del código y `EXPLAIN QUERY PLAN`, sin benchmarks de tiempo. Ejecuta
`python tools/check_query_plans.py`: SQLite en memoria, schema histórico,
560 pagos ficticios; luego aplica las migraciones a la misma base. Los planes
se validaron con SQLite 3.53.1. El optimizador puede variar entre versiones.

Definiciones: n alumnos, p pagos totales, c certificados totales, k filas
relacionadas de un alumno, a participaciones totales, g alumnos de un grupo,
B bytes de base/adjuntos, F archivos. Costos aproximados de índices B-tree;
no son latencias ni garantías del optimizador.

| Operación | Antes | Después | Evidencia/impacto |
| --- | --- | --- | --- |
| Identificar alumno al guardar | Búsqueda por nombre con índice, ambigua en homónimos | PK por ID: O(log n) | Corrección de identidad; no se afirma mejora asintótica frente a una búsqueda ya indexada |
| Seleccionar alumno en UI | Acoplamiento al orden de lista | Diccionario por ID: O(1) promedio | Independiente de nombres y orden; el diccionario se reconstruye en O(n) al refrescar |
| Último pago | Índice student_id + ordenamiento de k filas, aproximadamente O(log p + k log k) | Índice compuesto y LIMIT: O(log p) | Antes TEMP B-TREE; después covering idx_payments_latest |
| Último certificado | Índice student_id + ordenamiento: O(log c + k log k) | Índice compuesto y LIMIT: O(log c) | Sin TEMP B-TREE, idx_certificates_latest; el path requiere leer una fila |
| Participaciones de alumno | Recorrido O(a), luego joins/ordenamiento | Selección O(log a + k), luego joins/ordenamiento | idx_participations_student; el orden por fecha de tabla relacionada aún puede requerir O(k log k) |
| Referencias de actividad compartida | Recorrido O(a) | Búsqueda/conteo O(log a + k) | idx_participations_activity; COUNT no se declara O(1) |
| Validar IDs de grupo | No existía validación central uniforme | IN parametrizado, lotes de 500 y set: aproximadamente O(g log n) | Un round-trip por lote, sin buscar por nombre ni query Python por alumno |
| Listar alumnos | Lista completa + subqueries indexadas y sort de UI | Lista completa + subqueries con índices compuestos + sort O(n log n) | No hay paginación; no se atribuye O(1) al listado |
| Historial pagos | Índice simple y sort | Índice compuesto para filtrar/ordenar | O(log p + k) para proyección ordenada del historial |
| Backup | No había snapshot verificado conjunto | Copia/hash lineal en bytes + integridad SQLite | O(B) para I/O, más validación/normalización SQL; hashing usa memoria acotada |
| Restore | Copia manual | Respaldo previo + copia/hash/validación + migración | Varias pasadas O(B), espacio temporal adicional; no se promete latencia fija |

## Índices agregados (migración 002)

- `idx_payments_latest(student_id, payment_date DESC, payment_id DESC)`.
- `idx_certificates_latest(student_id, issue_date DESC, certificate_id DESC)`.
- `idx_participations_student(student_id, student_activity_id DESC)`.
- `idx_participations_activity(activity_id)`.

Se mantienen los índices históricos por compatibilidad. Los nuevos tienen
costos de espacio/escritura; no se agregaron índices a todas las columnas.
No se reemplazó la consulta única del listado por un loop con N+1 round-trips:
las subqueries correlacionadas ya estaban dentro de SQL y ahora aprovechan
mejor los índices. Continúan dos búsquedas de último certificado por alumno;
eliminar ese pequeño costo requeriría complejidad SQL adicional sin medición.

## Memoria y UI

Hashes leen bloques de 1 MiB. Inventario y mapa de copias usan O(F) memoria;
SQLite y el listado pueden requerir memoria adicional. Un backup renombra
adjuntos en su copia y actualiza referencias por PK, con costo de índices
además de la copia de bytes. No se considera la operación completa puramente
O(B) si la base contiene muchas referencias.

Backup, restore, copia de certificados y preparación inicial están en un
worker. Un lock coordina todas las instancias ONCA; durante el trabajo la UI
bloquea edición y mantiene el loop de eventos. CRUD/consultas permanecen
síncronos: volúmenes extraordinarios o bloqueo externo todavía pueden causar
esperas; medir antes de introducir paginación o más threads.

## Actividad próxima e indicadores (v3)

El listado anterior no consultaba actividad próxima; no se atribuye una mejora
de velocidad frente a una función que no existía. El nuevo cálculo usa un único
`SELECT` con `LEFT JOIN` a un agregado por `student_id`, no n consultas desde UI.
Se filtra fecha válida desde hoy y estados pendientes/confirmados, y se obtiene
`MIN(activity_date)`. Las pruebas cuentan un solo SELECT para todo el listado.

Con r participaciones candidatas, el agrupamiento puede requerir O(r log r)
y memoria proporcional a los grupos; depende del plan SQLite. El listado aún
incluye subconsultas indexadas y el ordenamiento de UI O(n log n). El estado
médico es una columna de la proyección, sin búsquedas de archivos por fila.
No se añadieron índices: se reutilizan los de actividad/participación existentes.

La validación de teléfono recorre un string de longitud L: O(L), conservando el
formato y contando únicamente dígitos. No se inventa una mejora asintótica.
