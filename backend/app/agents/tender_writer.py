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

参考FEILIKS-Porsche标书结构：
- 公司愿景与使命（中英双语）
- 核心业务能力（仓储/运输/供应链解决方案）
- 行业经验：在{industry}行业的服务年限、客户数量、代表客户logo列表
- 质量认证表格：

| 认证 | 编号 | 有效期 | 认证机构 | 适用范围 |
|------|------|--------|---------|---------|
| ISO 9001:2015 | [请填写] | [请填写] | [请填写] | 全部业务 |
| ISO 14001:2015 | [请填写] | [请填写] | [请填写] | 环境管理 |
| IATF 16949 | [请填写] | [请填写] | [请填写] | 汽车行业 |

- 网络布局：全国仓库总面积、网点分布、员工总数
- 行业奖项与荣誉
- 财务概况（年营业额、进出口总额）

注意：具体公司信息用[请填写]标注。""",
        "data_keys": ["requirements"],
    },
    {
        "number": 2,
        "title": "仓库运营设计 (Warehouse Operation Design)",
        "prompt_template": """撰写投标文件第2章：仓库运营设计。这是整份标书最核心的章节。

参考BOSCH-Wuxi标书结构，必须包含以下子章节：

### 2.1 选址方案 (Location Proposal)
- 候选地址对比表：| 地址 | 面积 | 到客户距离 | 往返时间 | 月租金 | 消防等级 |
- 选址逻辑说明

### 2.2 仓库建筑规格 (Building Specifications)
- 参考FEILIKS格式：| 项目 | 规格 |（总面积、净高、地面承载、消防等级、月台数）

### 2.3 仓库布局设计 (Layout Design)
- 功能分区表：| 编号 | 区域名称 | 面积(㎡) | 占比 | 用途说明 |
- 参考FEILIKS C3布局：收货区→分拣区→存储区→拣选区→包装区→发货区
- CCTV/温湿度传感器布局点位说明

### 2.4 货架与存储设计 (Rack and Shelving Design)
- 存储系统表：| 区域 | 货架类型 | 层数 | 承重/层 | 托盘位 | 规格 |
- 参考：横梁式货架/夹层货架/地堆存储的组合方案

### 2.5 运营组织方案 (Operation Organization)
- 人力计算逻辑（参考FEILIKS）：
  日均入库量 × 入库效率 = 入库人数
  日均出库量 × 拣选效率 = 拣选人数
- 5年人力规划表：| 角色 | Y1 | Y2 | Y3 | Y4 | Y5 |
- 组织架构树形图

### 2.6 设备与IT方案 (MHE and IT Plan)
- MHE表：| 设备 | 用途 | 数量 |（前移式/平衡重/地牛/电动托盘车）
- IT设备表：| 设备 | 用途 | 数量 |（RF枪/标签打印机/工作站）

### 2.7 物料流程 (Material Flow)
- 入库流程：卸货→目视检查→扫描清点→分拣→贴标→上架
- 出库流程：拣选→分拣→扫描验证→包装→集货→装车
- 特殊流程：退货处理/报废/盘点/钥匙切割

## 分析数据
{data}

每个小节必须有至少一个表格。引用实际分析数据中的数字。""",
        "data_keys": ["solution", "data_analysis", "requirements"],
    },
    {
        "number": 3,
        "title": "运输线路设计 (Transportation Design)",
        "prompt_template": """撰写投标文件第3章：运输设计。

参考FEILIKS-Porsche入库运输方案：

### 3.1 运输网络概览
- 入库来源：机场/海港/工厂 → 仓库
- 运输方式：空运/海运/公路多式联运
- 服务范围示意（文字描述物流节点和线路）

### 3.2 车辆资源配置
- 车辆规格表：| 车型 | 长(m) | 宽(m) | 高(m) | 载重(T) | 自有数量 |
- 参考FEILIKS：4.2m/7.6m/9.6m/12.5m/16.5m多种车型
- 自有车队 vs 合作承运商说明

### 3.3 危险品运输方案 (如适用)
- DG运输资质证明
- 运输流程：港口提货→转运→仓库
- 温控/锂电池专项处理

### 3.4 绿色运输方案
- EV电动车方案（适用于机场短途）
- LNG车辆方案（适用于海港中长途）
- 碳减排对比表：| 方案 | 碳排放 | 减排比例 | 适用场景 |

### 3.5 承运商管理
- 5步选择流程：资质审核→成本谈判→合同审批→移交运营→绩效监控
- 车辆检查标准和维保计划

## 分析数据
{data}

如果没有具体线路数据，基于行业经验和仓库吞吐量推算。""",
        "data_keys": ["solution", "data_analysis", "requirements"],
    },
    {
        "number": 4,
        "title": "自动化与数字化方案 (Automation & Digitalization)",
        "prompt_template": """撰写投标文件第4章：自动化与数字化方案。

参考FEILIKS-Porsche自动化方案结构：

### 4.1 方案总览
- 自动化矩阵表：| 功能 | 收货 | 上架 | 拣选 | 包装 | 发货 |
- 每个功能对应的自动化方案（AGV/CTU机器人/SOP在线指导/多功能包装台）
- 总投资汇总

### 4.2 分阶段实施路线图
- Phase 1 (合同期内必做)：SOP在线指导、多功能包装台、AGV
- Phase 2 (合同期内选做)：CTU料箱机器人、跟随拣选机器人
- Phase 3 (延展期)：无人机盘点、数字孪生
- 实施时间线

### 4.3 投资回报分析
参考FEILIKS CTU/AGV对比分析格式：
- CTU vs 传统拣货车对比表：| 项目 | CTU方案 | 传统方案 |（含一次性投资、年运行成本、回本周期）
- AGV vs 平衡重叉车对比表
- 6年累计成本曲线说明

### 4.4 IT系统集成
- 3层集成方案：
  Tier 1 全集成（API对接SAP EWM）
  Tier 2 部分集成（RPA/Batch Job）
  Tier 3 独立运行（零IT风险）
- 强调：客户零买断风险，LSP承担折旧

### 4.5 数字孪生与看板
- 数字孪生架构（基础设施→网络→数据→平台→应用→展示）
- 运营看板KPI：收货看板/出货看板/库存看板/异常看板

## 分析数据
{data}

引用自动化推荐Agent的具体建议和ROI数据。""",
        "data_keys": ["automation", "solution"],
    },
    {
        "number": 5,
        "title": "项目实施与运营整合 (Implementation & Operation Integration)",
        "prompt_template": """撰写投标文件第5章：项目实施与运营整合。

参考FEILIKS-Porsche实施方案：

### 5.1 项目管理团队
- 组织架构树形图（决策层→项目管理层→实施运营层→后勤支持层）
- 关键角色：项目总监/大客户经理/运营经理/实施经理
- 升级机制表：| 时限 | 2h | 12h | 24h | 2天 | → 对应负责人

### 5.2 实施时间线 (14周甘特图)
参考FEILIKS 2026实施计划：
- W1-2: 合同签署与仓库租赁
- W3-6: 仓库改造、设备采购、网络布线、CCTV安装
- W7-10: SOP编写、人员招聘、培训（现场5天+FEILIKS站点3天）
- W11-12: 库存盘点移交
- W13-14: 试运行 + Go-Live

### 5.3 人员保障双轨策略
- 留用策略：保留现有团队70%+，薪资对标方案
- 应急策略：50名技术工人 + 10名SAP用户从周边项目调配
- 培训课程表：| 主题 | 天数 | 内容 | 讲师 | 学员 |

### 5.4 运营整合机制
- 客户协作5维度（参考FEILIKS）：项目发展30% + 大客户关注10% + 创新推动20% + OPEX共享30% + 合同延展10%
- 现场管理SFM方法：信息中心→问题排序→现场确认→问题解决→流程验证
- CIP看板设计：安全/质量/士气/环境/效率

### 5.5 应急预案
- 应急分类表：| 风险类别 | 风险事项 | 即时措施 | L1升级 | L2升级 |
- 覆盖：人力短缺/设备故障/系统宕机/盘点异常/安全隐患

## 分析数据
{data}

时间线要具体到周，里程碑要可衡量。""",
        "data_keys": ["solution", "risks"],
    },
    {
        "number": 6,
        "title": "补充信息 (Additional Information)",
        "prompt_template": """撰写投标文件第6章：补充信息。

### 6.1 质量管理体系 (Quality Management System)
- 质量认证清单表：| 认证 | 适用范围 | 有效期 | 审核频率 |
- 质量流程检查清单表：| 流程 | 检查项 | 频率 | 负责人 | 工具 |
- 审核和改善机制（年度审计 + 飞行检查）

### 6.2 可持续物流 (Sustainable Logistics)
参考FEILIKS方案：
- 绿色仓库方案：可回收周转箱（PP材质、IoT芯片追踪、电子围栏）
- 环保包装：水活性胶带、蜂窝纸填充
- 碳排放管理和ESG报告

### 6.3 风险管理与BCP
- 已识别风险汇总表：| 风险等级 | 数量 | 前3大风险 |
- 业务连续性计划(BCP)：覆盖消防/台风/地震/疫情/电力中断
- 风险识别鱼骨图分类：人/机/料/法/环/测/管理

### 6.4 报价假设条件
- ⚠️ 假设条件表格：| 编号 | 假设 | 当前值 | 偏差>20%影响 |
- 注明"如实际偏差>20%则需双方协商调整报价"

## 分析数据
{data}

风险管理引用Stage 9的分析结果。""",
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
        return """你是资深物流投标文件撰写专家，服务Porsche/Bosch/BMW等500强客户。

写作规则：
1. 数据驱动：引用分析数据中的实际数值，不编造
2. 每个子章节至少一个Markdown表格
3. 计算透明：展示推导（如人力=490托÷18托/人=27人）
4. 中英双语标题："中文 (English)"
5. 专业术语：Milk Run/Kitting/FMEA/AGV/WCS/SAP EWM
6. 需补充信息标注[请填写]
7. 每章至少1个差异化亮点

格式：Markdown正文，不要JSON，不要重复章节标题。"""

    async def _execute(self, input_data: dict, project_context: dict) -> dict:
        all_outputs = input_data.get("all_stage_outputs", {})
        data_map = self._build_data_map(all_outputs)

        industry = project_context.get("industry", "物流")
        context_str = json.dumps(project_context, ensure_ascii=False, default=str)[:800]

        # Generate chapters one by one (sequential to avoid rate limits)
        chapters = []
        summary_parts = []

        for ch_def in CHAPTERS:
            logger.info("tender_writing_chapter", chapter=ch_def["number"], title=ch_def["title"])

            try:
                content = await self._write_chapter(ch_def, data_map, context_str, industry, project_context)
                logger.info("tender_chapter_done", chapter=ch_def["number"], words=len(content))
            except Exception as e:
                content = f"[章节生成失败: {str(e)[:200]}]"
                logger.error("tender_chapter_failed", chapter=ch_def["number"], error=str(e))

            chapters.append({
                "chapter": ch_def["number"],
                "title": ch_def["title"],
                "content": content,
                "word_count": len(content),
            })

            first_line = content.split("\n")[0].strip()[:120]
            summary_parts.append(f"第{ch_def['number']}章 {ch_def['title']}：{first_line}")

            # Brief pause between chapters to avoid rate limiting
            await asyncio.sleep(2)

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

        # Keep data compact to avoid server disconnect on long requests
        data_str = json.dumps(relevant_data, ensure_ascii=False, default=str)[:3000] if relevant_data else "暂无具体数据，请基于行业最佳实践撰写，关键数据标注[待确认]"

        prompt = ch_def["prompt_template"].format(
            data=data_str,
            industry=industry,
            context=context_str,
        )

        prompt += f"\n\n## 项目背景\n{context_str}"
        prompt += f"\n\n请直接输出本章Markdown正文内容（800-1200字）。"

        return await self.call_llm(prompt, max_tokens=2500, project_context=project_context)

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

        return await self.call_llm(prompt, max_tokens=1000, project_context=project_context)

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
