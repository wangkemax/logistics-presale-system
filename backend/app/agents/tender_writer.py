"""Stage 10: Tender Writer Agent.

Generates professional tender documents with:
- Data-driven content referencing actual pipeline analysis results
- Structured tables (markdown) for key data points
- Calculation logic transparency (showing how numbers are derived)
- Chinese as primary language with English section subtitles
- Chapter-by-chapter generation to produce full-length documents
"""

import json
import asyncio
import structlog

from app.agents.base import BaseAgent

logger = structlog.get_logger()

CHAPTERS = [
    {
        "number": 1,
        "title": "公司简介 (Company Profile)",
        "prompt_template": """撰写投标文件第1章：公司简介。

要求：
- 包含公司概况、核心业务能力、行业经验
- 列出质量认证体系（如ISO9001、IATF16949等）
- 说明在{industry}行业的服务经验和客户案例
- 提供网络布局和团队规模数据
- 使用表格呈现关键资质信息

注意：部分信息用[请填写]标注，供投标方补充。""",
        "data_keys": ["requirements"],
    },
    {
        "number": 2,
        "title": "仓库运营设计 (Warehouse Operation Design)",
        "prompt_template": """撰写投标文件第2章：仓库运营设计。这是整份标书最核心的章节。

必须包含以下子章节，每个子章节使用表格呈现关键数据：

### 2.1 选址方案 (Location Proposal)
- 基于项目需求推荐选址区域
- 用表格列出：地址、到客户工厂距离、往返时间
- 说明选址逻辑

### 2.2 仓库建筑规格 (Building Specifications)
- 用表格列出：总面积、净高、码头数、消防要求、电力等
- 部分信息标注[请填写]

### 2.3 仓库布局设计 (Layout Design)
- 功能分区表格：区域名称、面积(㎡)、位置、物流动线
- 物流动线原则说明
- 温湿度检测点布局表格（如适用）

### 2.4 货架与存储设计 (Rack and Shelving Design)
- 表格：区域、货架类型、层数、单层净高、承重、托盘位数
- 设计要点说明

### 2.5 运营组织方案 (Operation Organization Plan)
- 人力计算逻辑表格：岗位类型、计算基础、效率标准、人数推算
- 组织架构图（用文字树形结构）
- 关键岗位资质要求表格

### 2.6 设备与IT方案 (MHE and IT Devices Plan)
- 物料搬运设备表格：设备、品牌建议、型号、数量、用途
- IT设备表格：设备、品牌、数量、用途

## 分析数据
{data}

每个小节必须有至少一个表格。引用实际分析数据中的数字。""",
        "data_keys": ["solution", "data_analysis", "requirements"],
    },
    {
        "number": 3,
        "title": "运输线路设计 (Transportation/Milk Run Design)",
        "prompt_template": """撰写投标文件第3章：运输/配送线路设计。

包含：
### 3.1 资源计算逻辑 (Calculation Logic)
- 说明车辆和人员计算方法论
- 公式：所需车辆数 = 日运行总时长 ÷ 单车可用时长

### 3.2 资源配置方案 (Resource Arrangement)
- 逐线路计算表格：线路、日运行时长、车辆数、班次、司机数、计算说明
- 车队配置表格：线路、车型、品牌建议、特殊配置、来源
- 如适用，提供电动车 vs 燃油车对比表（月租、能源费、维保、总成本、年节省）

## 分析数据
{data}

如果没有具体线路数据，基于行业经验和仓库吞吐量推算配送需求。""",
        "data_keys": ["solution", "data_analysis", "requirements"],
    },
    {
        "number": 4,
        "title": "自动化与数字化方案 (Automation and Digitalization Concept)",
        "prompt_template": """撰写投标文件第4章：自动化与数字化方案。

### 4.1 方案总览
- 响应客户需求中的自动化场景
- 总览表格：序号、场景、方案、投资(万元)、实施阶段
- 汇总：总投资、Phase 1投资、年节省

### 4.2 实施路线图
- 分Phase列出实施计划（Phase 1: Go-Live前, Phase 2: 稳定期, Phase 3: 优化期）
- 每个Phase的具体内容和时间

### 4.3 差异化技术亮点
- 选择1-2个技术亮点展开说明（如电动车方案、视觉检测、无人机盘点等）
- 用对比表展示技术优势

## 分析数据
{data}

引用自动化推荐Agent的具体建议和ROI数据。""",
        "data_keys": ["automation", "solution"],
    },
    {
        "number": 5,
        "title": "项目实施方案 (Project Implementation)",
        "prompt_template": """撰写投标文件第5章：项目实施方案。

### 5.1 实施组织架构 (Implementation Organization)
- 用文字树形图展示项目组织架构
- 关键实施成员资质要求

### 5.2 搬迁流程与资源 (Relocation Process)
- 搬迁计划表格：阶段、时间、日均量、增配资源、关键措施
- 搬迁风控措施（清单形式）

### 5.3 Go-Live后稳定方案 (Stabilization Plan)
- 稳定期措施表格：时段、措施、负责人

### 5.4 实施时间线 (Timeline)
- 里程碑表格：时间、里程碑、关键活动
- 标注关键Go-Live日期（用★标记）

## 分析数据
{data}

时间线要具体到月份，里程碑要可衡量。""",
        "data_keys": ["solution", "risks"],
    },
    {
        "number": 6,
        "title": "补充信息 (Additional Information)",
        "prompt_template": """撰写投标文件第6章：补充信息。

### 6.1 质量管理体系
- 质量体系认证和流程清单
- 审核和改善机制

### 6.2 风险管理
- 已识别风险汇总表：风险等级、数量、关键风险
- 业务连续性计划(BCP)覆盖范围

### 6.3 报价假设条件
- ⚠️ 假设条件表格：编号、假设、当前值、偏差影响说明
- 注明"如实际偏差>20%则需重新报价"

## 分析数据
{data}

风险管理引用Stage 9的分析结果。假设条件要具体、可衡量。""",
        "data_keys": ["risks", "cost_model"],
    },
]


class TenderWriterAgent(BaseAgent):
    name = "tender_writer"
    description = "生成专业投标文档内容（数据驱动、表格丰富、计算透明）"
    stage_number = 10
    timeout_minutes = 30

    @property
    def system_prompt(self) -> str:
        return """你是一位服务于世界500强客户（如Porsche、Bosch、BMW等）的资深物流投标文件撰写专家。
你撰写的投标文件以数据驱动、结构清晰、专业可信著称。你的标书帮助LSP赢得了多个年合同金额过千万的仓储项目。

## 写作风格要求

1. **数据驱动**：每个论点都用具体数字支撑。引用分析数据中的实际数值，如面积、吞吐量、人员编制、投资金额。数字必须来源于输入数据，不能凭空编造
2. **表格密集**：每个子章节至少包含一个Markdown表格。表格是投标文件的核心信息载体
3. **计算透明**：展示推导过程。例如：
   - 人力需求 = 日均出库量490托 ÷ 人均效率18托/班 = 27人 → 含轮班系数1.15 ≈ 31人
   - 仓库面积 = RDC区3,500㎡ + 暂存500㎡ + 温控1,200㎡ + 通道1,000㎡ = ~6,200㎡
4. **中英双语标题**：章节和子章节标题使用"中文 (English)"格式
5. **专业术语**：正确使用物流行业术语（VDA标签、Milk Run、Kitting、FMEA、8D、PSS、PEQ、SFM、CTU、AGV、WCS、SAP EWM）
6. **留白标注**：需要投标方补充的信息标注[请填写]，如公司名称、仓库地址、租赁方信息
7. **差异化亮点**：每章至少提出1个差异化优势（绿色物流、数字孪生、零买断风险、自有车队等）
8. **组织架构图**：用文字树形结构（如├──、│、└──）展示组织和流程层级
9. **风险意识**：关键假设标注"如实际偏差>20%则需重新报价"
10. **5年视角**：人力规划、成本模型、效率提升都要展示5年趋势

## 格式规范

- 使用Markdown格式（标题、表格、列表、粗体）
- 表格使用 | 列1 | 列2 | 列3 | 格式，表头下方用 |------|------|------| 分隔
- 每章至少1500字，核心章节（第2章仓库运营设计）至少3000字
- 不要输出JSON，直接输出Markdown正文
- 不要重复章节编号和标题（调用方会添加）
- 子章节使用 ### 格式"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        all_outputs = input_data.get("all_stage_outputs", {})
        data_map = self._build_data_map(all_outputs)

        industry = project_context.get("industry", "物流")
        context_str = json.dumps(project_context, ensure_ascii=False, default=str)[:800]

        # Generate chapters in pairs for speed
        chapters = [None] * len(CHAPTERS)
        summary_parts = []

        for batch_start in range(0, len(CHAPTERS), 2):
            batch = CHAPTERS[batch_start: batch_start + 2]
            tasks = [
                self._write_chapter(ch_def, data_map, context_str, industry, project_context)
                for ch_def in batch
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for ch_def, result in zip(batch, results):
                idx = ch_def["number"] - 1
                if isinstance(result, Exception):
                    content = f"[章节生成失败: {str(result)[:200]}]"
                    logger.error("tender_chapter_failed", chapter=ch_def["number"], error=str(result))
                else:
                    content = result
                    logger.info("tender_chapter_done", chapter=ch_def["number"], words=len(content))

                chapters[idx] = {
                    "chapter": ch_def["number"],
                    "title": ch_def["title"],
                    "content": content,
                    "word_count": len(content),
                }
                first_line = content.split("\n")[0].strip()[:120]
                summary_parts.append(f"第{ch_def['number']}章 {ch_def['title']}：{first_line}")

        # Generate executive summary
        exec_summary = await self._write_executive_summary(summary_parts, context_str, project_context)

        valid_chapters = [ch for ch in chapters if ch and ch["word_count"] > 50]
        total_words = sum(ch["word_count"] for ch in valid_chapters)

        return {
            "document_structure": valid_chapters,
            "executive_summary": exec_summary,
            "key_differentiators": self._extract_differentiators(valid_chapters),
            "total_word_count": total_words,
            "chapters_completed": len(valid_chapters),
            "chapters_total": len(CHAPTERS),
            "_confidence": 0.90 if total_words > 8000 else 0.70 if total_words > 4000 else 0.50,
        }

    async def _write_chapter(
        self, ch_def: dict, data_map: dict, context_str: str, industry: str,
        project_context: dict | None = None,
    ) -> str:
        """Write a single chapter using the chapter-specific prompt template."""
        relevant_data = {}
        for key in ch_def.get("data_keys", []):
            if key in data_map:
                relevant_data[key] = data_map[key]

        data_str = json.dumps(relevant_data, ensure_ascii=False, default=str)[:6000] if relevant_data else "暂无具体数据，请基于行业最佳实践撰写，关键数据标注[待确认]"

        prompt = ch_def["prompt_template"].format(
            data=data_str,
            industry=industry,
            context=context_str,
        )

        prompt += f"\n\n## 项目背景\n{context_str}"
        prompt += f"\n\n请直接输出本章Markdown正文内容（至少1500字，核心章节3000字）。"

        return await self.call_llm(prompt, max_tokens=4096, project_context=project_context)

    async def _write_executive_summary(
        self, parts: list[str], context_str: str, project_context: dict | None = None,
    ) -> str:
        """Generate executive summary from chapter summaries."""
        parts_text = "\n".join(f"- {p}" for p in parts)

        prompt = f"""基于以下各章节要点，撰写一份500-800字的执行摘要。

## 项目背景
{context_str}

## 各章节核心要点
{parts_text}

要求：
- 开头一段概述项目理解和方案定位
- 中间段落覆盖：方案亮点、关键数据、差异化优势
- 结尾段表达合作诚意和服务承诺
- 包含至少3个关键数据指标（面积、人员、投资等）
直接输出摘要正文。"""

        return await self.call_llm(prompt, max_tokens=2000, project_context=project_context)

    def _build_data_map(self, all_outputs: dict) -> dict:
        """Extract and organize key data from all stage outputs."""
        def get(num):
            return all_outputs.get(num, all_outputs.get(str(num), {}))

        reqs = get(1)
        solution = get(5)
        automation = get(6)
        cost_model = get(8)
        risks = get(9)
        data_analysis = get(3)

        return {
            "requirements": {
                "count": len(reqs.get("requirements", [])),
                "top_items": reqs.get("requirements", [])[:15],
                "project_overview": reqs.get("project_overview", {}),
                "key_metrics": reqs.get("key_metrics", {}),
                "missing_info": reqs.get("missing_critical_info", []),
            },
            "solution": {
                "executive_summary": solution.get("executive_summary", "")[:1000],
                "warehouse_design": solution.get("warehouse_design", {}),
                "operations_design": solution.get("operations_design", {}),
                "technology": solution.get("technology", {}),
                "staffing": solution.get("staffing", {}),
                "performance": solution.get("performance", {}),
            },
            "data_analysis": {
                "summary": json.dumps(data_analysis, ensure_ascii=False, default=str)[:2000],
            },
            "automation": {
                "level": automation.get("automation_level", ""),
                "recommendations": automation.get("recommendations", [])[:8],
                "total_investment": automation.get("total_investment_cny", 0),
            },
            "cost_model": {
                "pricing": cost_model.get("pricing", {}),
                "financial_indicators": cost_model.get("financial_indicators", {}),
                "cost_breakdown": {
                    k: v.get("year1", 0) if isinstance(v, dict) else v
                    for k, v in cost_model.get("cost_breakdown", {}).items()
                },
            },
            "risks": {
                "overall_level": risks.get("overall_risk_level", ""),
                "risk_matrix": risks.get("risk_matrix", [])[:10],
                "compliance": risks.get("compliance_status", {}),
                "top_3_risks": risks.get("top_3_risks", []),
            },
        }

    def _extract_differentiators(self, chapters: list[dict]) -> list[str]:
        """Extract key differentiators from generated content."""
        diffs = []
        keywords = ["优势", "领先", "独特", "差异化", "创新", "亮点", "节省", "提升", "保障"]
        for ch in chapters:
            for line in ch.get("content", "").split("\n"):
                s = line.strip()
                if any(kw in s for kw in keywords) and 15 < len(s) < 100 and not s.startswith("|") and not s.startswith("#"):
                    diffs.append(s.lstrip("- *"))
                    if len(diffs) >= 6:
                        return diffs
        return diffs or ["数据驱动的物流解决方案", "透明的成本计算模型", "分阶段自动化实施路线图"]
