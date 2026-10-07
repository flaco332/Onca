# Decisión de licencia del proyecto

Estado: **SELECTED — Apache-2.0**. El propietario autorizó expresamente al asistente
a elegir la licencia más adecuada para publicar esta aplicación.
Se incorpora el texto oficial íntegro en [LICENSE](LICENSE) y la atribución en
[NOTICE](NOTICE), sin inferir una identidad legal del autor Git.

## Motivo

La aplicación se orienta al uso por empresas y a publicación de fuente reutilizable.
Apache-2.0 permite uso comercial, modificación y redistribución, sin exigir hacer
públicas modificaciones privadas; incluye concesión expresa de patentes y reglas de
conservación de licencia/avisos e identificación de cambios. Es la elección para
el código y documentación originales del proyecto, no para datos de usuarios,
marcas o dependencias con licencia propia.

## Alternativas revisadas

| Opción | Uso comercial / modificación / redistribución | Atribución | Patentes | Publicar modificaciones |
| --- | --- | --- | --- | --- |
| MIT | Permitidos con condiciones | Conservar copyright/licencia | Sin concesión expresa como Apache | No exige publicar cambios |
| Apache-2.0 | Permitidos; admite derivados propietarios | Licencia/avisos y cambios señalados | Concesión expresa con condiciones | No exige publicar cambios privados |
| GPL-3.0 | Permitidos, incluido cobrar | Licencia/avisos y cambios | Reglas de sección 11 | Fuente correspondiente bajo GPL al distribuir derivados cubiertos |
| AGPL-3.0 | Permitidos con copyleft | Licencia/avisos y cambios | Reglas de GPLv3 | Añade oferta de fuente al interactuar por red con versiones modificadas |
| Propietario / source-available | Según contrato aprobado | Según términos propios | Según contrato | Según contrato; no presumir open source |

Fuentes: [MIT](https://opensource.org/license/mit),
[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0),
[GPL-3.0](https://opensource.org/license/gpl-3.0) y
[AGPL-3.0](https://opensource.org/license/agpl-3.0).

Apache-2.0 encaja mejor que el copyleft si se quiere permitir que empresas adapten
el escritorio internamente. Frente a MIT añade concesión expresa de patentes.
La excepción de [PyInstaller](https://pyinstaller.org/en/v6.20.0/license.html)
permite elegir licencia del programa empaquetado respetando las dependencias.
Consultar [el inventario](docs/dependencies-and-licenses.md).

## Alcance y pendientes

La atribución identifica colectivamente a los autores de Onca Alumnos; no inventa
una empresa titular ni publica nombres personales. Se conservan avisos existentes.
Antes de publicar, el propietario debe revisar derechos sobre aportaciones ajenas;
la elección de licencia no demuestra por sí sola la titularidad de todo material.
Branding/adjuntos locales de procedencia pendiente siguen excluidos.

La autorización para elegir licencia no autoriza push, publicación, cambio de
visibilidad, tag, Release o build. Estos pasos continúan pendientes en la
[checklist](docs/release-checklist.md) y [guía de publicación](docs/publication-guide.md).
