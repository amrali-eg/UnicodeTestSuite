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

from generator.binary import classify_fixture, generate_binary_fixtures
from generator.categories import (
    FIXTURE_CATEGORIES,
    LONGFORM_CATEGORY,
    SHARED_CATEGORIES,
    category_by_name,
)
from generator.documents import Document, load_documents
from generator.equivalence import compatible_encodings
from generator.encoder import (
    CORE_UNICODE_SPECS,
    LEGACY_FAMILIES,
    EncodingSpec,
    can_encode,
    encode_with_bom,
    strip_bom,
)
from generator.filenames import assert_filename_contract, build_filename, sanitize_component
from generator.hashing import sha256_bytes
from generator.longform import legacy_encodings_for, load_long_form_documents
from generator.verifier import verify_binary_file, verify_text_file

DOC_FOLDER = "00_Documentation"
INVALID_FOLDER = "11_InvalidUnicode"
LINE_ENDING_FOLDER = "12_LineEndings"
BINARY_FOLDER = "13_Binary"
LARGE_FILE_FOLDER = "14_LargeFiles"
LONGFORM_FOLDER = "15_LongForm"

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
    LONGFORM_FOLDER,
)


@dataclass(frozen=True)
class GeneratedFile:
    """One row of metadata describing a single generated corpus file."""

    doc_id: str
    category_code: str          # "15", or "" for fixtures with no numbered category
    category: str               # plain name, e.g. "CJK" - never the "15-CJK" slug
    encoding_label: str
    bom: str
    also_valid_as: tuple[str, ...]  # other encodings that decode these bytes identically
    line_ending: str
    characters: int
    size_bytes: int
    sha256: str
    relative_path: str


def _category_folder_token(doc: Document) -> str:
    """Directory-name token for a document's category, e.g. '15-CJK'."""
    return f"{doc.category_code}-{doc.category_name}"


def _category_filename_tokens(doc: Document) -> list[str]:
    """Filename tokens for a document's category, e.g. ['06', 'CJK'].

    Always two tokens: every document (ASCII or shared) has a numeric
    category code, so the encoding field always lands at the same
    position when a filename is split on "_" - see filenames.py.
    """
    return [doc.category_code, doc.category_name]


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
    category_code: str,
    category_name: str,
    line_ending_label: str,
) -> GeneratedFile:
    # Every file written through this function is document-derived, so the
    # filename parsing contract applies without exception. Checked before
    # the write so a violation aborts generation rather than shipping.
    assert_filename_contract(relative_path.rsplit("/", 1)[-1], spec.label)

    data = encode_with_bom(text, spec)
    full_path = _full_path(root, relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)

    digest = sha256_bytes(data)
    verify_text_file(full_path, spec, text, digest, len(data))

    return GeneratedFile(
        doc_id=doc_id,
        category_code=category_code,
        category=category_name,
        encoding_label=spec.label,
        bom=spec.bom_label,
        also_valid_as=compatible_encodings(strip_bom(data, spec), spec.label, text),
        line_ending=line_ending_label,
        characters=len(text),
        size_bytes=len(data),
        sha256=digest,
        relative_path=relative_path,
    )


def _ascii_spec() -> EncodingSpec:
    for spec in CORE_UNICODE_SPECS:
        if spec.label == "us-ascii":
            return spec
    raise RuntimeError("us-ascii spec not found in CORE_UNICODE_SPECS")


def _core_unicode_specs_excluding_ascii() -> tuple[EncodingSpec, ...]:
    return tuple(spec for spec in CORE_UNICODE_SPECS if spec.label != "us-ascii")


def _generate_documentation_copies(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """Write each canonical document as plain UTF-8/LF text for reference."""
    results: list[GeneratedFile] = []
    spec = EncodingSpec("utf-8", "utf-8", b"", DOC_FOLDER, None)
    for doc in documents:
        tokens = _category_filename_tokens(doc)
        filename = build_filename(doc.doc_id, tokens, doc.title, "utf-8", "NoBOM", "LF")
        relative_path = _posix_path(DOC_FOLDER, filename)
        results.append(_write_and_verify_text(root, relative_path, doc.text, spec, doc.doc_id, doc.category_code, doc.category_name, "LF"))

    categories_text = "\n".join(sorted({_category_folder_token(d) for d in documents})) + "\n"
    results.append(_write_plain_reference(root, _posix_path(DOC_FOLDER, "Categories.txt"), categories_text))

    encoding_labels = sorted({s.label for s in CORE_UNICODE_SPECS}) + [
        f"{spec.label} ({family[0].root_folder})"
        for family in LEGACY_FAMILIES
        for spec in family
    ]
    results.append(_write_plain_reference(root, _posix_path(DOC_FOLDER, "Encodings.txt"), "\n".join(encoding_labels) + "\n"))

    index_lines = [f"{d.doc_id}\t{_category_folder_token(d)}\t{d.title}" for d in documents]
    results.append(_write_plain_reference(root, _posix_path(DOC_FOLDER, "SourceDocumentsIndex.txt"), "\n".join(index_lines) + "\n"))

    return results


def _write_plain_reference(root: Path, relative_path: str, text: str) -> GeneratedFile:
    """Write a UTF-8 reference file and return its manifest record.

    These files (Categories.txt, Encodings.txt, SourceDocumentsIndex.txt)
    describe the corpus rather than being samples drawn from it, so they
    carry DocumentID "N/A" and are exempt from the filename contract. In
    v2.0 they were written with no bookkeeping at all, which left them
    outside Manifest.csv and MasterHashes.sha256 - they could be edited
    without either verification path noticing.
    """
    data = text.encode("utf-8")
    full_path = _full_path(root, relative_path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(data)

    digest = sha256_bytes(data)
    verify_binary_file(full_path, digest, len(data))
    return GeneratedFile(
        doc_id="N/A",
        category_code="",
        category="Documentation",
        encoding_label="utf-8",
        bom="NoBOM",
        # These are pure ASCII in practice, so they are valid under every
        # ASCII-superset encoding just like any other corpus file. Hardcoding
        # an empty set made a detector answering us-ascii look wrong.
        also_valid_as=compatible_encodings(data, "utf-8", text),
        line_ending="LF",
        characters=len(text),
        size_bytes=len(data),
        sha256=digest,
        relative_path=relative_path,
    )


def _generate_ascii_folder(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """01_ASCII: ASCII-only categories, encoded with the ASCII codec."""
    spec = _ascii_spec()
    results: list[GeneratedFile] = []
    for doc in documents:
        if doc.group != "ASCII":
            continue
        for line_label, variant_text in _default_line_ending(doc.text):
            tokens = _category_filename_tokens(doc)
            filename = build_filename(doc.doc_id, tokens, doc.title, spec.label, None, line_label)
            category_folder = _category_folder_token(doc)
            relative_path = _posix_path(ASCII_ROOT_FOLDER, category_folder, filename)
            results.append(_write_and_verify_text(
                root, relative_path, variant_text, spec, doc.doc_id, doc.category_code, doc.category_name, line_label,
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
                    root, relative_path, variant_text, spec, doc.doc_id, doc.category_code, doc.category_name, line_label,
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
                    filename = build_filename(doc.doc_id, tokens, doc.title, spec.label, None, line_label)
                    category_folder = _category_folder_token(doc)
                    relative_path = _posix_path(spec.root_folder, spec.family_subfolder, category_folder, filename)
                    results.append(_write_and_verify_text(
                        root, relative_path, variant_text, spec, doc.doc_id, doc.category_code, doc.category_name, line_label,
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
        label, bom, also = classify_fixture(data)
        results.append(GeneratedFile(
            doc_id="N/A", category_code="", category="InvalidUnicode",
            encoding_label=label, bom=bom, also_valid_as=also,
            line_ending="N/A", characters=0,
            size_bytes=len(data), sha256=digest, relative_path=relative_path,
        ))
    return results


def _generate_line_ending_showcase(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """12_LineEndings: curated CR/LF/CRLF/None showcase across many categories."""
    by_id = {d.doc_id: d for d in documents}
    # One representative document per ASCII category. (v2.0 described this
    # as a "mix of ASCII and shared groups"; every ID here is at or below
    # DOC000027, so all nine are in fact ASCII-group documents.)
    showcase_ids = [
        "DOC000001", "DOC000004", "DOC000007", "DOC000010", "DOC000013",
        "DOC000016", "DOC000019", "DOC000022", "DOC000025",
    ]
    spec = EncodingSpec("utf-8", "utf-8", b"", LINE_ENDING_FOLDER, None)
    results: list[GeneratedFile] = []
    for doc_id in showcase_ids:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        for line_label, variant_text in _line_ending_variants(doc.text):
            tokens = _category_filename_tokens(doc)
            filename = build_filename(doc.doc_id, tokens, doc.title, "utf-8", "NoBOM", line_label)
            relative_path = _posix_path(LINE_ENDING_FOLDER, filename)
            results.append(_write_and_verify_text(
                root, relative_path, variant_text, spec, doc.doc_id, doc.category_code, doc.category_name, line_label,
            ))

    # Two explicit edge cases that are not derived from any canonical
    # document. They still carry reserved DOC9xxxxx DocumentIDs and the
    # 20-LineEndingEdge fixture category so their filenames satisfy the
    # same parsing contract as every other .txt in the corpus - in v2.0
    # these were hand-built strings with only four "_" tokens, which put
    # the encoding out of reach at index 4 and silently broke consumers.
    edge_category = category_by_name(FIXTURE_CATEGORIES, "LineEndingEdge")
    edge_tokens = [edge_category.code, edge_category.name]
    edge_cases = (
        (
            "DOC900001",
            "NoNewlineAtAll",
            "None",
            "Single line document with absolutely no newline character at all.",
        ),
        (
            "DOC900002",
            "MixedLineEndings",
            "Mixed",
            "line one\r\nline two\nline three\rline four\r\n",
        ),
    )
    for doc_id, title, line_label, text in edge_cases:
        filename = build_filename(doc_id, edge_tokens, title, spec.label, spec.bom_label, line_label)
        relative_path = _posix_path(LINE_ENDING_FOLDER, filename)
        results.append(_write_and_verify_text(
            root, relative_path, text, spec, doc_id, edge_category.code, edge_category.name, line_label,
        ))

    return results


# Documents used for the line-ending matrix: one Latin, one Cyrillic,
# one CJK, all from the shared group so the content is not pure ASCII.
# Fixed ids, chosen for script spread and for encoding in a useful number
# of legacy code pages.
_MATRIX_DOC_IDS: tuple[str, ...] = (
    "DOC000029",  # Latin / French
    "DOC000044",  # Cyrillic / Russian
    "DOC000066",  # CJK / Japanese
)

# Legacy codecs offered to the matrix. Each document is emitted only in
# the ones that can represent it, via the usual can_encode check.
_MATRIX_LEGACY_LABELS: frozenset[str] = frozenset({
    "windows-1252", "iso-8859-1", "iso-8859-15",
    "windows-1251", "koi8-r", "iso-8859-5",
    "shift_jis", "euc-jp", "gb18030",
})


def _generate_line_ending_matrix(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """12_LineEndings/Matrix: CR/LF/CRLF across encodings, not just UTF-8.

    v2.0 varied the line terminator only within UTF-8, and only over nine
    pure-ASCII documents, so 1,130 of its 1,212 files were LF and the
    corpus contained no CRLF file in UTF-16, UTF-32, or any legacy code
    page at all. That left the single most common byte pattern in real
    Windows text - 0D 00 0A 00, CRLF in UTF-16LE - unrepresented, along
    with CRLF in windows-1252, which is arguably the most common legacy
    text file in existence. Several detectors use NUL placement and
    line-terminator regularity as UTF-16 evidence, so the gap sat exactly
    where the corpus was meant to be strongest.

    Emitting the full matrix corpus-wide would have tripled the file
    count for little extra signal, so this is a deliberate slice: three
    documents spanning Latin, Cyrillic and CJK, in every core Unicode
    encoding plus the legacy codecs that can represent them, each in all
    three terminators. That yields directly comparable triples - same
    document, same encoding, terminator the only variable.
    """
    by_id = {d.doc_id: d for d in documents}
    core_specs = [
        spec for spec in CORE_UNICODE_SPECS
        if spec.label != "us-ascii" and not spec.label.startswith("utf-32")
    ]
    legacy_specs = [
        spec for family in LEGACY_FAMILIES for spec in family
        if spec.label in _MATRIX_LEGACY_LABELS
    ]

    results: list[GeneratedFile] = []
    for doc_id in _MATRIX_DOC_IDS:
        doc = by_id.get(doc_id)
        if doc is None:
            continue
        for spec in core_specs + legacy_specs:
            if not can_encode(doc.text, spec.codec):
                continue
            bom_label = spec.bom_label if spec in core_specs else None
            for line_label, variant_text in _line_ending_variants(doc.text):
                filename = build_filename(
                    doc.doc_id,
                    _category_filename_tokens(doc),
                    doc.title,
                    spec.label,
                    bom_label,
                    line_label,
                )
                relative_path = _posix_path(
                    LINE_ENDING_FOLDER, "Matrix",
                    sanitize_component(spec.label), filename,
                )
                results.append(_write_and_verify_text(
                    root, relative_path, variant_text, spec, doc.doc_id,
                    doc.category_code, doc.category_name, line_label,
                ))
    return results


def _generate_large_files(root: Path, documents: list[Document]) -> list[GeneratedFile]:
    """14_LargeFiles: amplify a few representative documents into multi-MB files."""
    by_id = {d.doc_id: d for d in documents}
    plan = [
        ("DOC000064", "utf-8", "utf-8", b"", 3),        # a CJK doc
        ("DOC000031", "utf-16LE", "utf-16-le", b"\xff\xfe", 2),  # a Latin doc
        ("DOC000001", "utf-8", "utf-8", b"", 4),         # an ASCII/Programming doc
        ("DOC000094", "utf-8", "utf-8", b"", 3),         # a UnicodeMisc doc
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
            root, relative_path, large_text, spec, doc.doc_id, doc.category_code, doc.category_name, "LF",
        ))
    return results


def _generate_long_form(root: Path, project_root: Path) -> list[GeneratedFile]:
    """15_LongForm: multi-kilobyte natural-language text per encoding.

    Every other text folder holds short samples - a line or two - which
    exercise codec round-trips but are far below what a statistical
    detector needs to classify. These documents are several kilobytes
    each and are emitted into UTF-8 plus every legacy encoding capable of
    representing them, giving the corpus samples where byte-frequency and
    bigram models can actually converge.

    Each document is skipped for any encoding that cannot represent it,
    using the same can_encode check the rest of the corpus uses, so a
    script/code-page mismatch produces no file rather than mangled text.
    """
    documents = load_long_form_documents(project_root / "data" / "udhr")
    if not documents:
        return []

    tokens = [LONGFORM_CATEGORY.code, LONGFORM_CATEGORY.name]

    utf8_specs = (
        EncodingSpec("utf-8", "utf-8", b"", LONGFORM_FOLDER, None),
        EncodingSpec("utf-8", "utf-8", b"\xef\xbb\xbf", LONGFORM_FOLDER, None),
    )
    legacy_by_label = {
        spec.label: spec
        for family in LEGACY_FAMILIES
        for spec in family
    }

    results: list[GeneratedFile] = []
    for doc in documents:
        for spec in utf8_specs:
            filename = build_filename(
                doc.doc_id, tokens, doc.title, spec.label, spec.bom_label, "LF")
            relative_path = _posix_path(LONGFORM_FOLDER, spec.label, filename)
            results.append(_write_and_verify_text(
                root, relative_path, doc.text, spec, doc.doc_id, LONGFORM_CATEGORY.code, LONGFORM_CATEGORY.name, "LF",
            ))

        # Only the encodings that historically carried this language, not
        # every encoding capable of representing the bytes. See
        # LONGFORM_ENCODINGS for why the difference matters.
        for label in legacy_encodings_for(doc.title):
            spec = legacy_by_label.get(label)
            if spec is None or not can_encode(doc.text, spec.codec):
                continue
            filename = build_filename(
                doc.doc_id, tokens, doc.title, spec.label, None, "LF")
            relative_path = _posix_path(LONGFORM_FOLDER, sanitize_component(spec.label), filename)
            results.append(_write_and_verify_text(
                root, relative_path, doc.text, spec, doc.doc_id, LONGFORM_CATEGORY.code, LONGFORM_CATEGORY.name, "LF",
            ))
    return results


def generate_corpus(
    project_root: Path,
    output_root: Path | None = None,
) -> tuple[list[GeneratedFile], Path, list[tuple[str, str]]]:
    """Run the pipeline; return (records, output_root, source_overrides).

    The output directory (UnicodeTestSuite/) is deleted and recreated
    from scratch on every run so repeated runs never accumulate stale
    files from a previous generator version.
    """
    if output_root is None:
        output_root = project_root / "UnicodeTestSuite"
    if output_root.exists():
        shutil.rmtree(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    for folder in ALL_FOLDERS:
        (output_root / folder).mkdir(parents=True, exist_ok=True)

    documents, overrides = load_documents(project_root / "Source")

    records: list[GeneratedFile] = []
    records += _generate_documentation_copies(output_root, documents)
    records += _generate_ascii_folder(output_root, documents)
    records += _generate_core_unicode_folders(output_root, documents)
    records += _generate_legacy_families(output_root, documents)
    records += _generate_invalid_unicode_files(output_root)
    records += _generate_line_ending_showcase(output_root, documents)
    records += _generate_line_ending_matrix(output_root, documents)
    records += generate_binary_fixtures(output_root, BINARY_FOLDER, verify_binary_file, sha256_bytes, GeneratedFile)
    records += _generate_large_files(output_root, documents)
    records += _generate_long_form(output_root, project_root)

    return records, output_root, overrides
