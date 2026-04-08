"""基于 LLM 的本地推理翻译器实现（多语言通用方案）."""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import TYPE_CHECKING, AsyncIterator, Optional

from ...core.interface import TranslationResult, TranslatorInterface
from ...utils.errors import TranslationError

if TYPE_CHECKING:
    from .models.llm import LLMModel


class LLMTranslator(TranslatorInterface):
    """基于 LLM 的多语言翻译器。
    
    特点：
    - 使用单个小参数 LLM（3-7B）实现多语言互译
    - 支持提示词工程和结构化输出
    - 支持 LoRA 微调适配器加载
    - 易于定制和训练
    
    设计哲学：
    - 通过提示词引导实现语言对灵活转换
    - 保持模型轻量级，支持实时推理
    - 预留微调接口，支持后续领域适配
    """

    def __init__(
        self,
        model: LLMModel,
        prompt_template: Optional[str] = None,
        lora_adapter_path: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.3,
        dev_channel: Optional[dict] = None,
    ):
        """初始化 LLM 翻译器。
        
        Args:
            model: LLMModel 实例（已加载模型）
            prompt_template: 自定义提示词模板，使用 {src_lang}, {tgt_lang}, {text} 占位符
            lora_adapter_path: LoRA 适配器路径（用于微调）
            max_tokens: 生成的最大 token 数
            temperature: 生成温度（0.0-1.0，越低越确定）
            dev_channel: 开发调试通道配置
        """
        self.model: LLMModel = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.dev_channel = dev_channel or {}
        self.lora_adapter_path = lora_adapter_path
        
        if lora_adapter_path:
            self._load_lora_adapter(lora_adapter_path)
        
        self.prompt_template = prompt_template or self._default_prompt_template()

    def _default_prompt_template(self) -> str:
        """默认的多语言翻译提示词模板。
        
        关键设计：
        - 清晰指令：明确翻译目标
        - 结构化输出：便于解析
        - 任务示例：增强理解
        """
        return """You are a professional translator. Translate the following text from {src_lang} to {tgt_lang}.

Requirements:
- Preserve the original meaning and tone
- Keep technical terms and proper nouns unchanged
- Maintain punctuation and formatting

Source language: {src_lang}
Target language: {tgt_lang}

Source text:
{text}

Translated text:"""

    def _load_lora_adapter(self, adapter_path: str) -> None:
        """加载 LoRA 微调适配器。
        
        Args:
            adapter_path: LoRA 适配器文件路径
            
        Raises:
            FileNotFoundError: 适配器文件不存在
            TranslationError: 加载失败
        """
        try:
            self.model.load_lora_adapter(adapter_path)
        except Exception as e:
            raise TranslationError(f"Failed to load LoRA adapter from {adapter_path}: {e}")

    def _normalize_lang_code(self, lang: str) -> str:
        """规范化语言代码。
        
        支持多种格式：
        - "en" -> "English"
        - "zh" -> "Chinese (Simplified)" or "Chinese"
        - "zh-CN" -> "Chinese (Simplified)"
        - "ja" -> "Japanese"
        """
        lang_lower = lang.lower().strip()
        
        lang_map = {
            "en": "English",
            "zh": "Chinese",
            "zh-cn": "Chinese (Simplified)",
            "zh-tw": "Chinese (Traditional)",
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
        }
        
        return lang_map.get(lang_lower, lang.capitalize())

    def _build_prompt(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """构建翻译提示词。
        
        Args:
            text: 待翻译文本
            src_lang: 源语言代码
            tgt_lang: 目标语言代码
            
        Returns:
            格式化后的完整提示词
        """
        src_name = self._normalize_lang_code(src_lang)
        tgt_name = self._normalize_lang_code(tgt_lang)
        
        return self.prompt_template.format(
            src_lang=src_name,
            tgt_lang=tgt_name,
            text=text,
        )

    def _parse_translation_output(self, model_output: str) -> str:
        """从 LLM 输出中提取翻译结果。
        
        处理可能的输出格式：
        - 直接翻译文本
        - 带 JSON 结构的输出
        - 带前缀/后缀的输出
        
        Args:
            model_output: LLM 原始输出
            
        Returns:
            提取后的翻译文本
        """
        output = model_output.strip()
        
        # 尝试 JSON 解析（如果模型返回结构化输出）
        try:
            data = json.loads(output)
            if isinstance(data, dict):
                # 尝试常见的字段名
                for key in ["translation", "translated_text", "text", "result"]:
                    if key in data:
                        return str(data[key]).strip()
        except (json.JSONDecodeError, ValueError):
            pass
        
        # 清理常见前缀（例如 "Translated text:" 之后的内容）
        if "Translated text:" in output:
            output = output.split("Translated text:")[-1].strip()
        
        # 移除可能的 Markdown 代码块标记
        output = re.sub(r"^```.*?\n", "", output)
        output = re.sub(r"\n?```$", "", output)
        
        return output.strip()

    def translate(
        self,
        source_text: str,
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> TranslationResult:
        """同步翻译接口。
        
        Args:
            source_text: 待翻译文本
            src_lang: 源语言代码
            tgt_lang: 目标语言代码
            **kwargs: 其他参数（max_tokens, temperature 等）
            
        Returns:
            TranslationResult: 翻译结果
            
        Raises:
            TranslationError: 翻译失败
        """
        start_time = time.perf_counter()
        
        try:
            # 构建提示词
            prompt = self._build_prompt(source_text, src_lang, tgt_lang)
            
            # 调用模型推理
            max_tokens = kwargs.get("max_tokens", self.max_tokens)
            temperature = kwargs.get("temperature", self.temperature)
            
            model_output = self.model.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            # 解析输出
            translated_text = self._parse_translation_output(model_output)
            
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            
            return TranslationResult(
                text=translated_text,
                confidence=0.85,  # LLM 输出可信度通常较高
                is_final=True,
                latency_ms=latency_ms,
            )
            
        except Exception as e:
            raise TranslationError(f"LLM translation failed: {e}")

    async def translate_stream(
        self,
        source_chunks: AsyncIterator[str],
        src_lang: str,
        tgt_lang: str,
        **kwargs,
    ) -> AsyncIterator[TranslationResult]:
        """异步流式翻译接口。
        
        策略：
        - 缓存输入 chunks，直到句子完成
        - 完整句子后触发翻译
        - 支持字符级的增量输出
        
        Args:
            source_chunks: 异步迭代器，逐个产出文本片段
            src_lang: 源语言代码
            tgt_lang: 目标语言代码
            **kwargs: 其他参数
            
        Yields:
            TranslationResult: 翻译结果
        """
        buffer = ""
        sentence_delimiters = {"。", ".", "!", "?", "！", "？"}
        
        async for chunk in source_chunks:
            buffer += chunk
            
            # 检查是否有完整句子
            for delimiter in sentence_delimiters:
                if delimiter in buffer:
                    parts = buffer.split(delimiter, 1)
                    sentence = parts[0] + delimiter
                    buffer = parts[1] if len(parts) > 1 else ""
                    
                    # 异步翻译（避免阻塞）
                    result = await asyncio.get_event_loop().run_in_executor(
                        None, self.translate, sentence, src_lang, tgt_lang
                    )
                    yield result
        
        # 处理剩余的缓存
        if buffer.strip():
            result = await asyncio.get_event_loop().run_in_executor(
                None, self.translate, buffer, src_lang, tgt_lang
            )
            yield result

