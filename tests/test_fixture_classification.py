"""Binary-vs-text classification of the 13_Binary fixtures.

v3.0 labelled every fixture under 13_Binary as "Binary", including
`EmbeddedUtf8Bom.bin`, whose content is `before\\n<U+FEFF>middle\\nafter\\n`
— ordinary UTF-8 text that happens to carry a BOM somewhere other than
offset 0. A consumer benchmarking a detector against the corpus reported
it as a false positive: the detector answered utf-8, which is correct,
and the corpus called it wrong.

The classification rule is deliberately narrow. A fixture counts as text
only when it decodes as well-formed UTF-8 *and* contains no NUL byte.
UTF-8 well-formedness is self-validating, unlike a single-byte codec
which accepts any input at all; NUL is the universal binary signal, so a
detector calling a NUL-bearing file non-text is right even when every
other byte is printable ASCII.
"""

import unittest

from generator.binary import classify_fixture


class TextFixtureTests(unittest.TestCase):
    def test_well_formed_utf8_without_nul_is_text(self):
        data = "before\n﻿middle\nafter\n".encode("utf-8")
        label, bom, _ = classify_fixture(data)
        self.assertEqual(label, "utf-8")
        # The BOM is mid-file, so this is NOT a BOM-prefixed document.
        self.assertEqual(bom, "NoBOM")

    def test_leading_bom_is_reported_as_bom(self):
        label, bom, _ = classify_fixture("﻿".encode("utf-8"))
        self.assertEqual((label, bom), ("utf-8", "BOM"))

    def test_pure_ascii_also_lists_us_ascii(self):
        _, _, also = classify_fixture(b"A")
        self.assertIn("us-ascii", also)

    def test_non_ascii_text_does_not_claim_us_ascii(self):
        _, _, also = classify_fixture("café\n".encode("utf-8"))
        self.assertNotIn("us-ascii", also)


class BinaryFixtureTests(unittest.TestCase):
    def test_nul_means_binary_even_when_every_byte_is_ascii(self):
        empty_zip = b"PK\x05\x06" + bytes(18)
        self.assertEqual(classify_fixture(empty_zip)[0], "Binary")
        self.assertEqual(classify_fixture(bytes(8))[0], "Binary")

    def test_malformed_utf8_is_binary(self):
        self.assertEqual(classify_fixture(bytes([0xDE, 0xAD, 0xBE, 0xEF]))[0], "Binary")
        self.assertEqual(classify_fixture(b"\x89PNG\r\n\x1a\n")[0], "Binary")

    def test_all_byte_values_is_binary(self):
        self.assertEqual(classify_fixture(bytes(range(256)))[0], "Binary")

    def test_binary_carries_no_equivalence_set(self):
        label, bom, also = classify_fixture(bytes([0xFF, 0xFE, 0xFD]))
        self.assertEqual((label, bom, also), ("Binary", "N/A", ()))


class CorpusConsistencyTests(unittest.TestCase):
    """Nothing labelled Binary may be well-formed, NUL-free text."""

    def test_classification_is_self_consistent(self):
        samples = [
            b"",
            b"A",
            bytes(4),
            b"\x89PNG\r\n\x1a\n",
            "text\n".encode("utf-8"),
            "﻿bom\n".encode("utf-8"),
            bytes([0xC0, 0xAF]),
        ]
        for data in samples:
            with self.subTest(data=data):
                label, _, _ = classify_fixture(data)
                if label == "Binary":
                    continue
                self.assertNotIn(b"\x00", data)
                data.decode("utf-8")  # must not raise


if __name__ == "__main__":
    unittest.main()
