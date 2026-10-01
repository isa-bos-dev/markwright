from __future__ import annotations

import re
from typing import TYPE_CHECKING

from docling_core.types.doc import DocItemLabel

if TYPE_CHECKING:
    from docling_core.types.doc.document import DoclingDocument

# A leading arabic numbering like "1.", "3.1.", "4.2.3" — the dot and the space
# before the heading's own text are both optional, since real PDFs use either
# ("1.La sociedad..." vs "3.1. Datos simples").
_NUMBERING = re.compile(r"^(\d+(?:\.\d+)*)\.?\s*")

# Markdown headings stop meaning anything past ###### (6 hashes); level N maps
# to N+1 hashes (see docling_core's MarkdownParams._format_heading), so level
# is capped at 5.
_MAX_LEVEL = 5


def fix_heading_levels(document: DoclingDocument) -> None:
    """Set each numbered section heading's level from its own numbering.

    docling classifies "1." and "3.1." headings correctly as section headers,
    but gives every one of them the same flat level — so Markwright's export
    collapses a real hierarchy into same-depth ``##`` headings. This computes
    the real depth from the heading's own text instead, offset by one level
    so a top-level "1." section nests under the document's own (unnumbered)
    title instead of competing with it for ``#``. Headings with no leading
    number, or where the number isn't followed by real heading text, are left
    exactly as docling classified them (FID-FR-002, see Non-Goals in
    docs/specs/011-conversion-fidelity/specification.md).
    """
    for item in document.texts:
        if item.label != DocItemLabel.SECTION_HEADER:
            continue
        depth = _numbering_depth(item.text)
        if depth is None:
            continue
        item.level = min(depth + 1, _MAX_LEVEL)


def _numbering_depth(text: str) -> int | None:
    match = _NUMBERING.match(text)
    if match is None:
        return None
    rest = text[match.end() :]
    # Reject only an empty remainder (just a number, not a heading) or one that
    # starts with another digit (the number wasn't fully consumed by _NUMBERING).
    # Anything else — a letter, but also "¿"/"¡" or a quote, common in Spanish
    # headings right after the number — counts as real heading text.
    if not rest or rest[0].isdigit():
        return None
    return match.group(1).count(".")
