from docling_core.types.doc import CodeLanguageLabel
from docling_core.types.doc.document import DoclingDocument

from markwright.core.code_blocks import apply_code_fence_languages, format_code_blocks

# --- Valid JSON gets pretty-printed and tagged ---


def test_valid_json_is_pretty_printed_and_tagged() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_code(text='{"a": 1, "b": [1, 2]}', code_language=CodeLanguageLabel.UNKNOWN)

    languages = format_code_blocks(doc)

    assert item.code_language == CodeLanguageLabel.JSON
    assert item.text == '{\n  "a": 1,\n  "b": [\n    1,\n    2\n  ]\n}'
    assert languages == ["json"]


# --- Valid XML gets pretty-printed and tagged ---


def test_valid_xml_is_pretty_printed_and_tagged() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_code(text="<a><b>1</b><c>2</c></a>", code_language=CodeLanguageLabel.UNKNOWN)

    languages = format_code_blocks(doc)

    assert item.code_language == CodeLanguageLabel.XML
    assert item.text == "<a>\n  <b>1</b>\n  <c>2</c>\n</a>"
    assert languages == ["xml"]


# --- Anything else with an unknown language defaults to bash, untouched ---


def test_unparseable_content_defaults_to_bash_and_is_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_code(text="pip install markwright", code_language=CodeLanguageLabel.UNKNOWN)

    languages = format_code_blocks(doc)

    assert item.code_language == CodeLanguageLabel.BASH
    assert item.text == "pip install markwright"
    assert languages == ["bash"]


# --- A language docling already identified is kept, just tagged for the fence ---


def test_an_already_identified_language_is_kept_and_tagged() -> None:
    doc = DoclingDocument(name="test")
    item = doc.add_code(text="print('hola')", code_language=CodeLanguageLabel.PYTHON)

    languages = format_code_blocks(doc)

    assert item.code_language == CodeLanguageLabel.PYTHON
    assert item.text == "print('hola')"
    assert languages == ["python"]


# --- Multiple code items are returned in document order ---


def test_multiple_code_blocks_return_languages_in_document_order() -> None:
    doc = DoclingDocument(name="test")
    doc.add_code(text='{"a": 1}', code_language=CodeLanguageLabel.UNKNOWN)
    doc.add_code(text="<a>1</a>", code_language=CodeLanguageLabel.UNKNOWN)
    doc.add_code(text="echo hola", code_language=CodeLanguageLabel.UNKNOWN)

    languages = format_code_blocks(doc)

    assert languages == ["json", "xml", "bash"]


def test_a_document_with_no_code_items_returns_an_empty_list() -> None:
    doc = DoclingDocument(name="test")

    languages = format_code_blocks(doc)

    assert languages == []


# --- apply_code_fence_languages: string-level insertion into rendered Markdown ---


def test_a_single_fence_gets_its_language_tag_inserted() -> None:
    markdown = 'Texto.\n\n```\n{"a": 1}\n```\n\nMás texto.'

    result = apply_code_fence_languages(markdown, ["json"])

    assert result == 'Texto.\n\n```json\n{"a": 1}\n```\n\nMás texto.'


def test_multiple_fences_get_their_languages_in_order() -> None:
    markdown = "```\n{}\n```\n\n```\n<a/>\n```\n\n```\necho hola\n```"

    result = apply_code_fence_languages(markdown, ["json", "xml", "bash"])

    assert result == "```json\n{}\n```\n\n```xml\n<a/>\n```\n\n```bash\necho hola\n```"


def test_markdown_with_no_fences_is_left_untouched() -> None:
    markdown = "Solo texto normal, sin bloques de código."

    result = apply_code_fence_languages(markdown, [])

    assert result == markdown
