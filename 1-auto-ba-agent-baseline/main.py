#!/usr/bin/env python3
"""
Excel数据分析工作流 - 主入口
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.workflow import ExcelAnalysisWorkflow
from src.api_client import MeituanDeepSeekClient
from src.config import config
from src.utils import preview_excel, format_result, save_report, validate_excel_file


def main():
    """主函数"""
    
    print("\n" + "🚀 Excel数据分析工作流".center(80, "="))
    
    # 1. 验证配置
    try:
        config.validate()
        print(f"\n✅ 配置验证成功")
        print(f"   模型: {config.MEITUAN_MODEL}")
    except Exception as e:
        print(f"\n❌ 配置验证失败: {e}")
        print("\n请检查:")
        print("1. .env文件是否存在")
        print("2. MEITUAN_APP_ID是否已设置")
        return 1
    
    # 2. 获取Excel文件路径
    default_excel = "files/1.1/渠道增长部2022-2026年预算目标to子欣.xlsx"
    excel_path = input(f"\n📂 请输入Excel文件路径 (直接回车使用默认: {default_excel}): ").strip()
    
    if not excel_path:
        excel_path = default_excel
        print(f"   使用默认文件: {excel_path}")
    
    # 验证文件
    if not validate_excel_file(excel_path):
        return 1
    
    # 3. 是否预览数据
    preview = input("\n是否预览数据？(y/n, 默认n): ").strip().lower()
    if preview == 'y':
        preview_excel(excel_path)
    
    # 4. 获取查询
    query = input("\n📝 请输入你的分析需求: ").strip()
    
    if not query:
        print("❌ 未输入查询内容")
        return 1
    
    # 5. 初始化工作流
    try:
        client = MeituanDeepSeekClient()
        workflow = ExcelAnalysisWorkflow(
            api_call_func=lambda p: client.chat(p, stream=config.STREAM)
        )
        print("\n✅ 工作流初始化成功")
    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        return 1
    
    # 6. 执行分析
    print("\n" + "▶️ 开始执行工作流".center(80, "="))
    print("⏳ 正在分析中，请稍候...\n")
    
    try:
        result = workflow.run(query=query, excel_path=excel_path)
        
        # 7. 显示结果
        print(format_result(result))
        
        # 8. 保存报告
        if not result.get('error'):
            save = input("💾 是否保存分析报告？(y/n): ").strip().lower()
            if save == 'y':
                report_content = {
                    "查询": result['query'],
                    "分析目标": result['goal'],
                    "生成的代码": result['python_code'],
                    "执行结果": result['execution_result'],
                    "最终分析": result['analysis']
                }
                filepath = save_report(report_content)
                print(f"✅ 报告已保存到: {filepath}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 工作流执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
