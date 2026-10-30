"""Plan edits only while the client confirms our exact text and caret position."""


def replacement_delta(before, after):
    common = 0
    for old, new in zip(before, after):
        if old != new:
            break
        common += 1
    return len(before) - common, after[common:]


class DirectBuffer:
    def __init__(self):
        self.reset()

    def reset(self):
        self.text = ""
        self.expected = None

    def begin(self, snapshot):
        if snapshot is None:
            return False
        text, cursor, anchor = snapshot
        if not isinstance(text, str) or not 0 <= cursor <= len(text) or cursor != anchor:
            return False
        self.text = ""
        self.expected = snapshot
        return True

    def matches(self, snapshot):
        if self.expected is None or snapshot != self.expected:
            return False
        text, cursor, anchor = snapshot
        return cursor == anchor and cursor >= len(self.text) and text[cursor - len(self.text):cursor] == self.text

    def replace(self, value, snapshot):
        if not self.matches(snapshot):
            return None
        text, cursor, _anchor = snapshot
        remove, insert = replacement_delta(self.text, value)
        start = cursor - len(self.text)
        self.expected = (text[:start] + value + text[cursor:], start + len(value), start + len(value))
        self.text = value
        return remove, insert
