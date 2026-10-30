#!/usr/bin/python3
"""Try composing a line without installing or changing keyboard settings."""
import re
from telex import compose


def convert(line):
    return re.sub(r"[A-Za-z]+", lambda match: compose(match.group()), line)


if __name__ == "__main__":
    print("Bộ Gõ Việt — thử Telex. Ví dụ: Tooi ddang gox tieengs Vieetj")
    print("Nhập :q để thoát. Bản thử này chuyển đổi sau khi nhấn Enter.")
    while True:
        try:
            value = input("Telex> ")
        except (EOFError, KeyboardInterrupt):
            break
        if value == ":q":
            break
        print(convert(value))
