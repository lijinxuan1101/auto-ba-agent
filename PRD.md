
# 商业分析 Agent (Auto-BA Agent) 详细需求文档

## 1. 项目愿景

打造一个“即插即用”的商业分析专家。用户上传任意结构的多张 Excel 表格后，Agent 能够自主探测数据含义、推导表间关联、并执行复杂的跨表分析任务。

## 2. 核心技术栈

* **LLM:** DeepSeek-V3.2-Meituan 
接入方式
```
curl --location 'https://aigc.sankuai.com/v1/openai/native/chat/completions' \
--header 'Authorization: Bearer 申请的AppId' \
--header 'Content-Type: application/json' \
--data '{
    "model": "DeepSeek-V3.2-Meituan",
    "messages": [
        {
            "role": "user",
            "content": "给我说2个科学家的名字"
        }
    ],
    "stream": true,
    "chat_template_kwargs": {
        "thinking": true
    }
}'
```



## 3. 核心业务流程 (The Loop)

### 3.1 自动 Schema 探测与采样 (Data Profiling)

* **逻辑**：系统不应只读取列名，必须进行“深度采样”。
* **动作**：
1. 提取所有 Sheet 的列名、Dtypes 和空值率。
2. 对每一列执行 `unique()` 操作，提取 Top 5-10 个样本值。
3. 记录数值列的分布特征（Min, Max, Mean）。


* **目标**：为 LLM 推理提供足够的“数据指纹”。

### 3.2 动态语义对齐推理 (Dynamic Semantic Alignment)

* **逻辑**：利用 DeepSeek 的推理能力，在无外键约束的情况下构建逻辑关系。
* **输入**：各表的 Profiling 数据。
* **输出**：一个名为 `semantic_map` 的 JSON 结构，定义如下：
```json
{
  "nodes": [{"table": "T1", "desc": "..."}],
  "edges": [{"from": "T1.col_A", "to": "T2.col_B", "logic": "JOIN", "confidence": 0.9}]
}

```

### 3.3 闭环代码生成与验证 (Reasoning-Code-Check Loop)

***步骤 1：意图解析与策略路由 (Intent Routing)***

Agent 拿到 Query 后，不直接查 semantic_map，而是先思考：识别分析类型：是“描述性分析”（算总数）、“诊断性分析”（找原因）、还是“关联性分析”（跨表找关系）？按需提取子图：根据意图，从庞大的 semantic_map 中只提取必要的表和关联路径。例子：如果用户只问“本月销量”，即便 semantic_map 里有“用户详情”和“仓库位置”，也应直接忽略，避免引入多余的 Join 增加出错率。

***步骤 2：逻辑路径规划 (Logical Planning)***

基于意图，输出一份“伪代码计划”：
Plan: "1. 过滤订单表 A 的 2026 年数据 -> 2. 关联产品表 B 获取单价 -> 3. 计算 Total_Sales。"
关键点：这一步是纯逻辑，不涉及具体语法，目的是为了让 DeepSeek 在“写代码”前先对齐思路。

***步骤 3：代码生成 (Code Generation)***

根据规划，生成具体的 Python/Pandas 代码。
优先级：优先使用 pd.merge(how='left') 以保留主表数据，除非用户明确要求找“交集”。

***步骤 4：闭环验证与纠错 (Verify & Correct)***

不仅看报错 (Traceback)：还要看数据逻辑对不对。
逻辑检查：如果 Join 之后的行数比原表还多（产生了笛卡尔积），即使代码没报错，Agent 也要判定为“失败”，并反馈给推理节点重新检查 join_key。



