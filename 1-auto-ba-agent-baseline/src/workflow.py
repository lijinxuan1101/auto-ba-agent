"""
基于LangGraph的数据分析工作流

信息流转:
  query → agent识别问题 → python agent(tool) → agent分析结果 → 结果
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import pandas as pd
import os
import re
import json


class WorkflowState(TypedDict):
    """工作流状态"""
    query: str                                    # 用户原始查询
    excel_path: str                               # Excel文件路径
    task_plan: str                                # agent识别问题后的分析计划
    python_code: str                              # python agent生成的代码
    execution_result: str                         # python执行结果
    analysis: str                                 # 最终分析结果
    error: str                                    # 错误信息
    messages: Annotated[list, add_messages]        # 消息历史


class ExcelAnalysisWorkflow:
    """Excel数据分析工作流"""

    def __init__(self, api_call_func=None):
        self.api_call_func = api_call_func or (lambda p: f"默认响应: {p}...")
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        构建工作流图:
          agent_identify → python_agent_tool → agent_analyze → END
        """
        workflow = StateGraph(WorkflowState)

        workflow.add_node("agent_identify", self.agent_identify)
        workflow.add_node("python_agent_tool", self.python_agent_tool)
        workflow.add_node("agent_analyze", self.agent_analyze)

        workflow.set_entry_point("agent_identify")
        workflow.add_edge("agent_identify", "python_agent_tool")
        workflow.add_edge("python_agent_tool", "agent_analyze")
        workflow.add_edge("agent_analyze", END)

        return workflow.compile()

    # ── 节点1: agent识别问题 ──────────────────────────────────────────

    def agent_identify(self, state: WorkflowState) -> WorkflowState:
        """
        agent识别问题:
        - 理解用户query
        - 读取Excel结构
        - 输出分析计划 + 要执行的Python代码
        """
        excel_path = state['excel_path']

        if not os.path.exists(excel_path):
            state['error'] = f'文件不存在: {excel_path}'
            return state

        # 读取Excel元信息
        try:
            df = pd.read_excel(excel_path)
            excel_info = (
                f"文件: {excel_path}\n"
                f"行数: {len(df)}, 列数: {len(df.columns)}\n"
                f"列名: {list(df.columns)}\n"
                f"数据类型:\n{df.dtypes.to_string()}\n"
                f"前5行:\n{df.head(5).to_string()}"
            )
        except Exception as e:
            state['error'] = f'读取Excel失败: {e}'
            return state

        prompt = f"""你是一个数据分析agent。用户的问题和数据信息如下:

用户问题: {state['query']}

Excel数据信息:
{excel_info}

请你完成两件事:
1. 分析思路: 简要说明你打算如何分析这个问题（2-3句话）
2. Python代码: 生成一段完整的Python代码来分析数据，这段代码的执行结果会交给下一个agent来进行分析，要求:
   - 用 pd.read_excel(excel_path) 读取数据，excel_path变量已提供
   - 将最终分析结果赋值给 result 变量（字符串格式，包含关键数据和结论）
   - 代码必须是能直接执行的纯Python，不能有语法错误

请严格按以下JSON格式输出，不要输出任何其他内容:
{{"plan": "你的分析思路", "code": "你的Python代码"}}

注意：你的分析思路要简洁"""

        try:
            response = self.api_call_func(prompt)

            # 从响应中提取JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                state['error'] = f'LLM返回格式异常: {response[:200]}'
                return state

            json_str = json_match.group()

            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError:
                # JSON被截断，尝试修复：补全未闭合的引号和括号
                json_str = json_str.rstrip()
                if not json_str.endswith('}'):
                    json_str += '"}' 
                try:
                    parsed = json.loads(json_str)
                except json.JSONDecodeError:
                    # 最后手段：用正则分别提取plan和code
                    plan_m = re.search(r'"plan"\s*:\s*"(.*?)"', json_str, re.DOTALL)
                    code_m = re.search(r'"code"\s*:\s*"(.*)', json_str, re.DOTALL)
                    if plan_m and code_m:
                        state['task_plan'] = plan_m.group(1)
                        # 去掉末尾未闭合的引号/括号
                        code_raw = code_m.group(1).rstrip().rstrip('"').rstrip('}')
                        state['python_code'] = code_raw.encode().decode('unicode_escape')
                        return state
                    state['error'] = f'JSON修复失败: {json_str[:300]}'
                    return state

            state['task_plan'] = parsed.get('plan', '')
            state['python_code'] = parsed.get('code', '')

        except Exception as e:
            state['error'] = f'识别问题失败: {e}'

        return state

    # ── 节点2: python agent (tool) ───────────────────────────────────

    def python_agent_tool(self, state: WorkflowState) -> WorkflowState:
        """
        Python Agent Tool:
        - 执行上一步生成的Python代码
        - 返回执行结果
        """
        if state.get('error'):
            return state

        python_code = state.get('python_code', '')
        if not python_code:
            state['error'] = '没有可执行的代码'
            return state

        try:
            exec_globals = {
                'pd': pd,
                'excel_path': state['excel_path'],
                '__builtins__': __builtins__
            }

            exec(python_code, exec_globals)

            result = exec_globals.get('result', None)
            if result is None:
                state['execution_result'] = '代码执行完成，但未找到result变量'
            elif isinstance(result, pd.DataFrame):
                state['execution_result'] = result.to_string()
            else:
                state['execution_result'] = str(result)

        except Exception as e:
            state['error'] = f'代码执行失败: {e}'
            state['execution_result'] = f'执行报错: {e}'

        return state

    # ── 节点3: agent分析结果 ─────────────────────────────────────────

    def agent_analyze(self, state: WorkflowState) -> WorkflowState:
        """
        Agent分析结果:
        - 基于执行结果回答用户原始问题
        """
        if state.get('error') and not state.get('execution_result'):
            state['analysis'] = f"分析过程出错: {state['error']}"
            return state

        prompt = f"""你是一个数据分析专家。请基于以下信息回答用户的问题。

用户问题: {state['query']}

分析计划: {state['task_plan']}

Python执行结果:
{state['execution_result']}

请直接回答用户的问题，给出数据支撑的结论和洞察。语言简洁清晰。"""

        try:
            state['analysis'] = self.api_call_func(prompt)
        except Exception as e:
            state['error'] = f'分析结果失败: {e}'
            state['analysis'] = ''

        return state

    # ── 运行入口 ─────────────────────────────────────────────────────

    def run(self, query: str, excel_path: str) -> dict:
        initial_state = {
            'query': query,
            'excel_path': excel_path,
            'task_plan': '',
            'python_code': '',
            'execution_result': '',
            'analysis': '',
            'error': '',
            'messages': []
        }
        return self.graph.invoke(initial_state)
