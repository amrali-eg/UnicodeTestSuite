"""Long-form documents are emitted only into encodings that serve their language.

The corpus previously emitted every long-form document into every encoding
capable of representing it. That is a much larger set than it sounds: GB18030
encodes all of Unicode, and EUC-JP covers Latin letters through JIS X 0212, so
the corpus produced German in EUC-JP and Polish in GB18030. Those files are
valid encodings of the document and meaningless as detection targets - their
byte statistics are Latin, because the text is.

Measured against a real detector, the long-form set scored 92.3% where the
language matched the encoding and 60.0% where it did not, and the cross-script
pairings outnumbered the real ones 70 to 52. That was enough to hide the entire
benefit of long-form samples: restricted, long-form legacy accuracy is 92.2%
against 72.2% for the short samples; unrestricted it was 73.8%, indistinguishable
from the short ones.
"""

import unittest

from generator.encoder import LEGACY_FAMILIES
from generator.longform import (
    LONGFORM_ENCODINGS,
    LONGFORM_SOURCES,
    legacy_encodings_for,
)

LEGACY_LABELS = {spec.label for family in LEGACY_FAMILIES for spec in family}


class MapIntegrityTests(unittest.TestCase):
    def test_every_document_has_an_entry(self):
        titles = {title for _, title in LONGFORM_SOURCES}
        self.assertEqual(titles - set(LONGFORM_ENCODINGS), set())

    def test_no_entry_without_a_document(self):
        titles = {title for _, title in LONGFORM_SOURCES}
        self.assertEqual(set(LONGFORM_ENCODINGS) - titles, set())

    def test_every_label_is_a_real_corpus_encoding(self):
        used = {label for labels in LONGFORM_ENCODINGS.values() for label in labels}
        self.assertEqual(used - LEGACY_LABELS, set())

    def test_lookup_of_an_unknown_title_is_empty(self):
        self.assertEqual(legacy_encodings_for("NoSuchLanguage"), ())

    def test_no_duplicate_labels_within_a_language(self):
        for title, labels in LONGFORM_ENCODINGS.items():
            with self.subTest(language=title):
                self.assertEqual(len(labels), len(set(labels)))


class PairingSanityTests(unittest.TestCase):
    """The pairings the unrestricted corpus got wrong must stay excluded."""

    def test_european_languages_are_not_paired_with_east_asian_encodings(self):
        east_asian = {"shift_jis", "euc-jp", "gb2312", "gb18030", "big5",
                      "euc-kr", "iso-2022-kr"}
        european = ["German", "French", "Spanish", "Portuguese", "Italian",
                    "Dutch", "Polish", "Czech", "Hungarian", "Russian",
                    "Ukrainian", "Bulgarian", "Greek", "Turkish",
                    "Lithuanian", "Latvian"]
        for language in european:
            with self.subTest(language=language):
                self.assertEqual(
                    set(legacy_encodings_for(language)) & east_asian, set())

    def test_gb18030_serves_chinese_only(self):
        # GB18030 covers all of Unicode, which made it the single worst
        # offender: it could "represent" every document in the corpus.
        for title in LONGFORM_ENCODINGS:
            if "gb18030" in legacy_encodings_for(title):
                self.assertIn("Chinese", title)

    def test_cyrillic_encodings_serve_cyrillic_languages_only(self):
        cyrillic_only = {"koi8-r", "koi8-u", "iso-8859-5", "windows-1251"}
        for title, labels in LONGFORM_ENCODINGS.items():
            if set(labels) & cyrillic_only:
                with self.subTest(language=title):
                    self.assertIn(title, {"Russian", "Ukrainian", "Bulgarian"})

    def test_ukrainian_is_not_paired_with_koi8_r(self):
        # KOI8-R lacks the Ukrainian letters KOI8-U adds.
        self.assertNotIn("koi8-r", legacy_encodings_for("Ukrainian"))

    def test_ukrainian_is_not_paired_with_iso_8859_5(self):
        # ISO-8859-5 lacks U+0491 CYRILLIC SMALL LETTER GHE WITH UPTURN.
        self.assertNotIn("iso-8859-5", legacy_encodings_for("Ukrainian"))

    def test_romanian_has_no_legacy_encoding(self):
        # Romanian needs S and T with comma below (U+0218..U+021B), which
        # live in ISO-8859-16 - not in this corpus, because .NET has no code
        # page for it. windows-1250 and ISO-8859-2 carry only cedilla forms.
        self.assertEqual(legacy_encodings_for("Romanian"), ())

    def test_every_other_language_has_at_least_one_encoding(self):
        for title in LONGFORM_ENCODINGS:
            if title == "Romanian":
                continue
            with self.subTest(language=title):
                self.assertGreater(len(legacy_encodings_for(title)), 0)


if __name__ == "__main__":
    unittest.main()
