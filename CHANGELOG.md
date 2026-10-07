# Changelog

## [Unreleased]

Sin cambios posteriores a la candidata registrados aquí.

## [0.9.0-rc1] - 2026-10-06

Primera candidata de **fuente para revisión**, aún no publicada ni compilada como RC.
La versión se centraliza en app/version.py. No se inventa una release histórica
a partir de la versión interna anterior.

### Added

- Gestión de alumnos por student_id y Nombre/Apellidos separados.
- Pagos, actividades individuales/grupales y certificados PNG/PDF administrados.
- Backups diarios/manuales verificados y restore en carpeta nueva.
- Migraciones SQLite transaccionales hasta schema 4.
- Selector visual compartido y validación inline de fechas/teléfonos.
- Saldo de actividad en vivo con Decimal y bloqueo de sobrepagos.
- Verificación médica automática por ID, con rollback de UI ante fallos.
- Tests de primer inicio vacío, reinicio, metadata RC y protección del snapshot.
- Guías de desarrollo/deployment/publicación, checklist, Apache-2.0 y NOTICE.

### Changed

- Tablas ttk de alumnos/actividades, indicador V med y detalle de notas/saldo.
- Recursos separados de datos en el directorio del usuario.
- Metadata Windows compatible con SemVer RC, derivada de la versión única.
- Fixtures claramente sintéticas y aisladas de producción.
- Snapshot sin historial excluye informes internos y bloquea datos/binarios.
- Avisos originales y NOTICE vendorizados preparados para el futuro paquete.

### Fixed

- Nombres compuestos divididos por espacios al guardar.
- Teléfonos formateados rechazados, grados concatenados y pagos vacíos incorrectos.
- Ediciones de una actividad compartida que modificaban otros participantes.
- Verificación médica no persistida y saldo en vivo con valor anterior de Tk.
- Adjunto posterior a verificación sin archivo oculto por metadatos anteriores.

### Security

- SQL parametrizado, rutas UUID/relativas, rechazo de traversal/enlaces y límites de adjuntos.
- Logging técnico sin datos personales o valores de excepciones.
- .gitignore y exportador excluyen bases, logs, secretos, certificados y artefactos.
- Historial original con información privada: no publicar; usar snapshot revisado sin .git.
- Revisión de dependencias/licencias; Apache-2.0 seleccionada por delegación del propietario.
