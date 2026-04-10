# API 文档

Logistics Presale AI System REST API 完整参考文档。

**Base URL**: `http://localhost:8000/api/v1`

**交互式文档**: 启动 backend 后访问
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

---

## 目录

- [认证](#认证)
- [项目管理](#项目管理)
- [Pipeline 执行](#pipeline-执行)
- [报价管理](#报价管理)
- [文档生成](#文档生成)
- [知识库](#知识库)
- [LLM Provider](#llm-provider)
- [用户偏好](#用户偏好)
- [Prompt 管理](#prompt-管理)
- [模板](#模板)
- [批量操作](#批量操作)
- [审批流](#审批流)
- [统计分析](#统计分析)
- [WebSocket](#websocket)
- [错误响应](#错误响应)

---

## 认证

所有 API 调用（除 `/auth/*`）都需要在 Header 中携带 JWT Token：

```http
Authorization: Bearer <your_jwt_token>
```

### POST /auth/register

注册新用户。

**Request:**
```json
{
  "email": "user@example.com",
  "password": "your_password",
  "full_name": "Max Wang"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "Max Wang",
  "created_at": "2026-04-10T10:00:00Z"
}
```

### POST /auth/login

登录获取 JWT Token。

**Request:**
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  }
}
```

---

## 项目管理

### POST /projects

创建新的售前项目。

**Request:**
```json
{
  "name": "保时捷售后备件 RDC 项目",
  "description": "上海 RDC 仓储自动化方案",
  "client_name": "保时捷中国",
  "industry": "汽车备件"
}
```

**Response 201:** Project 对象

### GET /projects

列出当前用户的所有项目。

**Response:** Project 数组

### GET /projects/{project_id}

获取项目详情（含 stages、quotations、qa_issues）。

### POST /projects/{project_id}/clone

**复制项目**。基于现有项目创建副本（含已上传文件、配置），但状态重置为 pending。

**Response 201:** 新项目对象

### DELETE /projects/{project_id}

软删除项目（级联删除 stages、quotations、qa_issues、documents）。

### POST /projects/{project_id}/upload-tender

上传招标文件（支持 PDF/Word/Excel/TXT/MD，单次最多 10 个文件）。

**Request:** `multipart/form-data` with `files` field

**Response:**
```json
{
  "uploaded": 3,
  "extracted_chars": 45000,
  "files": ["招标文件.pdf", "技术附件.xlsx", "商务条款.docx"]
}
```

---

## Pipeline 执行

### POST /projects/{project_id}/run-pipeline

启动完整 12 阶段 AI Pipeline。

**Query 参数:**
- `language`: `zh` / `en` / `bilingual`（默认 `zh`）
- `provider`: LLM provider ID（默认从用户偏好或 anthropic）
- `model`: 模型 ID（默认 provider 的 default_model）

**示例:**
```http
POST /api/v1/projects/abc-123/run-pipeline?language=bilingual&provider=deepseek&model=deepseek-chat
```

**Response:**
```json
{
  "message": "Pipeline started",
  "project_id": "abc-123",
  "language": "bilingual"
}
```

> Pipeline 异步执行。通过 WebSocket 或轮询 `/projects/{id}/stages` 获取实时进度。

### POST /projects/{project_id}/run-stage

**单 Stage 重跑**。不重跑整个 Pipeline，只重跑指定 Stage。

**Request:**
```json
{
  "stage_number": 4,
  "override_input": {}
}
```

### POST /projects/{project_id}/resume-pipeline

从最后一个失败的 Stage 继续执行。

### GET /projects/{project_id}/stages

获取所有 Stage 状态和输出。

**Response:**
```json
[
  {
    "stage_number": 1,
    "stage_name": "招标文件解析",
    "agent_name": "requirement_extractor",
    "status": "completed",
    "output_data": {...},
    "qa_result": "PASS",
    "execution_time_seconds": 12,
    "started_at": "2026-04-10T10:00:00Z",
    "completed_at": "2026-04-10T10:00:12Z"
  }
]
```

### GET /projects/{project_id}/qa-issues

获取项目的所有 QA 问题。

### PATCH /projects/{project_id}/qa-issues/{issue_id}

解决 QA 问题。

**Request:**
```json
{ "resolution": "已修正面积数据为 8000 平方米" }
```

---

## 报价管理

### POST /quotations

手动创建报价。

### POST /quotations/generate-from-pipeline

基于 Pipeline 输出（Stage 5 + Stage 8）自动生成报价。

**Query:** `project_id`

### GET /projects/{project_id}/quotations

获取项目的所有报价版本。

### PATCH /quotations/{quotation_id}

更新报价（如调整毛利率、人工成本等）。

### GET /quotations/{quotation_id}/export-excel

导出 Excel 报价单。**返回二进制 .xlsx 文件**。

### POST /quotations/compare-schemes

对比多个报价方案。

**Request:**
```json
{ "quotation_ids": ["uuid1", "uuid2", "uuid3"] }
```

---

## 文档生成

### POST /projects/{project_id}/documents/generate

生成 Word/PDF/PPT 标书文档。

**Query 参数:**
- `doc_type`: `tender` (Word) / `pdf` / `ppt`

**Response:** 二进制文件（Content-Disposition: attachment）

### GET /projects/{project_id}/documents

列出已生成的文档。

### GET /projects/{project_id}/export-bundle

🆕 **一键打包 ZIP**。打包 Word + Excel + PDF + JSON 数据为单个 ZIP 文件。

**Response:** `application/zip` 二进制流

### GET /projects/{project_id}/export

导出项目完整数据为 JSON（用于备份/迁移）。

---

## 知识库

支持 3 个分类：
- `automation_case` - 自动化案例（设备 ROI 数据）
- `cost_model` - 成本模型（P&L 数据）
- `logistics_case` - 物流案例（标书/方案文档）

### POST /knowledge

手动创建知识条目。

**Request:**
```json
{
  "category": "automation_case",
  "title": "迪士尼项目 - AGV 系统",
  "content": "项目背景：...",
  "tags": ["AGV", "迪士尼", "ROI"],
  "metadata": {
    "客户": "迪士尼",
    "投资金额": 2859963
  }
}
```

### GET /knowledge

列出知识条目。

**Query:**
- `category`: 可选筛选分类
- `limit`: 默认 50
- `offset`: 默认 0

### GET /knowledge/{entry_id}

获取单条知识详情（含 file_name 和 has_file 字段）。

### DELETE /knowledge/{entry_id}

软删除知识条目。**返回 204 No Content**。

### POST /knowledge/search

搜索知识库。先尝试 Milvus 向量搜索，不可用时降级为 PostgreSQL 关键词搜索。

**Request:**
```json
{
  "query": "汽车备件 仓储 自动化",
  "category": "automation_case",
  "top_k": 5
}
```

**Response:**
```json
[
  {
    "id": "uuid",
    "title": "迪士尼 AGV 项目",
    "content": "...",
    "score": 0.85,
    "category": "automation_case",
    "tags": "AGV,迪士尼"
  }
]
```

### POST /knowledge/upload-roi-excel

🆕 **上传 ROI Excel**。自动解析 Equipment ROI 数据，每行设备转一条知识。

**Form Data:**
- `file`: Excel 文件（含 List/Summary/总览 工作表）

**Query:**
- `project_name`: 项目名称
- `client_name`: 客户名称

**Response:**
```json
{
  "imported": 6,
  "ids": ["uuid1", "uuid2", "..."],
  "preview": [{"title": "..."}]
}
```

### POST /knowledge/upload-cost-model

🆕 **上传 Cost Model Excel**。自动解析 P&L Sheet 为成本模型条目。

**Form Data:**
- `file`: Excel 文件（含 P&L Sheet）

**Query:**
- `project_name`, `client_name`, `industry`

**Response:**
```json
{
  "imported": 1,
  "id": "uuid",
  "title": "保时捷 - RDC 上海 - 成本模型",
  "summary": {
    "revenue_items": 10,
    "cost_items": 12,
    "total_revenue": 6232123.78,
    "total_cost": 6952710.74
  }
}
```

### POST /knowledge/upload-logistics-case

🆕 **上传物流案例文档**（PDF/Word/TXT/MD）。自动提取文本入库。

**Form Data:**
- `file`: 文档文件

**Query:**
- `title` (可选), `client_name`, `industry`

### GET /knowledge/{entry_id}/download

🆕 **下载知识源文件**。返回原始上传的 Excel/PDF/Word 二进制流。

### POST /knowledge/batch-import

批量导入知识条目。

**Request:**
```json
{
  "entries": [
    {"category": "...", "title": "...", "content": "...", "tags": []},
    ...
  ]
}
```

---

## LLM Provider

### GET /llm/providers

获取所有可用 LLM Provider 和模型。

**Response:**
```json
[
  {
    "id": "anthropic",
    "label": "Claude (Anthropic)",
    "available": true,
    "models": [
      {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4"},
      {"id": "claude-haiku-4-5", "name": "Claude Haiku 4.5"}
    ],
    "default_model": "claude-sonnet-4-20250514"
  },
  {
    "id": "deepseek",
    "label": "DeepSeek",
    "available": false,
    "models": [
      {"id": "deepseek-chat", "name": "DeepSeek V3"},
      {"id": "deepseek-reasoner", "name": "DeepSeek R1"}
    ],
    "default_model": "deepseek-chat"
  }
]
```

`available: false` 表示该 Provider 的 API Key 未在 `.env` 中配置。

支持的 6 个 Provider：`anthropic`、`openai`、`deepseek`、`gemini`、`minimax`、`glm`。

---

## 用户偏好

### GET /preferences

获取当前用户偏好（默认 Provider/Model、语言等）。

### PUT /preferences

更新用户偏好。

**Request:**
```json
{
  "default_provider": "deepseek",
  "default_model": "deepseek-chat",
  "default_language": "zh"
}
```

### DELETE /preferences

重置为系统默认值。

---

## Prompt 管理

### GET /prompts

列出所有 Agent 的当前 prompt 配置。

### GET /prompts/{agent_name}

获取指定 Agent 的 prompt（默认值 + 用户覆盖值）。

### PUT /prompts/{agent_name}

覆盖 Agent 的默认 prompt。

**Request:**
```json
{
  "system_prompt": "You are an expert..."
}
```

### DELETE /prompts/{agent_name}

恢复 Agent 默认 prompt。

---

## 模板

### GET /templates

列出所有项目模板（含预设的招标解析、报价等）。

### GET /templates/{template_id}

获取模板详情。

---

## 批量操作

### POST /projects/batch/archive

批量归档项目。

**Request:**
```json
{ "project_ids": ["uuid1", "uuid2"] }
```

### POST /projects/batch/reset-stages

批量重置项目的所有 Stage。

### GET /projects/batch/stats

获取批量操作统计。

---

## 审批流

### POST /quotations/{quotation_id}/submit

提交报价审批。

### POST /quotations/{quotation_id}/approve

批准/驳回报价。

**Request:**
```json
{
  "decision": "approved",
  "comment": "数据合理，可发送客户"
}
```

### POST /quotations/{quotation_id}/send-to-client

将报价发送给客户。

### GET /quotations/{quotation_id}/history

查看报价审批历史。

---

## 统计分析

### GET /analytics/overview

获取系统总览数据（项目数、报价数、平均执行时间等）。

### GET /analytics/pipeline-stats

Pipeline 执行统计（成功率、平均时长等）。

### GET /analytics/agent-performance

各 Agent 的执行性能（平均耗时、成功率、Token 消耗）。

### GET /analytics/recent-activity

最近活动记录。

---

## WebSocket

### WS /ws/projects/{project_id}

订阅项目实时更新（Pipeline 进度、Stage 状态变化）。

**消息格式:**
```json
{
  "type": "stage_update",
  "stage_number": 5,
  "status": "running",
  "data": {...}
}
```

**消息类型:**
- `stage_update` - Stage 状态变化
- `pipeline_complete` - Pipeline 完成
- `pipeline_failed` - Pipeline 失败
- `qa_issue` - 新增 QA 问题

---

## 错误响应

所有错误返回标准 HTTP 状态码 + JSON body：

```json
{
  "detail": "Error message description"
}
```

**常见状态码:**

| Code | 说明 |
|------|------|
| 400 | 请求参数错误 |
| 401 | 未认证（缺少或无效 Token） |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 请求体校验失败（Pydantic） |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（如 Milvus 离线） |

---

## 12 个 AI Agent 列表

| # | Agent | 用途 | 输入依赖 |
|---|-------|------|---------|
| 0 | 项目假设 | 手动输入项目背景 | — |
| 1 | RequirementExtractor | 招标文件解析 | uploaded files |
| 2 | RequirementClarifier | 需求澄清和补全 | Stage 1 |
| 3 | DataAnalyst | Excel/CSV 数据分析 | Stage 1 |
| 4 | KnowledgeBase | 知识库 RAG 检索 | Stage 1, 2 |
| 5 | LogisticsArchitect | 仓库方案设计 | Stage 1, 3, 4 |
| 6 | AutomationSolution | 自动化设备推荐 | Stage 1, 4, 5 |
| 7 | Benchmark | 历史案例对标 | Stage 1, 4 |
| 8 | CostModel | 成本建模和报价 | Stage 1, 4, 5, 6 |
| 9 | RiskCompliance | 风险与合规评估 | Stage 1, 5 |
| 10 | TenderWriter | 标书撰写（10 章节） | Stages 1-9 |
| 11 | QAAgent | 质量审核和打分 | Stage 10 |

---

## 使用示例

### 完整 Pipeline 执行流程

```bash
# 1. 登录
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass"}' | jq -r .access_token)

# 2. 创建项目
PROJECT_ID=$(curl -s -X POST http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"测试项目","client_name":"客户A","industry":"汽车"}' | jq -r .id)

# 3. 上传招标文件
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/upload-tender" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@招标文件.pdf"

# 4. 启动 Pipeline
curl -X POST "http://localhost:8000/api/v1/projects/$PROJECT_ID/run-pipeline?language=zh&provider=deepseek" \
  -H "Authorization: Bearer $TOKEN"

# 5. 轮询查看进度
curl "http://localhost:8000/api/v1/projects/$PROJECT_ID/stages" \
  -H "Authorization: Bearer $TOKEN"

# 6. 完成后下载完整交付包
curl -OJ "http://localhost:8000/api/v1/projects/$PROJECT_ID/export-bundle" \
  -H "Authorization: Bearer $TOKEN"
```

### Python SDK 示例

```python
import httpx

BASE_URL = "http://localhost:8000/api/v1"

# 登录
res = httpx.post(f"{BASE_URL}/auth/login", json={
    "email": "user@example.com",
    "password": "pass"
})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 创建项目
project = httpx.post(f"{BASE_URL}/projects", json={
    "name": "测试项目",
    "client_name": "客户A",
    "industry": "汽车"
}, headers=headers).json()

# 上传文件
with open("招标文件.pdf", "rb") as f:
    httpx.post(
        f"{BASE_URL}/projects/{project['id']}/upload-tender",
        files={"files": f},
        headers=headers
    )

# 启动 Pipeline
httpx.post(
    f"{BASE_URL}/projects/{project['id']}/run-pipeline",
    params={"language": "zh", "provider": "deepseek"},
    headers=headers
)
```

---

## OpenAPI Schema

完整的 OpenAPI 3.0 schema 可从 backend 直接获取：

```bash
curl http://localhost:8000/openapi.json > openapi.json
```

可以导入 Postman、Insomnia 或生成各语言的客户端 SDK：

```bash
# 生成 TypeScript SDK
npx @openapitools/openapi-generator-cli generate \
  -i http://localhost:8000/openapi.json \
  -g typescript-axios \
  -o ./client-ts

# 生成 Python SDK
openapi-generator generate \
  -i http://localhost:8000/openapi.json \
  -g python \
  -o ./client-py
```

---

**最后更新**: 2026-04-10
**API 版本**: v1
**对应系统版本**: v1.0.0
