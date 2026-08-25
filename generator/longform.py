"""Long-form source documents for 15_LongForm.

The canonical documents in generator/documents.py are deliberately short
- a line or two each - which is right for exercising codec round-trips
but far too short for *detection*. Measured on the v2.0 corpus, the
legacy-encoded files had a median length of 31 bytes and a maximum of
125; Mozilla-UDE-class detectors (uchardet, chardet, UTF.Unknown) build
byte-frequency and character-bigram models and need hundreds of bytes to
converge. A benchmark made only of 31-byte samples scores a strong
detector and a weak one almost identically on exactly the legacy
encodings that separate them.

This module supplies the counterweight: multi-kilobyte natural-language
text, one document per language, drawn from the UDHR in Unicode project.
See data/udhr/PROVENANCE.md for the pinned source artifact, its copyright
notice, the sources that were considered and rejected, and the character
substitutions applied here.

Documents get reserved DocumentIDs from the DOC8xxxxx block, which the
sequential DOC000001.. assignment in generator/documents.py can never
reach. The order below is fixed and append-only, exactly like the
canonical document lists, so the IDs stay stable across releases.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Fixed, append-only: (source filename, title). Position determines the
# reserved DocumentID, so entries may only be appended.
LONGFORM_SOURCES: tuple[tuple[str, str], ...] = (
    ("udhr_deu_1996.txt", "German"),
    ("udhr_fra.txt", "French"),
    ("udhr_spa.txt", "Spanish"),
    ("udhr_por_PT.txt", "Portuguese"),
    ("udhr_ita.txt", "Italian"),
    ("udhr_nld.txt", "Dutch"),
    ("udhr_pol.txt", "Polish"),
    ("udhr_ces.txt", "Czech"),
    ("udhr_hun.txt", "Hungarian"),
    ("udhr_ron_2006.txt", "Romanian"),
    ("udhr_rus.txt", "Russian"),
    ("udhr_ukr.txt", "Ukrainian"),
    ("udhr_bul.txt", "Bulgarian"),
    ("udhr_ell_monotonic.txt", "Greek"),
    ("udhr_heb.txt", "Hebrew"),
    ("udhr_arb.txt", "Arabic"),
    ("udhr_tur.txt", "Turkish"),
    ("udhr_lit.txt", "Lithuanian"),
    ("udhr_lav.txt", "Latvian"),
    ("udhr_vie.txt", "Vietnamese"),
    ("udhr_jpn.txt", "Japanese"),
    ("udhr_kor.txt", "Korean"),
    ("udhr_cmn_hans.txt", "ChineseSimplified"),
    ("udhr_cmn_hant.txt", "ChineseTraditional"),
)

# Legacy encodings each long-form document is emitted into.
#
# Deliberately narrower than "every encoding that can represent the text".
# EUC-JP can encode German, and GB18030 can encode anything at all, but a
# detector cannot be expected to identify German prose as EUC-JP: the byte
# statistics look like Latin text, because that is what they are. Such a
# file is a valid encoding of the document and a meaningless detection
# target, and emitting it only depresses a benchmark score without saying
# anything about the detector.
#
# Measured against a real detector on the unrestricted corpus: 92.3%
# accuracy where the language matched the encoding, 60.0% where it did not,
# with the cross-script pairings outnumbering the real ones 70 to 52 and
# hiding the effect entirely.
#
# Each entry lists the encodings that historically carried that language.
# The generator still applies the usual can_encode check on top, so a pair
# listed here but not actually representable is skipped rather than forced.
LONGFORM_ENCODINGS: dict[str, tuple[str, ...]] = {
    # Western European: Latin-1 and its Windows and Latin-9 counterparts.
    "German":     ("windows-1252", "iso-8859-1", "iso-8859-15"),
    "French":     ("windows-1252", "iso-8859-1", "iso-8859-15"),
    "Spanish":    ("windows-1252", "iso-8859-1", "iso-8859-15"),
    "Portuguese": ("windows-1252", "iso-8859-1", "iso-8859-15"),
    "Italian":    ("windows-1252", "iso-8859-1", "iso-8859-15"),
    "Dutch":      ("windows-1252", "iso-8859-1", "iso-8859-15"),

    # Central European: Latin-2 and windows-1250.
    "Polish":     ("windows-1250", "iso-8859-2"),
    "Czech":      ("windows-1250", "iso-8859-2"),
    "Hungarian":  ("windows-1250", "iso-8859-2"),
    # Romanian has no legacy encoding in this corpus. Correct modern
    # orthography needs S and T with comma below (U+0218..U+021B), which
    # live in ISO-8859-16 - excluded because .NET has no code page for it.
    # windows-1250 and ISO-8859-2 carry only the cedilla forms, so they
    # cannot represent the text and would be skipped anyway; recording the
    # gap is more honest than listing pairings that never fire.
    "Romanian":   (),

    # Cyrillic. ISO-8859-5 lacks Ukrainian ghe with upturn, and KOI8-R
    # lacks the Ukrainian letters KOI8-U adds, so the lists differ.
    "Russian":    ("windows-1251", "iso-8859-5", "koi8-r"),
    "Ukrainian":  ("windows-1251", "koi8-u"),
    "Bulgarian":  ("windows-1251", "iso-8859-5"),

    # Single-script code pages.
    "Greek":      ("windows-1253", "iso-8859-7"),
    "Hebrew":     ("windows-1255", "iso-8859-8"),
    "Arabic":     ("windows-1256", "iso-8859-6"),
    "Turkish":    ("windows-1254", "iso-8859-9", "iso-8859-3"),
    "Vietnamese": ("windows-1258",),

    # Baltic.
    "Lithuanian": ("windows-1257", "iso-8859-13", "iso-8859-4"),
    "Latvian":    ("windows-1257", "iso-8859-13", "iso-8859-4"),

    # East Asian. GB18030 belongs to Chinese despite covering all of
    # Unicode; it is the modern PRC standard, not a universal fallback.
    "Japanese":          ("shift_jis", "euc-jp"),
    "Korean":            ("euc-kr", "iso-2022-kr"),
    "ChineseSimplified": ("gb2312", "gb18030"),
    "ChineseTraditional": ("big5", "gb18030"),
}


def legacy_encodings_for(title: str) -> tuple[str, ...]:
    """Legacy encoding labels appropriate to a long-form document."""
    return LONGFORM_ENCODINGS.get(title, ())


# Substitutions applied to every long-form body before encoding, each
# documented in data/udhr/PROVENANCE.md. Both are chosen to unlock real
# encodings without altering content or destroying detection signal.
_TYPOGRAPHIC_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    # U+2010 HYPHEN -> U+002D HYPHEN-MINUS.
    # Absent from every code page in this corpus, windows-125x included,
    # so substituting costs no detection signal. It alone blocked 130
    # (language, codec) pairs across the vendored set - including
    # Ukrainian in KOI8-U and Bulgarian in windows-1251, where it was the
    # only blocking character in otherwise fully encodable text.
    ("‐", "-"),
    # U+1F18 GREEK CAPITAL LETTER EPSILON WITH PSILI -> U+0395 EPSILON.
    # A single polytonic character in udhr_ell_monotonic.txt, which by
    # its own filename is monotonic text; monotonic orthography drops the
    # breathing marks, so this restores the document to the form it
    # declares. Without it the only Greek document in the corpus cannot
    # be emitted in iso-8859-7 or windows-1253 at all.
    ("Ἐ", "Ε"),
)

# Deliberately NOT normalized: U+2013 EN DASH, U+2019 RIGHT SINGLE
# QUOTATION MARK, U+201C/U+201D DOUBLE QUOTATION MARKS. These live at
# 0x96, 0x92, 0x93 and 0x94 in the windows-125x code pages and are absent
# from every ISO-8859 part and both KOI8 variants. That byte range is the
# classic signal distinguishing windows-1252 from iso-8859-1, one of the
# hardest and most valuable discriminations a detector has to make, so
# the corpus keeps it rather than trading it for a little more coverage.


# Separator that closes the four-line provenance header in every source
# file. The header carries characters most legacy code pages lack, so it
# is stripped before encoding; see PROVENANCE.md for why that is correct.
_HEADER_SEPARATOR = "---"
_HEADER_SEARCH_LIMIT = 400


@dataclass(frozen=True)
class LongFormDocument:
    """One multi-kilobyte natural-language document."""

    doc_id: str
    title: str
    source_filename: str
    text: str


def _strip_header(raw_text: str) -> str:
    """Remove the copyright/provenance header from a UDHR plain-text file."""
    if _HEADER_SEPARATOR in raw_text[:_HEADER_SEARCH_LIMIT]:
        return raw_text.split(_HEADER_SEPARATOR, 1)[1].strip()
    return raw_text.strip()


def normalize_body(text: str) -> str:
    """Apply the documented typographic substitutions to a document body."""
    for source, replacement in _TYPOGRAPHIC_SUBSTITUTIONS:
        text = text.replace(source, replacement)
    return text


def load_long_form_documents(data_dir: Path) -> list[LongFormDocument]:
    """Load every vendored long-form document, in fixed order.

    `data_dir` is the data/udhr directory next to GenerateCorpus.py.
    Returns an empty list when the directory is absent, so a checkout
    without the vendored data still generates the rest of the corpus
    rather than failing outright. A file listed in LONGFORM_SOURCES but
    missing from an existing directory is an error: it would silently
    shrink the corpus and change every downstream count.
    """
    if not data_dir.is_dir():
        return []

    documents: list[LongFormDocument] = []
    for index, (filename, title) in enumerate(LONGFORM_SOURCES, start=1):
        path = data_dir / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"Long-form source {filename} is listed in LONGFORM_SOURCES "
                f"but missing from {data_dir}"
            )
        raw_text = path.read_bytes().decode("utf-8")
        body = normalize_body(_strip_header(raw_text))
        # Normalize to LF so line endings are decided by the corpus layer,
        # exactly as the canonical documents are.
        body = body.replace("\r\n", "\n").replace("\r", "\n")
        if not body.endswith("\n"):
            body += "\n"
        documents.append(LongFormDocument(
            doc_id=f"DOC8{index:05d}",
            title=title,
            source_filename=filename,
            text=body,
        ))
    return documents


def long_form_count() -> int:
    """Number of long-form documents the generator expects to find."""
    return len(LONGFORM_SOURCES)
