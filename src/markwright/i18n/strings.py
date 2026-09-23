DEFAULT_LANGUAGE = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "error.unsupported_file": (
            "The file could not be found, is not readable, or is not a PDF: {path}"
        ),
        "error.invalid_password": (
            "This PDF is password-protected: {path}. "
            "Please provide the correct password to continue."
        ),
        "error.corrupt_file": (
            "This file appears to be corrupted or could not be processed: {path}"
        ),
        "error.output_write_failed": (
            "The result could not be saved to: {path}. Check that the destination "
            "folder exists and that you have permission to write there."
        ),
        "progress.started": "Starting conversion...",
        "progress.converting": "Converting PDF to Markdown...",
        "progress.writing": "Saving result...",
        "progress.done": "Conversion complete.",
        "progress.partial_success.retryable": (
            "The conversion finished, but some pages had issues that might be "
            "temporary. You may want to try again."
        ),
        "progress.partial_success.not_retryable": (
            "The conversion finished, but some pages could not be processed "
            "correctly. This is likely due to the content of those pages, not "
            "a temporary issue."
        ),
        "error.unexpected": (
            "An unexpected error occurred. Run with --verbose for more details."
        ),
    },
    "es": {
        "error.unsupported_file": (
            "No se pudo encontrar el archivo, no es legible, o no es un PDF: {path}"
        ),
        "error.invalid_password": (
            "Este PDF está protegido con contraseña: {path}. "
            "Introduce la contraseña correcta para continuar."
        ),
        "error.corrupt_file": (
            "Este archivo parece estar dañado o no se pudo procesar: {path}"
        ),
        "error.output_write_failed": (
            "No se pudo guardar el resultado en: {path}. Comprueba que la carpeta "
            "de destino existe y que tienes permiso para escribir en ella."
        ),
        "progress.started": "Iniciando conversión...",
        "progress.converting": "Convirtiendo PDF a Markdown...",
        "progress.writing": "Guardando resultado...",
        "progress.done": "Conversión completada.",
        "progress.partial_success.retryable": (
            "La conversión terminó, pero algunas páginas tuvieron problemas que "
            "podrían ser temporales. Puede que quieras intentarlo de nuevo."
        ),
        "progress.partial_success.not_retryable": (
            "La conversión terminó, pero algunas páginas no se pudieron procesar "
            "correctamente. Probablemente se deba al contenido de esas páginas, "
            "no a un problema temporal."
        ),
        "error.unexpected": (
            "Ocurrió un error inesperado. Ejecuta con --verbose para más detalles."
        ),
    },
}


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs: object) -> str:
    """Return the localized string for ``key``, falling back to English.

    Falls back to English when ``lang`` is unsupported or the key is missing
    for that language, and to the key itself when it is missing everywhere
    — a visible sign something is wrong, rather than crashing the caller.
    """
    template = STRINGS.get(lang, {}).get(key) or STRINGS[DEFAULT_LANGUAGE].get(key) or key
    return template.format(**kwargs) if kwargs else template
