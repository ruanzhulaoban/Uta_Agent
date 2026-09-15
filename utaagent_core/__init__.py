"""Japanese lyric annotation with dictionary and compatible LLM enrichment."""
from .kana import to_romaji, katakana_to_hiragana, hiragana_to_katakana
from .mecab import MeCab, Token, find_mecab
from .jlpt import JlptTagger
from .annotator import Annotator
from .gloss_dict import GlossDict
from .llm import CompatibleClient, QwenClient, LLMError, DEFAULT_MODEL, DEFAULT_BASE_URL
from .glossifier import Glossifier
__version__ = "0.5.0"
__all__ = ["Annotator", "Glossifier", "GlossDict", "CompatibleClient", "QwenClient",
           "LLMError", "DEFAULT_MODEL", "DEFAULT_BASE_URL", "MeCab", "Token", "find_mecab",
           "JlptTagger", "to_romaji", "katakana_to_hiragana", "hiragana_to_katakana", "__version__"]
