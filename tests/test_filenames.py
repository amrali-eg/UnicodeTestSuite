"""Filename construction and the parsing contract.

The contract - encoding always at index 4 when the stem is split on "_" -
is stated unconditionally in README.md and is what lets consumers parse
filenames instead of Manifest.csv. v2.0 shipped two .txt files that broke
it, and a real consumer silently dropped them rather than failing loudly,
so these are regression tests for a defect that cost coverage in the
field.
"""

import unittest

from generator.filenames import (
    ENCODING_TOKEN_INDEX,
    FilenameContractError,
    assert_filename_contract,
    build_filename,
    sanitize_component,
)


class SanitizeComponentTests(unittest.TestCase):
    def test_underscore_becomes_hyphen(self):
        # Not stripped: "shift_jis" must not split into two fields when a
        # consumer splits the filename on "_".
        self.assertEqual(sanitize_component("shift_jis"), "shift-jis")

    def test_hyphens_are_preserved(self):
        self.assertEqual(sanitize_component("iso-8859-1"), "iso-8859-1")
        self.assertEqual(sanitize_component("windows-1250"), "windows-1250")

    def test_invalid_characters_are_stripped(self):
        self.assertEqual(sanitize_component("a b/c:d"), "abcd")

    def test_leading_and_trailing_hyphens_are_trimmed(self):
        self.assertEqual(sanitize_component("--x--"), "x")

    def test_empty_result_falls_back(self):
        # Must never return "", which would collapse two fields together.
        self.assertEqual(sanitize_component("///"), "X")
        self.assertEqual(sanitize_component(""), "X")


class BuildFilenameTests(unittest.TestCase):
    def test_encoding_lands_at_the_documented_index(self):
        name = build_filename(
            "DOC000123", ["15", "CJK"], "Japanese", "utf-16LE", "BOM", "CRLF")
        self.assertEqual(name, "DOC000123_15_CJK_Japanese_utf-16LE_BOM_CRLF.txt")
        stem = name.rsplit(".", 1)[0]
        self.assertEqual(stem.split("_")[ENCODING_TOKEN_INDEX], "utf-16LE")

    def test_index_is_stable_when_bom_field_is_absent(self):
        # The BOM token is omitted for encodings with no BOM concept; the
        # encoding must not shift position as a result.
        name = build_filename(
            "DOC000028", ["10", "Latin"], "English", "iso-8859-1", None, "LF")
        stem = name.rsplit(".", 1)[0]
        self.assertEqual(stem.split("_")[ENCODING_TOKEN_INDEX], "iso-8859-1")

    def test_underscore_codec_does_not_shift_later_fields(self):
        name = build_filename(
            "DOC000100", ["15", "CJK"], "Japanese", "shift_jis", None, "LF")
        stem = name.rsplit(".", 1)[0]
        tokens = stem.split("_")
        self.assertEqual(tokens[ENCODING_TOKEN_INDEX], "shift-jis")
        self.assertEqual(tokens[-1], "LF")


class FilenameContractTests(unittest.TestCase):
    def test_accepts_well_formed_names(self):
        for name, encoding in [
            ("DOC000123_15_CJK_Japanese_utf-16LE_BOM_CRLF.txt", "utf-16LE"),
            ("DOC000028_10_Latin_English_iso-8859-1_LF.txt", "iso-8859-1"),
            ("DOC000100_15_CJK_Japanese_shift-jis_LF.txt", "shift_jis"),
        ]:
            with self.subTest(name=name):
                assert_filename_contract(name, encoding)

    def test_rejects_the_v2_line_ending_fixtures(self):
        # Exactly the two files v2.0 shipped. Four tokens, so index 4 is
        # unreachable and a consumer parsing the encoding throws.
        for name in (
            "NoNewlineAtAll_UTF8_NoBOM_None.txt",
            "MixedLineEndingsWithinOneFile_UTF8_NoBOM_Mixed.txt",
        ):
            with self.subTest(name=name):
                with self.assertRaises(FilenameContractError):
                    assert_filename_contract(name, "utf-8")

    def test_rejects_wrong_encoding_token(self):
        with self.assertRaises(FilenameContractError):
            assert_filename_contract(
                "DOC000001_10_Latin_English_utf-8_LF.txt", "iso-8859-1")

    def test_rejects_the_v2_label_spelling(self):
        # v2.0 wrote "UTF8" in these filenames while the manifest said
        # "utf-8"; a consumer trusting the filename got a label that does
        # not match the manifest.
        with self.assertRaises(FilenameContractError):
            assert_filename_contract(
                "DOC900001_20_LineEndingEdge_NoNewline_UTF8_NoBOM_None.txt", "utf-8")


if __name__ == "__main__":
    unittest.main()
