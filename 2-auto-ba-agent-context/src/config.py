"""
配置管理模块
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """配置类"""
    
    # 项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent
    
    # 数据目录
    DATA_DIR = PROJECT_ROOT / "data"
    FILES_DIR = PROJECT_ROOT / "files"
    OUTPUT_DIR = PROJECT_ROOT / "output"
    
    # 默认Excel文件路径
    DEFAULT_EXCEL_PATH = "files/1.1/渠道增长部2022-2026年预算目标to子欣.xlsx"
    
    # API配置
    MEITUAN_APP_ID = os.getenv('MEITUAN_APP_ID')
    MEITUAN_API_URL = os.getenv(
        'MEITUAN_API_URL',
        'https://aigc.sankuai.com/v1/openai/native/chat/completions'
    )
    MEITUAN_MODEL = os.getenv('MEITUAN_MODEL', 'DeepSeek-V3.2-Meituan')
    
    # 模型参数
    TEMPERATURE = float(os.getenv('TEMPERATURE', '0.7'))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '4000'))
    STREAM = os.getenv('STREAM', 'false').lower() == 'true'
    ENABLE_THINKING = os.getenv('ENABLE_THINKING', 'true').lower() == 'true'
    
    @classmethod
    def validate(cls):
        """验证配置"""
        if not cls.MEITUAN_APP_ID:
            raise ValueError(
                "未设置MEITUAN_APP_ID。请在.env文件中设置或通过环境变量传入"
            )
        return True
    
    @classmethod
    def get_excel_path(cls, relative_path: str = None) -> Path:
        """
        获取Excel文件的完整路径
        
        Args:
            relative_path: 相对路径，如果为None则返回默认路径
        """
        if relative_path is None:
            relative_path = cls.DEFAULT_EXCEL_PATH
        return cls.PROJECT_ROOT / relative_path
    
    @classmethod
    def ensure_output_dir(cls):
        """确保输出目录存在"""
        cls.OUTPUT_DIR.mkdir(exist_ok=True)
        return cls.OUTPUT_DIR


# 创建全局配置实例
config = Config()
