"""Corpus generation orchestrator.

Owns the full pipeline:

- 00_Documentation: flat UTF-8/LF reference copy of every document.
- 01_ASCII: the nine ASCII-only categories, ASCII encoding, one file
  per document (folder: 01_ASCII/<Category>/).
- 02_UTF8 .. 06_UTF32BE: the ten shared categories, encoded into each
  of the five core Unicode Transformation Formats, BOM and NoBOM
  (folder: 0N_UTFxx/<code>-<Name>/).
- 07_WindowsCodePages, 08_ISO8859, 09_EastAsian, 10_Cyrillic: the
  shared categories re-encoded into every legacy codec capable of
  representing them (folder: 0N_Family/<CodecLabel>/<code>-<Name>/).
- 11_InvalidUnicode: fixed malformed byte-sequence fixtures.
- 12_LineEndings: curated CR/LF/CRLF/None showcase.
- 13_Binary: synthetic binary-format-signature stub fixtures.
- 14_LargeFiles: a handful of multi-megabyte amplified documents.

Generation aborts on the first integrity failure anywhere.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from generator.binary import generate_binary_fixtures
from generator.categories import SHARED_CATEGORIES
from generator.documents import Document, load_documents
from generator.encoder import (
    CORE_UNICODE_SPECS,
    LEGACY_FAMILIES,
    EncodingSpec,
    can_encode,
    encode_with_bom,
)
from generator.filenames import build_filename, sanitize_component
from generator.hashing import sha256_bytes
from generator.verifier import verify_binary_file, verify_text_file

DOC_FOLDER = "00_Documentation"
INVALID_FOLDER = "11_InvalidUnicode"
LINE_ENDING_FOLDER = "12_LineEndings"
BINARY_FOLDER = "13_Binary"
LARGE_FILE_FOLDER = "14_LargeFiles"

ASCII_ROOT_FOLDER = "01_ASCII"

# All top-level folders, in the fixed display/creation order.
ALL_FOLDERS: tuple[str, ...] = (
    DOC_FOLDER,
    ASCII_ROOT_FOLDER,
    "02_UTF8",
    "03_UTF16LE",
    "04_UTF16BE",
    "05_UTF32LE",
    "06_UTF32BE",
    "07_WindowsCodePages",
    "08_ISO8859",
    "09_EastAsian",
    "10_Cyrillic",
    INVALID_FOLDER,
    LINE_ENDING_FOLDER,
    BINARY_FOLDER,
    LARGE_FILE_FOLDER,
)


@dataclass(frozen=True)
class GeneratedFile:
    """One row of metadata describing a single generated corpus file."""

    doc_id: str
    category: str
    encoding_label: str
    bom: str
    line_ending: str
    characters: int
    size_bytes: int
    sha256: str
    relative_path: str


def _category_folder_token(doc: Document) -> str:
    """Directory-name token for a document's category, e.g. '06-CJK'."""
    if doc.category_code:
        return f"{doc.category_code}-{doc.category_name}"
    return doc.category_name


def _category_filename_tokens(doc: Document) -> list[str]:
    """Filename tokens for a document's category, e.g. ['06', 'CJK']."""
    if doc.category_code:
        return [doc.category_code, doc.category_name]
    return [doc.category_name]


def _line_ending_variants(text: str) -> list[tuple[str, str]]:
    """Return (label, text) pairs for every applicable line-ending variant.

    Text with no '\\n' at all gets a single "None" variant. Everything
    else gets LF/CRLF/CR variants. Used only by the dedicated
    12_LineEndings showcase - every other folder uses a single default
    LF file per document to keep the corpus at its intended size.
    """
    if "\n" not in text:
        return [("None", text)]
    return [
        ("LF", text),
        ("CRLF", text.replace("\n", "\r\n")),
        ("CR", text.replace("\n", "\r")),
    ]


def _posix_path(*parts: str) -> str:
    """Join path parts using '/' regardless of host OS, for manifest stability."""
    return "/".join(parts)


def _full_path(root: Path, relative_path: str) -> Path:
    """Resolve a '/'-joined relative path against root using the host OS separator."""
    return root.joinpath(*relative_path.split("/"))


def _write_and_verify_text(
    root: Path,
    relative_path: str,
    text: str,
    spec: EncodingSpec,
    doc_id: str,
    category_display: str,
    line_ending_label: str,
) -> GeneratedFile:
    data = encode_with_bom(text, spec)
    full_path = _full_path(root, relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)

    digest = sha256_bytes(data)
    verify_text_file(full_path, spec, text, digest, len(data))

    return GeneratedFile(
        doc_id=doc_id,
        category=category_display,
        encoding_label=spec.label,
        bom=spec.bom_label,
        line_ending=line_ending_label,
        characters=len(text),
        size_bytes=len(data),
        sha256=digest,
        relative_path=relative_path,
    )


def _ascii_spec() -> EncodingSpec:
    for spec in CORE_UNICODE_SPECS:
        if spec.label == "ASCII":
            return spec
    raise RuntimeError("ASCII spec not found in CORE_UNICODE_SPECS")


def _core_unicode_specs_excluding_ascii() -> tuple[EncodingSpec, ...]:
    return tuple(spec for spec in CORE_UNICODE_SPECS if spec.label != "ASCII")


def _generate_documentation_copies(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """Write each canonical document as plain UTF-8/LF text for reference."""
    results: list[GeneratedFile] = []
    spec = EncodingSpec("UTF8", "utf-8", b"", DOC_FOLDER, None)
    for doc in documents:
        tokens = _category_filename_tokens(doc)
        filename = build_filename(doc.doc_id, tokens, doc.title, "UTF8", "NoBOM", "LF")
        relative_path = _posix_path(DOC_FOLDER, filename)
        category_display = _category_folder_token(doc)
        results.append(_write_and_verify_text(root, relative_path, doc.text, spec, doc.doc_id, category_display, "LF"))

    categories_text = "\n".join(sorted({_category_folder_token(d) for d in documents})) + "\n"
    _write_plain_reference(root, _posix_path(DOC_FOLDER, "Categories.txt"), categories_text)

    encoding_labels = sorted({s.label for s in CORE_UNICODE_SPECS}) + [
        f"{spec.label} ({family[0].root_folder})"
        for family in LEGACY_FAMILIES
        for spec in family
    ]
    _write_plain_reference(root, _posix_path(DOC_FOLDER, "Encodings.txt"), "\n".join(encoding_labels) + "\n")

    index_lines = [f"{d.doc_id}\t{_category_folder_token(d)}\t{d.title}" for d in documents]
    _write_plain_reference(root, _posix_path(DOC_FOLDER, "SourceDocumentsIndex.txt"), "\n".join(index_lines) + "\n")

    return results


def _write_plain_reference(root: Path, relative_path: str, text: str) -> None:
    """Write a simple UTF-8 reference file with no verification bookkeeping."""
    full_path = _full_path(root, relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(text, encoding="utf-8", newline="\n")


def _generate_ascii_folder(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """01_ASCII: ASCII-only categories, encoded with the ASCII codec."""
    spec = _ascii_spec()
    results: list[GeneratedFile] = []
    for doc in documents:
        if doc.group != "ASCII":
            continue
        for line_label, variant_text in _default_line_ending(doc.text):
            filename = build_filename(doc.doc_id, [doc.category_name], doc.title, spec.label, spec.bom_label, line_label)
            relative_path = _posix_path(ASCII_ROOT_FOLDER, doc.category_name, filename)
            results.append(_write_and_verify_text(
                root, relative_path, variant_text, spec, doc.doc_id, doc.category_name, line_label,
            ))
    return results


def _default_line_ending(text: str) -> list[tuple[str, str]]:
    """The single default line-ending variant used outside 12_LineEndings."""
    if "\n" not in text:
        return [("None", text)]
    return [("LF", text)]


def _generate_core_unicode_folders(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """02_UTF8 .. 06_UTF32BE: shared categories in every core Unicode encoding."""
    results: list[GeneratedFile] = []
    shared_docs = [d for d in documents if d.group == "Shared"]
    for spec in _core_unicode_specs_excluding_ascii():
        for doc in shared_docs:
            if not can_encode(doc.text, spec.codec):
                continue
            for line_label, variant_text in _default_line_ending(doc.text):
                tokens = _category_filename_tokens(doc)
                filename = build_filename(doc.doc_id, tokens, doc.title, spec.label, spec.bom_label, line_label)
                category_folder = _category_folder_token(doc)
                relative_path = _posix_path(spec.root_folder, category_folder, filename)
                results.append(_write_and_verify_text(
                    root, relative_path, variant_text, spec, doc.doc_id, category_folder, line_label,
                ))
    return results


def _generate_legacy_families(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """07_WindowsCodePages .. 10_Cyrillic: shared categories where encodable."""
    results: list[GeneratedFile] = []
    shared_docs = [d for d in documents if d.group == "Shared"]
    for family in LEGACY_FAMILIES:
        for spec in family:
            for doc in shared_docs:
                if not can_encode(doc.text, spec.codec):
                    continue
                for line_label, variant_text in _default_line_ending(doc.text):
                    tokens = _category_filename_tokens(doc)
                    filename = build_filename(doc.doc_id, tokens, doc.title, spec.label, spec.bom_label, line_label)
                    category_folder = _category_folder_token(doc)
                    relative_path = _posix_path(spec.root_folder, spec.family_subfolder, category_folder, filename)
                    results.append(_write_and_verify_text(
                        root, relative_path, variant_text, spec, doc.doc_id, category_folder, line_label,
                    ))
    return results


def _generate_invalid_unicode_files(root: Path) -> list[GeneratedFile]:
    """11_InvalidUnicode: fixed malformed byte sequences, not derived from any document."""
    fixtures: dict[str, bytes] = {
        "LoneContinuationByte.bin": b"Valid ASCII prefix.\n\x80\nTrailing ASCII.\n",
        "TruncatedTwoByteSequence.bin": b"Prefix \xc2 truncated.\n",
        "OverlongEncodingOfSlash.bin": b"Overlong: \xc0\xaf end.\n",
        "OverlongEncodingOfNul.bin": b"Overlong NUL: \xe0\x80\x80 end.\n",
        "EncodedSurrogateHalf.bin": b"Surrogate: \xed\xa0\x80 end.\n",
        "CodepointBeyondMax.bin": b"Beyond U+10FFFF: \xf4\x90\x80\x80 end.\n",
        "InvalidLeadByteFE.bin": b"Invalid lead byte: \xfe end.\n",
        "InvalidLeadByteFF.bin": b"Invalid lead byte: \xff end.\n",
        "BadContinuationByte.bin": b"Bad continuation: \xe2\x28\xa1 end.\n",
        "UnpairedHighSurrogateUtf16.bin": "before".encode("utf-16-le") + b"\x00\xd8" + "after".encode("utf-16-le"),
        "TruncatedUtf32.bin": "test".encode("utf-32-le")[:-1],
        "MixedBomConfusion.bin": b"\xef\xbb\xbf\xff\xfe" + "confusing".encode("utf-8"),
    }
    results: list[GeneratedFile] = []
    for filename, data in fixtures.items():
        relative_path = _posix_path(INVALID_FOLDER, filename)
        full_path = _full_path(root, relative_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_bytes(data)
        digest = sha256_bytes(data)
        verify_binary_file(full_path, digest, len(data))
        results.append(GeneratedFile(
            doc_id="N/A", category="InvalidUnicode", encoding_label="Binary",
            bom="N/A", line_ending="N/A", characters=0,
            size_bytes=len(data), sha256=digest, relative_path=relative_path,
        ))
    return results


def _generate_line_ending_showcase(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """12_LineEndings: curated CR/LF/CRLF/None showcase across many categories."""
    by_id = {d.doc_id: d for d in documents}
    # One representative document per category (mix of ASCII and shared groups).
    showcase_ids = [
        "DOC000001", "DOC000004", "DOC000007", "DOC000010", "DOC000013", "DOC000016", "DOC000019", "DOC000022", "DOC000025",
    ]
    spec = EncodingSpec("UTF8", "utf-8", b"", LINE_ENDING_FOLDER, None)
    results: list[GeneratedFile] = []
    for doc_id in showcase_ids:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        for line_label, variant_text in _line_ending_variants(doc.text):
            tokens = _category_filename_tokens(doc)
            filename = build_filename(doc.doc_id, tokens, doc.title, "UTF8", "NoBOM", line_label)
            relative_path = _posix_path(LINE_ENDING_FOLDER, filename)
            results.append(_write_and_verify_text(
                root, relative_path, variant_text, spec, doc.doc_id, _category_folder_token(doc), line_label,
            ))

    # Explicit "None" edge case: genuinely zero newline characters at all.
    no_newline_text = "Single line document with absolutely no newline character at all."
    no_newline_filename = "NoNewlineAtAll_UTF8_NoBOM_None.txt"
    no_newline_path = _posix_path(LINE_ENDING_FOLDER, no_newline_filename)
    data = encode_with_bom(no_newline_text, spec)
    full_path = _full_path(root, no_newline_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    digest = sha256_bytes(data)
    verify_text_file(full_path, spec, no_newline_text, digest, len(data))
    results.append(GeneratedFile(
        doc_id="N/A", category="LineEndings", encoding_label="UTF8", bom="NoBOM",
        line_ending="None", characters=len(no_newline_text), size_bytes=len(data),
        sha256=digest, relative_path=no_newline_path,
    ))

    # Explicit "mixed within one file" edge case.
    mixed_text = "line one\r\nline two\nline three\rline four\r\n"
    mixed_filename = "MixedLineEndingsWithinOneFile_UTF8_NoBOM_Mixed.txt"
    mixed_path = _posix_path(LINE_ENDING_FOLDER, mixed_filename)
    data = encode_with_bom(mixed_text, spec)
    full_path = _full_path(root, mixed_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)
    digest = sha256_bytes(data)
    verify_text_file(full_path, spec, mixed_text, digest, len(data))
    results.append(GeneratedFile(
        doc_id="N/A", category="LineEndings", encoding_label="UTF8", bom="NoBOM",
        line_ending="Mixed", characters=len(mixed_text), size_bytes=len(data),
        sha256=digest, relative_path=mixed_path,
    ))
    return results


def _generate_large_files(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """14_LargeFiles: amplify a few representative documents into multi-MB files."""
    by_id = {d.doc_id: d for d in documents}
    plan = [
        ("DOC000064", "UTF8", "utf-8", b"", 3),        # a CJK doc
        ("DOC000031", "UTF16LE", "utf-16-le", b"\xff\xfe", 2),  # a Latin doc
        ("DOC000001", "UTF8", "utf-8", b"", 4),         # an ASCII/Programming doc
        ("DOC000094", "UTF8", "utf-8", b"", 3),         # a UnicodeMisc doc
    ]
    results: list[GeneratedFile] = []
    for doc_id, enc_label, codec, bom, target_mb in plan:
        doc = by_id[doc_id]
        unit = doc.text if doc.text.endswith("\n") else doc.text + "\n"
        target_bytes = target_mb * 1024 * 1024
        repeats = max(1, target_bytes // max(1, len(unit.encode(codec))))
        large_text = unit * repeats
        spec = EncodingSpec(enc_label, codec, bom, LARGE_FILE_FOLDER, None)
        tokens = _category_filename_tokens(doc)
        filename = build_filename(doc.doc_id, tokens, f"{doc.title}x{repeats}", enc_label, spec.bom_label, "LF")
        relative_path = _posix_path(LARGE_FILE_FOLDER, filename)
        results.append(_write_and_verify_text(
            root, relative_path, large_text, spec, doc.doc_id, _category_folder_token(doc), "LF",
        ))
    return results


def generate_corpus(project_root: Path) -> tuple[list[GeneratedFile], Path]:
    """Run the full generation pipeline and return (records, output_root).

    The output directory (UnicodeTestSuite/) is deleted and recreated
    from scratch on every run so repeated runs never accumulate stale
    files from a previous generator version.
    """
    output_root = project_root / "UnicodeTestSuite"
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for folder in ALL_FOLDERS:
        (output_root / folder).mkdir(parents=True, exist_ok=True)

    documents = load_documents(project_root / "Source")

    records: list[GeneratedFile] = []
    records += _generate_documentation_copies(output_root, documents)
    records += _generate_ascii_folder(output_root, documents)
    records += _generate_core_unicode_folders(output_root, documents)
    records += _generate_legacy_families(output_root, documents)
    records += _generate_invalid_unicode_files(output_root)
    records += _generate_line_ending_showcase(output_root, documents)
    records += generate_binary_fixtures(output_root, BINARY_FOLDER, verify_binary_file, sha256_bytes, GeneratedFile)
    records += _generate_large_files(output_root, documents)

    return records, output_root
