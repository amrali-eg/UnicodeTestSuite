"""Encoding equivalence sets.

These guard the criterion, which is the part that is easy to get wrong.
An earlier implementation qualified an encoding by byte round-tripping -
decode, re-encode, compare bytes - which is satisfied by every
single-byte codec for every input, because iso-8859-1 maps all 256 byte
values and reverses exactly. That produced "UTF-8 Japanese is also valid
as iso-8859-1", which is mojibake presented as an alternative reading.

The correct test is character equality: an encoding is an equally valid
answer only when it decodes the bytes to the same text.
"""

import unittest

from generator.equivalence import compatible_encodings, format_also_valid_as


class CompatibleEncodingsTests(unittest.TestCase):
    def test_pure_ascii_is_valid_under_ascii_supersets(self):
        text = "id,name,value\n1,alpha,10\n"
        payload = text.encode("ascii")
        result = compatible_encodings(payload, "utf-8", text)
        # This is the case that made a correct detector look wrong: a
        # pure-ASCII file declared utf-8, where answering "ascii" is if
        # anything the more precise answer.
        self.assertIn("us-ascii", result)
        self.assertIn("iso-8859-1", result)
        self.assertIn("windows-1252", result)
        self.assertNotIn("utf-8", result)  # the declared encoding is excluded

    def test_ascii_and_utf8_agree_symmetrically(self):
        text = "plain ascii\n"
        payload = text.encode("ascii")
        self.assertIn("utf-8", compatible_encodings(payload, "us-ascii", text))
        self.assertIn("us-ascii", compatible_encodings(payload, "utf-8", text))

    def test_mojibake_is_not_an_equivalent_answer(self):
        # The regression this module exists for. iso-8859-1 decodes these
        # bytes without error and re-encodes them exactly, but the text it
        # produces is not the text they encode.
        text = "こんにちは、世界。\n"
        payload = text.encode("utf-8")
        result = compatible_encodings(payload, "utf-8", text)
        self.assertNotIn("iso-8859-1", result)
        self.assertNotIn("koi8-r", result)
        self.assertNotIn("windows-1251", result)

    def test_genuinely_equivalent_legacy_pair_is_reported(self):
        # KOI8-U is a KOI8-R superset differing only in Ukrainian letters,
        # so Russian text really does read identically in both.
        text = "Привет! Как дела?\n"
        payload = text.encode("koi8_r")
        self.assertIn("koi8-u", compatible_encodings(payload, "koi8-r", text))

    def test_distinct_cyrillic_encodings_are_not_equivalent(self):
        text = "Привет! Как дела?\n"
        payload = text.encode("koi8_r")
        # windows-1251 decodes these bytes happily, into different letters.
        self.assertNotIn("windows-1251", compatible_encodings(payload, "koi8-r", text))

    def test_empty_payload_yields_empty_set(self):
        self.assertEqual(compatible_encodings(b"", "utf-8", ""), ())


class FormatTests(unittest.TestCase):
    def test_semicolon_separated(self):
        self.assertEqual(format_also_valid_as(("a", "b")), "a;b")

    def test_empty_set_renders_empty(self):
        self.assertEqual(format_also_valid_as(()), "")


if __name__ == "__main__":
    unittest.main()
