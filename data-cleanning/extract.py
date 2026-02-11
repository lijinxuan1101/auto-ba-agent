"""
从 data/ 下所有 Excel 中提取【搜索词】列，合并保存到 CSV
"""

import pandas as pd
from pathlib import Path

data_dir = Path(__file__).parent / "data"
all_keywords = []

for f in data_dir.glob("*.xlsx"):
    print(f"读取: {f.name}")
    df = pd.read_excel(f)
    if "query_item" in df.columns:
        all_keywords.append(df[["query_item"]])
    else:
        print(f"  ⚠️ 未找到【搜索词】列，跳过")

if all_keywords:
    result = pd.concat(all_keywords, ignore_index=True).drop_duplicates()
    output = data_dir.parent / "query_item.csv"
    result.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"\n✅ 已保存: {output}  ({len(result)} 条)")
else:
    print("❌ 没有提取到任何搜索词")
