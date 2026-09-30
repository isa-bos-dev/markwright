<div align="center">

[![English](https://img.shields.io/badge/English-4A90E2?style=for-the-badge&logoColor=white)](README.md)
[![Spanish](https://img.shields.io/badge/Spanish-FFDE59?style=for-the-badge&logoColor=white)](README_es.md)

<img src="assets/logo-512.png" alt="Logo de Markwright" width="140">

# Markwright

---

Un conversor de PDF a Markdown local y respetuoso con la privacidad, que preserva tablas, encabezados e imágenes. Construido con una interfaz gráfica sencilla y una CLI para scripting, pensado tanto para usuarios sin conocimientos técnicos como para desarrolladores — sin necesitar conexión a internet tras la primera descarga de modelos, disponible en inglés y español.

<!-- Tech Stack Badges -->
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Docling](https://img.shields.io/badge/Docling-1A73E8?style=for-the-badge&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter-306998?style=for-the-badge&logoColor=white)
![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white)
![Ruff](https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black)
[![Version](https://img.shields.io/badge/version-0.2.0-informational?style=for-the-badge)](CHANGELOG.md)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=for-the-badge)](LICENSE)

</div>

---

## Qué hace

Markwright convierte un archivo PDF a Markdown, conservando la estructura que
normalmente se pierde en una conversión ingenua: tablas, listas, jerarquía de
encabezados, y las imágenes incrustadas en el documento. Lee tanto páginas
escaneadas o solo-imagen mediante OCR (EasyOCR) como PDFs con una capa de texto
real, y puede descifrar PDFs protegidos con contraseña en memoria. Todo se
ejecuta en tu propio ordenador — ver [Privacidad](#privacidad) más abajo.

Se puede usar de tres formas:

- **Una interfaz gráfica** — doble clic para abrir, elige un PDF, pulsa convertir.
  Sin necesidad de terminal.
- **Una herramienta de línea de comandos**, para scripts: `markwright informe.pdf`.
- **Un menú interactivo de terminal**, para elegir un archivo sin escribir la ruta
  completa: `markwright menu`.

La interfaz (GUI y CLI) está disponible en inglés y español; puedes cambiarla,
junto con el tema claro/oscuro y el tamaño de letra, desde el icono de engranaje
de la GUI.

## Pruébalo ahora (desde el código fuente)

Markwright todavía no tiene un ejecutable empaquetado para descargar (está
planificado para la versión `v1.0.0` — ver [CHANGELOG.md](CHANGELOG.md)). Hasta
entonces, ejecutarlo desde el código fuente es sencillo:

**Requisitos:** Python 3.12+ y [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/isa-bos-dev/markwright.git
cd markwright
uv sync
```

Después, cualquiera de estos:

```bash
uv run markwright                  # abre la interfaz gráfica
uv run markwright informe.pdf      # convierte un archivo desde la línea de comandos
uv run markwright menu             # menú interactivo: elige un PDF de una lista
uv run markwright --help           # todas las opciones de la CLI (idioma, ruta de salida...)
```

La primera conversión descarga los modelos de OCR/diseño que necesita (unos
cientos de MB) desde sus fuentes oficiales. A partir de ahí, cada conversión se
ejecuta completamente sin conexión.

Desarrollado y probado sobre todo en Windows; el tema visual de la GUI está
pensado específicamente para Windows 11. El código tiene alternativas para abrir
la carpeta de resultado en macOS/Linux, pero esas plataformas aún no se han
verificado.

## Privacidad

El contenido de tus PDFs nunca sale de tu ordenador. La única petición de red que
hace Markwright es la descarga puntual de sus propios modelos de aprendizaje
automático, desde sus fuentes oficiales (Hugging Face, EasyOCR) — nunca tus
documentos. Ver [SECURITY.md](SECURITY.md) (en inglés) para el detalle completo,
incluyendo los riesgos conocidos y aceptados explícitamente, no pasados por alto.

## Estado del proyecto

Pre-1.0, en desarrollo activo. Ver [CHANGELOG.md](CHANGELOG.md) para lo que ya
existe y [SECURITY.md](SECURITY.md) para la política de seguridad y cómo reportar
una vulnerabilidad.

## Contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md) (en inglés) para cómo preparar el entorno
de desarrollo y qué se espera de un pull request.

## Licencia

[Apache-2.0](LICENSE). Ver [NOTICE](NOTICE) para los requisitos de atribución.
