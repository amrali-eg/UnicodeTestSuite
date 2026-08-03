"""Filename construction rules.

Every generated filename fully encodes its own metadata, e.g.:

    000123_06_CJK_Japanese_UTF16LE_BOM_CRLF.txt

`DocumentID_[CategoryCode_]CategoryName_Title_Encoding_BOM_LineEnding.ext`

so a file can be identified purely by its name, without consulting the
manifest. Filenames use only ASCII letters, digits, and underscores to
stay valid across Windows, Linux, and macOS.
"""

from __future__ import annotations

import re

_INVALID_CHARS = re.compile(r"[^A-Za-z0-9]+")


def sanitize_component(value: str) -> str:
    """Strip a filename component down to safe ASCII word characters."""
    cleaned = _INVALID_CHARS.sub("", value)
    return cleaned or "X"


def build_filename(
    doc_id: str,
    category_tokens: list[str],
    title: str,
    encoding_label: str,
    bom_label: str,
    line_ending_label: str,
    extension: str = "txt",
) -> str:
    """Build a fully self-describing filename for a generated corpus file.

    `category_tokens` is one token for ASCII categories (e.g. ["Programming"])
    or two tokens for shared categories (e.g. ["06", "CJK"]).
    """
    parts = [sanitize_component(doc_id)]
    parts.extend(sanitize_component(token) for token in category_tokens)
    parts.append(sanitize_component(title))
    parts.append(sanitize_component(encoding_label))
    parts.append(sanitize_component(bom_label))
    parts.append(sanitize_component(line_ending_label))
    return "_".join(parts) + f".{extension}"
