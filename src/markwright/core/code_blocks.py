from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING
from xml.parsers.expat import ExpatError

import defusedxml.minidom
from defusedxml.common import DefusedXmlException
from docling_core.types.doc import CodeItem, CodeLanguageLabel

if TYPE_CHECKING:
    from collections.abc import Iterator

    from docling_core.types.doc.document import DoclingDocument

# A block-level fence as docling's serializer always writes it — no language
# tag, ever (confirmed by reading its source: markdown.py hardcodes
# f"```\n{text}\n```"). Doesn't match single-backtick inline code, which
# applies to a different, much rarer shape of CodeItem (see format_code_blocks).
_FENCE = re.compile(r"```\n(.*?)\n```", re.DOTALL)


def format_code_blocks(document: DoclingDocument) -> list[str]:
    """Reformat and tag code blocks, returning a fence language per block, in order.

    docling's markdown serializer in the installed version never writes a
    fence language (```` ``` ```` always, never ```` ```python ````) —
    confirmed by reading its source, not assumed — so getting a language tag
    into the output needs a second pass over the generated Markdown text, for
    which this returns the ordered list of tags to apply (SYN-FR-005).

    A block docling couldn't identify (``UNKNOWN``) is tried as JSON, then as
    XML — both are self-describing, so a working parse means the reformatted,
    properly-indented version is provably correct, not a guess; the
    newlines PDF extraction drops (confirmed: docling's own raw text has
    none) are reconstructed this way, not inferred from layout. Anything that
    parses as neither is left exactly as extracted and tagged "bash" (most of
    her real documents are terminal commands).
    """
    languages: list[str] = []
    for item in document.texts:
        if not isinstance(item, CodeItem):
            continue
        if item.code_language == CodeLanguageLabel.UNKNOWN:
            item.code_language = _detect_and_reformat(item)
        languages.append(item.code_language.value.lower())
    return languages


def apply_code_fence_languages(markdown: str, languages: list[str]) -> str:
    """Insert a fence language tag docling's own serializer never writes.

    ``languages`` must be the list ``format_code_blocks`` returned for the
    same document, in the same (document) order — the Nth fenced block in
    the rendered Markdown is assumed to be the Nth code item, since the
    serializer walks the document in that order too.
    """
    remaining: Iterator[str] = iter(languages)

    def _tag(match: re.Match[str]) -> str:
        language = next(remaining, "")
        return f"```{language}\n{match.group(1)}\n```"

    return _FENCE.sub(_tag, markdown)


def _detect_and_reformat(item: CodeItem) -> CodeLanguageLabel:
    try:
        parsed = json.loads(item.text)
    except ValueError:
        pass
    else:
        item.text = json.dumps(parsed, indent=2, ensure_ascii=False)
        return CodeLanguageLabel.JSON

    try:
        # defusedxml, not stdlib xml.dom.minidom: this parses content pulled
        # from a PDF the user doesn't control, so it must resist XXE/entity-
        # expansion attacks, not just malformed input (ExpatError).
        dom = defusedxml.minidom.parseString(item.text)
    except (ExpatError, DefusedXmlException):
        pass
    else:
        pretty_lines = [line for line in dom.toprettyxml(indent="  ").splitlines() if line.strip()]
        if pretty_lines and pretty_lines[0].startswith("<?xml"):
            pretty_lines = pretty_lines[1:]
        item.text = "\n".join(pretty_lines)
        return CodeLanguageLabel.XML

    return CodeLanguageLabel.BASH
