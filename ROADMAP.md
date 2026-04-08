# Roadmap — 物流售前解决方案及报价系统

> 基于 [Logistics-Presale-AI-Team](https://github.com/wangkemax/Logistics-Presale-AI-Team) v2.2 Agent 架构
> 最后更新：2026-04-07

---

## 项目愿景

将 YAML Agent 定义与工作流编排蓝图，落地为**可交付的 Web 产品**：
上传招标文件 → AI 多 Agent 协同分析 → 生成方案 + 报价 + 标书 → QA 质量门禁

---

## Phase 1：MVP — 核心流程跑通 (Week 1-8)

> **目标**：上传招标 PDF → 自动解析需求 → 生成方案初稿 + 成本报价

| 模块 | 任务 | 状态 | 说明 |
|------|------|------|------|
| **基础设施** | 项目脚手架 (monorepo) | ✅ 完成 | Next.js + FastAPI + Docker Compose |
| | 数据库设计 (8 表) | ✅ 完成 | PostgreSQL, SQLAlchemy ORM |
| | Alembic 迁移 | ✅ 完成 | 初始迁移 001_initial |
| | JWT 认证 (RBAC) | ✅ 完成 | admin / consultant / client 三角色 |
| | 文件上传服务 | ✅ 完成 | S3/MinIO, 预签名 URL |
| | WebSocket 通信 | ✅ 完成 | Redis Pub/Sub 跨实例广播 |
| | CI/CD | ✅ 完成 | GitHub Actions (lint + build + docker) |
| **Agent 引擎** | Agent 基类 | ✅ 完成 | 超时/重试/自校验/JSON 解析 |
| | CEO Agent (编排器) | ✅ 完成 | 12 阶段流水线 + WS 通知 |
| | 需求提取 Agent | ✅ 完成 | PDF/Word 解析 + 结构化提取 |
| | 需求澄清 Agent | ✅ 完成 | 缺失数据识别 + 澄清问题生成 |
| | 数据分析 Agent | ✅ 完成 | 订单/SKU/容量分析 |
| | 知识库 Agent | ✅ 完成 | RAG 查询生成 + 知识综合 |
| | 方案设计 Agent | ✅ 完成 | 仓储布局 + 运营设计 + 技术选型 |
| | 自动化推荐 Agent | ✅ 完成 | 设备推荐 + ROI 评分 |
| | 案例匹配 Agent | ✅ 完成 | 相似度评分 + 经验提取 |
| | 成本建模 Agent | ✅ 完成 | 5 年 CAPEX/OPEX + ROI/IRR/NPV |
| | 风险评估 Agent | ✅ 完成 | 风险矩阵 + 合规检查 |
| | 标书撰写 Agent | ✅ 完成 | 10 章节标书内容生成 |
| | QA Agent | ✅ 完成 | P0/P1/P2 门禁 + 阻断逻辑 |
| **知识库** | RAG 检索服务 | ✅ 完成 | Milvus + OpenAI Embedding + 混合搜索 |
| | 知识库 API (CRUD + 搜索) | ✅ 完成 | 语义检索 + 批量导入 |
| | 种子数据 | ✅ 完成 | 7 条行业样本 (自动化/成本/案例) |
| **报价引擎** | 报价 API | ✅ 完成 | 从 pipeline 自动生成 + 手动调整 |
| | Excel 报价单 | ✅ 完成 | 4 Sheet 专业格式 (openpyxl) |
| | 财务指标计算 | ✅ 完成 | ROI/IRR/NPV/回本周期 (Agent 内置) |
| **前端** | Dashboard 首页 | ✅ 完成 | 项目列表 + 统计卡片 + 新建弹窗 |
| | 项目详情页 | ✅ 完成 | 流水线可视化 + 报价 + QA 三 Tab |
| | 登录/注册 | ✅ 完成 | JWT 认证流 |
| | API 客户端 | ✅ 完成 | 类型化 fetch 封装 |
| | WebSocket Hook | ✅ 完成 | 自动连接 + 心跳 + 断线重连 |
| | 前端 WS 集成到页面 | ✅ 完成 | Toast + 实时进度 + 连接指示器 |
| **文档处理** | PDF/Word 文本提取 | ✅ 完成 | pdfplumber + python-docx |

### Phase 1 完成率：**100%** ✓

---

## Phase 2：核心增强 — 文档生成与体验优化 (Week 9-14)

> **目标**：完整的文档输出能力 + 精细化的用户体验

| 模块 | 任务 | 状态 | 说明 |
|------|------|------|------|
| **文档生成** | 标书 Word 生成器 | ✅ 完成 | 封面 + 8章节 + 需求表 + 风险矩阵 |
| | 方案 PPT 生成器 | ✅ 完成 | 12页16:9 含表格+KPI卡片 |
| | PDF 导出 | ✅ 完成 | reportlab 纯 Python PDF 生成 |
| **前端增强** | 方案设计工作台 | ✅ 完成 | 5-tab 可视化(总览/仓库/运营/技术/人员) |
| | 报价工作台 | ✅ 完成 | 12 参数滑块 + 实时计算 + 5年现金流 |
| | 标书编辑器 | ✅ 完成 | 章节编辑 + AI 改写/扩展/润色 + 撤销 |
| | QA 审核面板 | ✅ 完成 | 按阶段分组 + 解决/接受 + 重跑阶段 |
| | 知识库浏览页 | ✅ 完成 | 语义搜索 + 分类 + 详情 + 添加 |
| **Agent 优化** | Prompt 精调 | ✅ 完成 | 运行时热更新 + 缓存自动失效 |
| | 多方案并行 | ✅ 完成 | 经济/均衡/高端 3方案 AI 生成 |
| | Agent 缓存 | ✅ 完成 | SHA256 输入哈希 + 24h TTL |

---

## Phase 3：生产就绪 (Week 15-18)

| 模块 | 任务 | 状态 | 说明 |
|------|------|------|------|
| **运维** | CI/CD Pipeline | ✅ 完成 | GitHub Actions → Docker → K8s |
| | 监控告警 | ✅ 完成 | /metrics endpoint + MetricsMiddleware |
| | 日志聚合 | ✅ 完成 | structlog JSON lines + request logging |
| **安全** | 安全审计 | ✅ 完成 | Security headers + input sanitization + HSTS |
| | API 限流 | ✅ 完成 | Redis 滑动窗口 + 分组限速 |
| | 数据加密 | ✅ 完成 | Fernet (AES-128-CBC) + PBKDF2 |
| **性能** | 数据库索引优化 | ✅ 完成 | 7 个组合索引 (002_indexes) |
| | LLM 调用优化 | ✅ 完成 | Stage 2/3/4 并行 + Stage 6/7 并行 |
| **测试** | 单元测试 | ✅ 完成 | 20+ test cases (agents/services/security) |
| | E2E 测试 | ✅ 完成 | 20-step integration test suite |
| | UAT | 🔲 待做 | 真实招标文件验证 |

---

## Phase 4：扩展功能 (Week 19+)

| 功能 | 说明 |
|------|------|
| 多语言支持 | 英文招标文件解析 + 双语标书生成 |
| 客户协作门户 | 客户端查看方案 + 在线反馈 |
| 项目模板 | ✅ 完成 — 6 套行业模板 |
| 报价审批流 | ✅ 完成 — 提交/审核/驳回/发送客户 |
| 数据分析看板 | ✅ 完成 — 项目统计/Agent 性能/Pipeline 指标 |
| 移动端适配 | ✅ 完成 — PWA manifest + Service Worker + 离线页面 |
| 私有化 LLM | 本地大模型部署 (降低 API 成本) |

---

## 技术架构总览

```
Frontend: Next.js 14 + React 18 + TailwindCSS
Backend:  FastAPI + SQLAlchemy (async) + Alembic
AI:       Claude API + LangGraph + RAG (Milvus)
Storage:  PostgreSQL + Redis + MinIO (S3)
Deploy:   Docker Compose (dev) → K8s (prod)
```

## 关键指标目标

| 指标 | MVP 目标 | 生产目标 |
|------|---------|---------|
| 招标文件解析时间 | < 5 分钟 | < 2 分钟 |
| 全流程耗时 (12 阶段) | < 30 分钟 | < 15 分钟 |
| 方案设计准确度 | 人工审核通过 | 80%+ 免审 |
| 报价误差 | < 20% | < 10% |
| QA P0 漏检率 | < 10% | < 2% |
