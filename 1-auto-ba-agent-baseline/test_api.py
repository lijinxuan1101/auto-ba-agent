"""
测试API - 打印原始SSE数据
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
from src.config import config

app_id = config.MEITUAN_APP_ID
url = "https://aigc.sankuai.com/v1/openai/native/chat/completions"

headers = {
    'Authorization': f'Bearer {app_id}',
    'Content-Type': 'application/json'
}

payload = {
    'model': 'DeepSeek-V3.2-Meituan',
    'messages': [
        {'role': 'user', 'content': '给我说2个科学家的名字'}
    ],
    'stream': False,
    'chat_template_kwargs': {
        'thinking': True
    }
}

print("发送流式请求...\n")

with requests.post(url, json=payload, headers=headers, stream=True, timeout=120) as resp:
    print(f"状态码: {resp.status_code}\n")

    for i, line in enumerate(resp.iter_lines()):
        if not line:
            continue
        raw = line.decode('utf-8')
        print(f"[{i}] {raw}")

        if raw.strip() == 'data: [DONE]':
            break
