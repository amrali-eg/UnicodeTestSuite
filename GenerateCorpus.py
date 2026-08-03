#!/usr/bin/env python3
"""Unicode Test Suite Generator (UTS) - entry point.

Run this script directly:

    python GenerateCorpus.py

or double-click it (Windows file associations permitting). With no
arguments it behaves exactly like `python GenerateCorpus.py generate`:
it deletes and rebuilds the UnicodeTestSuite/ output directory from
scratch, next to this script, verifying every file as it goes. No
configuration file is required for this, the common case.

Two optional subcommands are available for anyone who wants them:

    python GenerateCorpus.py generate   # same as no arguments
    python GenerateCorpus.py verify     # re-check an existing corpus

`verify` re-opens every file listed in an existing UnicodeTestSuite/
Manifest.csv, re-checks its size and SHA-256 against disk, and
re-decodes it under its declared encoding, WITHOUT regenerating
anything. Useful after copying or archiving the corpus.
"""

from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

# Make sure the `generator` package is importable when this script is
# run from any working directory (e.g. double-clicked).
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generator import GENERATOR_VERSION
from generator.certificate import write_certificate
from generator.corpus import generate_corpus
from generator.documents import document_count
from generator.manifest import (
    read_manifest_csv,
    write_html_index,
    write_manifest_csv,
    write_manifest_sqlite,
    write_master_hashes,
)
from generator.statistics import write_statistics
from generator.verifier import CorpusIntegrityError, verify_archived_file

README_TEMPLATE = """\
# UnicodeTestSuite

A deterministic Unicode / legacy-encoding regression corpus, generated
by Unicode Test Suite Generator (UTS) version {version}.

## What this is

{doc_count} canonical source documents: nine pure-ASCII categories plus
ten "shared" categories (Latin, Cyrillic, RTL, Indic, SoutheastAsian,
CJK, SupplementaryPlanes, Mathematics, Emoji, UnicodeMisc) forming one
identical logical corpus, re-encoded into every Unicode and legacy
encoding capable of representing it. Every single text file was
reopened after being written, decoded with its declared encoding, and
compared character-for-character against its source document before
this corpus was considered valid. See CorpusCertificate.txt for this
run's summary.

Script-content note: documents for scripts beyond common European
languages use representative code-point samples from the relevant
Unicode block rather than hand-composed sentences, which removes any
risk of transcription error and guarantees genuine block coverage -
see generator/documents.py for the full rationale.

## Layout

- `00_Documentation/` - every document in plain UTF-8/LF, plus
  Categories.txt, Encodings.txt, and SourceDocumentsIndex.txt.
- `01_ASCII/<Category>/` - the nine ASCII-only categories (Programming,
  JSON, XML, HTML, Markdown, CSV, Logs, Config, RandomASCII).
- `02_UTF8/` .. `06_UTF32BE/<code>-<Name>/` - the ten shared categories,
  BOM and NoBOM, in each of the five core Unicode Transformation Formats.
- `07_WindowsCodePages/<Codepage>/<code>-<Name>/` - Windows-1250..1258.
- `08_ISO8859/<Part>/<code>-<Name>/` - ISO-8859 parts 1-16 (part 12 excluded).
- `09_EastAsian/<Codec>/<code>-<Name>/` - Shift-JIS, CP932, EUC-JP,
  ISO-2022-JP, GB2312, GBK, GB18030, Big5, Big5-HKSCS, HZ, EUC-KR,
  CP949, ISO-2022-KR, Windows-874, TIS-620.
- `10_Cyrillic/<Codec>/<code>-<Name>/` - KOI8-R, KOI8-U.
- `11_InvalidUnicode/` - deliberately malformed byte sequences, not
  derived from any document, for decoder-failure testing.
- `12_LineEndings/` - a curated CR/LF/CRLF/None showcase, plus one file
  with mixed line endings within a single document.
- `13_Binary/<Category>/` - synthetic binary-format-signature stubs
  (EXE, DLL, PNG, JPG, GIF, ZIP, PDF, Office, Audio, Video, SQLite,
  Random) plus general binary edge fixtures.
- `14_LargeFiles/` - a handful of multi-megabyte amplified documents.

Every other folder (01-10) uses a single default LF-terminated file per
document; the full CR/LF/CRLF/None line-ending matrix lives only in
`12_LineEndings/`, by design, to keep the corpus at its intended size.

## Filenames

Every filename fully describes its own content, e.g.:

    DOC000066_06_CJK_Japanese_UTF16LE_BOM_LF.txt

`DocumentID_[Code_]CategoryName_Title_Encoding_BOM_LineEnding.txt`

## Determinism

Re-running `python GenerateCorpus.py` (or `... generate`) with an
unchanged `generator/` package and an unchanged `Source/` directory
reproduces byte-identical corpus files, `Manifest.csv`,
`Manifest.sqlite`, and `MasterHashes.sha256` - every hash in this run's
manifest will match the next run's. The only files that intentionally
differ between runs are `Statistics.txt` and `CorpusCertificate.txt`,
since both record this run's wall-clock timestamp and duration.

## Verifying integrity later

Two ways to re-check an already-generated corpus without regenerating it:

    python GenerateCorpus.py verify

or, on Linux/macOS, using the standard `sha256sum` format directly:

    cd UnicodeTestSuite && sha256sum -c MasterHashes.sha256

## Source/ overrides (optional)

If a file named `Source/<DOC_ID>.txt` exists next to
GenerateCorpus.py (e.g. `Source/DOC000001.txt`), its UTF-8 content
replaces that document's built-in text before generation. Entirely
optional; an empty `Source/` directory is the normal, expected state.
"""


def _run_generate() -> int:
    print(f"Unicode Test Suite Generator (UTS) v{GENERATOR_VERSION}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Canonical source documents: {document_count()}")
    print("Generating corpus...")

    started = time.monotonic()
    try:
        records, output_root = generate_corpus(PROJECT_ROOT)
    except CorpusIntegrityError as exc:
        print("\nFATAL: corpus integrity check failed. Generation aborted.")
        print(f"Reason: {exc}")
        return 1
    except Exception:
        print("\nFATAL: unexpected error during generation. Generation aborted.")
        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - started
    print(f"Generated and verified {len(records):,} files in {elapsed:.2f} seconds.")

    print("Writing Manifest.csv ...")
    write_manifest_csv(records, output_root / "Manifest.csv")

    print("Writing Manifest.sqlite ...")
    write_manifest_sqlite(records, output_root / "Manifest.sqlite")

    print("Writing MasterHashes.sha256 ...")
    master_hashes_path = output_root / "MasterHashes.sha256"
    write_master_hashes(records, master_hashes_path)

    print("Writing Statistics.txt ...")
    write_statistics(records, elapsed, output_root / "Statistics.txt")

    print("Writing CorpusCertificate.txt ...")
    write_certificate(records, elapsed, master_hashes_path, output_root / "CorpusCertificate.txt")

    print("Writing Index.html ...")
    write_html_index(records, output_root / "Index.html")

    print("Writing README.md ...")
    readme_text = README_TEMPLATE.format(version=GENERATOR_VERSION, doc_count=document_count())
    (output_root / "README.md").write_text(readme_text, encoding="utf-8", newline="\n")

    print("\nDone.")
    print(f"Corpus written to: {output_root}")
    return 0


def _run_verify() -> int:
    output_root = PROJECT_ROOT / "UnicodeTestSuite"
    manifest_path = output_root / "Manifest.csv"

    print(f"Unicode Test Suite Generator (UTS) v{GENERATOR_VERSION} - verify mode")
    print(f"Corpus directory: {output_root}")

    if not manifest_path.is_file():
        print(f"\nFATAL: {manifest_path} not found. Run 'generate' first.")
        return 1

    rows = read_manifest_csv(manifest_path)
    print(f"Re-checking {len(rows):,} files listed in Manifest.csv ...")

    started = time.monotonic()
    checked = 0
    for row in rows:
        full_path = output_root.joinpath(*row["RelativePath"].split("/"))
        try:
            verify_archived_file(
                full_path,
                row["Encoding"],
                row["BOM"],
                int(row["Bytes"]),
                row["SHA256"],
            )
        except CorpusIntegrityError as exc:
            print(f"\nFATAL: verification failed at file {checked + 1:,}/{len(rows):,}.")
            print(f"Reason: {exc}")
            return 1
        checked += 1

    elapsed = time.monotonic() - started
    print(f"All {checked:,} files verified OK in {elapsed:.2f} seconds.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="GenerateCorpus.py",
        description="Unicode Test Suite Generator (UTS): build or verify the corpus.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="generate",
        choices=("generate", "verify"),
        help="'generate' (default) rebuilds UnicodeTestSuite/ from scratch; "
             "'verify' re-checks an existing UnicodeTestSuite/ without rebuilding.",
    )
    args = parser.parse_args()

    if args.command == "verify":
        return _run_verify()
    return _run_generate()


if __name__ == "__main__":
    exit_code = main()
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass
    sys.exit(exit_code)
