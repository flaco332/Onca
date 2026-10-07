# Checklist de release candidate

Fecha de revisión: 2026-10-06. Esta lista se refiere a la candidata de fuente,
no al repositorio original completo ni a un nuevo EXE.
Versión única en app/version.py. Resultados en [release-review.md](release-review.md).

## Fuente y privacidad

- [x] Versión RC actualizada y metadata Windows revisada sin compilar.
- [x] Suite completa final registrada: 209 passed / 0 failed / 0 skipped.
- [x] pip check del entorno nuevo.
- [x] Base nueva vacía y reinicio sin seeds.
- [x] Snapshot licenciado revisado: 86 archivos, 46 enlaces; suite y smoke desde copia sin historial.
- [x] Sin alumnos/pagos/actividades/certificados de prueba en el runtime.
- [x] Sin bases, backups, logs, certificados o binarios incluidos en fuente.
- [x] Datos sintéticos solo en tests; excluidos del futuro paquete Windows.
- [x] Sin patrones de PII/secretos detectados en fuente candidata revisada.
- [x] README actualizado.
- [x] Arquitectura documentada.
- [x] Developer guide y deployment guide.
- [x] Changelog de cambios reales.
- [x] Licencia propia Apache-2.0 seleccionada por delegación del propietario; LICENSE/NOTICE.
- [x] Licencias/dependencias revisadas.
- [x] THIRD_PARTY_NOTICES y términos Tcl/Tk originales preparados.
- [x] Historial original privado identificado y excluido del snapshot.

## Pendientes antes de distribuir

- [ ] Derechos sobre aportaciones ajenas revisados por el propietario.
- [ ] CI verde observado en GitHub sobre fuente revisada.
- [ ] Autorización del usuario para compilar.
- [ ] Build limpio en destino nuevo.
- [ ] Smoke EXE.
- [ ] Inventario de DLL/hooks/avisos del binario final.
- [ ] Checksum del EXE RC.
- [ ] Prueba en Windows limpio.
- [ ] Revisión manual de DPI, formularios y backup/restore.
- [ ] Aprobación del usuario para publicación.
- [ ] Push de fuente sin historial privado a destino aprobado.
- [ ] Tag aprobado.
- [ ] GitHub Release aprobada.

**BUILD: NOT EXECUTED — waiting for final user approval.**
No se autoriza publicar el historial original. La candidata licenciada está
preparada para revisión del propietario; publicación y build siguen pendientes.
Pasos concretos: [publication-guide.md](publication-guide.md).
