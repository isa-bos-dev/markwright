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

# Level for an unnumbered heading that isn't the document's own title (e.g. a
# margin note's own heading, "Ejemplo", "No obstante...") — 4 hashes, nested
# below even a 2-level numbered subsection (SYN-FR-002).
_UNNUMBERED_LEVEL = 3


def fix_heading_levels(document: DoclingDocument) -> None:
    """Set each section heading's level from its own numbering, or its role.

    docling classifies "1." and "3.1." headings correctly as section headers,
    but gives every one of them the same flat level — so Markwright's export
    collapses a real hierarchy into same-depth ``##`` headings. This computes
    the real depth from the heading's own text instead, offset by one level
    so a top-level "1." section nests under the document's own (unnumbered)
    title instead of competing with it for ``#`` (FID-FR-002).

    A heading with no leading number is either the document's own title — the
    first section header found, which becomes the document's one ``#`` — or
    some other unnumbered heading (a margin note's own title, "Ejemplo"),
    which is pushed to a fixed, deeply-nested level instead of competing with
    real chapter/section headings (SYN-FR-002). This can't tell an unnumbered
    heading that is secretly a byline or a redundant table of contents from a
    real one — that's still an editorial judgment call, not automated (see
    Non-Goals in docs/specs/012-syntax-fidelity/specification.md).
    """
    seen_title = False
    for item in document.texts:
        if item.label != DocItemLabel.SECTION_HEADER:
            continue
        depth = _numbering_depth(item.text)
        if depth is not None:
            item.level = min(depth + 1, _MAX_LEVEL)
        elif not seen_title:
            item.level = 0
        else:
            item.level = _UNNUMBERED_LEVEL
        seen_title = True


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
