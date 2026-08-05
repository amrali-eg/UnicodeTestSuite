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
- `01_ASCII/<code>-<Name>/` - the nine ASCII-only categories (codes
  01-09: Programming, JSON, XML, HTML, Markdown, CSV, Logs, Config,
  RandomASCII).
- `02_UTF8/` .. `06_UTF32BE/<code>-<Name>/` - the ten shared categories
  (codes 10-19), BOM and NoBOM, in each of the five core Unicode
  Transformation Formats.
- `07_WindowsCodePages/<Codepage>/<code>-<Name>/` - windows-1250..1258.
- `08_ISO8859/<Part>/<code>-<Name>/` - iso-8859-1, -2, -3, -4, -5, -6,
  -7, -8, -9, -13, -15 (11 parts; see "Encoding names and .NET" below
  for why parts 10, 11, 14, and 16 aren't included).
- `09_EastAsian/<Codec>/<code>-<Name>/` - shift_jis, euc-jp, gb2312,
  gb18030, big5, euc-kr, iso-2022-kr (7 codecs).
- `10_Cyrillic/<Codec>/<code>-<Name>/` - koi8-r, koi8-u.
- `11_InvalidUnicode/` - deliberately malformed byte sequences, not
  derived from any document, for decoder-failure testing.
- `12_LineEndings/` - a curated CR/LF/CRLF/None showcase, plus one file
  with mixed line endings within a single document.
- `13_Binary/<Category>/` - synthetic binary-format-signature stubs
  (EXE, DLL, PNG, JPG, GIF, ZIP, PDF, Office, Audio, Video, SQLite,
  Random) plus general binary edge fixtures.
- `14_LargeFiles/` - a handful of multi-megabyte amplified documents.

Every category - ASCII or shared - has a numeric code, and codes
follow tree order: the nine ASCII-only categories (used only in
01_ASCII, the first root folder) get codes 01-09, and the ten shared
categories (used starting from 02_UTF8, the second root folder) get
codes 10-19. Every code in the corpus is globally unique. Every other
folder (01-10) uses a single default LF-terminated file per document;
the full CR/LF/CRLF/None line-ending matrix lives only in
`12_LineEndings/`, by design, to keep the corpus at its intended size.

## Encoding names and .NET

Encoding names throughout (folder names and the Encoding field in
filenames/Manifest.csv) were chosen as the best match between Python's
codec names and .NET's `Encoding.GetEncoding` names, verified against
both. **On .NET Core / .NET 5+, only ASCII, ISO-8859-1, and UTF-7/8/16/32
resolve out of the box.** Every other name here (all of Windows-125x,
ISO-8859-2..16, Shift-JIS, GB18030, Big5, KOI8-R/U, etc.) requires the
app to add the `System.Text.Encoding.CodePages` package and call
`Encoding.RegisterProvider(CodePagesEncodingProvider.Instance)` once at
startup - only .NET Framework has them built in. Without that call,
`Encoding.GetEncoding(...)` throws `NotSupportedException` for every
name outside that first group, regardless of how correct the name is.

A number of legacy encodings Python distinguishes have no clean,
unambiguous .NET equivalent at all and were left out of the corpus
rather than given a guessed, colliding, or silently-wrong name:

- **CP932, GBK** - .NET has no distinct identity from Shift-JIS/GB2312
  respectively; it literally returns the other encoding by name
  (confirmed: dotnet/runtime#43745).
- **ISO-2022-JP, Big5-HKSCS, HZ, TIS-620** - no confirmed .NET code
  page at all.
- **ISO-8859-10, -14, -16** - confirmed by live testing, not just
  research: `Encoding.GetEncoding(28600)` (part 10's code page number)
  throws "No data is available for encoding 28600" even with
  `CodePagesEncodingProvider` registered, meaning the code page was
  never actually implemented in .NET, by number or by name. Parts 14
  and 16 were never real Windows code pages either and are assumed to
  fail the same way.
- **ISO-8859-11** - confirmed by live testing to be a *silent*
  mismatch rather than a clean failure: `Encoding.GetEncoding("iso-8859-11")`
  does not throw, but returns .NET's "Thai (Windows)" encoding - code
  page 874, not a genuine distinct ISO-8859-11 implementation. Python's
  `iso8859-11` and `cp874` codecs are confirmed to disagree across the
  whole 0x80-0x9F range, so this name would satisfy "GetEncoding
  doesn't throw" while potentially handing back a decoder that
  disagrees with the actual file bytes - worse than an honest failure.
- **CP874, CP949** - confirmed by live testing (with
  `CodePagesEncodingProvider` registered) that `"cp874"` and `"cp949"`
  both throw in .NET. No alternate name works in both ecosystems
  either: .NET's own names for these code pages ("windows-874" and
  "ks_c_5601-1987") are not valid Python names for the same codecs -
  "windows-874" isn't a recognized Python alias for `cp874`, and
  "ks_c_5601-1987" is a Python alias for a *different* codec (`euc_kr`),
  not `cp949`. Two further CP949 candidates suggested by Python's own
  alias list, `"ms949"` and `"uhc"`, were also tested live in .NET and
  both throw as well.

## Filenames

Every filename fully describes its own content - and its encoding can
be parsed directly from the filename alone, without consulting the
manifest - e.g.:

    DOC000123_15_CJK_Japanese_utf-16LE_BOM_CRLF.txt
    DOC000028_10_Latin_English_iso-8859-1_LF.txt
    DOC000014_05_Markdown_List_us-ascii_LF.txt

`DocumentID_CategoryCode_CategoryName_Title_Encoding_[BOM_]LineEnding.txt`

Every category (ASCII or shared) has a numeric code, so this format
never varies in field count except for the optional BOM field: split a
filename on "_" and the Encoding is always at index 4 (the 5th token),
regardless of category or whether BOM is present:

    index 0: DocumentID
    index 1: CategoryCode
    index 2: CategoryName
    index 3: Title
    index 4: Encoding   <- always here
    index 5: BOM (present only for encodings that have a BOM concept)
    last:    LineEnding

A value containing "_" (e.g. the Python codec name "shift_jis") is
normalized to "-" in filenames only ("shift-jis"), so it can never be
mistaken for a field boundary; Manifest.csv and the folder name still
carry the exact, unmodified codec name.

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

If a file named `Source/<DocumentID>.txt` exists next to
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
