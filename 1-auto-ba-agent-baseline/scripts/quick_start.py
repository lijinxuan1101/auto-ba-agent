"""
快速启动脚本
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.workflow import ExcelAnalysisWorkflow
from src.api_client import MeituanDeepSeekClient

DEFAULT_QUERY = "闪购新客本月环比上涨较大，请帮我分析近半年来趋势波动及规模变化的关系"
EXCEL_PATH = "files/1.1/渠道增长部2022-2026年预算目标to子欣.xlsx"
OUTPUT_DIR = Path("output")


def save_result(result: dict):
    """保存运行结果到output目录"""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = OUTPUT_DIR / f"result_{timestamp}.json"

    to_save = {
        "query": result.get("query", ""),
        "task_plan": result.get("task_plan", ""),
        "python_code": result.get("python_code", ""),
        "execution_result": result.get("execution_result", ""),
        "analysis": result.get("analysis", ""),
        "error": result.get("error", ""),
        "timestamp": timestamp
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)

    print(f"\n结果已保存: {filepath}")


def main():
    try:
        client = MeituanDeepSeekClient()
        workflow = ExcelAnalysisWorkflow(
            api_call_func=lambda p: client.chat(p)
        )
    except Exception as e:
        print(f"初始化失败: {e}")
        return

    print(f"查询: {DEFAULT_QUERY}")
    print(f"文件: {EXCEL_PATH}")
    print("正在分析...\n")

    result = workflow.run(query=DEFAULT_QUERY, excel_path=EXCEL_PATH)

    if result.get('error'):
        print(f"错误: {result['error']}\n")

    if result.get('analysis'):
        print(result['analysis'])
    else:
        print("未生成分析结果")

    # 保存结果
    save_result(result)


if __name__ == '__main__':
    main()
