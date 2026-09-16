"""Identify Latin-script lyrics that should remain plain text."""
import unicodedata


def is_latin_text(text):
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and all("LATIN" in unicodedata.name(c, "") for c in letters)
