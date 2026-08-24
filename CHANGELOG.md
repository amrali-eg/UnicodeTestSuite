# Changelog

All notable changes to UnicodeTestSuite are documented in this file.

The project follows a deterministic generation model. Every release is fully reproducible and verified after generation.

---

## [3.0] - 2026-08-24

A correctness release. v2.0's central promises — cryptographic integrity,
a machine-parseable filename contract, and usable detection ground truth
— each had a hole in them. This release closes those, and adds the
long-form and line-ending coverage the corpus needed in order to
discriminate between detectors rather than defeat all of them equally.

**This release is not backward compatible.** `Manifest.csv` gains
columns, two files are renamed, and several documents change content, so
hashes move. Consumers should read `ManifestVersion.txt` (or the `meta`
table in `Manifest.sqlite`) to tell a v2 corpus from a v3 one.

### Fixed

#### Integrity: `verify` passed on a tampered corpus

`MasterHashes.sha256` covered 1,212 of the 1,222 files a v2.0 corpus
contained. `Manifest.csv`, `Manifest.sqlite`, `Index.html`,
`Statistics.txt`, `README.md`, `MasterHashes.sha256` itself, and the
three `00_Documentation/*.txt` reference files were all outside it. A
corpus could be edited in ways that changed what a consumer reads — the
manifest being the ground truth every harness parses — while both
`GenerateCorpus.py verify` and `sha256sum -c` reported success.
`CorpusCertificate.txt` recorded a `MasterHashes SHA-256` anchor that
nothing ever checked.

* The `00_Documentation` reference files now produce manifest records.
* `CorpusCertificate.txt` is written last and records the SHA-256 of
  every metadata file, including `MasterHashes.sha256`.
* `verify` re-checks those hashes before trusting the manifest, and fails
  on files present on disk but absent from it.
* CI replays all three tamper cases and fails if any stops being caught.

#### Filename contract: two files broke the documented rule

`12_LineEndings/NoNewlineAtAll_UTF8_NoBOM_None.txt` and
`MixedLineEndingsWithinOneFile_UTF8_NoBOM_Mixed.txt` split into four
tokens on `_`, so `tokens[4]` — documented as always the encoding — threw.
They also spelled the encoding `UTF8` while the manifest said `utf-8`. A
.NET consumer benchmarking against v2.0 silently dropped exactly these
two files rather than failing loudly.

* Both are rebuilt through `build_filename()` with reserved `DOC9xxxxx`
  ids and a new `20-LineEndingEdge` fixture category.
* `assert_filename_contract()` now runs on every document-derived file at
  generation time, so a hand-built name cannot break the contract again.

#### Documents that did not cover what they claimed

* `DOC000064` and `DOC000065` were byte-identical: the phrase used is
  written the same in Simplified and Traditional Chinese. They now differ
  at the code-point level, which also gives Big5 a genuine
  traditional-Chinese sample.
* Dutch, Norwegian and Hungarian were pure ASCII by accident; all three
  languages use diacritics and now carry them. This removed 51 files that
  existed only as ambiguous duplicates across unrelated code pages.
* English remains pure ASCII deliberately — see `AlsoValidAs` below.

#### Destructive `generate`

`generate` called `shutil.rmtree` unconditionally, in a script whose
docstring invites double-clicking, on a directory sharing its name with
the published release archive. Extracting the release next to the
generator and running it destroyed the download without a prompt.

* An existing corpus directory now requires interactive confirmation, or
  `--force` in a non-interactive session.
* `--corpus DIR` targets any directory, for both subcommands. `verify`
  was previously locked to the one path `generate` would delete.

### Added

#### `AlsoValidAs`: ground truth is a set, not a scalar

v2.0 asserted one correct encoding per file, but 300 of 1,150 text files
were byte-identical to a file carrying a *different* declared encoding.
27 byte sequences appeared twice under contradictory labels — once in
`01_ASCII` as `us-ascii`, once in `00_Documentation` as `utf-8`. No
detector can satisfy both rows. A detector answering `ascii` for
pure-ASCII content, the more precise answer, scored 65 false negatives
against v2.0 for being right.

`AlsoValidAs` lists every encoding that decodes a file's bytes to the
*same characters*. The set is computed from the bytes, not from which
duplicates the corpus happens to contain, so pure-ASCII content is marked
valid under all 30 ASCII-superset encodings whether or not it is emitted
in each. Harnesses should score set membership rather than string
equality.

The test is character equality, deliberately not byte round-tripping:
every single-byte codec decodes arbitrary bytes without error and
re-encodes them exactly, so round-tripping would report UTF-8 Japanese as
also valid as `iso-8859-1`, which is mojibake rather than an alternative
reading.

#### `15_LongForm`: samples a detector can actually classify

v2.0's legacy-encoded files had a median length of **31 bytes** and a
maximum of 125. Mozilla-UDE-class detectors build byte-frequency and
bigram models and need hundreds of bytes to converge, so every detector
failed that portion for the same uninformative reason and the benchmark
could not tell a strong one from a weak one.

`15_LongForm` adds 170 files across 29 encodings, 122 of them legacy,
with a median of 13,649 bytes and none under 64. Source is the UDHR in
Unicode project, pinned by SHA-256; see `data/udhr/PROVENANCE.md` for the
artifact, the attribution, the two documented substitutions, and the
sources considered and rejected. The short samples are kept — they remain
good round-trip tests.

#### `12_LineEndings/Matrix`: CR and CRLF beyond UTF-8

v2.0 varied the terminator only within UTF-8 and only over nine
pure-ASCII documents. 1,130 of 1,212 files were LF, and the corpus
contained no CRLF file in UTF-16, UTF-32, or any legacy code page —
leaving `0D 00 0A 00`, CRLF in UTF-16LE and the most common byte pattern
in real Windows text, entirely unrepresented.

Three documents spanning Latin, Cyrillic and CJK, in every core Unicode
encoding plus the legacy codecs that can represent them, each in CR, LF
and CRLF. CR/CRLF coverage goes from 1 encoding to 12.

#### Other additions

* `CategoryCode` column. v2.0's `Category` mixed two shapes — `15-CJK`
  for most rows, bare `InvalidUnicode` or `Random` for fixtures — so
  splitting on `-` gave a valid code for most rows and a silent wrong
  answer for the rest. `CategoryCode` is the code (empty for fixtures)
  and `Category` is always a plain name. Directories keep the `15-CJK`
  slug.
* `ManifestVersion.txt`, a `meta` table in `Manifest.sqlite`, and a
  `Manifest version` line in the certificate. `README.md` has claimed
  since v2.0 that every corpus records a manifest version; none did.
* Source override provenance. Overrides changed corpus content while
  leaving every recorded field identical, making a hash mismatch
  undiagnosable. The certificate now records the overridden document ids
  and each override file's SHA-256, or `none`.
* `tests/` — 40 stdlib `unittest` tests covering the filename contract,
  the equivalence criterion, encoder lookup, category code disjointness,
  document identity, line-ending variants and certificate parsing.
* `.github/workflows/ci.yml` — unit tests on Linux and Windows across
  3.11–3.13; generate and verify on both; determinism checked by
  regenerating and diffing; cross-platform determinism compared between
  Linux and Windows; and an integrity job replaying the v2.0 tamper
  cases.
* `pyproject.toml` declaring `requires-python = ">=3.11"`.
* `LICENSE-CORPUS` with the CC BY 4.0 text, promised by v2.0's README but
  never shipped, plus a carve-out for the UDHR-derived content.
* `.gitignore` — the generator writes its output beside the script, and a
  `git add -A` after a run committed the whole corpus.

### Changed

* `Manifest.csv` columns are now: `DocumentID`, `CategoryCode`,
  `Category`, `Encoding`, `BOM`, `AlsoValidAs`, `LineEnding`,
  `Characters`, `Bytes`, `SHA256`, `RelativePath`.
* Corrected a comment describing the `12_LineEndings` showcase documents
  as "a mix of ASCII and shared groups". Every id there is at or below
  `DOC000027`; all nine are ASCII.
* Clarified the encoding count. v1.0 and v2.0 reported "supported
  encodings" as 51 and 40, which counted `EncodingSpec` entries with BOM
  and BOM-less variants listed separately. The corpus has **35 distinct
  encodings** (6 Unicode plus 29 legacy); 40 is the spec-variant count.
  Nothing about the corpus changed — only the figure being reported.

### Statistics

| Item | v2.0 | v3.0 |
| --- | ---: | ---: |
| Total generated files | 1,212 | 1,430 |
| Canonical documents | 94 | 94 |
| Long-form documents | 0 | 24 |
| Root folders | 15 | 16 |
| Distinct encodings | 35 | 35 |
| Encoding spec variants (BOM counted separately) | 40 | 40 |
| Legacy sample median | 31 B | 56 B |
| Legacy sample maximum | 125 B | 27,819 B |
| Encodings with CR/CRLF | 1 | 12 |
| Files covered by MasterHashes | 1,212 of 1,222 | all |

---

## [2.0] - 2026-08-04

This release focuses on correctness, interoperability, deterministic generation, and machine-readable corpus metadata.

### Added

* Added deterministic `generate` and `verify` command-line modes.
* Added exhaustive post-generation verification.
* Added synthetic binary format signature generation.
* Added globally unique numeric category codes.
* Added a deterministic filename format suitable for automated parsing.
* Added verification that every generated filename places the encoding token at a fixed position.

### Changed

#### Encoding Names

* Replaced cosmetic encoding labels with canonical Python/.NET codec identifiers.
* Standardized Unicode encoding names (for example `utf-8`, `utf-16LE`, `utf-32BE`).
* Standardized Windows code pages (`windows-1250` through `windows-1258`).
* Standardized ISO-8859 codec names.
* Standardized KOI8 codec names.
* Standardized East Asian codec names.

#### Filename Format

* Redesigned filenames to be fully machine-readable.
* Preserved hyphens inside encoding names (for example `iso-8859-1`, `shift-jis`).
* Converted underscores inside encoding identifiers to hyphens for filenames only, preventing ambiguous parsing.
* Guaranteed that the encoding identifier is always located at index **4** (the fifth token).

Filename format:

```text
DocumentID_CategoryCode_CategoryName_Title_Encoding_[BOM_]LineEnding.ext
```

#### Category Organization

* Unified ASCII and shared document categories into a single category model.
* Added numeric identifiers to ASCII categories.
* Renumbered all categories to follow directory order.
* Category codes are now globally unique.

#### Corpus

* Reduced duplicate encodings.
* Removed unsupported or ambiguous codec aliases.
* Updated the corpus to contain only verified encoding identifiers.

### Removed

Removed encodings that could not be reliably supported by both Python and .NET or that represented duplicate implementations.

#### Removed ISO-8859 variants

* iso-8859-10
* iso-8859-11
* iso-8859-14
* iso-8859-16

#### Removed East Asian aliases

* cp932
* gbk
* cp874
* cp949
* ISO-2022-JP
* Big5-HKSCS
* HZ
* TIS-620

### Validation

Every remaining encoding has been verified through research and/or live .NET testing.

Validation includes:

* Python codec compatibility
* .NET `Encoding.GetEncoding()`
* deterministic corpus generation
* deterministic verification
* filename parsing verification
* post-generation hash verification

### Statistics

| Item                  | Value |
| --------------------- | ----: |
| Total generated files | 1,212 |
| Canonical documents   |    94 |
| Root folders          |    15 |
| Supported encodings   |    40 |
| Windows code pages    |     9 |
| ISO-8859 encodings    |    11 |
| East Asian encodings  |     7 |
| KOI8 encodings        |     2 |

---

## [1.0]

Initial public release.

Features included:

* 94 canonical Unicode documents.
* 15 root folders.
* 51 supported encodings
* 1,300 generated files
* Unicode, Windows, ISO-8859, East Asian and legacy encodings.
* Binary signature corpus.
* Deterministic generation.
* Manifest generation.
