"""LLM 模型封装（基于 Hugging Face Transformers）."""

from __future__ import annotations

import os
from typing import Optional, Union

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    pipeline,
)

from ....utils.errors import TranslationError


class LLMModel:
    """通用 LLM 模型封装。
    
    功能：
    - 模型加载与卸载
    - 支持多种量化方式（8bit, 4bit, 无量化）
    - LoRA 适配器动态加载
    - 文本生成接口
    - 设备自动检测和管理
    """

    def __init__(
        self,
        model_id: str,
        device: str = "auto",
        quantization: Optional[str] = None,
        load_in_8bit: bool = False,
        load_in_4bit: bool = False,
        bnb_4bit_compute_dtype: str = "float16",
        bnb_4bit_quant_type: str = "nf4",
        bnb_4bit_use_double_quant: bool = True,
    ):
        """初始化 LLM 模型。
        
        Args:
            model_id: Hugging Face 模型 ID（如 "Qwen/Qwen2.5-3B-Instruct"）
            device: 设备选择 ("auto", "cpu", "cuda", "mps")
            quantization: 量化方式 ("4bit", "8bit", "int8" 或 None)
            load_in_8bit: 是否使用 8-bit 量化
            load_in_4bit: 是否使用 4-bit 量化
            bnb_4bit_compute_dtype: 4-bit 量化的计算类型
            bnb_4bit_quant_type: 4-bit 量化类型 ("nf4" 或 "fp4")
            bnb_4bit_use_double_quant: 是否对 4-bit 量化后的值再量化
        """
        self.model_id = model_id
        self.device = self._detect_device(device)
        self.quantization = quantization
        
        # 保存量化配置
        self.quantization_config = {
            "load_in_8bit": load_in_8bit or quantization in ("8bit", "int8"),
            "load_in_4bit": load_in_4bit or quantization == "4bit",
            "bnb_4bit_compute_dtype": self._get_torch_dtype(bnb_4bit_compute_dtype),
            "bnb_4bit_quant_type": bnb_4bit_quant_type,
            "bnb_4bit_use_double_quant": bnb_4bit_use_double_quant,
        }
        
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._lora_adapters = []  # 加载的 LoRA 适配器列表
        
        # 延迟加载
        self._load_model()

    @staticmethod
    def _detect_device(device: str) -> str:
        """自动检测可用设备。
        
        Args:
            device: 用户指定的设备
            
        Returns:
            确定的设备名称
        """
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device

    @staticmethod
    def _get_torch_dtype(dtype_str: str) -> torch.dtype:
        """将字符串转换为 torch.dtype。
        
        Args:
            dtype_str: 数据类型字符串 ("float16", "float32", "bfloat16")
            
        Returns:
            torch.dtype 对象
        """
        dtype_map = {
            "float16": torch.float16,
            "float32": torch.float32,
            "bfloat16": torch.bfloat16,
            "fp16": torch.float16,
            "fp32": torch.float32,
        }
        return dtype_map.get(dtype_str.lower(), torch.float16)

    def _load_model(self) -> None:
        """加载模型和分词器。
        
        Raises:
            TranslationError: 模型加载失败
        """
        try:
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id,
                trust_remote_code=True,
            )
            
            # 配置模型加载参数
            model_kwargs = {
                "device_map": self.device if self.device != "cpu" else None,
                "torch_dtype": self._get_torch_dtype("float16"),
                "trust_remote_code": True,
            }
            
            # 应用量化配置
            if self.quantization_config["load_in_4bit"]:
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_quant_type=self.quantization_config["bnb_4bit_quant_type"],
                    bnb_4bit_compute_dtype=self.quantization_config["bnb_4bit_compute_dtype"],
                    bnb_4bit_use_double_quant=self.quantization_config["bnb_4bit_use_double_quant"],
                )
                model_kwargs["quantization_config"] = bnb_config
                # 4-bit 量化时禁用设备映射
                model_kwargs.pop("device_map", None)
                model_kwargs["device_map"] = "auto"
                
            elif self.quantization_config["load_in_8bit"]:
                model_kwargs["load_in_8bit"] = True
                model_kwargs.pop("torch_dtype", None)
            
            if self.device == "cpu":
                model_kwargs.pop("device_map", None)
            
            # 加载模型
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                **model_kwargs,
            )
            
            # 创建 pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device if self.device != "cpu" else 0,
            )
            
        except Exception as e:
            raise TranslationError(f"Failed to load model {self.model_id}: {e}")

    def load_lora_adapter(self, adapter_path: str) -> None:
        """加载 LoRA 适配器。
        
        Args:
            adapter_path: LoRA 适配器目录路径
            
        Raises:
            FileNotFoundError: 适配器路径不存在
            TranslationError: 加载失败
        """
        if not os.path.exists(adapter_path):
            raise FileNotFoundError(f"LoRA adapter path not found: {adapter_path}")
        
        try:
            from peft import PeftModel
            
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            self._lora_adapters.append(adapter_path)
            
            # 重新创建 pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device if self.device != "cpu" else 0,
            )
            
        except ImportError:
            raise TranslationError("PEFT library not installed. Install it with: pip install peft")
        except Exception as e:
            raise TranslationError(f"Failed to load LoRA adapter from {adapter_path}: {e}")

    def unload_lora_adapter(self) -> None:
        """卸载 LoRA 适配器，恢复到基础模型。
        
        Raises:
            TranslationError: 模型没有加载 LoRA 适配器
        """
        if not self._lora_adapters:
            raise TranslationError("No LoRA adapter loaded")
        
        try:
            from peft import PeftModel
            
            self.model = self.model.base_model.model if hasattr(self.model, 'base_model') else self.model
            self._lora_adapters.clear()
            
            # 重新创建 pipeline
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device if self.device != "cpu" else 0,
            )
            
        except Exception as e:
            raise TranslationError(f"Failed to unload LoRA adapter: {e}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.3,
        top_p: float = 0.95,
        top_k: Optional[int] = None,
        **kwargs,
    ) -> str:
        """生成文本。
        
        Args:
            prompt: 输入提示词
            max_tokens: 生成的最大 token 数
            temperature: 温度参数（0.0-1.0）
            top_p: nucleus sampling 参数
            top_k: top-k 采样参数
            **kwargs: 其他参数传递给 pipeline
            
        Returns:
            生成的文本
            
        Raises:
            TranslationError: 生成失败
        """
        try:
            # 使用 pipeline 生成
            outputs = self.pipeline(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                do_sample=True if temperature > 0 else False,
                return_full_text=False,
                **kwargs,
            )
            
            generated_text = outputs[0]["generated_text"]
            return generated_text
            
        except Exception as e:
            raise TranslationError(f"Failed to generate text: {e}")

    def unload(self) -> None:
        """卸载模型并释放内存。"""
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        self._lora_adapters.clear()
        
        # 尝试清理 GPU 内存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def __del__(self):
        """析构函数，确保释放资源。"""
        self.unload()

    def __repr__(self) -> str:
        return f"LLMModel(model_id={self.model_id}, device={self.device}, quantization={self.quantization})"
