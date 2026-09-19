"""Identify Latin-script lyrics that should remain plain text."""
import unicodedata


def is_punctuation(text):
    return bool(text.strip()) and all(
        c.isspace() or unicodedata.category(c)[0] in ("P", "S") for c in text)


def is_plain_text(text):
    return is_latin_text(text) or is_punctuation(text)


def is_latin_text(text):
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all("LATIN" in unicodedata.name(c, "") for c in letters)
