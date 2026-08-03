"""Encoding table and per-document encode capability checks.

Every encoding the corpus can target is described by an EncodingSpec.
Encodings incapable of representing a given document's text are simply
skipped for that document, detected by attempting the real encode and
catching UnicodeEncodeError.

Two families of specs exist:

- CORE_UNICODE_SPECS: ASCII plus the five Unicode Transformation
  Formats (UTF-8/16LE/16BE/32LE/32BE), each with a NoBOM and (except
  ASCII) BOM variant. These map straight to folders 01_ASCII..06_UTF32BE.
- LEGACY_FAMILIES: groups of related legacy codepages/encodings, each
  written under one root folder with one subfolder per member codec
  (e.g. 07_WindowsCodePages/Windows1250/, 09_EastAsian/ShiftJIS/).
  None of these have a BOM concept.

corpus.py is responsible for nesting a category subfolder underneath
whichever of these a document's shared category maps to.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EncodingSpec:
    """Describes one output encoding variant."""

    label: str             # human-readable label used in filenames, e.g. "UTF16LE"
    codec: str              # Python codec name used for encode()/decode()
    bom_bytes: bytes         # b"" if this variant never has a BOM
    root_folder: str         # top-level corpus folder this variant lives under
    family_subfolder: str | None  # optional nested folder (legacy codec families)

    @property
    def has_bom(self) -> bool:
        return len(self.bom_bytes) > 0

    @property
    def bom_label(self) -> str:
        return "BOM" if self.has_bom else "NoBOM"


# The six core Unicode encoding folders (01_ASCII .. 06_UTF32BE).
CORE_UNICODE_SPECS: tuple[EncodingSpec, ...] = (
    EncodingSpec("ASCII", "ascii", b"", "01_ASCII", None),

    EncodingSpec("UTF8", "utf-8", b"", "02_UTF8", None),
    EncodingSpec("UTF8", "utf-8", b"\xef\xbb\xbf", "02_UTF8", None),

    EncodingSpec("UTF16LE", "utf-16-le", b"", "03_UTF16LE", None),
    EncodingSpec("UTF16LE", "utf-16-le", b"\xff\xfe", "03_UTF16LE", None),

    EncodingSpec("UTF16BE", "utf-16-be", b"", "04_UTF16BE", None),
    EncodingSpec("UTF16BE", "utf-16-be", b"\xfe\xff", "04_UTF16BE", None),

    EncodingSpec("UTF32LE", "utf-32-le", b"", "05_UTF32LE", None),
    EncodingSpec("UTF32LE", "utf-32-le", b"\xff\xfe\x00\x00", "05_UTF32LE", None),

    EncodingSpec("UTF32BE", "utf-32-be", b"", "06_UTF32BE", None),
    EncodingSpec("UTF32BE", "utf-32-be", b"\x00\x00\xfe\xff", "06_UTF32BE", None),
)


def _legacy(root_folder: str, entries: tuple[tuple[str, str], ...]) -> tuple[EncodingSpec, ...]:
    """Build EncodingSpecs for a legacy family: (label, codec) pairs, no BOM."""
    return tuple(
        EncodingSpec(label, codec, b"", root_folder, label)
        for label, codec in entries
    )


# 07_WindowsCodePages: the nine Windows code pages 1250-1258.
WINDOWS_CODEPAGE_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "07_WindowsCodePages",
    (
        ("Windows1250", "cp1250"),
        ("Windows1251", "cp1251"),
        ("Windows1252", "cp1252"),
        ("Windows1253", "cp1253"),
        ("Windows1254", "cp1254"),
        ("Windows1255", "cp1255"),
        ("Windows1256", "cp1256"),
        ("Windows1257", "cp1257"),
        ("Windows1258", "cp1258"),
    ),
)

# 08_ISO8859: parts 1-16, excluding part 12 (never finalized/withdrawn).
ISO8859_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "08_ISO8859",
    tuple(
        (f"ISO8859{part}", f"iso8859-{part}")
        for part in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16)
    ),
)

# 09_EastAsian: Japanese, Chinese, Korean, and Southeast-Asian legacy encodings.
EAST_ASIAN_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "09_EastAsian",
    (
        ("ShiftJIS", "shift_jis"),
        ("CP932", "cp932"),
        ("EUCJP", "euc_jp"),
        ("ISO2022JP", "iso2022_jp"),
        ("GB2312", "gb2312"),
        ("GBK", "gbk"),
        ("GB18030", "gb18030"),
        ("Big5", "big5"),
        ("Big5HKSCS", "big5hkscs"),
        ("HZ", "hz"),
        ("EUCKR", "euc_kr"),
        ("CP949", "cp949"),
        ("ISO2022KR", "iso2022_kr"),
        ("Windows874", "cp874"),
        ("TIS620", "tis_620"),
    ),
)

# 10_Cyrillic: Cyrillic-focused legacy encodings not already covered by
# 07_WindowsCodePages / 08_ISO8859 (kept here for convenient discovery).
CYRILLIC_LEGACY_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "10_Cyrillic",
    (
        ("KOI8R", "koi8_r"),
        ("KOI8U", "koi8_u"),
    ),
)

LEGACY_FAMILIES: tuple[tuple[EncodingSpec, ...], ...] = (
    WINDOWS_CODEPAGE_SPECS,
    ISO8859_SPECS,
    EAST_ASIAN_SPECS,
    CYRILLIC_LEGACY_SPECS,
)


def can_encode(text: str, codec: str) -> bool:
    """Return True if `text` can be losslessly encoded with `codec`."""
    try:
        text.encode(codec)
    except UnicodeEncodeError:
        return False
    return True


def encode_with_bom(text: str, spec: EncodingSpec) -> bytes:
    """Encode `text` under the given spec, prefixing its BOM if any."""
    return spec.bom_bytes + text.encode(spec.codec)


def strip_bom(data: bytes, spec: EncodingSpec) -> bytes:
    """Remove this spec's BOM prefix from raw bytes, if present."""
    if spec.has_bom and data.startswith(spec.bom_bytes):
        return data[len(spec.bom_bytes):]
    return data


def all_specs() -> tuple[EncodingSpec, ...]:
    """Every EncodingSpec the generator knows about, core and legacy."""
    specs: list[EncodingSpec] = list(CORE_UNICODE_SPECS)
    for family in LEGACY_FAMILIES:
        specs.extend(family)
    return tuple(specs)


def find_spec(label: str, bom_label: str) -> EncodingSpec | None:
    """Look up the EncodingSpec matching a manifest (Encoding, BOM) pair.

    Returns None for pseudo-labels like "Binary" that don't correspond
    to a real text codec (invalid-unicode and binary fixtures).
    """
    for spec in all_specs():
        if spec.label == label and spec.bom_label == bom_label:
            return spec
    return None
