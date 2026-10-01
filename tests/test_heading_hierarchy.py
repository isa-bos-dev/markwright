from docling_core.types.doc import DocItemLabel, SectionHeaderItem
from docling_core.types.doc.document import DoclingDocument

from markwright.core.heading_hierarchy import fix_heading_levels


def _level(doc: DoclingDocument, index: int = 0) -> int:
    item = doc.texts[index]
    assert isinstance(item, SectionHeaderItem)
    return item.level


# --- Numbered headings get their depth from their own numbering ---


def test_top_level_numbered_heading_with_no_space_after_the_dot_becomes_level_one() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.La sociedad de la información")

    fix_heading_levels(doc)

    assert _level(doc) == 1  # "##" — nests under the document's own (unnumbered) title


def test_two_component_numbered_heading_with_space_after_the_dot_becomes_level_two() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="3.1. Datos simples")

    fix_heading_levels(doc)

    assert _level(doc) == 2


def test_numbered_heading_followed_by_an_inverted_question_mark_is_still_detected() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="3.¿Qué es un dato?")

    fix_heading_levels(doc)

    assert _level(doc) == 1


def test_three_component_numbered_heading_becomes_level_three() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="4.2.3 Sub-sub-sección")

    fix_heading_levels(doc)

    assert _level(doc) == 3


def test_sibling_numbered_headings_get_different_levels_from_a_flat_default() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.Primera sección")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.1. Subsección")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="2.Segunda sección")

    fix_heading_levels(doc)

    assert [_level(doc, i) for i in range(3)] == [1, 2, 1]


# --- The first heading is the document's title; later unnumbered headings
# --- are pushed to a fixed, deeply-nested level instead of competing with
# --- real chapter/section headings (SYN-FR-002).


def test_the_first_heading_in_the_document_becomes_the_title_at_level_zero() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="Fundamentos de data science")

    fix_heading_levels(doc)

    assert _level(doc) == 0  # "#"


def test_a_number_only_heading_as_the_first_heading_also_becomes_the_title() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="2024")

    fix_heading_levels(doc)

    assert _level(doc) == 0


def test_an_unnumbered_heading_after_the_title_is_pushed_to_a_fixed_deep_level() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="Fundamentos de data science")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.La sociedad de la información")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="Ejemplo")

    fix_heading_levels(doc)

    assert [_level(doc, i) for i in range(3)] == [0, 1, 3]  # "#", "##", "####"


def test_an_unnumbered_heading_that_comes_first_because_the_document_opens_numbered() -> None:
    # If the very first heading is already numbered, there's no separate
    # title to promote — it just gets its own numbered depth as usual, and
    # any *later* unnumbered heading still goes to the fixed deep level.
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.Primer capítulo")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="Ejemplo")

    fix_heading_levels(doc)

    assert [_level(doc, i) for i in range(2)] == [1, 3]


def test_deep_numbering_is_capped_so_markdown_never_exceeds_six_hashes() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.SECTION_HEADER, text="1.1.1.1.1.1.1 Demasiado profundo")

    fix_heading_levels(doc)

    assert _level(doc) == 5


# --- Only section headers are touched ---


def test_plain_text_items_are_left_untouched() -> None:
    doc = DoclingDocument(name="test")
    doc.add_text(label=DocItemLabel.TEXT, text="1.1. Esto no es un título")

    fix_heading_levels(doc)  # must not raise, even though TextItem has no .level

    assert doc.texts[0].text == "1.1. Esto no es un título"
