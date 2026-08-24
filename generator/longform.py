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
