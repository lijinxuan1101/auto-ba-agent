# 商业分析 Agent (Auto-BA Agent)

基于 LangGraph + DeepSeek API 的自动化商业分析系统。

## 核心功能

✅ **自动数据探测**：深度采样 Excel 数据，提取列特征和样本值  
✅ **语义对齐推理**：利用 DeepSeek 推断表间关联关系  
✅ **闭环代码生成**：意图识别 → 逻辑规划 → 代码生成 → 执行验证  
✅ **持久化存储**：SQLite 保存对话历史和分析结果  
✅ **错误自动纠正**：失败后自动重试，逻辑检查（如笛卡尔积检测）

## 技术架构

```
┌─────────────────────────────────────────────────────┐
│                    BAAgentApp                        │
│             (主应用 & 会话管理)                      │
└────────────┬────────────────────────────────────────┘
             │
       ┌─────┴─────┬────────────┬──────────────┐
       │           │            │              │
┌──────▼─────┐ ┌──▼──────┐  ┌──▼────────┐ ┌───▼──────┐
│DataProfiler│ │Semantic │  │ BAAgent   │ │Persist   │
│            │ │ Mapper  │  │(LangGraph)│ │ ence     │
│Excel读取   │ │语义推理 │  │           │ │SQLite    │
│Schema探测  │ │关系图   │  │4步闭环    │ │历史记录  │
└────────────┘ └─────────┘  └───────────┘ └──────────┘
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 美团 AIGC AppId（必需）
AIGC_APP_ID=your_app_id_here
```

### 3. 准备数据

将 Excel 文件放到 `data/` 目录下（或任意路径）。

### 4. 运行示例

```bash
python example.py
```

## 使用方式

### 方式 1：Python API

```python
from app import BAAgentApp

# 创建应用
app = BAAgentApp()

# 加载 Excel 数据
app.load_excel("data/sales_data.xlsx")

# 执行分析
app.analyze("统计 2026 年的总销售额")
app.analyze("找出销量最高的前 5 个产品")

# 查看历史
app.get_history()
```

### 方式 2：交互式模式

```python
from example import example_interactive_mode
example_interactive_mode()
```

## 核心流程详解

### 1. 数据探测（Data Profiling）

```python
from data_profiler import DataProfiler

profiler = DataProfiler(sample_size=10)
tables = profiler.load_excel("data.xlsx")
profiles = profiler.profile_all_tables()

# 输出：
# - 列名、数据类型、空值率
# - 唯一值数量
# - Top 10 样本值
# - 数值列的 Min/Max/Mean
```

### 2. 语义对齐（Semantic Alignment）

```python
from semantic_mapper import SemanticMapper

mapper = SemanticMapper(llm)
semantic_map = mapper.generate_semantic_map(profile_summary)

# 输出 JSON：
# {
#   "nodes": [{"table": "订单表", "description": "..."}],
#   "edges": [
#     {"from_col": "订单.产品ID", "to_col": "产品.ID", 
#      "logic": "JOIN", "confidence": 0.9}
#   ]
# }
```

### 3. LangGraph 闭环流程

```
┌──────────────┐
│意图识别      │ → 分析用户问题类型（描述性/诊断性/关联性）
└──────┬───────┘
       ▼
┌──────────────┐
│逻辑规划      │ → 输出伪代码：过滤 → JOIN → 计算
└──────┬───────┘
       ▼
┌──────────────┐
│代码生成      │ → 生成 Pandas 代码
└──────┬───────┘
       ▼
┌──────────────┐
│执行验证      │ → 运行代码 + 逻辑检查（笛卡尔积）
└──────┬───────┘
       │
       ├─ 成功 → 返回结果
       └─ 失败 → 重新规划（最多 3 次）
```

### 4. 持久化存储

```python
from persistence import PersistenceManager

pm = PersistenceManager("ba_agent.db")

# 保存对话
pm.save_conversation(session_id, query, result=answer)

# 查询历史
history = pm.get_conversation_history(session_id, limit=10)
```

## 项目结构

```
mvpagent/
├── app.py                    # 主应用入口
├── example.py                # 使用示例
├── data_profiler.py          # 数据探测模块
├── semantic_mapper.py        # 语义对齐模块
├── agent_graph.py            # LangGraph 闭环流程
├── persistence.py            # SQLite 持久化
├── requirements.txt          # 依赖列表
├── .env                      # 环境变量（需创建）
├── PRD.md                    # 产品需求文档
├── README.md                 # 本文件
└── data/                     # 数据目录（需创建）
    └── example.xlsx
```

## API 配置说明

### DeepSeek API（美团 AIGC）

```python
# 默认配置（在 app.py 中）
base_url = "https://aigc.sankuai.com/v1/openai/native"
model = "DeepSeek-V3.2-Meituan"
extra_body = {
    "chat_template_kwargs": {"thinking": True}
}
```

**获取 AppId**：向美团 AIGC 团队申请

## 常见问题

### Q1: 如何切换到其他 LLM？

修改 `app.py` 中的 `create_llm()` 函数：

```python
from langchain_anthropic import ChatAnthropic

def create_llm():
    return ChatAnthropic(model="claude-3-5-sonnet-20241022")
```

### Q2: 如何处理大文件？

调整采样参数：

```python
profiler = DataProfiler(sample_size=5)  # 减少采样数
```

### Q3: 分析失败怎么办？

1. 查看终端输出的详细错误信息
2. 检查 `ba_agent.db` 中的 `conversations` 表
3. 调整 `max_retries` 参数（在 `agent_graph.py`）

### Q4: 如何自定义 System Prompt？

修改 `agent_graph.py` 中各节点的 `system_prompt`。

## 性能优化建议

1. **大表预处理**：超过 10 万行的表，建议先筛选/采样
2. **缓存语义图**：首次生成后保存，后续直接加载
3. **并发处理**：多表可并行探测（TODO）

## 开发计划

- [ ] 支持 CSV/JSON 等格式
- [ ] Web UI 界面
- [ ] 可视化结果（图表生成）
- [ ] 多轮对话优化（上下文压缩）
- [ ] 更多数据源（MySQL、API）

## 贡献指南

欢迎提交 Issue 和 PR！

## 许可证

MIT License
