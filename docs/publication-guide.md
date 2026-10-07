# Publicar la candidata de fuente

## Estado actual

Licencia propia Apache-2.0 incorporada en LICENSE y NOTICE.
La candidata licenciada se exporta a release-candidate/source-v0.9.0-rc1-licensed.
La copia anterior se conserva; no utilizarla para publicar porque carece de LICENSE.

Fuente lista para revisión local. Publicación pendiente de derechos revisados
por el propietario, checklist manual, CI remoto y aprobación final.
No hay EXE RC nuevo. Build y publicación son autorizaciones separadas.

## 1. Revisar la aplicación sin datos privados

Abrir PowerShell en la fuente licenciada. Preparar Python como indica
[developer-guide.md](developer-guide.md) y usar un perfil temporal:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$reviewData = Join-Path $env:TEMP ("Onca-review-" + [guid]::NewGuid().ToString('N'))
$env:ONCA_DATA_DIR = $reviewData
.venv\Scripts\python.exe run.py
```

Al abrir debe haber cero alumnos, pagos, certificados y actividades. El arranque
normal puede generar un backup de la base vacía. Crear únicamente ejemplos
sintéticos, cerrar/reabrir y revisar la [checklist manual](manual-validation.md):
Nombre/Apellidos e ID, pagos, calendario, saldo/sobrepago, V med, actividades
grupales, modo oscuro, backups y restauración en otra carpeta.
Anotar resultados y fallos sin adjuntar bases, certificados, logs o datos reales.
Cerrar la app antes de quitar ONCA_DATA_DIR de la sesión.

## 2. Repetir checks si se cambia código

```powershell
$env:ONCA_GUI_TESTS = '1'
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe tools/public_snapshot.py --check
.venv\Scripts\python.exe tools/check_query_plans.py
.venv\Scripts\python.exe tools/smoke_test.py
```

Registrar passed/failed/skipped. Si cambia código, corregirlo y volver a exportar
a un destino nuevo desde los commits revisados. No copiar después archivos de
prueba a la fuente candidata. No presentar resultados previos como checks nuevos.

## 3. Crear un repositorio público limpio — después de aprobación

**No hacer público el repositorio original ni importarlo/clonarlo como base del
nuevo:** su historial contiene información privada. La candidata no lleva .git.
No aplicar force push, mirror, import repository o limpieza automática de historial.

Crear en GitHub un repositorio nuevo y vacío, inicialmente privado para comprobar
CI. No precrear README, licencia ni .gitignore: ya están en la candidata.
No usar el repositorio original como template. Nunca incluir todas sus ramas/tags.
[Instrucciones oficiales](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository).

Copiar solo la candidata licenciada a una carpeta nueva fuera del checkout original,
y abrir PowerShell allí. El entorno .venv, datos temporales y logs no pertenecen a
la copia; el snapshot entregado ya excluye esos archivos. Verificar que no exista .git.

Los comandos siguientes son instrucciones futuras, **no se han ejecutado**.
Sustituir URL_REPOSITORIO_NUEVO por la URL del repositorio nuevo, no origin original.

```powershell
git init -b publication-review
git config user.name "Onca maintainer"
git config user.email "DIRECCION_NOREPLY_DE_TU_CUENTA"
git add -- .
git diff --cached --check
git diff --cached --stat
git diff --cached
git commit -m "chore: prepare Onca Alumnos source release candidate"
git log -1 --format=fuller
git status
git remote add origin URL_REPOSITORIO_NUEVO
git remote -v
```

Antes del commit sustituir la dirección de ejemplo por el noreply que aparece
en GitHub → Settings → Emails; no usar un correo privado. Configuración local,
sin cambiar la identidad del repositorio original o la configuración global.
[Privacidad de email](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).
Comprobar que el nuevo repositorio tenga solamente el commit inicial de fuente
limpia y revisar todos los archivos antes de enviarlos.

Solo tras autorizar el envío al repositorio nuevo:

```powershell
git push -u origin publication-review
```

El workflow Tests valida sin hacer deployment. No ejecutar Build Windows:
requiere aprobación de build separada. Observar CI verde y revisar README/licencias
en GitHub. Si no se ejecuta CI o falla, resolver antes de publicar. Cambiar visibilidad
del repositorio nuevo únicamente después de revisión y aprobación; el original
permanece privado. No existe autorización automática por seguir esta guía.

## 4. Crear una pre-release de fuente — después de aprobación

En el repositorio nuevo: Releases → Draft a new release.
Elegir un tag nuevo v0.9.0-rc1 sobre el commit aprobado, comprobar que no existe ya,
título Onca Alumnos 0.9.0-rc1, notas basadas en CHANGELOG y marcar pre-release.
Indicar que la entrega es de fuente y requiere Python; no prometer un EXE.
Guardar como draft hasta completar la revisión. GitHub ofrece ZIP/tar.gz de fuente
del tag del repositorio limpio; no adjuntar ZIP del proyecto original.
[Gestión de releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

Nunca reemplazar una release o tag existente. Publicar solo con autorización final.
Fuente pública no significa aplicación lista para instalación por usuarios finales.

## 5. Windows Application — pendiente de otra autorización

Después de aprobar el build, seguir [deployment.md](deployment.md) en destino nuevo.
Revisar smoke EXE, runtime/DLL y avisos, LICENSE/NOTICE, manifest/checksum,
Windows limpio, DPI y respaldo/restauración. Distribuir EXE y avisos juntos;
no work/, datos, backups o logs. El EXE anterior no representa esta candidata.

**BUILD: NOT EXECUTED — waiting for final user approval.**

## 6. Criterio para declarar listo

- Fuente: licencia y avisos presentes, datos excluidos, tests/checks aprobados,
  derechos revisados, checklist manual completada y CI verde observado.
- Publicación: destino nuevo sin historial original y autorización final.
- Windows: además build nuevo verificado, checksum, avisos y prueba limpia.

Resultados y límites actuales: [release-review.md](release-review.md).
No marcar CI, revisión humana o EXE como verificados sin evidencia.
