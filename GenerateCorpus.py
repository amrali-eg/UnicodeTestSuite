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

from generator import GENERATOR_VERSION, MANIFEST_VERSION
from generator.certificate import METADATA_FILES, parse_metadata_hashes, write_certificate
from generator.corpus import generate_corpus
from generator.documents import document_count
from generator.filenames import FilenameContractError
from generator.hashing import sha256_file
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

The long-form documents in 15_LongForm are a separate set, drawn from
the UDHR in Unicode project: the Universal Declaration of Human Rights,
published by the United Nations, in a plain-text preparation by that
project. They exist because detection needs length that round-trip
testing does not. Their source files, copyright notices intact, and the
full provenance record are in data/udhr/ in the generator repository.

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
- `12_LineEndings/` - a curated CR/LF/CRLF/None showcase over ASCII
  documents in UTF-8, plus one file with mixed line endings within a
  single document, plus `Matrix/<Encoding>/`: three documents (Latin,
  Cyrillic, CJK) in every core Unicode encoding and each legacy codec
  that can represent them, in CR, LF and CRLF. The matrix is where
  patterns like `0D 00 0A 00` - CRLF in UTF-16LE - live.
- `13_Binary/<Category>/` - synthetic binary-format-signature stubs
  (EXE, DLL, PNG, JPG, GIF, ZIP, PDF, Office, Audio, Video, SQLite,
  Random) plus general binary edge fixtures.
- `14_LargeFiles/` - a handful of multi-megabyte amplified documents.
- `15_LongForm/<Encoding>/` - multi-kilobyte natural-language text, one
  document per language, in every encoding capable of representing it.
  The per-category documents elsewhere are short by design, which suits
  round-trip testing but is far below what a statistical detector needs
  to classify; these are the samples where byte-frequency and bigram
  models can actually converge.

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

This is checked for every document-derived file as it is written, and
generation aborts rather than emitting a filename that breaks it.

Three groups of files are deliberately NOT document-derived and do not
follow the format: the `.bin` fixtures under 11_InvalidUnicode/ and
13_Binary/, and the three reference files in 00_Documentation/
(Categories.txt, Encodings.txt, SourceDocumentsIndex.txt). Filter on
".txt" with a "DOC"-prefixed DocumentID, or read Manifest.csv.

## Detection ground truth (Manifest.csv)

Manifest.csv columns are:

    DocumentID, CategoryCode, Category, Encoding, BOM, AlsoValidAs,
    LineEnding, Characters, Bytes, SHA256, RelativePath

`Encoding` records what produced the bytes. It is not, on its own, the
right thing to score a detector against: a byte sequence is frequently
valid, and decodes identically, under many encodings at once. Pure-ASCII
content is legitimately readable as us-ascii, utf-8, every Windows code
page and every ISO-8859 part, simultaneously.

`AlsoValidAs` is a semicolon-separated list of every other encoding that
decodes that file's bytes to the *same characters*, and is empty when
the declared encoding is the only correct answer.

A benchmark harness should accept a detector's answer when it matches
`Encoding` OR appears in `AlsoValidAs`. Scoring string equality against
`Encoding` alone marks correct answers wrong - a detector reporting
"ascii" for pure-ASCII content, if anything the more precise answer, is
right, and this corpus says so.

The set is computed from the bytes, not from which duplicate files the
corpus happens to contain, so it is complete regardless of which
encodings a given document was emitted in.

`CategoryCode` is the two-digit code ("15") and is empty for fixtures
with no numbered category; `Category` is always a plain name ("CJK").
Directory names still use the combined "15-CJK" slug.

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
    python GenerateCorpus.py verify --corpus /path/to/UnicodeTestSuite

This re-checks the metadata files against the SHA-256 values recorded in
CorpusCertificate.txt, then every file against Manifest.csv, re-decoding
each under its declared encoding, and finally fails if any file is
present on disk but absent from the manifest. The certificate is the
anchor: it is written last and covers MasterHashes.sha256 itself.

Or, on Linux/macOS, using the standard `sha256sum` format directly:

    cd UnicodeTestSuite && sha256sum -c MasterHashes.sha256

Note that sha256sum checks only the files listed in MasterHashes.sha256.
It cannot detect an added file or a modified manifest; use
`GenerateCorpus.py verify` for the whole chain.

## Source/ overrides (optional)

If a file named `Source/<DocumentID>.txt` exists next to
GenerateCorpus.py (e.g. `Source/DOC000001.txt`), its UTF-8 content
replaces that document's built-in text before generation. Entirely
optional; an empty `Source/` directory is the normal, expected state.
"""


def _resolve_target(explicit: str | None) -> Path:
    """Corpus directory to operate on: --corpus if given, else the default."""
    if explicit:
        return Path(explicit).expanduser().resolve()
    return PROJECT_ROOT / "UnicodeTestSuite"


def _confirm_destroy(output_root: Path, force: bool) -> bool:
    """Decide whether an existing corpus directory may be deleted.

    v2.0 called shutil.rmtree unconditionally, in a script whose own
    docstring invites double-clicking, on a directory with the same name
    as the published release archive. Extracting the release next to the
    generator and running it destroyed the download with no prompt.
    """
    if not output_root.exists():
        return True
    if force:
        return True

    entry_count = sum(1 for _ in output_root.rglob("*"))
    print(f"\nWARNING: {output_root} already exists and holds {entry_count:,} entries.")
    print("Generating will DELETE it and rebuild from scratch.")

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Refusing to delete it in a non-interactive session.")
        print("Re-run with --force if that is what you want.")
        return False

    try:
        answer = input("Delete and regenerate? [y/N] ").strip().lower()
    except EOFError:
        return False
    return answer in ("y", "yes")


def _run_generate(corpus_dir: str | None = None, force: bool = False) -> int:
    output_root = _resolve_target(corpus_dir)

    print(f"Unicode Test Suite Generator (UTS) v{GENERATOR_VERSION}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Target:       {output_root}")
    print(f"Canonical source documents: {document_count()}")

    if not _confirm_destroy(output_root, force):
        print("Aborted. Nothing was deleted.")
        return 1

    print("Generating corpus...")
    started = time.monotonic()
    try:
        records, output_root, overrides = generate_corpus(PROJECT_ROOT, output_root)
    except CorpusIntegrityError as exc:
        print("\nFATAL: corpus integrity check failed. Generation aborted.")
        print(f"Reason: {exc}")
        return 1
    except FilenameContractError as exc:
        print("\nFATAL: a generated filename violates the parsing contract.")
        print(f"Reason: {exc}")
        return 1
    except Exception:
        print("\nFATAL: unexpected error during generation. Generation aborted.")
        traceback.print_exc()
        return 1

    elapsed = time.monotonic() - started
    print(f"Generated and verified {len(records):,} files in {elapsed:.2f} seconds.")
    if overrides:
        print(f"NOTE: {len(overrides)} Source/ override(s) applied; not the canonical corpus.")

    print("Writing Manifest.csv ...")
    write_manifest_csv(records, output_root / "Manifest.csv")

    print("Writing Manifest.sqlite ...")
    write_manifest_sqlite(records, output_root / "Manifest.sqlite")

    print("Writing MasterHashes.sha256 ...")
    write_master_hashes(records, output_root / "MasterHashes.sha256")

    print("Writing ManifestVersion.txt ...")
    (output_root / "ManifestVersion.txt").write_text(
        MANIFEST_VERSION + "\n", encoding="utf-8", newline="\n")

    print("Writing Statistics.txt ...")
    write_statistics(records, elapsed, output_root / "Statistics.txt")

    print("Writing Index.html ...")
    write_html_index(records, output_root / "Index.html")

    print("Writing README.md ...")
    readme_text = README_TEMPLATE.format(version=GENERATOR_VERSION, doc_count=document_count())
    (output_root / "README.md").write_text(readme_text, encoding="utf-8", newline="\n")

    # Written last, so it can hash everything above it and anchor the chain.
    print("Writing CorpusCertificate.txt ...")
    write_certificate(records, elapsed, output_root, output_root / "CorpusCertificate.txt", overrides)

    print("\nDone.")
    print(f"Corpus written to: {output_root}")
    return 0


def _verify_metadata_chain(output_root: Path) -> str | None:
    """Re-check the metadata files against CorpusCertificate.txt.

    Returns an error string, or None when the chain is intact.
    """
    certificate_path = output_root / "CorpusCertificate.txt"
    if not certificate_path.is_file():
        return f"{certificate_path} not found; cannot anchor the integrity chain"

    recorded = parse_metadata_hashes(certificate_path.read_text(encoding="utf-8"))
    for name in METADATA_FILES:
        path = output_root / name
        if name not in recorded:
            return f"certificate does not record a hash for {name}"
        if not path.is_file():
            return f"{name} is listed in the certificate but missing from disk"
        actual = sha256_file(path)
        if actual != recorded[name]:
            return f"{name} SHA-256 mismatch: certificate says {recorded[name]}, disk has {actual}"
    return None


def _find_unlisted_files(output_root: Path, listed: set[str]) -> list[str]:
    """Corpus files present on disk but absent from the manifest."""
    known = listed | set(METADATA_FILES) | {"CorpusCertificate.txt"}
    found = []
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(output_root).as_posix()
        if relative not in known:
            found.append(relative)
    return found


def _run_verify(corpus_dir: str | None = None) -> int:
    output_root = _resolve_target(corpus_dir)
    manifest_path = output_root / "Manifest.csv"

    print(f"Unicode Test Suite Generator (UTS) v{GENERATOR_VERSION} - verify mode")
    print(f"Corpus directory: {output_root}")

    if not manifest_path.is_file():
        print(f"\nFATAL: {manifest_path} not found. Run 'generate' first.")
        return 1

    print("Checking metadata chain against CorpusCertificate.txt ...")
    chain_error = _verify_metadata_chain(output_root)
    if chain_error is not None:
        print(f"\nFATAL: metadata chain broken. {chain_error}")
        return 1
    print(f"  {len(METADATA_FILES)} metadata files match the certificate.")

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

    print("Scanning for files not listed in the manifest ...")
    unlisted = _find_unlisted_files(output_root, {r["RelativePath"] for r in rows})
    if unlisted:
        print(f"\nFATAL: {len(unlisted)} file(s) present on disk but absent from Manifest.csv:")
        for relative in unlisted[:20]:
            print(f"  {relative}")
        if len(unlisted) > 20:
            print(f"  ... and {len(unlisted) - 20} more")
        return 1

    elapsed = time.monotonic() - started
    print(f"All {checked:,} files verified OK in {elapsed:.2f} seconds.")
    print("Metadata chain intact; no unlisted files.")
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
        help="'generate' (default) rebuilds the corpus from scratch; "
             "'verify' re-checks an existing corpus without rebuilding.",
    )
    parser.add_argument(
        "--corpus",
        metavar="DIR",
        default=None,
        help="corpus directory to build or verify "
             "(default: UnicodeTestSuite/ next to this script)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow 'generate' to delete an existing corpus directory without asking",
    )
    args = parser.parse_args()

    if args.command == "verify":
        return _run_verify(args.corpus)
    return _run_generate(args.corpus, args.force)


if __name__ == "__main__":
    exit_code = main()
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass
    sys.exit(exit_code)
