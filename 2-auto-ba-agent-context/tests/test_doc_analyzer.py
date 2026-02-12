"""
文档分析 → Skill 生成脚本

功能: 读取 knowledge/ 下的所有文档，逐篇调用 LLM 分析，生成标准 Skill 模板文件到 skills/ 目录。

Skill 模板格式:
  Part 1: YAML 元数据（Planner & Task Agent 使用）
  Part 2: Markdown 分析框架（Result Analysis Agent 使用）

运行:
  cd 2-auto-ba-agent-context
  python -m tests.test_doc_analyzer
"""

import sys
import json
import re
from pathlib import Path
from typing import List, Callable

# 确保项目根目录在 sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.tools.doc_read_tool import DocReadTool
from src.api_client import MeituanDeepSeekClient


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Prompt: 让 LLM 从文档生成 Skill 模板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SKILL_GEN_PROMPT = """\
你是一位资深的商业分析专家和技能模板设计师。

请仔细阅读以下业务文档，然后为这篇文档生成一个**标准的 Skill 模板**。
Skill 模板将被数据分析 Agent 系统使用，指导 Agent 如何分析相关数据。

文档内容:
\"\"\"
{doc_content}
\"\"\"

请严格按照以下格式输出 Skill 模板（整个输出就是一个 .md 文件的内容）：

---
# =======================================================
# Part 1: 元数据控制区 (Planner & Task Agent 使用)
# =======================================================
skill_name: "英文标识_用下划线"
display_name: "中文技能名称"
description: "描述该技能适用的场景，当用户问什么问题时使用此技能"
tags: ["标签1", "标签2", "标签3"]
version: "v1.0"

data_requirements:
  - primary_metric: "主指标名称"
  - dimensions: ["需要下钻的维度1", "维度2"]
  - comparison: "对比方式 (WoW/MoM/YoY)"
---

# =======================================================
# Part 2: 分析师思维链 (Result Analysis Agent 使用)
# =======================================================

## 1. 分析目标 (Goal)
（根据文档内容，描述这个 Skill 要解决什么分析问题）

## 2. 核心分析逻辑 (Analytical Framework)
（根据文档中的业务逻辑，提炼出结构化的分析步骤，使用编号列表）

## 3. 书写与排版规范 (Writing Protocol)
* **结论先行 (BLUF)**：报告第一段必须是总结论。
* **数据颗粒度**：必须包含具体的绝对值和百分比，禁止只说"大幅上涨"。
* **结构要求**：
    * H2: 📉 核心结论
    * H2: 📊 数据概览 (使用 Markdown 表格)
    * H2: 🔍 深入分析
    * H2: 💡 建议与行动项

## 4. 语气与风格 (Tone & Style)
* 专业、客观、冷静。
* 多用短句，少用长难句。
* 关键数据加 **粗体**。

## 5. 优秀的模仿范例 (One-Shot Example)
（从文档中提取或模仿一段最能代表该分析场景的分析片段作为范例）

要求：
1. skill_name 必须是英文小写+下划线格式
2. 分析逻辑要紧密贴合文档中的业务内容，不要泛泛而谈
3. data_requirements 中的维度要从文档内容中提取真实的业务维度
4. One-Shot Example 要尽量具体，包含真实的数据格式和分析口径
5. 整个输出就是可以直接保存为 .md 文件的内容，不要加任何额外包裹
6. 结合分析的内容要具有skills的可泛化性，要具有一定的case的代表性
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SkillGenerator — 从文档生成 Skill 模板
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SkillGenerator:
    """读取文档，调用 LLM 生成 Skill 模板文件"""

    def __init__(self, api_call_func: Callable[[str], str], output_dir: Path):
        self.api_call = api_call_func
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, doc_content: str, source_name: str = "") -> dict:
        """
        从一篇文档生成 Skill 模板。

        Returns:
            {"success": bool, "skill_name": str, "file_path": str, "content": str}
        """
        if not doc_content or not doc_content.strip():
            return {"success": False, "skill_name": "", "file_path": "", "content": "", "error": "文档内容为空"}

        prompt = _SKILL_GEN_PROMPT.format(doc_content=doc_content[:8000])

        try:
            raw = self.api_call(prompt)
            content = self._clean_output(raw)
            # 直接复用 knowledge 文件名（去掉扩展名）
            skill_name = Path(source_name).stem
            file_path = self._save_skill(skill_name, content)

            return {
                "success": True,
                "skill_name": skill_name,
                "file_path": str(file_path),
                "content": content,
            }
        except Exception as e:
            return {"success": False, "skill_name": "", "file_path": "", "content": "", "error": str(e)}

    def _clean_output(self, raw: str) -> str:
        """清洗 LLM 输出，去掉多余的 markdown 代码块包裹"""
        content = raw.strip()
        # 去掉最外层的 ```markdown ... ``` 包裹
        if content.startswith("```"):
            lines = content.split("\n")
            # 去掉第一行 ``` 和最后一行 ```
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()

    def _extract_skill_name(self, content: str, fallback_name: str) -> str:
        """从生成的 Skill 内容中提取 skill_name"""
        match = re.search(r'skill_name:\s*"([^"]+)"', content)
        if match:
            return match.group(1)
        # fallback: 用文件名生成
        name = Path(fallback_name).stem
        name = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '_', name)
        return f"skill_{name.lower()}"

    def _save_skill(self, skill_name: str, content: str) -> Path:
        """保存 Skill 模板文件"""
        file_path = self.output_dir / f"{skill_name}.md"
        file_path.write_text(content, encoding="utf-8")
        return file_path


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  主流程
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print("\n" + "=" * 60)
    print("  文档 → Skill 模板 生成")
    print("=" * 60)

    # 1. 初始化 API
    try:
        client = MeituanDeepSeekClient()
        api_func = lambda p: client.chat(p)
        print("✅ API 连接成功\n")
    except Exception as e:
        print(f"❌ API 初始化失败: {e}")
        print("请检查 .env 中的 MEITUAN_APP_ID 配置")
        return

    # 2. 读取 knowledge/ 下的文档
    tool = DocReadTool()
    knowledge_dir = ROOT_DIR / "knowledge"
    all_files = tool.list_knowledge_files()
    # 只处理 knowledge/ 下的文档（skills/ 下的是已有 skill，不重复处理）
    files = [f for f in all_files if str(knowledge_dir) in f]

    if not files:
        print("⚠️ knowledge/ 目录下没有文件")
        print("请先放入业务文档（.md / .txt）再运行\n")
        return

    print(f"📂 找到 {len(files)} 篇知识文档:\n")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {Path(f).name}")

    # 3. 逐篇生成 Skill
    skills_dir = ROOT_DIR / "skills"
    generator = SkillGenerator(api_call_func=api_func, output_dir=skills_dir)
    results = []

    print("\n" + "-" * 60)
    for i, file_path in enumerate(files, 1):
        file_name = Path(file_path).name
        print(f"\n📄 [{i}/{len(files)}] 正在处理: {file_name}")

        content = tool.read_file(file_path)
        if content.startswith("[错误]"):
            print(f"   ⚠️ 跳过: {content}")
            continue

        print(f"   文档长度: {len(content)} 字符")
        print(f"   ⏳ 调用 LLM 生成 Skill 模板...")

        result = generator.generate(content, source_name=file_name)
        results.append(result)

        if result["success"]:
            print(f"   ✅ 生成成功: {result['skill_name']}")
            print(f"   💾 保存到: {result['file_path']}")

            # 打印摘要预览
            preview_lines = result["content"].split("\n")[:20]
            print(f"\n   --- 预览 (前 20 行) ---")
            for line in preview_lines:
                print(f"   {line}")
            print(f"   --- ... ---")
        else:
            print(f"   ❌ 生成失败: {result.get('error', '未知错误')}")

    # 4. 汇总
    success_count = sum(1 for r in results if r["success"])
    print("\n" + "=" * 60)
    print(f"  完成: {success_count}/{len(files)} 篇文档成功生成 Skill")
    print(f"  Skill 文件目录: {skills_dir}")
    print("=" * 60)

    if success_count > 0:
        print(f"\n生成的 Skill 文件:")
        for r in results:
            if r["success"]:
                print(f"  📝 {r['skill_name']}.md")
    print()


if __name__ == "__main__":
    main()
