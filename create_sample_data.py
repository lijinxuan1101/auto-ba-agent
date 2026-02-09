"""
创建示例数据文件
生成一个包含多 Sheet 的 Excel 文件用于测试
"""

import pandas as pd
from pathlib import Path

def create_sample_data():
    """创建示例数据"""
    
    # 订单表
    orders_data = {
        "订单ID": [1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008],
        "客户ID": ["C001", "C002", "C001", "C003", "C002", "C004", "C001", "C003"],
        "产品ID": ["P001", "P002", "P001", "P003", "P002", "P001", "P003", "P002"],
        "数量": [5, 3, 10, 2, 7, 4, 6, 8],
        "日期": ["2026-01-15", "2026-01-18", "2026-02-03", "2026-02-10", 
                 "2026-03-05", "2026-03-12", "2026-03-20", "2026-04-01"],
        "地区": ["北京", "上海", "北京", "广州", "上海", "深圳", "北京", "广州"],
    }
    df_orders = pd.DataFrame(orders_data)
    
    # 产品表
    products_data = {
        "产品ID": ["P001", "P002", "P003"],
        "产品名称": ["笔记本电脑", "无线鼠标", "机械键盘"],
        "单价": [5999, 199, 599],
        "类别": ["电脑", "配件", "配件"],
    }
    df_products = pd.DataFrame(products_data)
    
    # 客户表
    customers_data = {
        "客户ID": ["C001", "C002", "C003", "C004"],
        "客户名称": ["张三", "李四", "王五", "赵六"],
        "会员等级": ["金牌", "银牌", "金牌", "普通"],
        "注册日期": ["2025-01-01", "2025-03-15", "2025-06-20", "2025-12-01"],
    }
    df_customers = pd.DataFrame(customers_data)
    
    # 保存到 Excel（多 Sheet）
    output_path = Path("data/sample_sales_data.xlsx")
    output_path.parent.mkdir(exist_ok=True)
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_orders.to_excel(writer, sheet_name='订单', index=False)
        df_products.to_excel(writer, sheet_name='产品', index=False)
        df_customers.to_excel(writer, sheet_name='客户', index=False)
    
    print(f"✅ 示例数据已创建: {output_path}")
    print(f"   - 订单表: {len(df_orders)} 行")
    print(f"   - 产品表: {len(df_products)} 行")
    print(f"   - 客户表: {len(df_customers)} 行")

if __name__ == "__main__":
    create_sample_data()
