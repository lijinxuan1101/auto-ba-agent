# Excel数据分析工作流系统

基于LangGraph和美团DeepSeek模型的智能Excel数据分析工作流系统。

## 📁 项目结构

```
auto-ba-agent-baseline/
├── src/                          # 核心源代码
│   ├── __init__.py              # 包初始化
│   ├── workflow.py              # LangGraph工作流实现
│   ├── api_client.py            # 美团DeepSeek API客户端
│   ├── config.py                # 配置管理
│   └── utils.py                 # 工具函数
│
├── scripts/                      # 可执行脚本
│   ├── quick_start.py           # 快速启动（预算数据）
│   ├── run_budget_analysis.py   # 详细分析（预算数据）
│   └── run_workflow.py          # 通用工作流脚本
│
├── tests/                        # 测试文件
│   └── test_workflow.py         # 工作流测试
│
├── examples/                     # 使用示例
│   └── example_usage.py         # 完整使用示例
│
├── docs/                         # 文档
│   ├── README.md                # 项目文档
│   ├── QUICKSTART.md            # 快速入门
│   ├── START_HERE.md            # 导航文档
│   ├── FILES_README.md          # 数据文件说明
│   ├── 使用说明.md              # 详细使用说明
│   ├── 如何分析预算数据.md      # 预算数据分析指南
│   ├── 项目说明.txt             # 项目概览
│   └── 📖_阅读我.txt            # 快速指南
│
├── config/                       # 配置文件
│   └── .env.example             # 环境变量模板
│
├── data/                         # 测试数据
│   └── sample_sales.xlsx        # 示例数据
│
├── files/                        # 实际数据文件
│   └── 1.1/
│       └── 渠道增长部2022-2026年预算目标to子欣.xlsx
│
├── output/                       # 输出目录（自动创建）
│
├── main.py                       # 主入口文件
├── requirements.txt              # 依赖包
└── .env                          # 环境变量配置
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置API

编辑 `.env` 文件，设置你的美团AppId：

```bash
MEITUAN_APP_ID=你的AppId
```

### 3. 运行

**方式1: 使用主入口（推荐）**
```bash
python main.py
```

**方式2: 快速分析预算数据**
```bash
python scripts/quick_start.py
```

**方式3: 详细分析预算数据**
```bash
python scripts/run_budget_analysis.py
```

**方式4: 通用分析**
```bash
python scripts/run_workflow.py
```

## 📖 核心模块说明

### src/workflow.py
LangGraph工作流核心实现，包含4个步骤：
1. **define_goal** - 定义分析目标
2. **analyze_excel** - 生成Python代码
3. **execute_python** - 执行代码
4. **final_analysis** - 生成分析报告

### src/api_client.py
美团DeepSeek API客户端，支持：
- 流式/非流式调用
- 思考模式(thinking)
- 完整的错误处理

### src/config.py
配置管理模块，统一管理：
- API配置
- 目录路径
- 模型参数

### src/utils.py
工具函数集合：
- Excel预览
- 报告保存
- 结果格式化
- 文件验证

## 🎯 使用示例

### 在代码中使用

```python
from src.workflow import ExcelAnalysisWorkflow
from src.api_client import MeituanDeepSeekClient

# 初始化
client = MeituanDeepSeekClient()
workflow = ExcelAnalysisWorkflow(
    api_call_func=lambda p: client.chat(p)
)

# 运行分析
result = workflow.run(
    query="计算每个部门的预算总额",
    excel_path="files/1.1/渠道增长部2022-2026年预算目标to子欣.xlsx"
)

# 获取结果
print(result['analysis'])
```

### 使用工具函数

```python
from src.utils import preview_excel, save_report, format_result

# 预览Excel
df = preview_excel("your_file.xlsx")

# 格式化结果
formatted = format_result(result)
print(formatted)

# 保存报告
filepath = save_report(result)
```

## ⚙️ 配置说明

`.env` 文件配置项：

```bash
# 必填
MEITUAN_APP_ID=你的AppId

# 可选（有默认值）
MEITUAN_MODEL=DeepSeek-V3.2-Meituan
TEMPERATURE=0.7
MAX_TOKENS=4000
STREAM=false
ENABLE_THINKING=true
```

## 🔍 工作流程

```
用户输入
   ↓
【步骤1】AI理解需求，定义目标
   ↓
【步骤2】读取Excel，生成Python代码
   ↓
【步骤3】执行代码，获取结果
   ↓
【步骤4】AI解读结果，生成报告
   ↓
输出分析结果
```

## 📚 文档导航

- **新手入门** → `docs/QUICKSTART.md`
- **完整导航** → `docs/START_HERE.md`
- **预算数据分析** → `docs/如何分析预算数据.md`
- **详细使用** → `docs/使用说明.md`

## 🧪 测试

```bash
# 运行测试
python tests/test_workflow.py
```

## 📦 依赖

- `langgraph` - 工作流编排
- `langchain` - LangChain框架
- `pandas` - 数据处理
- `openpyxl` - Excel读写
- `requests` - API调用
- `python-dotenv` - 环境变量管理

## 🎓 学习路径

1. 阅读 `docs/START_HERE.md` 了解整体
2. 运行 `python tests/test_workflow.py` 测试
3. 阅读 `docs/如何分析预算数据.md` 学习使用
4. 运行 `python main.py` 进行实际分析
5. 查看 `src/` 目录源码深入理解

## 📞 技术支持

- 基础使用问题 → 查看 `docs/QUICKSTART.md`
- 预算数据分析 → 查看 `docs/如何分析预算数据.md`
- API配置问题 → 检查 `.env` 文件
- 详细功能说明 → 查看 `docs/README.md`

## 📝 版本

当前版本: 1.0.0

## 📄 许可

MIT License
