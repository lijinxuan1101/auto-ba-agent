"""
快速启动脚本
一键生成示例数据并运行 BA Agent
"""

import os
import sys
from pathlib import Path

# 1. 创建示例数据
print("=== 步骤 1：创建示例数据 ===\n")
from create_sample_data import create_sample_data
create_sample_data()

# 2. 检查环境变量
print("\n=== 步骤 2：检查环境变量 ===\n")
from dotenv import load_dotenv
load_dotenv()

aigc_app_id = os.getenv("AIGC_APP_ID")
if not aigc_app_id:
    print("❌ 未设置环境变量 AIGC_APP_ID")
    print("   请在 .env 文件中添加：")
    print("   AIGC_APP_ID=your_app_id")
    sys.exit(1)
else:
    print(f"✅ AIGC_APP_ID 已配置: {aigc_app_id[:10]}...")

# 3. 运行 BA Agent
print("\n=== 步骤 3：启动 BA Agent ===\n")
from app import BAAgentApp

app = BAAgentApp(session_id="quickstart_demo")

# 加载示例数据
app.load_excel("data/sample_sales_data.xlsx")

# 查看数据概览
print("\n" + "="*50)
app.show_data_info()
print("="*50 + "\n")

# 执行示例分析
print("=== 开始分析 ===\n")

queries = [
    "统计总共有多少订单？",
    "计算所有订单的总销售额（数量 × 单价）",
    "找出购买次数最多的客户",
]

for query in queries:
    app.analyze(query)
    print()

# 查看历史
print("=== 对话历史 ===")
app.get_history()

print("\n✅ 快速启动完成！")
print("   你可以修改 quick_start.py 中的 queries 列表来尝试其他分析。")
