"""
商业分析 Agent 主应用
基于 LangGraph + DeepSeek API 的自动化商业分析系统
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from data_profiler import DataProfiler
from semantic_mapper import SemanticMapper
from agent_graph import BAAgent
from persistence import PersistenceManager


# 加载环境变量
load_dotenv()


def create_llm() -> ChatOpenAI:
    """创建 LLM 实例（DeepSeek API）"""
    base_url = "https://aigc.sankuai.com/v1/openai/native"
    api_key = os.getenv("AIGC_APP_ID")
    
    if not api_key:
        raise ValueError("请设置环境变量 AIGC_APP_ID")
    
    return ChatOpenAI(
        model="DeepSeek-V3.2-Meituan",
        api_key=api_key,
        base_url=base_url,
        temperature=0,
        extra_body={
            "chat_template_kwargs": {
                "thinking": True,
            }
        }
    )


class BAAgentApp:
    """商业分析 Agent 应用"""
    
    def __init__(self, session_id: Optional[str] = None):
        """
        Args:
            session_id: 会话 ID，不传则自动生成
        """
        self.session_id = session_id or self._generate_session_id()
        
        # 初始化组件
        self.llm = create_llm()
        self.data_profiler = DataProfiler(sample_size=10)
        self.semantic_mapper = SemanticMapper(self.llm)
        self.agent = None  # 加载数据后初始化
        self.persistence = PersistenceManager()
        
        # 创建会话
        self.persistence.create_session(self.session_id)
        
        print(f"[系统] 会话 ID: {self.session_id}")
    
    @staticmethod
    def _generate_session_id() -> str:
        """生成会话 ID"""
        return f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def load_excel(self, file_path: str):
        """
        加载 Excel 文件并进行数据探测。
        
        Args:
            file_path: Excel 文件路径
        """
        print(f"\n[系统] 正在加载 Excel 文件: {file_path}")
        
        # 1. 加载数据
        tables = self.data_profiler.load_excel(file_path)
        print(f"[系统] 已加载 {len(tables)} 张表: {list(tables.keys())}")
        
        # 2. 数据探测
        print(f"[系统] 正在进行数据探测...")
        profiles = self.data_profiler.profile_all_tables()
        profile_summary = self.data_profiler.get_profile_summary()
        print(f"[系统] 数据探测完成")
        
        # 3. 生成语义关系图
        print(f"[系统] 正在生成语义关系图...")
        try:
            semantic_map = self.semantic_mapper.generate_semantic_map(profile_summary)
            print(f"[系统] 语义关系图生成完成: {len(semantic_map.nodes)} 个表, {len(semantic_map.edges)} 个关联")
        except Exception as e:
            print(f"[警告] 语义关系图生成失败: {e}")
            print(f"[系统] 将使用空的语义关系图继续")
        
        # 4. 初始化 Agent
        self.agent = BAAgent(
            llm=self.llm,
            data_profiler=self.data_profiler,
            semantic_mapper=self.semantic_mapper,
        )
        
        # 5. 保存到持久化存储
        self.persistence.save_data_source(
            session_id=self.session_id,
            file_path=file_path,
            profile_summary=profile_summary,
            semantic_map=self.semantic_mapper.to_json(),
        )
        
        print(f"[系统] 数据加载完成，可以开始分析\n")
    
    def analyze(self, query: str) -> str:
        """
        执行商业分析。
        
        Args:
            query: 用户问题
            
        Returns:
            分析结果
        """
        if not self.agent:
            return "[错误] 请先使用 load_excel() 加载数据"
        
        print(f"\n[用户] {query}")
        print(f"[系统] 正在分析...")
        
        try:
            # 执行分析
            answer = self.agent.analyze(query)
            
            # 保存对话记录
            self.persistence.save_conversation(
                session_id=self.session_id,
                query=query,
                result=answer,
            )
            
            print(f"[助手] {answer}\n")
            return answer
        
        except Exception as e:
            error_msg = f"分析失败: {e}"
            print(f"[错误] {error_msg}\n")
            
            # 保存错误记录
            self.persistence.save_conversation(
                session_id=self.session_id,
                query=query,
                error=str(e),
            )
            
            return error_msg
    
    def get_history(self, limit: int = 10):
        """获取对话历史"""
        history = self.persistence.get_conversation_history(self.session_id, limit)
        
        print(f"\n=== 对话历史 (最近 {len(history)} 条) ===")
        for record in reversed(history):
            print(f"\n[{record['timestamp']}]")
            print(f"用户: {record['query']}")
            if record['result']:
                print(f"助手: {record['result']}")
            if record['error']:
                print(f"错误: {record['error']}")
        print()
    
    def show_data_info(self):
        """显示当前加载的数据信息"""
        if not self.data_profiler.profiles:
            print("[系统] 尚未加载数据")
            return
        
        print(f"\n{self.data_profiler.get_profile_summary()}")


def main():
    """主函数：演示基本用法"""
    print("=== 商业分析 Agent ===\n")
    
    # 创建应用
    app = BAAgentApp()
    
    # 示例：加载 Excel 文件
    # 请替换为你的实际文件路径
    excel_file = "data/example.xlsx"
    
    if not Path(excel_file).exists():
        print(f"[提示] 请将 Excel 文件放到 {excel_file}")
        print(f"[提示] 或修改 app.py 中的 excel_file 路径")
        print(f"\n[系统] 演示模式：跳过数据加载\n")
        return
    
    # 加载数据
    app.load_excel(excel_file)
    
    # 查看数据概览
    app.show_data_info()
    
    # 执行分析（示例）
    app.analyze("统计 2026 年的总销售额")
    app.analyze("找出销量最高的前 5 个产品")
    
    # 查看历史
    app.get_history()


if __name__ == "__main__":
    main()
