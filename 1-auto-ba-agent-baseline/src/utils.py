"""
工具函数模块
"""

import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime


def preview_excel(file_path: str, max_rows: int = 5) -> Optional[pd.DataFrame]:
    """
    预览Excel文件
    
    Args:
        file_path: Excel文件路径
        max_rows: 预览的最大行数
        
    Returns:
        DataFrame或None
    """
    try:
        df = pd.read_excel(file_path)
        print("\n" + "="*80)
        print("📋 Excel文件预览".center(80))
        print("="*80)
        print(f"\n文件名: {Path(file_path).name}")
        print(f"数据维度: {df.shape[0]} 行 × {df.shape[1]} 列")
        print(f"\n列名:")
        for i, col in enumerate(df.columns, 1):
            print(f"  {i}. {col}")
        
        print(f"\n前{max_rows}行数据:")
        print(df.head(max_rows).to_string())
        print("\n" + "="*80 + "\n")
        return df
    except Exception as e:
        print(f"❌ 读取文件失败: {e}")
        return None


def save_report(content: dict, output_dir: str = "output") -> str:
    """
    保存分析报告
    
    Args:
        content: 报告内容字典
        output_dir: 输出目录
        
    Returns:
        保存的文件路径
    """
    from .config import config
    
    # 确保输出目录存在
    output_path = config.ensure_output_dir()
    
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_report_{timestamp}.txt"
    filepath = output_path / filename
    
    # 写入报告
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("Excel数据分析报告\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for key, value in content.items():
            f.write(f"{key}:\n{value}\n\n")
        
        f.write("=" * 80 + "\n")
    
    return str(filepath)


def format_result(result: dict) -> str:
    """
    格式化分析结果用于显示
    
    Args:
        result: 分析结果字典
        
    Returns:
        格式化后的字符串
    """
    output = []
    output.append("\n" + "="*80)
    output.append("📊 工作流执行结果".center(80))
    output.append("="*80)
    
    if result.get('error'):
        output.append(f"\n❌ 错误: {result['error']}")
    else:
        output.append("\n【1️⃣ 用户查询】")
        output.append(f"   {result.get('query', 'N/A')}")
        
        output.append("\n【2️⃣ 定义的目标】")
        output.append(result.get('goal', 'N/A'))
        
        output.append("\n【3️⃣ 生成的Python代码】")
        output.append("```python")
        output.append(result.get('python_code', 'N/A'))
        output.append("```")
        
        output.append("\n【4️⃣ 执行结果】")
        exec_result = result.get('execution_result', 'N/A')
        if len(exec_result) > 1000:
            output.append(exec_result[:1000] + "\n... (结果过长,已截断)")
        else:
            output.append(exec_result)
        
        output.append("\n【5️⃣ 最终分析】")
        output.append(result.get('analysis', 'N/A'))
        
        output.append("\n" + "✅ 工作流执行成功!".center(80, "="))
    
    output.append("\n" + "="*80 + "\n")
    
    return "\n".join(output)


def validate_excel_file(file_path: str) -> bool:
    """
    验证Excel文件是否存在且可读
    
    Args:
        file_path: Excel文件路径
        
    Returns:
        是否有效
    """
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ 文件不存在: {file_path}")
        return False
    
    if not path.suffix.lower() in ['.xlsx', '.xls']:
        print(f"❌ 不支持的文件格式: {path.suffix}")
        return False
    
    try:
        pd.read_excel(file_path, nrows=1)
        return True
    except Exception as e:
        print(f"❌ 文件无法读取: {e}")
        return False
