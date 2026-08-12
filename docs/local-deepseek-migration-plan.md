# DeepSeek + 本地数据层重构计划

## 目标

将项目从 Google Cloud 托管架构迁移为本地数据架构：

- DeepSeek API 负责 Agent 推理和工具调用；
- Google ADK 仅作为本地 Agent 编排框架；
- DuckDB 保存性能数据、Cell Trace、KPI、Incident 和分析结果；
- 本地 JSON/Markdown 提供 RCA 规则和内部文档；
- 本地相似度算法搜索历史 Incident；
- 不再需要 Google Cloud 项目、ADC、BigQuery、Vertex AI Search 或 Terraform。

## 目标架构

```text
ADK Agent -> DeepSeek API
    |
    +----> DuckDB (.local/telco_demo.duckdb)
    +----> data/rca-rules/*.json
    +----> docs/*.md
    +----> .local/logs/*.jsonl
```

## 保留边界

保留现有 Incident Detector、RCA Root Agent、专职子 Agent、Session State、动态工具集和人工审批。重构集中在模型、存储、规则检索、相似事故检索与日志层。

## 实施阶段

| 阶段 | 内容 | 状态 |
|---|---|---|
| 0 | 固化计划和验收标准 | 完成 |
| 1 | 共享配置、DeepSeek 模型工厂、最小工具调用能力 | 完成 |
| 2 | DuckDB Schema、CSV 初始化和数据访问层 | 完成 |
| 3 | 迁移 Incident Detector | 完成 |
| 4 | 迁移 RCA 数据工具和 Incident 更新 | 完成 |
| 5 | 本地规则、内部文档、外部文档与相似事故检索 | 完成 |
| 6 | 移除 Google Cloud/Terraform 活动依赖，更新文档 | 完成 |
| 7 | 离线测试、DeepSeek 联调和端到端验收 | 完成 |

## 验收标准

1. 新环境只需 Python 和 DeepSeek API Key。
2. `python -m telco_local.init_db` 可重复执行并初始化本地数据库。
3. `adk web` 可以同时加载 `incident_detector` 和 `root_cause_analysis`。
4. Incident Detector 能发现异常并写入本地 Incident 表。
5. RCA Agent 能检索规则、查询 Trace、判断严重度、生成并回写报告。
6. 运行路径中不存在 `google.cloud`、BigQuery、Discovery Engine、Vertex AI 或 ADC 依赖。
7. 原始 IMSI、MSISDN、IMEISV 默认不发送给 DeepSeek。
8. 核心数据工具具有无需 API Key 的离线测试。

## 风险与处理

- DeepSeek Tool Calling 与 ADK 兼容性：先以单工具冒烟测试验证。
- CSV 类型推断差异：初始化时显式转换时间字段，KPI 使用固定 SQL。
- 原 BigQuery 嵌套字段：在 DuckDB Incident 表中使用 JSON 保存 `kpi_missed`。
- 相似事故语义能力下降：第一版使用本地 TF-IDF，接口保持可替换。
- 外部资料不可用：默认关闭外部抓取，不阻塞 RCA 主流程。
- 敏感标识泄漏：仅向模型提供聚合统计和脱敏 Incident。

## 目标运行命令

```powershell
cd agents
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m telco_local.init_db
python -m telco_local.smoke_test
python -m telco_local.e2e_test
.\start_web.ps1
```

## 当前验证记录

- DuckDB 初始化：13,440 条 Performance、579 条 Cell Trace；
- KPI 基准：首行 E-RAB 成功率 `99.768%`，retainability `1.5497`；
- 离线测试：8 项通过；
- 依赖检查：无破损依赖；
- ADK Web：启动成功，共发现 12 个主 Agent/子 Agent；
- 云端活动依赖扫描：未发现 BigQuery、Vertex AI、Discovery Engine 或 ADC 引用；
- DeepSeek 工具调用冒烟：通过，Agent 成功调用本地健康检查工具；
- Incident Detector → RCA 真实端到端验收：通过，覆盖异常发现、事故创建、规则检索、Trace 聚合、分析、严重度、内外部资料、相似事故和报告生成；
- 人工审批边界：端到端验收未执行模拟动作且未写回未批准报告；批准后的报告写回由离线测试覆盖；
- DeepSeek 多工具调用已在根 Agent 回调层串行化，避免有状态 RCA 阶段的并行竞态。
