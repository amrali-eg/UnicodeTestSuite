"""Category taxonomy.

Two independent taxonomies exist:

- ASCII_CATEGORIES: categories used only under 01_ASCII (pure ASCII
  content only - these are never re-encoded into other encodings).
- SHARED_CATEGORIES: the ten numbered categories whose documents form
  the identical logical corpus re-encoded into every core Unicode
  encoding (02_UTF8 .. 06_UTF32BE) and, where a given legacy encoding
  is capable of representing them, into the legacy encoding families
  too (07_WindowsCodePages, 08_ISO8859, 09_EastAsian, 10_Cyrillic).

Both orders are fixed and append-only, exactly like CATEGORY_ORDER was
in the previous revision, so DocumentIDs stay stable across releases.
"""

from __future__ import annotations

from dataclasses import dataclass

# Categories that live only under 01_ASCII. Fixed, append-only order.
ASCII_CATEGORIES: tuple[str, ...] = (
    "Programming",
    "JSON",
    "XML",
    "HTML",
    "Markdown",
    "CSV",
    "Logs",
    "Config",
    "RandomASCII",
)


@dataclass(frozen=True)
class SharedCategory:
    """One of the ten numbered categories shared across all Unicode encodings."""

    code: str   # two-digit code, e.g. "06"
    name: str   # short name, e.g. "CJK"

    @property
    def slug(self) -> str:
        """Directory / filename token, e.g. "06-CJK"."""
        return f"{self.code}-{self.name}"


# Fixed, append-only order. Content assignment rationale (documented in
# README.md): Greek and other scripts without a dedicated bucket land in
# 10-UnicodeMisc alongside symbol/edge-case documents.
SHARED_CATEGORIES: tuple[SharedCategory, ...] = (
    SharedCategory("01", "Latin"),
    SharedCategory("02", "Cyrillic"),
    SharedCategory("03", "RTL"),
    SharedCategory("04", "Indic"),
    SharedCategory("05", "SoutheastAsian"),
    SharedCategory("06", "CJK"),
    SharedCategory("07", "SupplementaryPlanes"),
    SharedCategory("08", "Mathematics"),
    SharedCategory("09", "Emoji"),
    SharedCategory("10", "UnicodeMisc"),
)


def shared_category_by_name(name: str) -> SharedCategory:
    """Look up a SharedCategory by its short name."""
    for category in SHARED_CATEGORIES:
        if category.name == name:
            return category
    raise KeyError(f"Unknown shared category: {name}")


# Binary-format stub categories, used only under 13_Binary. Fixed order.
BINARY_CATEGORIES: tuple[str, ...] = (
    "EXE", "DLL", "PNG", "JPG", "GIF", "ZIP", "PDF",
    "Office", "Audio", "Video", "SQLite", "Random",
)
