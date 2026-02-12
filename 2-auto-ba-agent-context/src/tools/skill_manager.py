"""
Skill Manager - 技能文档管理工具

负责解析、匹配 skills/ 目录下的技能模板文件。

支持的 Skill 文件格式:
  ---
  # 注释行（会被忽略）
  skill_name: "英文标识"
  display_name: "中文名称"
  description: "适用场景描述"
  tags: ["标签1", "标签2"]
  version: "v1.0"
  data_requirements:
    - primary_metric: "主指标"
    - dimensions: ["维度1", "维度2"]
    - comparison: "WoW/MoM/YoY"
  ---
  (Markdown 正文: Part 2 分析师思维链)
"""

import re
import json
from pathlib import Path
from typing import List, Optional, Dict


class SkillManager:
    """技能文档管理器"""

    def __init__(self, skills_dir: Optional[str] = None):
        project_root = Path(__file__).parent.parent.parent
        self.skills_dir = Path(skills_dir) if skills_dir else project_root / "skills"
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, dict] = {}  # name → parsed skill
        self._load_all()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 解析
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def _parse_skill_file(self, file_path: Path) -> Optional[dict]:
        """
        解析单个 skill 文件，提取 YAML 元数据 + Markdown 正文

        Returns:
            {
                "file_path": str,
                "meta": { name, display_name, description, tags, ... },
                "prompt_template": str (Markdown 正文，即 Part 2)
            }
        """
        try:
            content = file_path.read_text(encoding='utf-8')
        except Exception:
            return None

        # 匹配 YAML frontmatter: --- ... ---
        fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not fm_match:
            return None

        yaml_str = fm_match.group(1)
        body = content[fm_match.end():]

        # 简易 YAML 解析
        meta = self._simple_yaml_parse(yaml_str)

        # 兼容新旧两种格式: skill_name / name
        if meta.get('skill_name') and not meta.get('name'):
            meta['name'] = meta['skill_name']
        if not meta.get('name'):
            # fallback: 用文件名作为 name
            meta['name'] = file_path.stem

        return {
            "file_path": str(file_path),
            "meta": meta,
            "prompt_template": body.strip(),
        }

    @staticmethod
    def _simple_yaml_parse(yaml_str: str) -> dict:
        """
        简易 YAML 解析器

        支持:
          - 注释行 (# ...)
          - 字符串: key: "value" 或 key: value
          - 列表: key: ["a", "b"]
          - 多行缩进块 (如 data_requirements) 会被跳过
        """
        result = {}
        for line in yaml_str.strip().split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # 跳过缩进行（属于多行 YAML 块，如 data_requirements 的子项）
            if line.startswith('-') and ':' in line and not line.startswith('---'):
                continue
            match = re.match(r'^(\w+)\s*:\s*(.+)$', line)
            if not match:
                continue
            key = match.group(1)
            value = match.group(2).strip()

            # 解析列表: ["a", "b", "c"]
            if value.startswith('['):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    value = [v.strip().strip('"').strip("'") for v in value.strip('[]').split(',')]
            # 解析带引号的字符串
            elif value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            result[key] = value
        return result

    def _load_all(self):
        """加载 skills/ 下所有 .md 文件到缓存"""
        self._cache.clear()
        for f in self.skills_dir.glob("*.md"):
            if f.name.startswith('_') or f.name == 'README.md':
                continue
            skill = self._parse_skill_file(f)
            if skill:
                self._cache[skill['meta']['name']] = skill

    def reload(self):
        """重新加载全部 skill"""
        self._load_all()

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 查询 & 匹配
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def list_skills(self) -> List[dict]:
        """列出所有已注册的 skill 摘要"""
        return [
            {
                "name": s['meta']['name'],
                "display_name": s['meta'].get('display_name', ''),
                "description": s['meta'].get('description', ''),
                "tags": s['meta'].get('tags', []),
            }
            for s in self._cache.values()
        ]

    def get_skill(self, name: str) -> Optional[dict]:
        """按名称获取完整 skill"""
        return self._cache.get(name)

    def match_skill(self, query: str) -> Optional[dict]:
        """
        根据用户 query 匹配最佳 skill

        匹配策略:
        1. tags 双向匹配（tag 在 query 中 或 query 片段在 tag 中）
        2. description 与 query 的 2-gram 交叉匹配
        3. trigger_keywords 精确匹配（兼容旧格式）

        Returns:
            最佳匹配的 skill dict，或 None
        """
        query_lower = query.lower()
        query_grams = self._extract_ngrams(query_lower, n=2)
        best_skill = None
        best_score = 0

        for skill in self._cache.values():
            meta = skill['meta']
            score = 0

            # tags 双向匹配
            tags = meta.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            for tag in tags:
                tag_lower = tag.lower()
                # 完整 tag 在 query 中
                if tag_lower in query_lower:
                    score += 8
                # query 的 2-gram 在 tag 中（如 query="大促分析", tag="电商大促" → "大促" 命中）
                else:
                    tag_grams = self._extract_ngrams(tag_lower, n=2)
                    overlap = query_grams & tag_grams
                    score += len(overlap) * 2

            # description 与 query 的 2-gram 交叉匹配
            desc = meta.get('description', '').lower()
            if desc:
                for gram in query_grams:
                    if gram in desc:
                        score += 1

            # 兼容旧格式: trigger_keywords
            keywords = meta.get('trigger_keywords', [])
            if isinstance(keywords, str):
                keywords = [keywords]
            for kw in keywords:
                if kw.lower() in query_lower:
                    score += 10

            if score > best_score:
                best_score = score
                best_skill = skill

        return best_skill if best_score > 0 else None

    @staticmethod
    def _extract_ngrams(text: str, n: int = 2) -> set:
        """提取文本的 n-gram 集合（用于中文模糊匹配）"""
        # 移除标点和空格
        cleaned = re.sub(r'[\s,，。！!？?;；、\-—()（）\[\]【】""\'\']', '', text)
        if len(cleaned) < n:
            return {cleaned} if cleaned else set()
        return {cleaned[i:i+n] for i in range(len(cleaned) - n + 1)}

    def get_prompt_for_query(self, query: str) -> Optional[str]:
        """根据 query 匹配 skill 并返回其 prompt_template"""
        skill = self.match_skill(query)
        if skill:
            return skill['prompt_template']
        return None

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 删除
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    def delete_skill(self, name: str) -> bool:
        """删除 skill"""
        skill = self._cache.get(name)
        if not skill:
            return False
        try:
            Path(skill['file_path']).unlink()
            del self._cache[name]
            return True
        except Exception:
            return False
