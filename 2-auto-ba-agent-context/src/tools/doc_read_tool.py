"""
DocReadTool — 知识文档检索 & 读取

从 knowledge/ 和 skills/ 目录中搜索、读取文档，提供给其他 Agent 使用。
"""

import re
from pathlib import Path
from typing import List, Optional


class DocReadTool:
    """
    知识文档检索 & 读取工具。

    功能:
      - list_knowledge_files(): 列出所有可用文件
      - read_file(path):        读取指定文件内容
      - search(query):          基于关键词搜索全部文档段落
    """

    SUPPORTED_EXTS = {'.md', '.txt', '.csv', '.json'}

    def __init__(
        self,
        knowledge_dir: Optional[str] = None,
        skills_dir: Optional[str] = None,
    ):
        # 项目根: 2-auto-ba-agent-context/
        project_root = Path(__file__).resolve().parent.parent.parent
        self.knowledge_dir = Path(knowledge_dir) if knowledge_dir else project_root / "knowledge"
        self.skills_dir = Path(skills_dir) if skills_dir else project_root / "skills"

        # 确保目录存在
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    # ── 列出文件 ──────────────────────────────

    def list_knowledge_files(self) -> List[str]:
        """列出 knowledge/ 和 skills/ 下的所有支持文件"""
        files: List[str] = []
        for d in (self.knowledge_dir, self.skills_dir):
            for f in sorted(d.rglob("*")):
                if f.is_file() and f.suffix in self.SUPPORTED_EXTS:
                    files.append(str(f))
        return files

    # ── 读取文件 ──────────────────────────────

    @staticmethod
    def read_file(file_path: str) -> str:
        """读取单个文件的文本内容"""
        p = Path(file_path)
        if not p.exists():
            return f"[错误] 文件不存在: {file_path}"
        try:
            return p.read_text(encoding="utf-8")
        except Exception as e:
            return f"[错误] 读取失败: {e}"

    # ── 搜索 ──────────────────────────────────

    def search(self, query: str, max_results: int = 10) -> List[dict]:
        """
        基于关键词搜索 knowledge/ 和 skills/ 下的文档。

        Returns:
            [{ "source": str, "content": str, "score": int }, ...]
            按相关度降序排列。
        """
        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        results: List[dict] = []
        for file_path_str in self.list_knowledge_files():
            content = self.read_file(file_path_str)
            if content.startswith("[错误]"):
                continue

            # 按空行分段
            paragraphs = re.split(r"\n\s*\n", content)
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                score = sum(1 for kw in keywords if kw.lower() in para.lower())
                if score > 0:
                    results.append({
                        "source": file_path_str,
                        "content": para,
                        "score": score,
                    })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    # ── 内部: 提取关键词 ──────────────────────

    @staticmethod
    def _extract_keywords(query: str) -> List[str]:
        """从 query 中提取关键词（简单分词 + 中文 2-gram）"""
        cleaned = re.sub(r"[,，;；。！!？?\s]+", " ", query).strip()
        words = cleaned.split()
        keywords: List[str] = []
        for w in words:
            if len(w) <= 1:
                continue
            keywords.append(w)
            # 对中文长词做 2-gram 拆分
            if len(w) >= 4 and not w.isascii():
                for i in range(len(w) - 1):
                    keywords.append(w[i : i + 2])
        return list(set(keywords)) if keywords else [query]
