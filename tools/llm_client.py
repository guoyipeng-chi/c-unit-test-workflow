#!/usr/bin/env python3
"""
LLM Client (vLLM + Ollama fallback)
优先使用vLLM；当vLLM不可用时可自动回退到Ollama
"""

import requests
import json
import os
from typing import Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMClient:
    """统一LLM客户端：vLLM优先，支持自动回退Ollama"""
    
    def __init__(self, api_base: Optional[str] = None, 
                 model: str = "qwen-coder", 
                 api_key: str = "dummy"):
        """
        初始化vLLM客户端
        
        优先级: 环境变量 > 参数 > 默认值
        
        Args:
            api_base: vLLM服务的API地址
                环境变量: VLLM_API_BASE
                默认: http://localhost:8000
            model: 模型名称
                环境变量: VLLM_MODEL
                默认: qwen-coder
            api_key: API密钥
                环境变量: VLLM_API_KEY
                默认: dummy
        
        示例:
            # 使用环境变量
            export VLLM_API_BASE=http://192.168.1.100:8000
            client = VLLMClient()
            
            # 直接指定
            client = VLLMClient(api_base="http://my-server:8000")
        """
        # 优先级: 环境变量 > 参数 > 默认值
        self.api_base = (os.getenv('VLLM_API_BASE') or 
                        api_base or 
                        "http://localhost:8000").rstrip('/')
        self.model = os.getenv('VLLM_MODEL') or model
        self.api_key = os.getenv('VLLM_API_KEY') or api_key
        self.timeout = int(os.getenv('VLLM_TIMEOUT', '120'))

        # Ollama配置
        self.ollama_api_base = (os.getenv('OLLAMA_API_BASE') or "http://localhost:11434").rstrip('/')
        self.ollama_model = os.getenv('OLLAMA_MODEL') or "deepseek-r1:7b"
        self.ollama_timeout = int(os.getenv('OLLAMA_TIMEOUT', '900'))
        self.ollama_max_tokens = int(os.getenv('OLLAMA_MAX_TOKENS', '2048'))

        # 后端策略: auto / vllm / ollama
        self.backend_preference = (os.getenv('LLM_BACKEND') or "auto").strip().lower()
        self.allow_ollama_fallback = (os.getenv('VLLM_FALLBACK_TO_OLLAMA', 'true').strip().lower()
                          in ('1', 'true', 'yes', 'on'))

        self.active_backend = None
        self.active_api_base = None
        self.active_model = None
        
        # 检查连接
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """检查连接并选择可用后端"""
        # 强制使用Ollama
        if self.backend_preference == 'ollama':
            if self._check_ollama_connection():
                self.active_backend = 'ollama'
                self.active_api_base = self.ollama_api_base
                self.active_model = self.ollama_model
                logger.info(f"✓ Connected to Ollama at {self.active_api_base} (model={self.active_model})")
                return True
            logger.warning(f"✗ Cannot connect to Ollama: {self.ollama_api_base}")
            return False

        # 强制使用vLLM
        if self.backend_preference == 'vllm':
            if self._check_vllm_connection():
                self.active_backend = 'vllm'
                self.active_api_base = self.api_base
                self.active_model = self.model
                logger.info(f"✓ Connected to vLLM service at {self.active_api_base} (model={self.active_model})")
                return True
            logger.warning(f"✗ Cannot connect to vLLM: {self.api_base}")
            return False

        # auto: 优先vLLM，再回退Ollama
        if self._check_vllm_connection():
            self.active_backend = 'vllm'
            self.active_api_base = self.api_base
            self.active_model = self.model
            logger.info(f"✓ Connected to vLLM service at {self.active_api_base} (model={self.active_model})")
            return True

        if self.allow_ollama_fallback and self._check_ollama_connection():
            self.active_backend = 'ollama'
            self.active_api_base = self.ollama_api_base
            self.active_model = self.ollama_model
            logger.info(f"✓ vLLM unavailable, fallback to Ollama at {self.active_api_base} (model={self.active_model})")
            return True

        logger.warning("✗ No available LLM backend (vLLM/Ollama)")
        return False

    def _check_vllm_connection(self) -> bool:
        """检查vLLM连接"""
        try:
            response = requests.get(
                f"{self.api_base}/v1/models",
                timeout=5,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.warning(f"vLLM connection check failed: {e}")
            return False

    def _check_ollama_connection(self) -> bool:
        """检查Ollama连接"""
        try:
            response = requests.get(
                f"{self.ollama_api_base}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama connection check failed: {e}")
            return False

    def _generate_vllm(self, prompt: str, temperature: float, max_tokens: int, top_p: float) -> str:
        """调用vLLM chat/completions"""
        url = f"{self.api_base}/v1/chat/completions"

        messages = [{"role": "user", "content": prompt}]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"vLLM API error: {response.status_code} - {response.text}")

        result = response.json()
        if result.get("choices") and len(result["choices"]) > 0:
            return result["choices"][0]["message"].get("content", "")
        return ""

    def _generate_ollama(self, prompt: str, temperature: float, max_tokens: int, top_p: float) -> str:
        """调用Ollama generate接口"""
        effective_max_tokens = min(max_tokens, self.ollama_max_tokens)
        url = f"{self.ollama_api_base}/api/generate"
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": effective_max_tokens,
            }
        }

        response = requests.post(
            url,
            json=payload,
            timeout=self.ollama_timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Ollama API error: {response.status_code} - {response.text}")

        result = response.json()
        return result.get("response", "")
    
    def generate(self, prompt: str, 
                temperature: float = 0.7, 
                max_tokens: int = 4096,
                top_p: float = 0.95) -> str:
        """
        调用vLLM生成文本（使用Chat API生成独立的代码片段）
        
        使用 /v1/chat/completions 而不是 /v1/completions
        这样生成的是独立的代码片段，而不是文本续写
        
        Args:
            prompt: 输入提示
            temperature: 温度参数 (0-2, 默认0.7)
            max_tokens: 最大生成token数 (默认4096)
            top_p: nucleus采样参数 (默认0.95)
            
        Returns:
            生成的文本
        """
        try:
            # 初次未选中后端时尝试选择
            if not self.active_backend:
                self._check_connection()

            # 优先走当前后端
            if self.active_backend == 'ollama':
                logger.info(f"Calling Ollama generate... (model={self.ollama_model}, max_tokens={max_tokens})")
                generated_text = self._generate_ollama(prompt, temperature, max_tokens, top_p)
                logger.info(f"✓ Generated {len(generated_text)} chars")
                return generated_text

            logger.info(f"Calling vLLM chat/completions... (model={self.model}, max_tokens={max_tokens})")
            generated_text = self._generate_vllm(prompt, temperature, max_tokens, top_p)
            logger.info(f"✓ Generated {len(generated_text)} chars")
            return generated_text

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
        except Exception as e:
            logger.error(f"Generation failed: {e}")

        # vLLM失败且允许回退时，尝试Ollama
        if self.allow_ollama_fallback and self.active_backend != 'ollama' and self._check_ollama_connection():
            try:
                logger.warning("vLLM generation failed, fallback to Ollama...")
                self.active_backend = 'ollama'
                self.active_api_base = self.ollama_api_base
                self.active_model = self.ollama_model
                generated_text = self._generate_ollama(prompt, temperature, max_tokens, top_p)
                logger.info(f"✓ Generated {len(generated_text)} chars via Ollama fallback")
                return generated_text
            except Exception as e:
                logger.error(f"Ollama fallback failed: {e}")

        return ""
    
    def chat_complete(self, messages: List[Dict[str, str]], 
                     temperature: float = 0.7,
                     max_tokens: int = 4096) -> str:
        """
        调用Chat API - 已被generate()方法使用
        
        Args:
            messages: 消息列表 [{'role': 'user', 'content': '...'}, ...]
            temperature: 温度参数
            max_tokens: 最大生成token数
            
        Returns:
            生成的响应
        """
        # 注意: generate()方法现在也使用此Chat API
        url = f"{self.api_base}/v1/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            if self.active_backend == 'ollama':
                prompt = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages])
                return self._generate_ollama(prompt, temperature, max_tokens, top_p=0.95)

            logger.info("Calling vLLM chat API...")
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"].get("content", "")
                    logger.info(f"✓ Generated response ({len(content)} chars)")
                    return content
            else:
                logger.error(f"API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Chat request failed: {e}")
        
        return ""


def create_client(api_base: Optional[str] = None,
                 model: Optional[str] = None) -> VLLMClient:
    """
    工厂函数：创建vLLM客户端
    
    优先级: 环境变量 > 参数 > 默认值
    
    Args:
        api_base: vLLM服务地址（可通过环境变量VLLM_API_BASE覆盖）
        model: 模型名称（可通过环境变量VLLM_MODEL覆盖）
        
    Returns:
        VLLMClient实例
    """
    return VLLMClient(api_base=api_base, model=model)


if __name__ == "__main__":
    # 测试
    client = VLLMClient()
    prompt = "Write a simple C function that validates a student name"
    response = client.generate(prompt, max_tokens=500)
    print(response)
