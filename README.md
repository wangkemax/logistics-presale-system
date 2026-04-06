# Logistics Presale AI System

物流售前解决方案及报价系统 — 基于多 Agent 协同的 AI 售前平台

> 基于 [Logistics-Presale-AI-Team](https://github.com/wangkemax/Logistics-Presale-AI-Team) v2.2 的 Agent 架构与工作流定义

---

## 核心能力

- **招标文件智能解析** — PDF/Word 上传，AI 自动提取结构化需求
- **11 Agent 协同方案设计** — 仓储布局 + 运营设计 + 自动化推荐 + 成本建模
- **自动报价与财务分析** — ROI / IRR / NPV / 回本周期 + Excel 报价单导出
- **标书一键生成** — 10 章节专业投标文档
- **QA 质量门禁** — P0 问题自动阻断，确保交付质量
- **知识库 RAG 检索** — 自动化案例 + 成本基准 + 物流案例 语义搜索
- **实时状态推送** — WebSocket + Redis Pub/Sub 实时查看 Agent 执行进度

## 12 阶段 AI 流水线

```
Stage 0  项目假设      → Stage 1  招标文件解析  → Stage 2  需求澄清
Stage 3  数据分析      → Stage 4  知识库检索    → Stage 5  方案设计
Stage 6  自动化推荐    → Stage 7  案例匹配      → Stage 8  成本建模
Stage 9  风险评估      → Stage 10 标书撰写      → Stage 11 QA 审核 (门禁)
```

## Quick Start

```bash
# 1. 克隆
git clone https://github.com/wangkemax/logistics-presale-system.git
cd logistics-presale-system

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY 和 OPENAI_API_KEY

# 3. 启动 (API + PostgreSQL + Redis + MinIO)
docker compose up -d

# 4. 数据库迁移
docker compose exec backend alembic upgrade head

# 5. 导入知识库种子数据 (可选)
docker compose exec backend python -m app.scripts.seed_knowledge

# 6. 访问
# Frontend:  http://localhost:3000
# API Docs:  http://localhost:8000/docs
# MinIO:     http://localhost:9001 (minioadmin/minioadmin)
```

## Tech Stack

| 层 | 技术 |
|----|------|
| Frontend | Next.js 14, React 18, TailwindCSS |
| Backend | FastAPI, SQLAlchemy (async), Alembic |
| AI | Claude API, OpenAI Embeddings |
| Database | PostgreSQL 16, Redis 7 |
| Vector DB | Milvus (RAG 语义检索) |
| Storage | MinIO (S3-compatible) |
| Realtime | WebSocket, Redis Pub/Sub |
| Deploy | Docker Compose (dev), K8s (prod) |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/        # 11 个 AI Agent + orchestrator
│   │   ├── api/routes/    # REST API (auth, projects, quotations, knowledge)
│   │   ├── core/          # config, database, llm, security
│   │   ├── models/        # 8 个 SQLAlchemy ORM 模型
│   │   ├── schemas/       # Pydantic 请求/响应
│   │   ├── services/      # RAG, WebSocket, S3, Excel, PDF解析
│   │   └── scripts/       # 数据初始化脚本
│   └── alembic/           # 数据库迁移
├── frontend/
│   └── src/
│       ├── app/           # Next.js 页面
│       └── lib/           # API 客户端, 状态管理, WebSocket
├── docker-compose.yml
├── ROADMAP.md             # 开发路线图
└── PROGRESS.md            # 开发进度报告
```

## Documentation

- [ROADMAP.md](ROADMAP.md) — 完整路线图与里程碑
- [PROGRESS.md](PROGRESS.md) — 当前进度、文件清单、API 端点总览

## Development

```bash
make install          # 安装所有依赖
make dev              # 启动 backend + frontend
make migrate          # 执行数据库迁移
make reset-db         # 重置数据库
make logs             # 查看日志
```
