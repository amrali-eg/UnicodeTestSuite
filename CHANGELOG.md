# Changelog

All notable changes to UnicodeTestSuite are documented in this file.

The project follows a deterministic generation model. Every release is fully reproducible and verified after generation.

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
