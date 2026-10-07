# Validación manual de escritorio

Usar una instalación temporal vacía con nombres inventados y adjuntos
sintéticos. No abrir bases privadas. Anotar Windows, escala DPI, Python/EXE,
versión ONCA, resultado y errores sin datos personales. Esta checklist requiere
una revisión humana; los tests automáticos no certifican cada interacción.
Para la ampliación actual de v4 usar source con datos sintéticos: no hay un
EXE nuevo. El ejecutable validado antes de esta ampliación permanece intacto
y no sirve para revisar sus funcionalidades nuevas.

## Checklist de la ampliación v4

**VERIFIED MANUALLY:** ninguna. Todos los puntos siguientes siguen pendientes.

- [ ] Abrir fecha de nacimiento desde el campo y desde Elegir.
- [ ] Navegar año.
- [ ] Navegar mes.
- [ ] Seleccionar día y confirmar; valor visible YYYY-MM-DD.
- [ ] Impedir nacimiento futuro.
- [ ] Revisar 29 de febrero y cambio de año/mes.
- [ ] Abrir fecha de actividad y seleccionar pasado/futuro.
- [ ] Abrir fecha de pago y seleccionar fecha.
- [ ] Abrir fecha de certificado y seleccionar fecha no futura.
- [ ] Marcar verificado; observar V med inmediatamente sin botón adicional.
- [ ] Desmarcar verificado; observar V med desaparecer.
- [ ] Fecha de certificado vacía/futura: error inline y verificación sin guardar.
- [ ] Mantener la pestaña y ediciones sin guardar al verificar.
- [ ] Verificar sin archivo y adjuntar después un PNG/PDF sintético.
- [ ] Costo 1200, pagado 400: restante $800.00.
- [ ] Pagado 1200: restante $0.00.
- [ ] Pagado 1400: error rojo y guardado bloqueado.
- [ ] Costo negativo.
- [ ] Pago negativo.
- [ ] Texto inválido, NaN, infinito, vacío y más de dos decimales.
- [ ] Decimales 0.30 y 0.10: restante $0.20.
- [ ] Restante no editable y nunca negativo.
- [ ] Lugar sin mapa; actividad guardada con lugar vacío o textual.
- [ ] Lugar con mapa: N/A, mapa solo investigado en esta ampliación.
- [ ] Aplicación sin Internet: alumnos, actividades, pagos, verificación y backups.
- [ ] Modo oscuro, teclado/F4, ubicación/tamaño del popup y DPI 100/125/150%.
- [ ] Guardar, cerrar/reabrir y restaurar una copia sintética en carpeta nueva.

Mapa no implementado: el informe de investigación fue retirado de esta candidata.

## Alumnos

- [ ] Crear y guardar; cerrar/reiniciar y comprobar persistencia.
- [ ] Editar únicamente el ID seleccionado.
- [ ] Dar de baja con confirmación; comprobar historial conservado.
- [ ] Crear dos homónimos; verificar IDs, pagos, certificados y actividades independientes.

## Pagos

- [ ] Crear un pago ficticio.
- [ ] Editar fecha/monto del pago seleccionado.
- [ ] Eliminar con confirmación y revisar el historial.
- [ ] Rechazar fechas inválidas, montos negativos, NaN/infinito y selección obsoleta.

## Actividades

- [ ] Crear individual y grupal, con alumnos visibles por ID.
- [ ] Editar participación compartida sin cambiar a los demás.
- [ ] Cambiar selección principal mientras el formulario permanece abierto: conserva destinatarios.
- [ ] Eliminar participación; conservar actividad si todavía tiene otros alumnos.

## Certificados

- [ ] Adjuntar PNG/PDF sintético a un alumno guardado.
- [ ] Previsualizar PNG y abrir con el visor del sistema.
- [ ] Desvincular con confirmación; archivo físico conservado.
- [ ] Rechazar archivo inexistente, extensión/contenido incorrecto y ruta inválida.
- [ ] Mover instalación sintética cerrada; resolver rutas relativas con nuevo ONCA_DATA_DIR.

## Backup

- [ ] Crear y comprobar estado de finalización.
- [ ] Validar inventario, SQLite y checksum.
- [ ] Copiar un backup sintético, alterar un archivo y comprobar rechazo.
- [ ] Restaurar en carpeta nueva y comprobar respaldo previo.
- [ ] Activar la carpeta restaurada después de cerrar; verificar datos y adjuntos.
- [ ] Comprobar que base activa/destino existente no se sobrescriben ante error.

## UI

- [ ] Redimensionar; comprobar tablas, formularios y desplazamiento.
- [ ] Revisar tema claro/oscuro, espaciado y contraste.
- [ ] Revisar mensajes, validaciones, confirmaciones y estados.
- [ ] Comprobar que backup/restore no congelen ventanas ni actualicen widgets desde workers.
- [ ] Intentar cerrar durante operación: debe esperar su finalización.
- [ ] Revisar escala Windows 100%, 125%, 150% y 200%; ninguna se declara validada por un smoke test.

## EXE

- [ ] Abrir desde una carpeta diferente con datos temporales.
- [ ] Guardar alumnos/pagos/actividades y adjuntar PNG/PDF sintéticos.
- [ ] Crear/restaurar backup desde el EXE.
- [ ] Cerrar ordenadamente; reiniciar y verificar persistencia.
- [ ] Verificar versión/About, SHA-256 y avisos de terceros distribuidos.
