"""
测试工作流 - 使用模拟数据和模拟API
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow import ExcelAnalysisWorkflow
import pandas as pd
import os


def create_sample_excel():
    """创建一个示例Excel文件用于测试"""
    data = {
        '产品名称': ['产品A', '产品B', '产品C', '产品D', '产品E'],
        '类别': ['电子', '服装', '电子', '食品', '服装'],
        '销售额': [15000, 8000, 22000, 5000, 12000],
        '销售数量': [150, 200, 180, 100, 160],
        '月份': ['2024-01', '2024-01', '2024-02', '2024-02', '2024-03']
    }
    
    df = pd.DataFrame(data)
    
    # 创建data目录
    os.makedirs('data', exist_ok=True)
    
    # 保存Excel
    excel_path = 'data/sample_sales.xlsx'
    df.to_excel(excel_path, index=False)
    
    print(f"✅ 已创建示例Excel文件: {excel_path}")
    print(f"\n数据预览:")
    print(df)
    print()
    
    return excel_path


def mock_api_call(prompt: str) -> str:
    """
    模拟LLM API调用
    根据prompt的内容返回不同的模拟响应
    """
    print(f"\n{'='*60}")
    print(f"📝 收到提示词 (前200字符):")
    print(prompt[:200] + "..." if len(prompt) > 200 else prompt)
    print(f"{'='*60}\n")
    
    # 根据prompt内容判断当前是哪个步骤
    if "定义数据分析的目标" in prompt:
        # 步骤1: 定义目标
        response = """
分析目标:
1. 从Excel文件中读取销售数据
2. 按产品类别分组,计算每个类别的总销售额
3. 找出销售额最高的前3个产品类别
4. 返回类别名称和对应的总销售额
"""
        print("🎯 [步骤1] 返回目标定义")
        
    elif "生成完整的Python代码" in prompt:
        # 步骤2: 生成Python代码
        response = """
import pandas as pd

# 读取Excel文件
df = pd.read_excel(excel_path)

# 按类别分组并计算总销售额
category_sales = df.groupby('类别')['销售额'].sum().sort_values(ascending=False)

# 获取前3个类别
top_3_categories = category_sales.head(3)

# 格式化结果
result = top_3_categories
"""
        print("🐍 [步骤2] 返回Python分析代码")
        
    elif "对结果的详细解读" in prompt:
        # 步骤4: 最终分析
        response = """
📊 分析结果解读:

根据对销售数据的分析,我发现:

1. **销售额最高的前3个产品类别:**
   - 电子类: 总销售额37,000元,表现最佳
   - 服装类: 总销售额20,000元,排名第二
   - 食品类: 总销售额5,000元,排名第三

2. **关键洞察:**
   - 电子类产品占据主导地位,销售额几乎是服装类的两倍
   - 食品类销售额相对较低,可能需要加强营销推广
   - 电子和服装两个类别贡献了大部分销售额

3. **建议:**
   - 继续保持电子类产品的优势,可考虑扩大产品线
   - 提升服装类产品的营销力度,争取缩小与电子类的差距
   - 分析食品类销售不佳的原因,优化产品组合或定价策略
"""
        print("📈 [步骤4] 返回最终分析")
        
    else:
        response = "这是一个模拟响应"
    
    print(f"💬 模拟API响应 (前200字符):")
    print(response[:200] + "..." if len(response) > 200 else response)
    print()
    
    return response


def test_workflow():
    """测试完整工作流"""
    print("\n" + "🚀 开始测试LangGraph工作流".center(80, "="))
    
    # 1. 创建示例数据
    print("\n📁 步骤0: 准备测试数据")
    excel_path = create_sample_excel()
    
    # 2. 创建工作流实例
    print("\n⚙️ 初始化工作流")
    workflow = ExcelAnalysisWorkflow(api_call_func=mock_api_call)
    
    # 3. 运行工作流
    print("\n▶️ 运行工作流")
    result = workflow.run(
        query="帮我分析这个销售数据表,计算每个产品类别的总销售额,并找出销售额最高的前3个类别",
        excel_path=excel_path
    )
    
    # 4. 打印结果
    print("\n" + "📋 工作流执行结果".center(80, "="))
    
    print("\n1️⃣ 用户查询:")
    print(f"   {result['query']}")
    
    print("\n2️⃣ 定义的目标:")
    print(result['goal'])
    
    print("\n3️⃣ 生成的Python代码:")
    print("```python")
    print(result['python_code'])
    print("```")
    
    print("\n4️⃣ 执行结果:")
    print(result['execution_result'])
    
    print("\n5️⃣ 最终分析:")
    print(result['analysis'])
    
    if result.get('error'):
        print(f"\n❌ 错误: {result['error']}")
    else:
        print("\n" + "✅ 工作流执行成功!".center(80, "="))
    
    print("\n" + "="*80)
    
    return result


if __name__ == '__main__':
    test_workflow()
