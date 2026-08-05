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
#
# Labels chosen as the best match between Python's codec names and
# .NET's Encoding.WebName/EncodingInfo.Name values, verified against
# both (see generator/documents.py module docstring policy notes for
# the general approach). Bare "utf-16"/"utf-32" were deliberately
# rejected for the LE variants: in Python those names resolve to a
# *different*, BOM-native codec than "utf-16-le"/"utf-32-le" (the one
# actually used here), even though .NET's own EncodingInfo.Name for
# that codepage is the unadorned "utf-16"/"utf-32". "utf-16LE"/
# "utf-32LE" are valid, unambiguous input in both ecosystems instead.
CORE_UNICODE_SPECS: tuple[EncodingSpec, ...] = (
    EncodingSpec("us-ascii", "ascii", b"", "01_ASCII", None),

    EncodingSpec("utf-8", "utf-8", b"", "02_UTF8", None),
    EncodingSpec("utf-8", "utf-8", b"\xef\xbb\xbf", "02_UTF8", None),

    EncodingSpec("utf-16LE", "utf-16-le", b"", "03_UTF16LE", None),
    EncodingSpec("utf-16LE", "utf-16-le", b"\xff\xfe", "03_UTF16LE", None),

    EncodingSpec("utf-16BE", "utf-16-be", b"", "04_UTF16BE", None),
    EncodingSpec("utf-16BE", "utf-16-be", b"\xfe\xff", "04_UTF16BE", None),

    EncodingSpec("utf-32LE", "utf-32-le", b"", "05_UTF32LE", None),
    EncodingSpec("utf-32LE", "utf-32-le", b"\xff\xfe\x00\x00", "05_UTF32LE", None),

    EncodingSpec("utf-32BE", "utf-32-be", b"", "06_UTF32BE", None),
    EncodingSpec("utf-32BE", "utf-32-be", b"\x00\x00\xfe\xff", "06_UTF32BE", None),
)


def _legacy(root_folder: str, entries: tuple[tuple[str, str], ...]) -> tuple[EncodingSpec, ...]:
    """Build EncodingSpecs for a legacy family: (label, codec) pairs, no BOM."""
    return tuple(
        EncodingSpec(label, codec, b"", root_folder, label)
        for label, codec in entries
    )


# 07_WindowsCodePages: the nine Windows code pages 1250-1258.
# Labels confirmed as .NET's own EncodingInfo.Name / WebName values,
# and confirmed as valid Python aliases resolving to the same codec.
WINDOWS_CODEPAGE_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "07_WindowsCodePages",
    (
        ("windows-1250", "cp1250"),
        ("windows-1251", "cp1251"),
        ("windows-1252", "cp1252"),
        ("windows-1253", "cp1253"),
        ("windows-1254", "cp1254"),
        ("windows-1255", "cp1255"),
        ("windows-1256", "cp1256"),
        ("windows-1257", "cp1257"),
        ("windows-1258", "cp1258"),
    ),
)

# 08_ISO8859: parts 1-9, 13, 15 (11 parts total). "iso-8859-N" confirmed
# as a valid Python alias for every part used here.
#
# Parts 10, 11, 14, and 16 were removed after live .NET testing (not
# just research) confirmed they don't work:
# - Part 10 (28600): Encoding.GetEncoding(28600) itself throws "No data
#   is available for encoding 28600" - confirming the code page was
#   never actually implemented in .NET at all, by number or by name.
#   Parts 14 (28604) and 16 (28606) were never real Windows code pages
#   either, for the same reason, and are assumed to fail identically.
# - Part 11 is a subtler case: Encoding.GetEncoding("iso-8859-11")
#   does *not* throw, but returns the "Thai (Windows)" encoding - i.e.
#   code page 874, not a genuine distinct ISO-8859-11 implementation.
#   Python's iso8859-11 and cp874 codecs are confirmed to diverge
#   across the whole 0x80-0x9F range (cp874 leaves those unmapped;
#   iso8859-11 maps them as C1 controls), so using this name would
#   satisfy "GetEncoding doesn't throw" while silently handing back a
#   decoder that can disagree with the actual bytes for anything in
#   that range - worse than a clean failure, so it was dropped too.
ISO8859_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "08_ISO8859",
    tuple(
        (f"iso-8859-{part}", f"iso8859-{part}")
        for part in (1, 2, 3, 4, 5, 6, 7, 8, 9, 13, 15)
    ),
)

# 09_EastAsian: Japanese, Chinese, and Korean legacy encodings.
#
# CP932 and GBK were removed here rather than renamed: .NET has no
# distinct identity for either one. Codepage 932 is called "shift_jis"
# regardless of whether you think of it as Shift-JIS or CP932, and
# codepage 936 is called "gb2312" even though its actual repertoire is
# GBK's (confirmed by a reported .NET bug: asking .NET for "gbk" by
# name returns its "gb2312" encoding - dotnet/runtime#43745). Keeping
# both Python-distinct codecs would have meant two folders mapping to
# the same .NET name, so the CP932/GBK entries were dropped as
# redundant with ShiftJIS/GB2312 for this project's purposes.
#
# ISO2022JP, Big5HKSCS, HZ, and TIS620 were removed for the same
# "every enc_token must resolve via Encoding.GetEncoding" requirement:
# no confirmed, unambiguous, non-colliding .NET name could be found for
# any of them (Big5-HKSCS in particular was never a native Windows
# code page at all).
#
# CP874 and CP949 were also removed after live .NET testing. Both
# "cp874" and "cp949" throw in .NET (confirmed with
# CodePagesEncodingProvider registered), and no alternate name works in
# both ecosystems either: .NET's own names for these code pages
# ("windows-874" and "ks_c_5601-1987") are not valid Python names for
# the same codecs at all - "windows-874" isn't a recognized Python
# alias for cp874, and "ks_c_5601-1987" is a Python alias for a
# *different* codec (euc_kr), not cp949. Two further CP949 candidates
# suggested by Python's own alias list, "ms949" and "uhc", were also
# tested live in .NET and both throw. No shared name exists.
#
# IMPORTANT for requirement 2 (Encoding.GetEncoding(enc_token) must
# work): on .NET Core / .NET 5+, none of the encodings below resolve
# out of the box - only ASCII, ISO-8859-1, and UTF-7/8/16/32 do. Every
# other name here requires the app to add the
# System.Text.Encoding.CodePages package and call
# Encoding.RegisterProvider(CodePagesEncodingProvider.Instance) once at
# startup; only .NET Framework has them built in.
EAST_ASIAN_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "09_EastAsian",
    (
        ("shift_jis", "shift_jis"),
        ("euc-jp", "euc_jp"),
        ("gb2312", "gb2312"),
        ("gb18030", "gb18030"),
        ("big5", "big5"),
        ("euc-kr", "euc_kr"),
        ("iso-2022-kr", "iso2022_kr"),
    ),
)

# 10_Cyrillic: Cyrillic-focused legacy encodings not already covered by
# 07_WindowsCodePages / 08_ISO8859 (kept here for convenient discovery).
CYRILLIC_LEGACY_SPECS: tuple[EncodingSpec, ...] = _legacy(
    "10_Cyrillic",
    (
        ("koi8-r", "koi8_r"),
        ("koi8-u", "koi8_u"),
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
