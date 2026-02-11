"""
使用示例: 如何集成你的API并运行workflow
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import ExcelAnalysisWorkflow
import requests
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def call_llm_api(prompt: str) -> str:
    """
    调用美团DeepSeek API
    
    Args:
        prompt: 提示词
        
    Returns:
        LLM的响应文本
    """
    api_url = os.getenv('MEITUAN_API_URL', 'https://aigc.sankuai.com/v1/openai/native/chat/completions')
    app_id = os.getenv('MEITUAN_APP_ID')
    model = os.getenv('MEITUAN_MODEL', 'DeepSeek-V3.2-Meituan')
    
    if not app_id:
        raise ValueError("请在.env文件中设置MEITUAN_APP_ID")
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {app_id}'
    }
    
    # 根据环境变量决定是否使用流式响应
    use_stream = os.getenv('STREAM', 'false').lower() == 'true'
    enable_thinking = os.getenv('ENABLE_THINKING', 'true').lower() == 'true'
    
    payload = {
        'model': model,
        'messages': [
            {'role': 'user', 'content': prompt}
        ],
        'stream': use_stream,
        'temperature': float(os.getenv('TEMPERATURE', '0.7')),
        'max_tokens': int(os.getenv('MAX_TOKENS', '4000'))
    }
    
    # 添加thinking配置
    if enable_thinking:
        payload['chat_template_kwargs'] = {'thinking': True}
    
    try:
        if use_stream:
            # 流式响应处理
            return _handle_stream_response(api_url, headers, payload)
        else:
            # 非流式响应处理
            response = requests.post(api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"API调用失败: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应内容: {e.response.text}")
        raise


def _handle_stream_response(api_url: str, headers: dict, payload: dict) -> str:
    """
    处理流式响应
    
    Args:
        api_url: API地址
        headers: 请求头
        payload: 请求体
        
    Returns:
        完整的响应文本
    """
    import json
    
    full_response = ""
    
    with requests.post(api_url, json=payload, headers=headers, stream=True, timeout=60) as response:
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # 跳过空行和非data行
                if not line.startswith('data: '):
                    continue
                
                # 移除"data: "前缀
                data_str = line[6:]
                
                # 检查是否是结束标记
                if data_str.strip() == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    delta = data.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    
                    if content:
                        full_response += content
                        # 可选: 打印实时内容
                        # print(content, end='', flush=True)
                        
                except json.JSONDecodeError:
                    continue
    
    return full_response


def main():
    """主函数"""
    
    # 创建工作流实例,传入你的API调用函数
    workflow = ExcelAnalysisWorkflow(api_call_func=call_llm_api)
    
    # 运行工作流
    result = workflow.run(
        query="帮我分析这个销售数据表,计算每个产品类别的总销售额,并找出销售额最高的前3个类别",
        excel_path="data/sales_data.xlsx"  # 替换为你的Excel文件路径
    )
    
    # 打印各个阶段的结果
    print("\n" + "="*80)
    print("工作流执行结果")
    print("="*80)
    
    print("\n1. 用户查询:")
    print(result['query'])
    
    print("\n2. 定义的目标:")
    print(result['goal'])
    
    print("\n3. 生成的Python代码:")
    print(result['python_code'])
    
    print("\n4. 执行结果:")
    print(result['execution_result'][:500] + "..." if len(result['execution_result']) > 500 else result['execution_result'])
    
    print("\n5. 最终分析:")
    print(result['analysis'])
    
    if result.get('error'):
        print(f"\n⚠️ 错误: {result['error']}")
    else:
        print("\n✅ 工作流执行成功!")
    
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
