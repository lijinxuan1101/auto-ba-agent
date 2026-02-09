"""
商业分析 Agent 使用示例
演示如何使用 BA Agent 进行数据分析
"""

from app import BAAgentApp

def example_basic_usage():
    """示例 1：基本使用流程"""
    print("=== 示例 1：基本使用流程 ===\n")
    
    # 1. 创建应用实例
    app = BAAgentApp()
    
    # 2. 加载 Excel 数据
    app.load_excel("data/sales_data.xlsx")
    
    # 3. 查看数据概览
    app.show_data_info()
    
    # 4. 执行分析
    app.analyze("统计 2026 年的总销售额")
    app.analyze("找出销量最高的前 5 个产品")
    app.analyze("分析不同地区的销售情况")
    
    # 5. 查看历史
    app.get_history()


def example_multi_table_analysis():
    """示例 2：跨表分析"""
    print("\n=== 示例 2：跨表分析 ===\n")
    
    app = BAAgentApp(session_id="multi_table_session")
    
    # 加载包含多个 Sheet 的 Excel
    app.load_excel("data/multi_sheet_data.xlsx")
    
    # 跨表关联分析
    app.analyze("结合订单表和产品表，计算每个产品的总销售额")
    app.analyze("找出购买金额最高的前 10 个客户")


def example_interactive_mode():
    """示例 3：交互式模式"""
    print("\n=== 示例 3：交互式模式 ===\n")
    
    app = BAAgentApp()
    
    # 加载数据
    excel_file = input("请输入 Excel 文件路径: ").strip()
    app.load_excel(excel_file)
    
    # 交互式分析
    print("\n开始交互式分析（输入 'quit' 退出）\n")
    
    while True:
        query = input("请输入分析问题: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("退出分析")
            break
        
        if not query:
            continue
        
        app.analyze(query)


if __name__ == "__main__":
    # 运行示例 1
    example_basic_usage()
    
    # 取消注释以运行其他示例
    # example_multi_table_analysis()
    # example_interactive_mode()
