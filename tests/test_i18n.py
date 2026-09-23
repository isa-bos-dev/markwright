import pytest

from markwright.i18n.strings import DEFAULT_LANGUAGE, STRINGS, SUPPORTED_LANGUAGES, t

# --- Success cases ---


def test_supported_languages_maps_codes_to_native_names() -> None:
    assert SUPPORTED_LANGUAGES == {"en": "English", "es": "Español"}


def test_supported_languages_match_the_languages_with_translations() -> None:
    assert set(SUPPORTED_LANGUAGES) == set(STRINGS)


def test_default_language_is_supported() -> None:
    assert DEFAULT_LANGUAGE in SUPPORTED_LANGUAGES


def test_language_selector_prompt_has_a_translation_in_every_language() -> None:
    for language in SUPPORTED_LANGUAGES:
        assert "language_selector.prompt" in STRINGS[language]



def test_t_returns_english_text_for_known_key() -> None:
    result = t("progress.started", "en")

    assert result == STRINGS["en"]["progress.started"]


def test_t_returns_spanish_text_for_known_key() -> None:
    result = t("progress.started", "es")

    assert result == STRINGS["es"]["progress.started"]


def test_all_english_keys_exist_in_spanish() -> None:
    missing = set(STRINGS["en"]) - set(STRINGS["es"])

    assert missing == set()


def test_all_spanish_keys_exist_in_english() -> None:
    missing = set(STRINGS["es"]) - set(STRINGS["en"])

    assert missing == set()


def test_t_interpolates_parameters() -> None:
    result = t("error.unsupported_file", "en", path="report.pdf")

    assert "report.pdf" in result


@pytest.mark.parametrize(
    "key",
    [
        "error.unsupported_file",
        "error.invalid_password",
        "error.corrupt_file",
        "error.output_write_failed",
    ],
)
def test_every_exception_type_has_a_translation_key(key: str) -> None:
    assert key in STRINGS["en"]
    assert key in STRINGS["es"]


@pytest.mark.parametrize(
    "key",
    ["progress.started", "progress.converting", "progress.writing", "progress.done"],
)
def test_every_progress_stage_has_a_translation_key(key: str) -> None:
    assert key in STRINGS["en"]
    assert key in STRINGS["es"]


@pytest.mark.parametrize(
    "key",
    [
        "progress.partial_success.retryable",
        "progress.partial_success.not_retryable",
    ],
)
def test_every_partial_success_variant_has_a_translation_key(key: str) -> None:
    assert key in STRINGS["en"]
    assert key in STRINGS["es"]


# --- Error cases ---


def test_t_falls_back_to_english_for_unsupported_language() -> None:
    result = t("progress.started", "fr")

    assert result == STRINGS["en"]["progress.started"]


def test_t_returns_the_key_itself_for_a_completely_unknown_key() -> None:
    result = t("this.key.does.not.exist", "en")

    assert result == "this.key.does.not.exist"
