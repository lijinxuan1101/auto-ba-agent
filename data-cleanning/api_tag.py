import pandas as pd
import requests
import json
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= 配置区域 (请修改这里) =================

# 1. 替换为你申请到的真实 AppId
API_APP_ID = "22014276729611534358" 

# 2. 输入输出文件路径（基于脚本所在目录，无论从哪里运行都能找到）
SCRIPT_DIR = Path(__file__).parent
INPUT_FILE = SCRIPT_DIR / "query_item.csv"
OUTPUT_FILE = SCRIPT_DIR / "tagged_result.xlsx"

# 3. 接口配置 (基于你提供的 curl)
API_URL = "https://aigc.sankuai.com/v1/openai/native/chat/completions"
MODEL_NAME = "DeepSeek-V3.2-Meituan"

# 4. 运行参数
BATCH_SIZE = 10       # 每次发给大模型处理几条数据 (建议 5-10)
MAX_WORKERS = 2       # 并发线程数（降低避免 429）
MAX_RETRIES = 5       # 遇到 429 限流时最多重试几次

# ================= 提示词定义 =================

SYSTEM_PROMPT = """
你是一个美团商业分析的数据标注专家。你的任务是判断每条搜索词属于以下 9 个商品品类中的哪些。

品类定义：
1. alcohol (酒类): 各类酒饮，如：白酒、红酒、啤酒、精酿、威士忌、清酒、鸡尾酒、果酒、黄酒等。
2. snack (休闲食品类): 零食、小吃、即食食品，如：坚果、薯片、饼干、巧克力、蜜饯、辣条、卤味、糕点、膨化食品等。
3. flower (鲜花类): 鲜花及相关服务，如：玫瑰、百合、花束、永生花、绿植、多肉、干花、花艺、开业花篮等。
4. beauty (美妆类): 护肤与彩妆产品，如：口红、面膜、防晒霜、粉底、眼影、精华液、洗面奶、香水、美甲等。
5. digital (数码家电类): 电子产品与家用电器，如：iPhone、耳机、充电宝、空调、洗衣机、扫地机器人、电脑、平板、相机等。
6. baby (母婴类): 母婴用品与服务，如：奶粉、纸尿裤、婴儿车、儿童玩具、孕妇装、辅食、早教、待产包等。
7. dairy (乳品类): 牛奶及乳制品，如：纯牛奶、酸奶、奶酪、鲜奶、脱脂奶、有机奶、乳酸菌饮料、羊奶等。
8. fresh (生鲜果蔬类): 新鲜食材、水果、蔬菜，如：三文鱼、牛排、大闸蟹、榴莲、车厘子、草莓、西兰花、土豆等。
9. general (日用百货类): 日常生活用品与服装百货，如：纸巾、洗衣液、牙刷、衣架、收纳盒、T恤、袜子、雨伞等。

判断规则：
- 每个品类只输出 1（属于）或 0（不属于）
- 一条搜索词可以同时属于多个品类
- 如果搜索词不属于以上任何品类，所有品类都填 0

输入格式：一个包含 "id" 和 "text" 的 JSON 列表。
输出格式：严格的 JSON 列表，每个元素包含 "id" 和 "tags"，tags 的值只能是 1 或 0。

示例输入：
[{"id": 0, "text": "精酿啤酒"}, {"id": 1, "text": "车厘子"}, {"id": 2, "text": "iPhone16"}]

示例输出：
[{"id": 0, "tags": {"alcohol": 1, "snack": 0, "flower": 0, "beauty": 0, "digital": 0, "baby": 0, "dairy": 0, "fresh": 0, "general": 0}}, {"id": 1, "tags": {"alcohol": 0, "snack": 0, "flower": 0, "beauty": 0, "digital": 0, "baby": 0, "dairy": 0, "fresh": 1, "general": 0}}, {"id": 2, "tags": {"alcohol": 0, "snack": 0, "flower": 0, "beauty": 0, "digital": 1, "baby": 0, "dairy": 0, "fresh": 0, "general": 0}}]
"""

# ================= 核心功能函数 =================

def call_deepseek_api(batch_data):
    """
    发送一个批次的数据给 DeepSeek，遇到 429 自动退避重试
    """
    headers = {
        "Authorization": f"Bearer {API_APP_ID}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(batch_data, ensure_ascii=False)}
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 4096,
        "chat_template_kwargs": {
            "thinking": False
        }
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
            
            # 429 限流：等待后重试
            if response.status_code == 429:
                wait = min(15 * attempt, 60)  # 第1次等15s, 第2次30s, 第3次45s, 最多60s
                print(f"⏳ 429 限流，第 {attempt}/{MAX_RETRIES} 次重试，等待 {wait}s ...")
                time.sleep(wait)
                continue
            
            # 其他非200错误：直接返回
            if response.status_code != 200:
                print(f"API Error {response.status_code}: {response.text}")
                return []
                
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                clean_content = content.replace("```json", "").replace("```", "").strip()
                return json.loads(clean_content)
            else:
                print(f"API 返回结构异常: {result}")
                return []
                
        except Exception as e:
            print(f"请求发生异常: {e}")
            return []
    
    print(f"❌ 重试 {MAX_RETRIES} 次仍失败，跳过本批次")
    return []

TAG_COLS = [
    'alcohol', 'snack', 'flower', 'beauty', 'digital',
    'baby', 'dairy', 'fresh', 'general',
]


def process_etl(preview=False, max_rows=None):
    """
    Args:
        preview:  True 时只跑第 1 个批次（10 条），打印详细结果供检查
        max_rows: 不为 None 时，只处理前 max_rows 条数据
    """
    # 1. 读取 CSV
    print(f"正在读取 {INPUT_FILE} ...")
    try:
        df = pd.read_csv(INPUT_FILE)
        text_column_name = df.columns[0]
        print(f"默认使用第一列 '{text_column_name}' 作为文本输入源")
        print(f"文件共 {len(df)} 条数据")
        if max_rows and max_rows < len(df):
            df = df.head(max_rows).copy()
            print(f"限量模式：只处理前 {max_rows} 条")
        print(f"本次处理 {len(df)} 条")
    except Exception as e:
        print(f"读取 CSV 失败: {e}")
        return

    # 2. 准备批次数据
    batches = []
    current_batch = []
    
    for index, row in df.iterrows():
        text_content = str(row[text_column_name])
        current_batch.append({"id": index, "text": text_content})
        
        if len(current_batch) >= BATCH_SIZE:
            batches.append(current_batch)
            current_batch = []
    
    if current_batch:
        batches.append(current_batch)

    # ===== 预览模式：只跑 1 个批次 =====
    if preview:
        print(f"\n{'='*50}")
        print(f"  预览模式：只处理第 1 批（{len(batches[0])} 条）")
        print(f"{'='*50}")
        
        batch = batches[0]
        print(f"\n发送的数据：")
        for item in batch:
            print(f"  [{item['id']}] {item['text']}")
        
        print(f"\n正在调用 API ...\n")
        result = call_deepseek_api(batch)
        
        if not result:
            print("❌ API 调用失败，请检查网络或 AppId")
            return
        
        print(f"✅ 返回 {len(result)} 条结果：\n")
        # 预览表格：直接用 TAG_COLS 做表头（9 列不长，无需缩写）
        header = f"{'搜索词':<30} | " + " | ".join(f"{col:>8}" for col in TAG_COLS)
        print(header)
        print("-" * len(header))
        for item in result:
            tags = item.get('tags', {})
            text = next((b['text'] for b in batch if b['id'] == item['id']), '?')
            vals = " | ".join(f"{tags.get(col, 0):>8}" for col in TAG_COLS)
            print(f"{text:<30} | {vals}")
        
        print(f"\n{'='*50}")
        print("预览完成。确认没问题后，运行全量模式：选择 2")
        print(f"{'='*50}")
        return

    # ===== 全量模式 =====
    print(f"拆分为 {len(batches)} 个批次，开始并发处理...")

    # 3. 并发执行 API 调用
    results_map = {}
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_batch = {executor.submit(call_deepseek_api, batch): batch for batch in batches}
        
        completed_count = 0
        for future in as_completed(future_to_batch):
            completed_count += 1
            batch_result = future.result()
            
            if batch_result:
                for item in batch_result:
                    if 'id' in item and 'tags' in item:
                        results_map[item['id']] = item['tags']
            
            if completed_count % 10 == 0 or completed_count == len(batches):
                print(f"进度: {completed_count}/{len(batches)} 批次完成 ({len(results_map)} 条已打标)")

    # 4. 合并结果
    print("正在合并标签数据...")
    
    for col in TAG_COLS:
        df[col] = 0

    success_count = 0
    for index in df.index:
        if index in results_map:
            tags = results_map[index]
            for col in TAG_COLS:
                df.at[index, col] = int(tags.get(col, 0))
            success_count += 1

    # 5. 保存结果
    try:
        df.to_excel(OUTPUT_FILE, index=False)
        print(f"\n========================================")
        print(f" 处理完成！成功打标 {success_count}/{len(df)} 条数据")
        print(f" 结果已保存至: {OUTPUT_FILE}")
        print(f"========================================")
    except Exception as e:
        print(f"保存 Excel 失败: {e}")


if __name__ == "__main__":
    print("\n请选择运行模式：")
    print("  1. 预览模式（只跑 1 批，看看效果）")
    print("  2. 全量模式（处理全部数据）")
    print("  3. 限量模式（只跑前 N 条）")
    choice = input("\n请输入 1 / 2 / 3: ").strip()
    
    if choice == "1":
        process_etl(preview=True)
    elif choice == "2":
        process_etl(preview=False)
    elif choice == "3":
        n = input("请输入要处理的条数（默认 2000）: ").strip()
        n = int(n) if n else 2000
        process_etl(preview=False, max_rows=n)
    else:
        print("无效输入，退出")