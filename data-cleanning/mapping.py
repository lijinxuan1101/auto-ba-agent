"""
遍历 data/ 下所有 Excel，逐个与打标结果合并，输出到 mapping/ 文件夹
通过 query_item 列做左连接，保留原始数据的所有行，匹配上标签
"""

import pandas as pd
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DATA_DIR = SCRIPT_DIR / "data"
MAPPING_DIR = SCRIPT_DIR / "mapping"
MAPPING_DIR.mkdir(exist_ok=True)

TAGGED_FILE = SCRIPT_DIR / "tagged_result_2000.xlsx"
TAG_COLS = ['alcohol', 'snack', 'flower', 'beauty', 'digital', 'baby', 'dairy', 'fresh', 'general']

# ===== 1. 读取打标结果 =====
print("读取打标结果...")
df_tags = pd.read_excel(TAGGED_FILE)
df_tags_slim = df_tags[['query_item'] + TAG_COLS].drop_duplicates(subset='query_item')
print(f"  打标数据: {df_tags_slim.shape[0]} 条唯一搜索词\n")

# ===== 2. 遍历 data/ 下所有 Excel =====
files = [f for f in DATA_DIR.glob("*.xlsx") if not f.name.startswith("~$")]

if not files:
    print("❌ data/ 下没有找到 Excel 文件")
    exit()

print(f"找到 {len(files)} 个文件，开始逐个合并：\n")

for f in files:
    print(f"📄 {f.name}")
    print(f"   读取中（大文件可能较慢）...")
    
    try:
        df = pd.read_excel(f)
    except Exception as e:
        print(f"   ⚠️ 读取失败: {e}，跳过\n")
        continue
    
    print(f"   原始数据: {df.shape[0]} 行 × {df.shape[1]} 列")
    
    if 'query_item' not in df.columns:
        print(f"   ⚠️ 没有 query_item 列，跳过\n")
        continue
    
    # LEFT JOIN
    df_merged = df.merge(df_tags_slim, on='query_item', how='left')
    for col in TAG_COLS:
        df_merged[col] = df_merged[col].fillna(0).astype(int)
    
    # 统计匹配率
    matched = (df_merged[TAG_COLS].sum(axis=1) > 0).sum()
    print(f"   匹配标签: {matched}/{len(df_merged)} ({matched/len(df_merged)*100:.1f}%)")
    
    # 保存
    out_name = f.stem + "_tagged.xlsx"
    out_path = MAPPING_DIR / out_name
    df_merged.to_excel(out_path, index=False)
    print(f"   ✅ 已保存: {out_path}\n")

print("=" * 50)
print("全部完成！结果在 mapping/ 文件夹下")
