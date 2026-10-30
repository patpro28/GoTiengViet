import unittest
import unicodedata
from telex import Telex, compose


class ComposerTests(unittest.TestCase):
    def test_words(self):
        examples = {
            "tieengs": "tiếng", "Vieetj": "Việt", "Tooi": "Tôi",
            "ddang": "đang", "ddawng": "đăng", "ddas": "đá",
            "DDOONGF": "ĐỒNG", "nguowif": "người", "nguwowif": "người",
            "dduowngf": "đường", "dduwowngf": "đường", "dduongwf": "đường",
            "truowngf": "trường", "truowcj": "trược", "ruowuj": "rượu",
            "muaw": "mưa", "muwaf": "mừa", "giuwax": "giữa",
            "quaws": "quắ", "quoocs": "quốc", "giaf": "già", "gif": "gì",
            "quys": "quý", "quyeenf": "quyền", "khuya": "khuya",
            "hoaf": "hòa", "khoer": "khỏe", "thuyr": "thủy",
            "hoangf": "hoàng", "tuyeetj": "tuyệt",
            "toans": "toán", "toasn": "toán", "asn": "án",
            "oans": "oán", "oafs": "óa", "asf": "à", "asz": "a",
            "aaa": "aa", "eee": "ee", "ooo": "oo", "ddd": "dd",
            "aww": "aw", "oww": "ow", "uww": "uw", "uoww": "uow",
            "ass": "as", "aff": "af", "arr": "ar", "axx": "ax", "ajj": "aj",
            "s": "s", "w": "w", "z": "z", "hello": "hello",
        }
        for raw, expected in examples.items():
            with self.subTest(raw=raw):
                self.assertEqual(compose(raw), expected)

    def test_every_vowel_tone_case(self):
        for raw, base in {"a":"a", "aw":"ă", "aa":"â", "e":"e", "ee":"ê", "i":"i", "o":"o", "oo":"ô", "ow":"ơ", "u":"u", "uw":"ư", "y":"y"}.items():
            for key, mark in {"s":"\u0301", "f":"\u0300", "r":"\u0309", "x":"\u0303", "j":"\u0323"}.items():
                for upper in (False, True):
                    typed = (raw + key).upper() if upper else raw + key
                    expected = unicodedata.normalize("NFC", (base.upper() if upper else base) + mark)
                    with self.subTest(typed=typed):
                        self.assertEqual(compose(typed), expected)

    def test_backspace_deletes_displayed_character(self):
        composer = Telex()
        for char in "tieengs":
            composer.feed(char)
        self.assertEqual(composer.backspace(), "tiến")
        self.assertEqual(composer.backspace(), "tiế")
        self.assertEqual(composer.backspace(), "ti")
        self.assertEqual(composer.backspace(), "t")
        self.assertEqual(composer.backspace(), "")
        self.assertEqual(composer.backspace(), "")

    def test_original_keys_and_reset(self):
        composer = Telex()
        for char in "Vieetj":
            composer.feed(char)
        self.assertEqual(composer.raw, "Vieetj")
        composer.clear()
        self.assertEqual(composer.text, "")
        self.assertEqual(composer.raw, "")

    def test_tone_relocates_as_syllable_grows(self):
        composer = Telex()
        for char in "hoas":
            composer.feed(char)
        self.assertEqual(composer.text, "hóa")
        self.assertEqual(composer.feed("n"), "hoán")


if __name__ == "__main__":
    unittest.main(verbosity=2)
