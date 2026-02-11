"""
Excel数据分析工作流系统
基于LangGraph和美团DeepSeek
"""

__version__ = "1.0.0"
__author__ = "Auto BA Agent"

from .workflow import ExcelAnalysisWorkflow
from .api_client import MeituanDeepSeekClient

__all__ = [
    "ExcelAnalysisWorkflow",
    "MeituanDeepSeekClient",
]
