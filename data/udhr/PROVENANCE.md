# Long-form source text: provenance

The files in this directory are the source for the `15_LongForm/` portion
of the corpus. They are vendored verbatim, byte for byte, including each
file's original copyright and provenance header.

## Source artifact

| Field | Value |
|-------|-------|
| Project | UDHR in Unicode |
| Original home | https://www.unicode.org/udhr |
| Artifact | `udhr_txt.zip` |
| Size | 2,204,698 bytes |
| SHA-256 | `7500656f5ec984a9bad35801273d9ac44ff967724720c84d6c3dd8d042ba2515` |
| Retrieved from | Internet Archive snapshot of the original Unicode URL |
| Entries in artifact | 487 (471 language-coded, 16 numeric) |
| Vendored here | 24 |

The Unicode Consortium **discontinued the UDHR in Unicode project in
January 2024** and no longer hosts the data. The pinned SHA-256 above is
what makes this vendoring reproducible despite the dead upstream: anyone
can obtain the same archive and confirm they have the same bytes.

## Copyright and attribution

Every vendored file retains its original header, which reads:

```
Universal Declaration of Human Rights - <Language>
© 1996 – 2009 The Office of the High Commissioner for Human Rights
This plain text version prepared by the “UDHR in Unicode”
project, https://www.unicode.org/udhr.
```

The Universal Declaration of Human Rights is published by the United
Nations. The plain-text preparation is the work of the UDHR in Unicode
project. Both are credited here, in the generated corpus `README.md`,
and in `00_Documentation/`.

The generator strips this header before encoding the body into corpus
files, because the header itself contains characters (`©`, an en dash,
and curly quotation marks) that most legacy code pages cannot represent
— including it would make the text unencodable in the very encodings the
long-form documents exist to exercise. The notice is preserved with the
redistributed source, which is where it belongs; attribution travels
with the corpus separately.

## Sources considered and rejected

**NLTK `udhr2`** (`corpora/udhr2.zip`, SHA-256 `0796c314b0…c7f3`) is a
repackaging of this same Unicode data and its NLTK metadata labels it
`license="public domain"`. It was rejected: the repackaging **strips the
copyright and provenance header**, so that label is applied to a modified
derivative whose own notice — asserting OHCHR copyright — has been
removed. A third-party characterisation cannot override the primary
artifact's notice, and the stripped copy makes preserving that notice
impossible. It also carries 388 entries against the original's 471.

**`eric-muller/udhr` on GitHub** is the former maintainer's repository and
remains active, but ships **no LICENSE file**, which under default
copyright grants no redistribution right. Rejected as a licensing basis.

**`chardet/test-data`** is a large, well-catalogued encoding-detection
corpus, but states `Each test file is copyright its respective publisher`
and exists as a separate repository, in its own words, "since licensing
can be an issue". Its contents are mixed-provenance (CulturaX / Common
Crawl derivatives, web-scraped RSS feeds, vendored Mozilla and Chromium
test files). Unsuitable for redistribution under this corpus's CC BY 4.0
terms; worth knowing as a complementary corpus, not as a source.

## Applied substitutions

Two substitutions are applied to the body text before encoding. Both are
in `generator/longform.py`; both were chosen because they unlock real
encodings without altering content.

### U+2010 HYPHEN → U+002D HYPHEN-MINUS

A typographic hyphen that **no** code page in this corpus can represent,
windows-125x included. Measured across the vendored set it alone blocked
**130** (language, codec) pairs — including Ukrainian in KOI8-U and
Bulgarian in windows-1251, where it was the *only* blocking character in
otherwise fully encodable text. It is visually and semantically the same
hyphen as U+002D, so the substitution changes no content and, because no
code page carries it, costs no detection signal either.

### U+1F18 GREEK CAPITAL LETTER EPSILON WITH PSILI → U+0395 EPSILON

A single polytonic character (one occurrence) in
`udhr_ell_monotonic.txt` — a file that by its own name is monotonic
text, an orthography which drops the breathing marks. The substitution
restores the document to the form it declares. Without it, the corpus's
only Greek document cannot be emitted in `iso-8859-7` or
`windows-1253` at all, leaving both encodings with no long-form sample.

## Deliberately NOT normalized

`U+2013 EN DASH`, `U+2019 RIGHT SINGLE QUOTATION MARK`, and
`U+201C`/`U+201D` are left exactly as the source has them, even though
they block several encodings:

| Character | windows-1252 | windows-1251 | iso-8859-1 | koi8-r |
|-----------|--------------|--------------|------------|--------|
| U+2010 HYPHEN | absent | absent | absent | absent |
| U+2013 EN DASH | `0x96` | `0x96` | absent | absent |
| U+2019 RSQUO | `0x92` | `0x92` | absent | absent |
| U+201C LDQUO | `0x93` | `0x93` | absent | absent |

That `0x91`–`0x97` range is the classic signal distinguishing
windows-1252 from iso-8859-1 — one of the hardest and most valuable
discriminations a detector has to make. Normalizing those characters
would buy a little more coverage by destroying exactly the evidence the
corpus exists to provide. U+2010 is safe to substitute precisely because
it is missing from every column.

Every remaining encoding failure is a genuine script/code-page mismatch
and is left to the generator's existing `can_encode` skip: a document is
simply not emitted in an encoding that cannot represent it. Spanish `ñ`
is correctly absent from ISO-8859-2, Dutch `ë` from KOI8-R, Ukrainian
`ґ` from ISO-8859-5.

Known consequence: `ChineseTraditional` is **not** emitted in Big5. Its
text contains U+75E9 and U+8991 (3 occurrences in 3,733 characters),
which Big5 genuinely lacks. Substituting them would corrupt the text, so
the document is skipped for that encoding instead.
