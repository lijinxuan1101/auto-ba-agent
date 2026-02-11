"""
美团DeepSeek API客户端
"""

import requests
from typing import Optional

try:
    from .config import config
except ImportError:
    from config import config


class MeituanDeepSeekClient:
    """美团DeepSeek API客户端"""

    def __init__(self, app_id: Optional[str] = None):
        self.app_id = app_id or config.MEITUAN_APP_ID
        self.api_url = "https://aigc.sankuai.com/v1/openai/native/chat/completions"
        self.model = "DeepSeek-V3.2-Meituan"

        if not self.app_id:
            raise ValueError("未设置MEITUAN_APP_ID，请在.env文件中设置")

    def chat(self, prompt: str, thinking: bool = False) -> str:
        """
        调用聊天API
        
        Args:
            prompt: 提示词
            thinking: 是否启用思考模式（需要结构化输出时建议关闭）
        """
        headers = {
            'Authorization': f'Bearer {self.app_id}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'stream': False,
            'max_tokens': 16384,
            'chat_template_kwargs': {
                'thinking': thinking
            }
        }

        response = requests.post(
            self.api_url,
            json=payload,
            headers=headers,
            timeout=300
        )
        response.raise_for_status()

        return response.json()['choices'][0]['message']['content']


def create_api_function() -> callable:
    client = MeituanDeepSeekClient()
    return lambda prompt: client.chat(prompt)
