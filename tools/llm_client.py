#!/usr/bin/env python3
"""
LLM Client for vLLM Qwen3 Coder
使用OpenAI兼容的API调用远程vLLM服务的Qwen3 Coder
"""

import requests
import json
import os
from typing import Optional, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VLLMClient:
    """vLLM客户端，通过OpenAI API兼容接口调用Qwen3 Coder"""
    
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
        
        # 检查连接
        self._check_connection()
    
    def _check_connection(self) -> bool:
        """检查与vLLM服务的连接"""
        try:
            response = requests.get(
                f"{self.api_base}/v1/models",
                timeout=5,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            if response.status_code == 200:
                logger.info(f"✓ Connected to vLLM service at {self.api_base}")
                return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"✗ Cannot connect to vLLM: {e}")
            return False
    
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
        # 使用Chat API而不是completions API
        # completions API会进行文本续写
        # chat/completions API能更好地理解指令并生成独立的代码
        url = f"{self.api_base}/v1/chat/completions"
        
        # 构建消息格式（Chat API所需）
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
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
        
        try:
            logger.info(f"Calling vLLM chat/completions... (max_tokens={max_tokens})")
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    # Chat API返回的是message.content而不是text
                    generated_text = result["choices"][0]["message"].get("content", "")
                    logger.info(f"✓ Generated {len(generated_text)} chars")
                    return generated_text
            else:
                logger.error(f"API error: {response.status_code} - {response.text}")
                
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
        
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
