"""Small, offline Telex composer. All output is NFC Unicode."""
import unicodedata as ud

TONES = {"s": "\u0301", "f": "\u0300", "r": "\u0309", "x": "\u0303", "j": "\u0323"}
VOWELS = "aăâeêioôơuưy"


def split_char(char):
    parts = ud.normalize("NFD", char)
    tone = next((x for x in parts if x in TONES.values()), "")
    return ud.normalize("NFC", "".join(x for x in parts if x not in TONES.values())), tone


class Telex:
    def __init__(self, modern_tone=False):
        self.modern_tone = modern_tone
        self.clear()

    def clear(self):
        self.letters = []
        self.tone = ""
        self.raw = ""

    def _target(self):
        indices = [i for i, c in enumerate(self.letters) if c.lower() in VOWELS]
        if len(indices) > 1:
            # The u in qu and i in gi are consonant glides when followed by a vowel.
            if indices[0] == 1 and "".join(self.letters[:2]).lower() in ("qu", "gi"):
                indices.pop(0)
        if not indices:
            return None
        marked = [i for i in indices if self.letters[i].lower() in "ăâêôơư"]
        if marked:
            return marked[-1]
        if len(indices) == 1:
            return indices[0]
        if len(indices) >= 3:
            return indices[-2]
        if self.modern_tone and "".join(self.letters[i].lower() for i in indices) in ("oa", "oe", "uy"):
            return indices[-1]
        # Traditional placement: hòa, khỏe, thủy; hoàng, tuyết, tuyệt.
        return indices[-1] if indices[-1] < len(self.letters) - 1 else indices[0]

    @property
    def text(self):
        letters = list(self.letters)
        target = self._target()
        if self.tone and target is not None:
            letters[target] = ud.normalize("NFC", letters[target] + self.tone)
        return "".join(letters)

    def _set(self, index, char):
        self.letters[index] = char.upper() if self.letters[index].isupper() else char

    def feed(self, char):
        if len(char) != 1 or not char.isascii() or not char.isalpha():
            raise ValueError("feed() accepts one ASCII letter")
        self.raw += char
        key = char.lower()
        if key in TONES and self._target() is not None:
            if self.tone == TONES[key]:
                self.tone = ""
                self.letters.append(char)  # ass -> as; repeated tone key escapes it.
            else:
                self.tone = TONES[key]
        elif key == "z" and self.tone:
            self.tone = ""
        elif key == "d" and self.letters and self.letters[-1].lower() in "dđ":
            if self.letters[-1].lower() == "d":
                self._set(len(self.letters) - 1, "đ")
            else:
                self._set(len(self.letters) - 1, "d")
                self.letters.append(char)
        elif key in "aeo" and self._circumflex(char):
            pass
        elif key == "w" and self._horn(char):
            pass
        else:
            self.letters.append(char)
        return self.text

    def _circumflex(self, char):
        key = char.lower()
        shaped = {"a": "â", "e": "ê", "o": "ô"}[key]
        # Allow modifiers at the end of the syllable: tieeng or tienge.
        for index in range(len(self.letters) - 1, -1, -1):
            current = self.letters[index].lower()
            if current in VOWELS:
                if current == key:
                    self._set(index, shaped)
                    return True
                if current == shaped:
                    self._set(index, key)
                    self.letters.append(char)
                    return True
                return False
        return False

    def _horn(self, char):
        indices = [i for i, c in enumerate(self.letters) if c.lower() in VOWELS]
        if not indices:
            return False
        last = indices[-1]
        # uo/ươ stay a pair even with a trailing consonant or an added i/u.
        for a, b in zip(indices, indices[1:]):
            pair = (self.letters[a] + self.letters[b]).lower()
            if b == a + 1 and pair in ("ua", "ưa") and not (a > 0 and self.letters[a - 1].lower() == "q"):
                self._set(a, "u" if pair == "ưa" else "ư")
                if pair == "ưa":
                    self.letters.append(char)
                return True
            if b == a + 1 and pair in ("uo", "uô", "ưo", "uơ", "ươ"):
                if pair == "ươ":
                    self._set(a, "u")
                    self._set(b, "o")
                    self.letters.append(char)
                else:
                    self._set(a, "ư")
                    self._set(b, "ơ")
                return True
        # A trailing i/y is a glide: oiw -> ơi, uiw -> ưi, ayw -> ăy.
        # Keep the same target on a repeated w so oiww escapes to oiw.
        if (len(indices) > 1 and self.letters[last].lower() in "iy"
                and indices[-2] == last - 1):
            last = indices[-2]
        current = self.letters[last].lower()
        replacements = {"a": "ă", "o": "ơ", "u": "ư"}
        reverse = {v: k for k, v in replacements.items()}
        if current in replacements:
            self._set(last, replacements[current])
            return True
        if current in reverse:
            self._set(last, reverse[current])
            self.letters.append(char)
            return True
        return False

    def backspace(self):
        remaining = self.text[:-1]
        self.clear()
        for char in remaining:
            base, tone = split_char(char)
            self.letters.append(base)
            if tone:
                self.tone = tone
        # Start a new literal baseline after editing existing composed text.
        self.raw = remaining
        return self.text


def compose(keys):
    composer = Telex()
    for char in keys:
        composer.feed(char)
    return composer.text
