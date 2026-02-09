"""
LangGraph 对话流：意图识别 -> 规划 -> 代码生成 -> 验证
实现 PRD 3.3 闭环代码生成与验证
"""

from typing import TypedDict, Annotated, List, Dict, Any
from typing_extensions import TypedDict
import json
import traceback

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import pandas as pd

from data_profiler import DataProfiler
from semantic_mapper import SemanticMapper, SemanticMap


class AgentState(TypedDict):
    """Agent 状态"""
    # 输入
    query: str  # 用户问题
    
    # 数据相关
    profile_summary: str  # 数据探测摘要
    semantic_map: Dict[str, Any]  # 语义关系图
    tables: Dict[str, Any]  # 实际数据表（table_name -> DataFrame 的序列化表示）
    
    # 推理过程
    intent: str  # 意图识别结果
    plan: str  # 逻辑规划
    code: str  # 生成的代码
    execution_result: Any  # 代码执行结果
    error: str  # 错误信息
    
    # 控制
    retry_count: int  # 重试次数
    max_retries: int  # 最大重试次数
    
    # 输出
    answer: str  # 最终答案
    messages: List[Any]  # 对话历史


class BAAgent:
    """商业分析 Agent：基于 LangGraph 的闭环分析流程"""
    
    def __init__(
        self,
        llm: ChatOpenAI,
        data_profiler: DataProfiler,
        semantic_mapper: SemanticMapper,
        max_retries: int = 3,
    ):
        self.llm = llm
        self.data_profiler = data_profiler
        self.semantic_mapper = semantic_mapper
        self.max_retries = max_retries
        
        # 构建 LangGraph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """构建 LangGraph 对话流"""
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("intent_routing", self.intent_routing)
        workflow.add_node("logical_planning", self.logical_planning)
        workflow.add_node("code_generation", self.code_generation)
        workflow.add_node("execution_verification", self.execution_verification)
        workflow.add_node("format_answer", self.format_answer)
        
        # 定义流程
        workflow.set_entry_point("intent_routing")
        
        workflow.add_edge("intent_routing", "logical_planning")
        workflow.add_edge("logical_planning", "code_generation")
        workflow.add_edge("code_generation", "execution_verification")
        
        # 验证后的条件分支
        workflow.add_conditional_edges(
            "execution_verification",
            self.should_retry,
            {
                "retry": "logical_planning",  # 失败 -> 重新规划
                "success": "format_answer",   # 成功 -> 格式化答案
                "give_up": "format_answer",   # 超过重试次数 -> 返回错误
            }
        )
        
        workflow.add_edge("format_answer", END)
        
        return workflow.compile()
    
    # ==================== 节点函数 ====================
    
    def intent_routing(self, state: AgentState) -> AgentState:
        """步骤 1：意图解析与策略路由"""
        query = state["query"]
        profile_summary = state["profile_summary"]
        
        system_prompt = """你是一个商业分析意图识别专家。分析用户的查询，识别：

1. 分析类型：
   - 描述性分析（统计、汇总）
   - 诊断性分析（找原因、对比）
   - 关联性分析（跨表关联）

2. 涉及的表和字段

3. 需要的关联路径

输出 JSON 格式：
{
  "analysis_type": "描述性分析",
  "mentioned_tables": ["表A", "表B"],
  "key_fields": ["字段1", "字段2"],
  "description": "简要描述用户意图"
}
"""
        
        user_prompt = f"""数据概览：
{profile_summary}

用户问题：{query}

请分析用户意图。"""
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        
        try:
            intent_data = json.loads(content)
            state["intent"] = json.dumps(intent_data, ensure_ascii=False)
        except:
            state["intent"] = content
        
        return state
    
    def logical_planning(self, state: AgentState) -> AgentState:
        """步骤 2：逻辑路径规划"""
        query = state["query"]
        intent = state["intent"]
        semantic_map_str = json.dumps(state["semantic_map"], ensure_ascii=False, indent=2)
        
        system_prompt = """你是一个数据分析逻辑规划专家。基于用户意图和语义关系图，规划分析步骤。

输出格式（伪代码）：
Plan:
1. 过滤表 A 的条件
2. 关联表 B (使用 A.col_x = B.col_y)
3. 计算聚合指标
4. 排序/筛选结果

注意：
- 优先使用 left join 保留主表数据
- 明确 join 键
- 避免不必要的表关联
"""
        
        user_prompt = f"""用户意图：
{intent}

语义关系图：
{semantic_map_str}

用户问题：{query}

请输出逻辑规划。"""
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        state["plan"] = response.content
        return state
    
    def code_generation(self, state: AgentState) -> AgentState:
        """步骤 3：代码生成"""
        plan = state["plan"]
        profile_summary = state["profile_summary"]
        
        system_prompt = """你是一个 Python/Pandas 代码生成专家。基于逻辑规划生成可执行代码。

要求：
1. 使用 pandas 进行数据处理
2. 表已加载为 DataFrame，变量名为 `tables['表名']`
3. 优先使用 pd.merge(how='left')
4. 最终结果赋值给 `result` 变量
5. 只输出 Python 代码，不要解释

示例：
```python
# 获取表
df_orders = tables['orders']
df_products = tables['products']

# 过滤 2026 年数据
df_2026 = df_orders[df_orders['year'] == 2026]

# 关联产品表
df_merged = pd.merge(df_2026, df_products, left_on='product_id', right_on='id', how='left')

# 计算销售额
df_merged['total_sales'] = df_merged['quantity'] * df_merged['price']

# 汇总
result = df_merged['total_sales'].sum()
```
"""
        
        user_prompt = f"""数据概览：
{profile_summary}

逻辑规划：
{plan}

请生成 Python 代码。"""
        
        response = self.llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        
        content = response.content
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        state["code"] = content
        return state
    
    def execution_verification(self, state: AgentState) -> AgentState:
        """步骤 4：闭环验证与纠错"""
        code = state["code"]
        
        # 准备执行环境
        tables = {
            name: self.data_profiler.get_table(name)
            for name in self.data_profiler.tables.keys()
        }
        
        exec_globals = {
            "pd": pd,
            "tables": tables,
            "result": None,
        }
        
        try:
            # 执行代码
            exec(code, exec_globals)
            result = exec_globals.get("result")
            
            # 逻辑检查
            if result is None:
                state["error"] = "代码未生成 result 变量"
                state["execution_result"] = None
            elif isinstance(result, pd.DataFrame):
                # 检查是否产生笛卡尔积
                original_rows = sum(len(df) for df in tables.values())
                if len(result) > original_rows * 2:
                    state["error"] = f"可能产生了笛卡尔积：结果行数 {len(result)} 远大于原始行数 {original_rows}"
                    state["execution_result"] = None
                else:
                    state["execution_result"] = result.to_dict()
                    state["error"] = ""
            else:
                state["execution_result"] = str(result)
                state["error"] = ""
        
        except Exception as e:
            state["error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
            state["execution_result"] = None
        
        return state
    
    def format_answer(self, state: AgentState) -> AgentState:
        """格式化最终答案"""
        if state["error"]:
            state["answer"] = f"分析失败：{state['error']}"
        else:
            result = state["execution_result"]
            state["answer"] = f"分析结果：\n{result}"
        
        return state
    
    # ==================== 条件判断 ====================
    
    def should_retry(self, state: AgentState) -> str:
        """判断是否需要重试"""
        if not state["error"]:
            return "success"
        
        retry_count = state.get("retry_count", 0)
        if retry_count >= state.get("max_retries", self.max_retries):
            return "give_up"
        
        state["retry_count"] = retry_count + 1
        return "retry"
    
    # ==================== 对外接口 ====================
    
    def analyze(self, query: str) -> str:
        """
        执行商业分析。
        
        Args:
            query: 用户问题
            
        Returns:
            分析结果
        """
        # 准备初始状态
        initial_state: AgentState = {
            "query": query,
            "profile_summary": self.data_profiler.get_profile_summary(),
            "semantic_map": self.semantic_mapper.to_dict(),
            "tables": {},
            "intent": "",
            "plan": "",
            "code": "",
            "execution_result": None,
            "error": "",
            "retry_count": 0,
            "max_retries": self.max_retries,
            "answer": "",
            "messages": [],
        }
        
        # 执行 Graph
        final_state = self.graph.invoke(initial_state)
        
        return final_state["answer"]
