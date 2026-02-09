"""
语义对齐推理：生成 semantic_map
实现 PRD 3.2 动态语义对齐推理
"""

from typing import List, Dict, Any
from pydantic import BaseModel
import json

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI


class SemanticNode(BaseModel):
    """语义图的节点（表）"""
    table: str
    description: str


class SemanticEdge(BaseModel):
    """语义图的边（表间关联）"""
    from_col: str  # 格式: "table.column"
    to_col: str
    logic: str  # "JOIN", "LOOKUP", etc.
    confidence: float


class SemanticMap(BaseModel):
    """完整的语义关系图"""
    nodes: List[SemanticNode]
    edges: List[SemanticEdge]


class SemanticMapper:
    """语义对齐推理器：利用 LLM 推断表间关系"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.semantic_map: Optional[SemanticMap] = None
    
    def generate_semantic_map(self, profile_summary: str) -> SemanticMap:
        """
        基于数据 Profile 生成语义关系图。
        
        Args:
            profile_summary: 数据探测摘要文本
            
        Returns:
            SemanticMap 对象
        """
        system_prompt = """你是一个数据关系分析专家。你的任务是：

1. 分析多张表的列名、数据类型和样本值
2. 推断表之间可能存在的关联关系（JOIN 键）
3. 输出 JSON 格式的语义关系图

输出格式：
{
  "nodes": [
    {"table": "表名", "description": "表的业务含义"}
  ],
  "edges": [
    {"from_col": "表A.列X", "to_col": "表B.列Y", "logic": "JOIN", "confidence": 0.9}
  ]
}

注意：
- confidence 取值 0-1，表示关联的置信度
- 只输出可能的关联，不要编造
- 考虑列名相似度、数据类型匹配、样本值重叠度
"""
        
        user_prompt = f"""请分析以下数据表，推断它们之间的关联关系：

{profile_summary}

请输出 JSON 格式的语义关系图。"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        
        response = self.llm.invoke(messages)
        content = response.content
        
        # 提取 JSON（处理 markdown 代码块）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # 解析 JSON
        try:
            data = json.loads(content)
            semantic_map = SemanticMap(**data)
            self.semantic_map = semantic_map
            return semantic_map
        except Exception as e:
            raise ValueError(f"LLM 返回的 JSON 格式错误: {e}\n内容: {content}")
    
    def get_relevant_subgraph(
        self,
        intent: str,
        mentioned_tables: List[str],
    ) -> SemanticMap:
        """
        根据意图提取相关子图。
        
        Args:
            intent: 用户意图描述
            mentioned_tables: 用户提到的表名列表
            
        Returns:
            相关的子图
        """
        if not self.semantic_map:
            raise ValueError("尚未生成 semantic_map，请先调用 generate_semantic_map()")
        
        # 提取相关节点
        relevant_nodes = [
            node for node in self.semantic_map.nodes
            if any(table in node.table for table in mentioned_tables)
        ]
        
        # 提取相关边
        relevant_tables_set = {node.table for node in relevant_nodes}
        relevant_edges = [
            edge for edge in self.semantic_map.edges
            if (edge.from_col.split(".")[0] in relevant_tables_set
                and edge.to_col.split(".")[0] in relevant_tables_set)
        ]
        
        return SemanticMap(nodes=relevant_nodes, edges=relevant_edges)
    
    def to_dict(self) -> Dict[str, Any]:
        """将 semantic_map 转换为字典"""
        if not self.semantic_map:
            return {}
        return self.semantic_map.model_dump()
    
    def to_json(self) -> str:
        """将 semantic_map 转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
