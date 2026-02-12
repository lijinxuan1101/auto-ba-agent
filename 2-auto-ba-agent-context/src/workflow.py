from typing import TypedDict, Annotated, Literal
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
import pandas as pd
import os
import re
import json

from .tools.python_tool import PythonTool
from .tools.doc_read_tool import DocReadTool
from .tools.skill_manager import SkillManager


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 状态定义
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class WorkflowState(TypedDict):
    """工作流全局状态"""
    # 输入
    query: str                                       # 用户原始查询
    excel_path: str                                  # Excel 文件路径

    # planner 输出
    route: str                                       # 路由决策: "need_context" | "direct_analysis"
    planner_reasoning: str                           # planner 的判断理由

    # context handle 输出
    context_info: str                                # 检索到的上下文知识
    excel_info: str                                  # Excel 元信息
    matched_skill: str                               # 匹配到的 skill 名称
    skill_prompt: str                                # skill 的提示词模板

    # task analysis 输出
    task_plan: str                                   # 分析计划
    python_code: str                                 # 生成的 Python 代码
    execution_result: str                            # 代码执行结果
    code_attempts: int                               # 代码执行尝试次数

    # result analysis 输出
    analysis: str                                    # 最终分析报告

    # 通用
    error: str                                       # 错误信息
    messages: Annotated[list, add_messages]           # 消息历史


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 工作流主类
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ExcelAnalysisWorkflow:
    """多 Agent Excel 数据分析工作流"""

    def __init__(self, api_call_func=None):
        self.api_call_func = api_call_func or (lambda p: f"默认响应: {p[:50]}...")
        self.python_tool = PythonTool(api_call_func=self.api_call_func)
        self.doc_read_tool = DocReadTool()
        self.skill_manager = SkillManager()
        self.graph = self._build_graph()

    # ── 构建 LangGraph ──────────────────────────────────────────

    def _build_graph(self) -> StateGraph:
        """
        构建多 Agent 工作流图:

        planner_agent
            ├── (need_context) → context_handle_agent → skill_agent → task_analysis_agent → result_analysis_agent
            └── (direct)       → read_excel_info ──────────────────→ task_analysis_agent → result_analysis_agent
        """
        workflow = StateGraph(WorkflowState)

        # 注册节点
        workflow.add_node("planner_agent", self.planner_agent)
        workflow.add_node("context_handle_agent", self.context_handle_agent)
        workflow.add_node("skill_agent", self.skill_agent)
        workflow.add_node("read_excel_info", self.read_excel_info)
        workflow.add_node("task_analysis_agent", self.task_analysis_agent)
        workflow.add_node("result_analysis_agent", self.result_analysis_agent)

        # 入口
        workflow.set_entry_point("planner_agent")

        # 条件路由：planner 决定走哪条路
        workflow.add_conditional_edges(
            "planner_agent",
            self._route_decision,
            {
                "need_context": "context_handle_agent",
                "direct_analysis": "read_excel_info",
            }
        )

        # context_handle → skill_agent（传递文档给 skill agent 维护）
        workflow.add_edge("context_handle_agent", "skill_agent")
        # skill_agent → task_analysis
        workflow.add_edge("skill_agent", "task_analysis_agent")
        # read_excel_info → task_analysis（直接路径跳过 skill agent）
        workflow.add_edge("read_excel_info", "task_analysis_agent")
        # task_analysis → result_analysis
        workflow.add_edge("task_analysis_agent", "result_analysis_agent")
        # result_analysis → END
        workflow.add_edge("result_analysis_agent", END)

        return workflow.compile()

    @staticmethod
    def _route_decision(state: WorkflowState) -> str:
        """根据 planner 的 route 字段决定走哪条路"""
        return state.get('route', 'direct_analysis')

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Primary Agent: Planner
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def planner_agent(self, state: WorkflowState) -> dict:
        """
        Planner Agent - 意图路由

        判断 query 是否需要额外的知识上下文：
        - need_context: 需要检索知识库（涉及业务定义、行业知识、历史报告等）
        - direct_analysis: 直接用 Excel 数据就能分析
        """
        print("\n🧠 [Planner Agent] 分析用户意图...")

        prompt = f"""你是一个智能规划 Agent。用户提出了一个数据分析需求，你需要判断是否需要额外的知识上下文来辅助分析。

用户查询: {state['query']}
数据文件: {state['excel_path']}

请判断这个查询属于哪种类型：
1. "need_context" - 需要额外知识上下文（例如：涉及业务术语定义、行业基准、历史对比标准、特定业务逻辑等）
2. "direct_analysis" - 直接用数据就能分析（例如：数据趋势、统计描述、环比同比、分布分析等）

请严格按以下 JSON 格式输出：
{{"route": "need_context 或 direct_analysis", "reasoning": "判断理由（一句话）"}}"""

        try:
            response = self.api_call_func(prompt)
            json_match = re.search(r'\{.*?\}', response, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                route = parsed.get('route', 'direct_analysis')
                reasoning = parsed.get('reasoning', '')
            else:
                route = 'direct_analysis'
                reasoning = 'LLM 返回格式异常，默认直接分析'
        except Exception as e:
            route = 'direct_analysis'
            reasoning = f'Planner 调用异常: {e}，默认直接分析'

        # 确保 route 值合法
        if route not in ('need_context', 'direct_analysis'):
            route = 'direct_analysis'

        print(f"   路由决策: {route}")
        print(f"   理由: {reasoning}")

        return {
            'route': route,
            'planner_reasoning': reasoning,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sub Agent: Context Handle
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def context_handle_agent(self, state: WorkflowState) -> dict:
        """
        Context Handle Agent - 文档检索 + 拼接上下文

        流程:
        1. 检索知识库文档
        2. 把检索结果拼接为上下文文本
        3. 读取 Excel 元信息
        """
        print("\n📚 [Context Handle Agent] 检索知识文档...")

        # 1. 检索相关文档
        docs = self.doc_read_tool.search(state['query'])

        if docs:
            print(f"   找到 {len(docs)} 条相关文档")

            # 2. 拼接检索到的文档为上下文
            context_parts = []
            for i, doc in enumerate(docs, 1):
                source = doc.get('source', f'文档{i}')
                content = doc.get('content', '')
                context_parts.append(f"--- 来源: {source} ---\n{content}")
            context_info = "\n\n".join(context_parts)

            print(f"   上下文长度: {len(context_info)} 字符")
        else:
            context_info = ""
            print("   未检索到知识文档")

        # 3. 读取 Excel 元信息
        excel_info = self._read_excel_metadata(state['excel_path'])

        return {
            'context_info': context_info,
            'excel_info': excel_info,
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sub Agent: Skill Agent（维护 skill 数据库）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def skill_agent(self, state: WorkflowState) -> dict:
        """
        Skill Agent - 匹配 skill 模板

        从 skills/ 目录中匹配与用户查询最相关的 Skill，
        将其 prompt_template（Part 2 分析框架）传递给下游 Agent。

        Skill 文件由 test_doc_analyzer.py 离线预生成。
        """
        print("\n🎯 [Skill Agent] 匹配 Skill 模板...")

        query = state['query']

        # 列出可用 skills
        all_skills = self.skill_manager.list_skills()
        if all_skills:
            print(f"   可用 Skill ({len(all_skills)} 个):")
            for s in all_skills:
                print(f"     - {s.get('display_name', s['name'])}")

        # 匹配最佳 skill
        skill = self.skill_manager.match_skill(query)

        if skill:
            name = skill['meta'].get('display_name', skill['meta']['name'])
            print(f"   ✅ 匹配到: {name}")
            return {
                'matched_skill': name,
                'skill_prompt': skill['prompt_template'],
            }

        # 没匹配到 → 使用通用分析模板
        print("   未匹配到 Skill，将使用通用分析模板")
        return {
            'matched_skill': '',
            'skill_prompt': '',
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 辅助节点: 读取 Excel 信息（直接分析路径）
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def read_excel_info(self, state: WorkflowState) -> dict:
        """直接分析路径：只读取 Excel 元信息，不检索知识库"""
        print("\n📊 [Read Excel Info] 读取数据结构...")
        excel_info = self._read_excel_metadata(state['excel_path'])
        return {
            'excel_info': excel_info,
            'context_info': '',
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sub Agent: Task Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def task_analysis_agent(self, state: WorkflowState) -> dict:
        """
        Task Analysis Agent - 生成代码 + 执行 + 自检回路

        调用 python_tool 执行代码，失败自动修正重跑
        """
        print("\n⚙️ [Task Analysis Agent] 生成分析代码...")

        if state.get('error'):
            return {}

        excel_info = state.get('excel_info', '')
        context_info = state.get('context_info', '')

        # 构造 prompt
        context_section = ""
        if context_info:
            context_section = f"""
相关知识上下文（请参考，但以实际数据为准）:
{context_info}
"""

        prompt = f"""你是一个数据分析 Agent。请根据以下信息生成 Python 分析代码。

用户问题: {state['query']}

Excel 数据信息:
{excel_info}
{context_section}
请生成一段完整的 Python 代码来分析数据，要求:
- 用 pd.read_excel(excel_path) 读取数据，excel_path 变量已提供
- 将最终分析结果赋值给 result 变量（字符串格式，包含关键数据和结论）
- 代码必须是能直接执行的纯 Python，不能有语法错误
- 分析要全面，包含数据统计、趋势、对比等

请严格按以下 JSON 格式输出:
{{"plan": "你的分析思路（2-3句话）", "code": "你的Python代码"}}"""

        try:
            response = self.api_call_func(prompt)

            # 提取 JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return {'error': f'LLM 返回格式异常: {response[:200]}'}

            json_str = json_match.group()
            try:
                parsed = json.loads(json_str)
            except json.JSONDecodeError:
                # 尝试正则提取
                plan_m = re.search(r'"plan"\s*:\s*"(.*?)"', json_str, re.DOTALL)
                code_m = re.search(r'"code"\s*:\s*"(.*)', json_str, re.DOTALL)
                if plan_m and code_m:
                    task_plan = plan_m.group(1)
                    code_raw = code_m.group(1).rstrip().rstrip('"').rstrip('}')
                    python_code = code_raw.encode().decode('unicode_escape')
                else:
                    return {'error': f'JSON 解析失败: {json_str[:300]}'}
            else:
                task_plan = parsed.get('plan', '')
                python_code = parsed.get('code', '')

            print(f"   分析计划: {task_plan[:100]}...")
            print(f"   代码长度: {len(python_code)} 字符")

        except Exception as e:
            return {'error': f'代码生成失败: {e}'}

        # 使用 python_tool 执行代码（带自检重试）
        print("\n🔄 [Python Tool] 执行代码...")
        exec_result = self.python_tool.execute_with_retry(
            code=python_code,
            excel_path=state['excel_path'],
            query=state['query'],
            excel_info=excel_info,
        )

        if exec_result['success']:
            print(f"   ✅ 执行成功（第 {exec_result['attempts']} 次）")
        else:
            print(f"   ❌ 执行失败: {exec_result['error'][:100]}")

        return {
            'task_plan': task_plan,
            'python_code': exec_result['code'],
            'execution_result': exec_result['result'] or exec_result['error'],
            'code_attempts': exec_result['attempts'],
            'error': '' if exec_result['success'] else exec_result['error'],
        }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # Sub Agent: Result Analysis
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def result_analysis_agent(self, state: WorkflowState) -> dict:
        """
        Result Analysis Agent - 汇总结果生成最终报告

        如果匹配到了 skill 模板，使用 skill 的提示词指令来约束输出格式
        """
        print("\n📝 [Result Analysis Agent] 生成分析报告...")

        if state.get('error') and not state.get('execution_result'):
            return {'analysis': f"分析过程出错: {state['error']}"}

        # 检查是否有匹配的 skill 模板
        skill_prompt = state.get('skill_prompt', '')
        if skill_prompt:
            print(f"   使用 Skill 模板: {state.get('matched_skill', '?')}")
            # 用 skill 模板作为 system prompt 的核心指令
            prompt = f"""{skill_prompt}

---
以下是本次分析的具体数据，请严格按照上述模板生成报告。

用户问题: {state['query']}

分析计划: {state.get('task_plan', '')}

Python 执行结果 (execution_result):
{state.get('execution_result', '')}
"""
        else:
            # 没有 skill 模板，使用通用 prompt
            context_hint = ""
            if state.get('context_info'):
                context_hint = f"""
参考知识:
{state['context_info'][:500]}
"""
            prompt = f"""你是一个数据分析专家。请基于以下信息回答用户的问题，生成一份清晰的分析报告。

用户问题: {state['query']}

分析计划: {state.get('task_plan', '')}

Python 执行结果:
{state.get('execution_result', '')}
{context_hint}
要求:
1. 直接回答用户的问题，给出数据支撑的结论和洞察
2. 语言简洁清晰，结构化展示（可用标题、列表等）
3. 如果有异常数据或值得关注的点，请特别指出"""

        try:
            analysis = self.api_call_func(prompt)
            print("   ✅ 报告生成完成")
            return {'analysis': analysis}
        except Exception as e:
            return {
                'error': f'结果分析失败: {e}',
                'analysis': '',
            }

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 工具函数
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    @staticmethod
    def _read_excel_metadata(excel_path: str) -> str:
        """读取 Excel 文件的元信息"""
        if not os.path.exists(excel_path):
            return f"文件不存在: {excel_path}"
        try:
            df = pd.read_excel(excel_path)
            return (
                f"文件: {excel_path}\n"
                f"行数: {len(df)}, 列数: {len(df.columns)}\n"
                f"列名: {list(df.columns)}\n"
                f"数据类型:\n{df.dtypes.to_string()}\n"
                f"前5行:\n{df.head(5).to_string()}"
            )
        except Exception as e:
            return f"读取 Excel 失败: {e}"

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 运行入口
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def run(self, query: str, excel_path: str) -> dict:
        """运行完整工作流"""
        print("\n" + "=" * 60)
        print("  Multi-Agent Excel 分析工作流启动")
        print("=" * 60)
        print(f"  Query: {query}")
        print(f"  Excel: {excel_path}")
        print("=" * 60)

        initial_state = {
            'query': query,
            'excel_path': excel_path,
            'route': '',
            'planner_reasoning': '',
            'context_info': '',
            'excel_info': '',
            'matched_skill': '',
            'skill_prompt': '',
            'task_plan': '',
            'python_code': '',
            'execution_result': '',
            'code_attempts': 0,
            'analysis': '',
            'error': '',
            'messages': [],
        }
        return self.graph.invoke(initial_state)
