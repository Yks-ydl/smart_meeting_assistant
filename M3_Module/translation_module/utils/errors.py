"""自定义异常类。"""


class TranslationError(Exception):
    """翻译通用异常。"""


class TranslationTimeoutError(TranslationError):
    """翻译超时异常。"""


class UnsupportedLanguageError(TranslationError):
    """不支持的语言异常。"""
