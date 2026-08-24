"""Encoder lookup, document identity, line-ending variants, certificate parsing."""

import unittest

from generator.categories import (
    ASCII_CATEGORIES,
    FIXTURE_CATEGORIES,
    LONGFORM_CATEGORY,
    SHARED_CATEGORIES,
    category_by_name,
)
from generator.certificate import METADATA_FILES, parse_metadata_hashes
from generator.corpus import _default_line_ending, _line_ending_variants
from generator.documents import _build_documents
from generator.encoder import find_spec
from generator.longform import LONGFORM_SOURCES, normalize_body


class FindSpecTests(unittest.TestCase):
    def test_bom_and_nobom_variants_are_distinct(self):
        with_bom = find_spec("utf-8", "BOM")
        without = find_spec("utf-8", "NoBOM")
        self.assertIsNotNone(with_bom)
        self.assertIsNotNone(without)
        self.assertTrue(with_bom.has_bom)
        self.assertFalse(without.has_bom)

    def test_legacy_specs_resolve(self):
        spec = find_spec("shift_jis", "NoBOM")
        self.assertIsNotNone(spec)
        self.assertEqual(spec.codec, "shift_jis")

    def test_pseudo_labels_return_none(self):
        # "Binary" is used for fixtures with no real text codec; verify
        # relies on None here to fall back to size+hash only.
        self.assertIsNone(find_spec("Binary", "N/A"))


class CategoryTests(unittest.TestCase):
    def test_code_ranges_do_not_overlap(self):
        ascii_codes = {c.code for c in ASCII_CATEGORIES}
        shared_codes = {c.code for c in SHARED_CATEGORIES}
        fixture_codes = {c.code for c in FIXTURE_CATEGORIES}
        longform = {LONGFORM_CATEGORY.code}
        all_sets = [ascii_codes, shared_codes, fixture_codes, longform]
        for i, a in enumerate(all_sets):
            for b in all_sets[i + 1:]:
                self.assertEqual(a & b, set(), "category codes must be globally unique")

    def test_lookup_by_name(self):
        self.assertEqual(category_by_name(SHARED_CATEGORIES, "CJK").code, "15")
        with self.assertRaises(KeyError):
            category_by_name(SHARED_CATEGORIES, "NoSuchCategory")

    def test_slug_shape(self):
        self.assertEqual(category_by_name(SHARED_CATEGORIES, "CJK").slug, "15-CJK")


class DocumentIdentityTests(unittest.TestCase):
    def test_ids_are_unique_and_sequential(self):
        docs = _build_documents()
        ids = [d.doc_id for d in docs]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(ids[0], "DOC000001")
        self.assertEqual(ids, [f"DOC{i:06d}" for i in range(1, len(ids) + 1)])

    def test_reserved_blocks_cannot_collide_with_sequential_ids(self):
        # Long-form uses DOC8xxxxx and fixtures DOC9xxxxx. Both are safe
        # only while the sequential range stays far below them.
        docs = _build_documents()
        self.assertLess(len(docs), 800000)

    def test_no_two_documents_share_content_within_a_category(self):
        # v2.0 shipped ChineseSimplified and ChineseTraditional with byte
        # identical text, advertising coverage it did not have.
        seen = {}
        for doc in _build_documents():
            key = (doc.category_name, doc.text)
            self.assertNotIn(
                key, seen,
                f"{doc.doc_id} duplicates {seen.get(key)} in {doc.category_name}")
            seen[key] = doc.doc_id

    def test_longform_sources_are_unique(self):
        filenames = [f for f, _ in LONGFORM_SOURCES]
        titles = [t for _, t in LONGFORM_SOURCES]
        self.assertEqual(len(filenames), len(set(filenames)))
        self.assertEqual(len(titles), len(set(titles)))


class LineEndingVariantTests(unittest.TestCase):
    def test_text_without_newline_gets_a_single_none_variant(self):
        self.assertEqual(_line_ending_variants("no newline"), [("None", "no newline")])
        self.assertEqual(_default_line_ending("no newline"), [("None", "no newline")])

    def test_variants_cover_all_three_terminators(self):
        labels = [label for label, _ in _line_ending_variants("a\nb\n")]
        self.assertEqual(labels, ["LF", "CRLF", "CR"])

    def test_variant_text_is_actually_converted(self):
        variants = dict(_line_ending_variants("a\nb\n"))
        self.assertEqual(variants["CRLF"], "a\r\nb\r\n")
        self.assertEqual(variants["CR"], "a\rb\r")
        self.assertNotIn("\n", variants["CR"])

    def test_default_outside_the_showcase_is_lf_only(self):
        self.assertEqual(_default_line_ending("a\nb\n"), [("LF", "a\nb\n")])


class LongFormNormalizationTests(unittest.TestCase):
    def test_typographic_hyphen_is_replaced(self):
        # U+2010 exists in no code page in the corpus, windows-125x
        # included, so substituting it costs no detection signal.
        self.assertEqual(normalize_body("a‐b"), "a-b")

    def test_polytonic_epsilon_is_folded_for_monotonic_text(self):
        self.assertEqual(normalize_body("Ἐ"), "Ε")

    def test_windows_only_punctuation_is_preserved(self):
        # 0x91-0x97 in windows-125x, absent from ISO-8859 and KOI8. This
        # is the classic windows-1252 vs iso-8859-1 discriminator and the
        # corpus must not normalize it away.
        for ch in ("–", "’", "“", "”"):
            with self.subTest(char=ch):
                self.assertEqual(normalize_body(ch), ch)


class CertificateParsingTests(unittest.TestCase):
    def test_recovers_recorded_hashes(self):
        digest = "a" * 64
        text = (
            "Metadata file hashes (SHA-256)\n"
            "-----\n"
            f"  Manifest.csv           {digest}\n"
            f"  MasterHashes.sha256    {'b' * 64}\n"
        )
        parsed = parse_metadata_hashes(text)
        self.assertEqual(parsed["Manifest.csv"], digest)
        self.assertEqual(parsed["MasterHashes.sha256"], "b" * 64)

    def test_ignores_unrelated_lines(self):
        parsed = parse_metadata_hashes("Generator version:    3.0.0\nsome noise\n")
        self.assertEqual(parsed, {})

    def test_master_hashes_is_covered(self):
        # The chain anchor: if MasterHashes itself were not recorded,
        # nothing would detect it being rewritten wholesale.
        self.assertIn("MasterHashes.sha256", METADATA_FILES)
        self.assertIn("Manifest.csv", METADATA_FILES)


if __name__ == "__main__":
    unittest.main()
