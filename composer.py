"""Offline input methods and text tools; no desktop dependencies."""
import unicodedata
from telex import Telex, TONES, VOWELS


class VNI(Telex):
    def feed(self, char):
        if len(char) != 1 or not char.isascii() or not char.isalnum():
            raise ValueError("VNI accepts one ASCII letter or digit")
        self.raw += char
        if char in "12345" and self._target() is not None:
            tone = TONES[dict(zip("12345", "sfrxj"))[char]]
            if self.tone == tone:
                self.tone = ""
                self.letters.append(char)
            else:
                self.tone = tone
        elif char == "0" and self.tone:
            self.tone = ""
        elif char == "9" and self.letters and self.letters[-1].lower() in "dđ":
            index = len(self.letters) - 1
            old = self.letters[index].lower()
            self._set(index, "đ" if old == "d" else "d")
            if old == "đ":
                self.letters.append(char)
        elif char in "678":
            self._shape(char)
        else:
            self.letters.append(char)
        return self.text

    def _shape(self, key):
        pairs = {"6": {"a": "â", "e": "ê", "o": "ô"}, "7": {"u": "ư", "o": "ơ"}, "8": {"a": "ă"}}[key]
        indices = [i for i, char in enumerate(self.letters) if char.lower() in VOWELS]
        if key == "7":
            for a, b in zip(indices, indices[1:]):
                pair = (self.letters[a] + self.letters[b]).lower()
                if b == a + 1 and pair in ("uo", "ưo", "uơ", "ươ"):
                    escaped = pair == "ươ"
                    self._set(a, "u" if escaped else "ư")
                    self._set(b, "o" if escaped else "ơ")
                    if escaped:
                        self.letters.append(key)
                    return
        if indices:
            index = indices[-1]
            current = self.letters[index].lower()
            reverse = {v: k for k, v in pairs.items()}
            if current in pairs:
                self._set(index, pairs[current])
                return
            if current in reverse:
                self._set(index, reverse[current])
        self.letters.append(key)


def create_composer(settings):
    return (VNI if settings["input_method"] == "vni" else Telex)(modern_tone=settings["modern_tone"])


def expanded_text(composer, settings):
    if settings["macros_enabled"]:
        return settings["macros"].get(composer.raw, composer.text)
    return composer.text


def accepts_key(char, settings):
    return bool(char and char.isascii() and (char.isalpha() or char.isdigit() and (settings["input_method"] == "vni" or settings["macros_enabled"])))


def feed_key(composer, char, settings):
    if char.isdigit() and settings["input_method"] == "telex":
        composer.raw += char
        composer.letters.append(char)
    else:
        composer.feed(char)


def is_word_boundary(char):
    return bool(char and (char in "\r\n\t" or char.isprintable() and not char.isalnum()))


def preview(text, settings):
    composer = create_composer(settings)
    result = []
    for char in text:
        if accepts_key(char, settings):
            if len(composer.raw) >= 128:
                result.append(composer.text)
                composer.clear()
            feed_key(composer, char, settings)
        else:
            result.extend((expanded_text(composer, settings) if is_word_boundary(char) else composer.text, char))
            composer.clear()
    return "".join(result) + composer.text


def convert_text(text, mode):
    if mode == "strip":
        return "".join(char for char in unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D")) if not unicodedata.combining(char))
    return {"upper": str.upper, "lower": str.lower, "title": str.title}[mode](text)
