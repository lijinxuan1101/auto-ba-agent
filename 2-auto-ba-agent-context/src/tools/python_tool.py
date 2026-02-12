"""
Python Tool - 代码执行工具（带自检回路）

流程:
  生成代码 → 执行 → 检查结果 → 失败则修正重跑（最多 MAX_RETRIES 次）
"""

import pandas as pd
import traceback
from typing import Optional, Callable


class PythonTool:
    """Python 代码执行器，支持自检重试"""

    MAX_RETRIES = 3  # 最大重试次数

    def __init__(self, api_call_func: Optional[Callable] = None):
        """
        Args:
            api_call_func: LLM 调用函数，用于代码修正
        """
        self.api_call_func = api_call_func

    def execute(self, code: str, excel_path: str) -> dict:
        """
        执行代码并返回结果

        Returns:
            {"success": bool, "result": str, "error": str, "code": str}
        """
        exec_globals = {
            'pd': pd,
            'excel_path': excel_path,
            '__builtins__': __builtins__,
        }

        try:
            exec(code, exec_globals)
            result = exec_globals.get('result', None)

            if result is None:
                return {
                    "success": False,
                    "result": "",
                    "error": "代码执行完成，但未找到 result 变量。请确保代码将结果赋值给 result。",
                    "code": code,
                }

            if isinstance(result, pd.DataFrame):
                result_str = result.to_string()
            else:
                result_str = str(result)

            return {"success": True, "result": result_str, "error": "", "code": code}

        except Exception as e:
            return {
                "success": False,
                "result": "",
                "error": f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
                "code": code,
            }

    def execute_with_retry(self, code: str, excel_path: str, query: str = "",
                           excel_info: str = "") -> dict:
        """
        执行代码，失败时自动让 LLM 修正并重试

        Args:
            code: 初始 Python 代码
            excel_path: Excel 文件路径
            query: 用户原始查询（用于修正提示）
            excel_info: Excel 元信息（用于修正提示）

        Returns:
            {"success": bool, "result": str, "error": str, "code": str, "attempts": int}
        """
        current_code = code

        for attempt in range(1, self.MAX_RETRIES + 1):
            result = self.execute(current_code, excel_path)
            result['attempts'] = attempt

            if result['success']:
                if attempt > 1:
                    print(f"  ✅ 第 {attempt} 次执行成功")
                return result

            print(f"  ⚠️ 第 {attempt}/{self.MAX_RETRIES} 次执行失败: {result['error'][:100]}")

            # 如果有 LLM 函数且还有重试机会，尝试修正代码
            if self.api_call_func and attempt < self.MAX_RETRIES:
                fixed_code = self._fix_code(current_code, result['error'], query, excel_info)
                if fixed_code and fixed_code != current_code:
                    current_code = fixed_code
                    print(f"  🔧 已修正代码，第 {attempt + 1} 次尝试...")
                else:
                    break  # LLM 没能修正，不再重试

        return result

    def _fix_code(self, broken_code: str, error_msg: str,
                  query: str, excel_info: str) -> Optional[str]:
        """让 LLM 修正出错的代码"""
        if not self.api_call_func:
            return None

        prompt = f"""以下 Python 代码执行时报错了，请修正。

用户需求: {query}

Excel 数据信息:
{excel_info}

出错的代码:
```python
{broken_code}
```

错误信息:
{error_msg}

请只输出修正后的纯 Python 代码，不要输出任何解释文字，不要用 markdown 代码块包裹。
代码必须将最终结果赋值给 result 变量。"""

        try:
            response = self.api_call_func(prompt)
            # 清洗可能的 markdown 包裹
            code = response.strip()
            if code.startswith("```"):
                lines = code.split('\n')
                lines = [l for l in lines if not l.strip().startswith("```")]
                code = '\n'.join(lines)
            return code.strip()
        except Exception:
            return None
