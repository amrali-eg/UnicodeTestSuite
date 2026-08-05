"""Filename construction rules.

Every generated filename fully encodes its own metadata, e.g.:

    DOC000028_01_Latin_English_iso-8859-1_LF.txt

`DocumentID_CategoryCode_CategoryName_Title_Encoding_[BOM_]LineEnding.ext`

so a file can be identified - and its encoding parsed - purely from its
name, without consulting the manifest.

CategoryCode is never omitted (every category, ASCII or shared, has a
numeric code - see generator/categories.py), so the Encoding field
always lands at the same fixed position, the 5th token, when a
filename is split on "_":

    index 0: DocumentID
    index 1: CategoryCode
    index 2: CategoryName
    index 3: Title
    index 4: Encoding   <- always here, regardless of BOM presence
    index 5: BOM (only present for encodings that have a BOM concept)
    index 5 or 6: LineEnding (last token)

Fields are joined with "_", so each field's own content may freely
contain "-" (hyphens are preserved, e.g. "iso-8859-1", "windows-1250")
but never "_": any underscore inside a value (e.g. the Python codec
name "shift_jis") is normalized to "-" first, so it can never be
mistaken for a field boundary when the filename is split on "_".
"""

from __future__ import annotations

import re

# Letters, digits, and hyphens are kept; everything else (including a
# literal underscore, handled separately below) is stripped.
_INVALID_CHARS = re.compile(r"[^A-Za-z0-9-]+")


def sanitize_component(value: str) -> str:
    """Strip a filename component down to safe, unambiguous ASCII text.

    Hyphens are preserved so encoding names like "iso-8859-1" remain
    directly readable and parseable in the filename. Underscores are
    converted to hyphens first (rather than stripped) so a value such
    as "shift_jis" can't be split apart by code that naively splits the
    full filename on "_" to recover its fields.
    """
    normalized = value.replace("_", "-")
    cleaned = _INVALID_CHARS.sub("", normalized)
    cleaned = cleaned.strip("-")
    return cleaned or "X"


def build_filename(
    doc_id: str,
    category_tokens: list[str],
    title: str,
    encoding_label: str,
    bom_label: str | None,
    line_ending_label: str,
    extension: str = "txt",
) -> str:
    """Build a fully self-describing filename for a generated corpus file.

    `category_tokens` is always two tokens: [code, name], e.g.
    ["11", "Programming"] or ["06", "CJK"] - every category (ASCII or
    shared) has a numeric code, so this field never varies in length.

    `bom_label` is omitted entirely (not even as "NoBOM") when passed as
    None - used for encodings that have no BOM concept at all (ASCII and
    every legacy codepage), where the token would otherwise be a
    constant, redundant part of every filename in that folder. It is
    still recorded accurately in Manifest.csv regardless.
    """
    parts = [sanitize_component(doc_id)]
    parts.extend(sanitize_component(token) for token in category_tokens)
    parts.append(sanitize_component(title))
    parts.append(sanitize_component(encoding_label))
    if bom_label is not None:
        parts.append(sanitize_component(bom_label))
    parts.append(sanitize_component(line_ending_label))
    return "_".join(parts) + f".{extension}"
