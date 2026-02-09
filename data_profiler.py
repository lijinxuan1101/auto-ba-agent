"""
数据分析工具模块：Excel 读取、Schema 探测、采样
实现 PRD 3.1 自动 Schema 探测与采样
"""

from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd
from pydantic import BaseModel


class ColumnProfile(BaseModel):
    """列的数据画像"""
    name: str
    dtype: str
    null_rate: float
    unique_count: int
    sample_values: List[Any]
    # 数值列的统计特征
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None


class TableProfile(BaseModel):
    """表的数据画像"""
    table_name: str
    sheet_name: str
    row_count: int
    column_count: int
    columns: List[ColumnProfile]


class DataProfiler:
    """数据探测器：深度采样 Excel 数据"""
    
    def __init__(self, sample_size: int = 10):
        """
        Args:
            sample_size: 每列采样的样本数量
        """
        self.sample_size = sample_size
        self.tables: Dict[str, pd.DataFrame] = {}
        self.profiles: List[TableProfile] = []
    
    def load_excel(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """
        加载 Excel 文件，支持多 Sheet。
        
        Args:
            file_path: Excel 文件路径
            
        Returns:
            {sheet_name: DataFrame}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        # 读取所有 Sheet
        xl_file = pd.ExcelFile(file_path)
        tables = {}
        
        for sheet_name in xl_file.sheet_names:
            df = pd.read_excel(xl_file, sheet_name=sheet_name)
            table_name = f"{file_path.stem}_{sheet_name}"
            tables[table_name] = df
            self.tables[table_name] = df
        
        return tables
    
    def profile_column(self, series: pd.Series) -> ColumnProfile:
        """
        对单列进行深度采样。
        
        Args:
            series: Pandas Series
            
        Returns:
            ColumnProfile 对象
        """
        # 基础信息
        null_rate = series.isnull().sum() / len(series) if len(series) > 0 else 0
        unique_count = series.nunique()
        
        # 采样值（排除 NaN）
        valid_values = series.dropna()
        if len(valid_values) > 0:
            sample_values = valid_values.value_counts().head(self.sample_size).index.tolist()
        else:
            sample_values = []
        
        # 数值列的统计特征
        min_val = max_val = mean_val = None
        if pd.api.types.is_numeric_dtype(series):
            if len(valid_values) > 0:
                min_val = float(valid_values.min())
                max_val = float(valid_values.max())
                mean_val = float(valid_values.mean())
        
        return ColumnProfile(
            name=series.name,
            dtype=str(series.dtype),
            null_rate=round(null_rate, 4),
            unique_count=unique_count,
            sample_values=sample_values,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
        )
    
    def profile_table(self, table_name: str, df: pd.DataFrame) -> TableProfile:
        """
        对整张表进行深度采样。
        
        Args:
            table_name: 表名
            df: DataFrame
            
        Returns:
            TableProfile 对象
        """
        column_profiles = []
        for col in df.columns:
            col_profile = self.profile_column(df[col])
            column_profiles.append(col_profile)
        
        return TableProfile(
            table_name=table_name,
            sheet_name=table_name.split("_", 1)[-1] if "_" in table_name else table_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=column_profiles,
        )
    
    def profile_all_tables(self) -> List[TableProfile]:
        """
        对所有已加载的表进行采样。
        
        Returns:
            所有表的 Profile 列表
        """
        profiles = []
        for table_name, df in self.tables.items():
            profile = self.profile_table(table_name, df)
            profiles.append(profile)
        
        self.profiles = profiles
        return profiles
    
    def get_profile_summary(self) -> str:
        """
        获取人类可读的 Profile 摘要（用于传给 LLM）。
        
        Returns:
            Profile 摘要文本
        """
        lines = ["=== 数据探测结果 ===\n"]
        
        for profile in self.profiles:
            lines.append(f"## 表: {profile.table_name}")
            lines.append(f"行数: {profile.row_count}, 列数: {profile.column_count}\n")
            
            for col in profile.columns:
                lines.append(f"  - {col.name} ({col.dtype})")
                lines.append(f"    空值率: {col.null_rate:.2%}, 唯一值数: {col.unique_count}")
                lines.append(f"    样本值: {col.sample_values[:5]}")
                
                if col.min_value is not None:
                    lines.append(f"    数值范围: [{col.min_value:.2f}, {col.max_value:.2f}], 均值: {col.mean_value:.2f}")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def get_table(self, table_name: str) -> Optional[pd.DataFrame]:
        """获取指定表的 DataFrame"""
        return self.tables.get(table_name)
