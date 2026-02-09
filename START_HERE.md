# 🚀 开始使用商业分析 Agent

## 第一步：设置环境

### 1. 创建 `.env` 文件

在项目根目录创建 `.env`，写入：

```
AIGC_APP_ID=你申请的AppId
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

---

## 第二步：选择运行方式

### 方式 A：快速体验（推荐新手）

```bash
python quick_start.py
```

这会：
- ✅ 自动创建示例数据（订单、产品、客户）
- ✅ 运行 3 个示例分析
- ✅ 展示完整流程

### 方式 B：使用自己的数据

```python
from app import BAAgentApp

app = BAAgentApp()
app.load_excel("你的Excel文件路径.xlsx")
app.analyze("你的问题")
```

### 方式 C：交互式模式

```bash
python -c "from example import example_interactive_mode; example_interactive_mode()"
```

---

## 第三步：验证结果

### 查看生成的代码

```python
app.get_history()  # 会显示生成的 Python/Pandas 代码
```

### 查看数据库

```bash
sqlite3 ba_agent.db "SELECT * FROM conversations ORDER BY timestamp DESC LIMIT 5;"
```

---

## 项目文件说明

| 文件 | 说明 |
|------|------|
| `quick_start.py` | 一键启动脚本 |
| `app.py` | 主应用（BAAgentApp 类）|
| `example.py` | 使用示例 |
| `create_sample_data.py` | 生成测试数据 |
| | |
| `data_profiler.py` | 数据探测（Schema + 采样）|
| `semantic_mapper.py` | 语义对齐（表关系推理）|
| `agent_graph.py` | LangGraph 闭环流程 |
| `persistence.py` | SQLite 持久化 |
| | |
| `PRD.md` | 产品需求文档 |
| `README.md` | 项目概览 |
| `USAGE_GUIDE.md` | 详细使用指南 |

---

## 核心流程图

```
用户上传 Excel
      ↓
┌─────────────────┐
│1. 数据探测      │ → 提取列特征、样本值、统计信息
└────────┬────────┘
         ↓
┌─────────────────┐
│2. 语义对齐      │ → DeepSeek 推断表间关联
└────────┬────────┘
         ↓
┌─────────────────┐
│3. 用户提问      │
└────────┬────────┘
         ↓
┌─────────────────┐
│4. LangGraph流程 │
│  ├ 意图识别     │ → 分析问题类型、涉及的表
│  ├ 逻辑规划     │ → 输出伪代码计划
│  ├ 代码生成     │ → 生成 Pandas 代码
│  └ 执行验证     │ → 运行 + 逻辑检查（笛卡尔积）
│      │          │
│      ├ 成功 → 返回结果
│      └ 失败 → 重新规划（最多3次）
└─────────────────┘
         ↓
┌─────────────────┐
│5. 持久化存储    │ → 保存到 SQLite
└─────────────────┘
```

---

## 下一步

1. ✅ 运行 `quick_start.py` 体验完整流程
2. ✅ 尝试用自己的 Excel 数据
3. ✅ 查看 `USAGE_GUIDE.md` 了解高级用法
4. ✅ 阅读 `PRD.md` 了解设计理念

Happy Analyzing! 🎉
