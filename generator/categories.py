"""Category taxonomy.

Two independent taxonomies exist, both using the same numbered
Category shape so every document - ASCII or shared - gets a two-part
category token (code + name). This is deliberate: it keeps the
filename format identical regardless of category, so the encoding
field always lands in the same position when a filename is split on
"_" (see generator/filenames.py).

Codes follow the order things actually appear in the corpus tree:

- ASCII_CATEGORIES (codes 01-09): categories used only under
  01_ASCII - the first root folder - so they get the first block of
  codes. Pure ASCII content only; never re-encoded into other
  encodings.
- SHARED_CATEGORIES (codes 10-19): the ten numbered categories whose
  documents form the identical logical corpus re-encoded into every
  core Unicode encoding, starting with 02_UTF8 - the second root
  folder - and, where a given legacy encoding is capable of
  representing them, into the legacy encoding families too
  (07_WindowsCodePages, 08_ISO8859, 09_EastAsian, 10_Cyrillic).

This also matches DocumentID order: ASCII documents are assigned IDs
first (see generator/documents.py), so their categories having the
lower codes keeps both numbering schemes moving in the same direction.

The two code ranges (01-09 vs 10-19) never overlap, so a code number
uniquely identifies one category anywhere in the whole corpus, not
just within its own root folder.

Both orders are fixed and append-only, exactly like CATEGORY_ORDER was
in the previous revision, so DocumentIDs stay stable across releases.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    """One numbered category: a two-digit code plus a short name."""

    code: str   # two-digit code, e.g. "06" or "11"
    name: str   # short name, e.g. "CJK" or "Programming"

    @property
    def slug(self) -> str:
        """Directory / filename token, e.g. "15-CJK" or "01-Programming"."""
        return f"{self.code}-{self.name}"


# Categories that live only under 01_ASCII - the first root folder, so
# these get the first block of codes (01-09). Fixed, append-only order.
ASCII_CATEGORIES: tuple[Category, ...] = (
    Category("01", "Programming"),
    Category("02", "JSON"),
    Category("03", "XML"),
    Category("04", "HTML"),
    Category("05", "Markdown"),
    Category("06", "CSV"),
    Category("07", "Logs"),
    Category("08", "Config"),
    Category("09", "RandomASCII"),
)


# Codes 10-19 (distinct from ASCII_CATEGORIES' 01-09) so every code in
# the corpus is globally unique. Content assignment rationale
# (documented in README.md): Greek and other scripts without a
# dedicated bucket land in 19-UnicodeMisc alongside symbol/edge-case
# documents. Fixed, append-only order.
SHARED_CATEGORIES: tuple[Category, ...] = (
    Category("10", "Latin"),
    Category("11", "Cyrillic"),
    Category("12", "RTL"),
    Category("13", "Indic"),
    Category("14", "SoutheastAsian"),
    Category("15", "CJK"),
    Category("16", "SupplementaryPlanes"),
    Category("17", "Mathematics"),
    Category("18", "Emoji"),
    Category("19", "UnicodeMisc"),
)


def category_by_name(categories: tuple[Category, ...], name: str) -> Category:
    """Look up a Category by its short name within a given taxonomy."""
    for category in categories:
        if category.name == name:
            return category
    raise KeyError(f"Unknown category: {name}")


# Binary-format stub categories, used only under 13_Binary. Fixed order.
BINARY_CATEGORIES: tuple[str, ...] = (
    "EXE", "DLL", "PNG", "JPG", "GIF", "ZIP", "PDF",
    "Office", "Audio", "Video", "SQLite", "Random",
)
