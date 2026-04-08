"""翻译模块的提示词模板和工具函数。"""

from __future__ import annotations

from typing import Optional


class PromptTemplates:
    """翻译提示词模板库。
    
    针对不同场景提供预设模板，支持自定义修改。
    每个模板都包含：
    - 清晰的任务指令
    - 输入输出格式说明
    - 领域适配提示
    """
    
    # 基础翻译模板（通用）
    BASIC = """You are a professional translator. Translate the following text from {src_lang} to {tgt_lang}.

Requirements:
- Preserve the original meaning and tone
- Keep technical terms and proper nouns unchanged
- Maintain punctuation and formatting

Source language: {src_lang}
Target language: {tgt_lang}

Source text:
{text}

Translated text:"""

    # 会议记录翻译模板（带上下文保留）
    MEETING_NOTES = """You are a professional translator specializing in meeting minutes and action items. 
Translate the following meeting notes from {src_lang} to {tgt_lang}.

Requirements:
- Preserve technical terms, product names, and proper nouns exactly as they appear
- Maintain action items, deadlines, and decision points with high accuracy
- Keep the original structure and formatting
- Ensure consistency with standard terminology in business communication

Important entities to preserve:
- Action items (tasks assigned to people)
- Deadlines and time references
- Decision points and consensus items
- Technical specifications

Source language: {src_lang}
Target language: {tgt_lang}

Meeting notes:
{text}

Translated meeting notes:"""

    # 技术文档翻译模板
    TECHNICAL_DOCS = """You are a professional technical translator. Translate the following technical documentation 
from {src_lang} to {tgt_lang}.

Requirements:
- Preserve all technical terms, API names, and code references exactly
- Maintain code blocks and examples without translation
- Keep the original formatting and structure
- Ensure accuracy for instructions and warnings
- Preserve consistency with industry-standard terminology

Source language: {src_lang}
Target language: {tgt_lang}

Technical documentation:
{text}

Translated documentation:"""

    # 实时对话翻译模板（简洁、快速）
    REALTIME_CHAT = """Translate the following text from {src_lang} to {tgt_lang}. Be concise and direct.

{src_lang}: {text}
{tgt_lang}:"""

    # 结构化输出模板（返回 JSON）
    STRUCTURED_JSON = """You are a professional translator. Translate the following text from {src_lang} to {tgt_lang}.

Return the result in JSON format with the following structure:
{{
    "source_text": "<original text>",
    "translated_text": "<translated text>",
    "confidence": <0.0-1.0>,
    "notes": "<any translation notes>"
}}

Source language: {src_lang}
Target language: {tgt_lang}

Source text:
{text}

JSON Response:"""

    @classmethod
    def get_template(cls, name: str) -> str:
        """获取指定名称的模板。
        
        Args:
            name: 模板名称 ("basic", "meeting_notes", "technical_docs", "realtime_chat", "structured_json")
            
        Returns:
            模板字符串
            
        Raises:
            ValueError: 模板不存在
        """
        templates = {
            "basic": cls.BASIC,
            "meeting_notes": cls.MEETING_NOTES,
            "technical_docs": cls.TECHNICAL_DOCS,
            "realtime_chat": cls.REALTIME_CHAT,
            "structured_json": cls.STRUCTURED_JSON,
        }
        
        if name not in templates:
            raise ValueError(f"Unknown template: {name}. Available: {list(templates.keys())}")
        
        return templates[name]

    @classmethod
    def list_templates(cls) -> list[str]:
        """列出所有可用的模板名称。"""
        return [
            "basic",
            "meeting_notes",
            "technical_docs",
            "realtime_chat",
            "structured_json",
        ]


class LanguageNormalizer:
    """语言代码规范化工具。
    
    支持多种语言代码格式转换：
    - ISO 639-1: "en", "zh"
    - ISO 639-1 with region: "zh-CN", "zh-TW", "pt-BR"
    - Full name: "English", "Chinese"
    """
    
    # 映射表：(代码 -> 全名)
    CODE_TO_NAME = {
        # 主要语言
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese",
        "ko": "Korean",
        "de": "German",
        "fr": "French",
        "es": "Spanish",
        "pt": "Portuguese",
        "ru": "Russian",
        "it": "Italian",
        "nl": "Dutch",
        "ar": "Arabic",
        "hi": "Hindi",
        "tr": "Turkish",
        "pl": "Polish",
        "vi": "Vietnamese",
        "id": "Indonesian",
        "th": "Thai",
        
        # 带地区的代码
        "zh-cn": "Chinese (Simplified)",
        "zh-hans": "Chinese (Simplified)",
        "zh-tw": "Chinese (Traditional)",
        "zh-hant": "Chinese (Traditional)",
        "pt-br": "Portuguese (Brazilian)",
        "pt-pt": "Portuguese (European)",
        "en-us": "English (American)",
        "en-gb": "English (British)",
    }
    
    @classmethod
    def normalize(cls, lang_code: str) -> str:
        """规范化语言代码为标准英文名称。
        
        Args:
            lang_code: 语言代码（支持多种格式）
            
        Returns:
            标准化后的英文名称
            
        Examples:
            >>> normalize("en") -> "English"
            >>> normalize("zh-CN") -> "Chinese (Simplified)"
            >>> normalize("Chinese") -> "Chinese"
        """
        lang_lower = lang_code.lower().strip().replace("_", "-")
        
        # 直接查表
        if lang_lower in cls.CODE_TO_NAME:
            return cls.CODE_TO_NAME[lang_lower]
        
        # 如果是全名，直接返回
        if any(lang_lower == name.lower() for name in cls.CODE_TO_NAME.values()):
            return lang_code.capitalize()
        
        # 只取语言部分（忽略地区）
        base_lang = lang_lower.split("-")[0]
        if base_lang in cls.CODE_TO_NAME:
            return cls.CODE_TO_NAME[base_lang]
        
        # 默认返回大写形式
        return lang_code.capitalize()

    @classmethod
    def is_valid(cls, lang_code: str) -> bool:
        """检查语言代码是否有效。
        
        Args:
            lang_code: 语言代码
            
        Returns:
            是否为有效的语言代码
        """
        lang_lower = lang_code.lower().strip().replace("_", "-")
        base_lang = lang_lower.split("-")[0]
        return lang_lower in cls.CODE_TO_NAME or base_lang in cls.CODE_TO_NAME or lang_lower in [name.lower() for name in cls.CODE_TO_NAME.values()]


class GlossaryProcessor:
    """词汇表处理工具。
    
    支持高优先级的术语替换，用于保留特定领域术语。
    """
    
    def __init__(self, glossary: Optional[dict[str, str]] = None):
        """初始化词汇表处理器。
        
        Args:
            glossary: 词汇表字典 {源词 -> 目标词}
        """
        self.glossary = glossary or {}
    
    def apply(self, text: str, case_sensitive: bool = False) -> str:
        """应用词汇表进行替换。
        
        Args:
            text: 待处理文本
            case_sensitive: 是否区分大小写
            
        Returns:
            替换后的文本
        """
        result = text
        for src, tgt in self.glossary.items():
            if case_sensitive:
                result = result.replace(src, tgt)
            else:
                # 简单的不区分大小写替换（保留原始大小写）
                import re
                pattern = re.compile(re.escape(src), re.IGNORECASE)
                result = pattern.sub(tgt, result)
        return result
    
    def add_entry(self, src: str, tgt: str) -> None:
        """添加词汇表条目。
        
        Args:
            src: 源词
            tgt: 目标词
        """
        self.glossary[src] = tgt
    
    def remove_entry(self, src: str) -> None:
        """移除词汇表条目。
        
        Args:
            src: 源词
        """
        if src in self.glossary:
            del self.glossary[src]


__all__ = [
    "PromptTemplates",
    "LanguageNormalizer",
    "GlossaryProcessor",
]
