"""Pipeline Orchestrator — the CEO Agent.

Manages the 12-stage pipeline, coordinates agent execution,
handles state management, and enforces QA gates.
"""

import asyncio
import structlog
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.llm import LLMClient
from app.models.models import Project, ProjectStage, QAIssue
from app.schemas.schemas import AgentOutput

from app.services.websocket_service import (
    notify_stage_started,
    notify_stage_completed,
    notify_stage_failed,
    notify_pipeline_completed,
)
from app.agents.requirement_extractor import RequirementExtractorAgent
from app.agents.requirement_clarifier import RequirementClarifierAgent
from app.agents.data_analyst import DataAnalystAgent
from app.agents.knowledge_base import KnowledgeBaseAgent
from app.agents.logistics_architect import LogisticsArchitectAgent
from app.agents.automation_solution import AutomationSolutionAgent
from app.agents.benchmark import BenchmarkAgent
from app.agents.cost_model import CostModelAgent
from app.agents.risk_compliance import RiskComplianceAgent
from app.agents.tender_writer import TenderWriterAgent
from app.agents.qa_agent import QAAgent

logger = structlog.get_logger()

# Stage definitions
STAGE_DEFINITIONS = [
    {"number": 0, "name": "项目假设", "agent": None},  # Manual input
    {"number": 1, "name": "招标文件解析", "agent": RequirementExtractorAgent},
    {"number": 2, "name": "需求澄清", "agent": RequirementClarifierAgent},
    {"number": 3, "name": "数据分析", "agent": DataAnalystAgent},
    {"number": 4, "name": "知识库检索", "agent": KnowledgeBaseAgent},
    {"number": 5, "name": "方案设计", "agent": LogisticsArchitectAgent},
    {"number": 6, "name": "自动化推荐", "agent": AutomationSolutionAgent},
    {"number": 7, "name": "案例匹配", "agent": BenchmarkAgent},
    {"number": 8, "name": "成本建模", "agent": CostModelAgent},
    {"number": 9, "name": "风险评估", "agent": RiskComplianceAgent},
    {"number": 10, "name": "标书撰写", "agent": TenderWriterAgent},
    {"number": 11, "name": "QA审核", "agent": QAAgent},
]


class PipelineOrchestrator:
    """Orchestrates the 12-stage presale pipeline."""

    def __init__(self, db: AsyncSession, llm: LLMClient):
        self.db = db
        self.llm = llm

    async def initialize_project(self, project: Project) -> list[ProjectStage]:
        """Create all 12 stage records for a new project."""
        stages = []
        for defn in STAGE_DEFINITIONS:
            stage = ProjectStage(
                project_id=project.id,
                stage_number=defn["number"],
                stage_name=defn["name"],
                agent_name=defn["agent"].__name__ if defn["agent"] else "manual",
                status="pending",
            )
            self.db.add(stage)
            stages.append(stage)
        await self.db.flush()
        return stages

    async def run_full_pipeline(
        self,
        project: Project,
        document_text: str = "",
        notify_callback=None,
        resume_from: int = 0,
        language: str = "",
        provider: str = "",
        model: str = "",
    ) -> dict:
        """Run all stages sequentially, respecting QA gates.
        
        Args:
            resume_from: Stage number to resume from.
            language: Output language ("zh" or "en").
            provider: LLM provider ("anthropic", "openai", "deepseek", "gemini").
            model: Specific model ID within the provider.
        """
        from app.core.config import get_settings
        lang = language or get_settings().default_language

        project_context = project.assumptions or {}
        project_context["_output_language"] = lang
        project_context["_llm_provider"] = provider
        project_context["_llm_model"] = model
        stage_outputs: dict[int, dict] = {}

        # Load completed stage outputs when resuming
        if resume_from > 0:
            logger.info("pipeline_resuming", project_id=str(project.id), resume_from=resume_from)
            result = await self.db.execute(
                select(ProjectStage).where(
                    ProjectStage.project_id == project.id,
                    ProjectStage.status == "completed",
                )
            )
            for stage in result.scalars().all():
                if stage.output_data and stage.stage_number < resume_from:
                    stage_outputs[stage.stage_number] = stage.output_data

        # Stage 0: project assumptions
        if 0 not in stage_outputs:
            stage_outputs[0] = project_context
            await self._update_stage(project.id, 0, "completed", project_context)

        if notify_callback:
            await notify_callback("stage_completed", 0)

        # ── Helper to skip completed stages ──
        def should_run(stage_num: int) -> bool:
            return stage_num >= resume_from or stage_num not in stage_outputs

        # Stage 1: Requirement Extraction (must be first)
        if should_run(1):
            s1_input = {"document_text": document_text, "file_name": "tender.pdf"}
            s1_result = await self._run_stage(1, s1_input, project_context, project_id=project.id)
            stage_outputs[1] = s1_result.data
            if s1_result.status != "success":
                return {"status": "failed", "failed_at": 1, "error": s1_result.data}

        # ── Parallel batch 1: Stages 2, 3, 4 (all depend only on Stage 1) ──
        stages_to_run_b1 = [s for s in [2, 3, 4] if should_run(s)]
        if stages_to_run_b1:
            logger.info("parallel_batch_start", batch=1, stages=stages_to_run_b1)
            s1_data = stage_outputs.get(1, {})
            s2_input = {
                "requirements": s1_data.get("requirements", []),
                "missing_critical_info": s1_data.get("missing_critical_info", []),
            }
            s3_input = {"requirements": s1_data}
            s4_input = {"requirements": s1_data}

            tasks = []
            for s in [2, 3, 4]:
                inp = {2: s2_input, 3: s3_input, 4: s4_input}[s]
                if should_run(s):
                    tasks.append(self._run_stage(s, inp, project_context, project_id=project.id))
                else:
                    tasks.append(asyncio.coroutine(lambda d=stage_outputs.get(s, {}): AgentOutput(stage_number=s, agent_name="cached", status="success", data=d, confidence=1.0))())

            results_b1 = await asyncio.gather(*tasks, return_exceptions=True)
            for i, s in enumerate([2, 3, 4]):
                r = results_b1[i]
                if not isinstance(r, Exception):
                    stage_outputs[s] = r.data

        # Stage 5: Logistics Architecture (depends on 1, 3, 4)
        if should_run(5):
            s5_input = {
                "requirements": stage_outputs.get(1, {}),
                "knowledge_context": stage_outputs.get(4, {}).get("synthesized_context", ""),
                "data_analysis": stage_outputs.get(3, {}),
            }
            s5_result = await self._run_stage(5, s5_input, project_context, project_id=project.id)
            stage_outputs[5] = s5_result.data

        # ── Parallel batch 2: Stages 6, 7 ──
        stages_to_run_b2 = [s for s in [6, 7] if should_run(s)]
        if stages_to_run_b2:
            logger.info("parallel_batch_start", batch=2, stages=stages_to_run_b2)
            s6_input = {
                "requirements": stage_outputs.get(1, {}),
                "solution_design": stage_outputs.get(5, {}),
                "automation_knowledge": stage_outputs.get(4, {}).get("retrieved_knowledge", {}).get("automation_cases", ""),
            }
            s7_input = {
                "requirements": stage_outputs.get(1, {}),
                "knowledge_cases": stage_outputs.get(4, {}).get("retrieved_knowledge", {}).get("logistics_cases", ""),
            }

            tasks2 = []
            for s in [6, 7]:
                inp = {6: s6_input, 7: s7_input}[s]
                if should_run(s):
                    tasks2.append(self._run_stage(s, inp, project_context, project_id=project.id))
                else:
                    tasks2.append(asyncio.coroutine(lambda d=stage_outputs.get(s, {}): AgentOutput(stage_number=s, agent_name="cached", status="success", data=d, confidence=1.0))())

            results_b2 = await asyncio.gather(*tasks2, return_exceptions=True)
            for i, s in enumerate([6, 7]):
                r = results_b2[i]
                if not isinstance(r, Exception):
                    stage_outputs[s] = r.data

        # Stage 8: Cost Model
        if should_run(8):
            s8_input = {
                "requirements": stage_outputs.get(1, {}),
                "solution_design": stage_outputs.get(5, {}),
                "automation_recommendations": stage_outputs.get(6, {}),
                "cost_references": stage_outputs.get(4, {}).get("retrieved_knowledge", {}).get("cost_benchmarks", ""),
            }
            s8_result = await self._run_stage(8, s8_input, project_context, project_id=project.id)
            stage_outputs[8] = s8_result.data

        # Stage 9: Risk & Compliance
        if should_run(9):
            s9_input = {
                "requirements": stage_outputs.get(1, {}),
                "solution_design": stage_outputs.get(5, {}),
            }
            s9_result = await self._run_stage(9, s9_input, project_context, project_id=project.id)
            stage_outputs[9] = s9_result.data

        # Stage 10: Tender Writing
        if should_run(10):
            s10_input = {"all_stage_outputs": stage_outputs}
            s10_result = await self._run_stage(10, s10_input, project_context, project_id=project.id)
            stage_outputs[10] = s10_result.data

        # Stage 11: QA Gate
        if should_run(11):
            s11_input = {"all_stage_outputs": stage_outputs}
            s11_result = await self._run_stage(11, s11_input, project_context, project_id=project.id)
            stage_outputs[11] = s11_result.data

        # Store QA issues
        qa_verdict = s11_result.data.get("overall_verdict", "FAIL")
        for issue in s11_result.data.get("issues", []):
            qa_issue = QAIssue(
                project_id=project.id,
                stage_number=issue.get("stage_affected", 11),
                severity=issue.get("severity", "P2"),
                category=issue.get("category"),
                description=issue.get("description", ""),
                suggestion=issue.get("suggestion"),
                status="open",
            )
            self.db.add(qa_issue)

        # Update project status
        project.status = "completed" if qa_verdict == "PASS" else "review_needed"
        await self.db.flush()

        # Notify: pipeline completed
        await notify_pipeline_completed(str(project.id), qa_verdict)

        return {
            "status": "completed",
            "qa_verdict": qa_verdict,
            "stage_outputs": stage_outputs,
        }

    async def run_single_stage(
        self,
        project: Project,
        stage_number: int,
        input_data: dict,
    ) -> AgentOutput:
        """Run a single stage with explicit input."""
        project_context = project.assumptions or {}
        return await self._run_stage(stage_number, input_data, project_context, project_id=project.id)

    async def _run_stage(
        self,
        stage_number: int,
        input_data: dict,
        project_context: dict,
        project_id=None,
    ) -> AgentOutput:
        """Execute a single agent stage with real-time notifications."""
        defn = STAGE_DEFINITIONS[stage_number]
        agent_cls = defn["agent"]

        if agent_cls is None:
            return AgentOutput(
                stage_number=stage_number,
                agent_name="manual",
                status="success",
                data=input_data,
                confidence=1.0,
            )

        # Notify: stage started
        if project_id:
            await notify_stage_started(str(project_id), stage_number, defn["name"])

        agent = agent_cls(self.llm)
        result = await agent.execute(input_data, project_context)

        # Persist stage output
        await self._update_stage(
            project_id,
            stage_number,
            result.status,
            result.data,
            result.confidence,
            result.execution_time_seconds,
        )

        # Notify: stage completed or failed
        if project_id:
            if result.status == "success":
                await notify_stage_completed(
                    str(project_id), stage_number, defn["name"], result.confidence
                )
            else:
                await notify_stage_failed(
                    str(project_id), stage_number,
                    result.data.get("error", "Unknown error"),
                )

        # Save any self-reported issues
        for issue in result.issues:
            if project_id:
                qa = QAIssue(
                    project_id=project_id,
                    stage_number=stage_number,
                    severity=issue.get("severity", "P2"),
                    category=issue.get("category"),
                    description=issue.get("description", ""),
                    suggestion=issue.get("suggestion"),
                    status="open",
                )
                self.db.add(qa)

        return result

    async def _update_stage(
        self,
        project_id,
        stage_number: int,
        status: str,
        output_data: dict = None,
        confidence: float = None,
        execution_time: float = None,
    ):
        """Update a stage record in the database."""
        if not project_id:
            return
        result = await self.db.execute(
            select(ProjectStage).where(
                ProjectStage.project_id == project_id,
                ProjectStage.stage_number == stage_number,
            )
        )
        stage = result.scalar_one_or_none()
        if stage:
            if status in ("success", "completed"):
                stage.status = "completed"
            elif status == "failed" or status == "error":
                stage.status = "failed"
            else:
                stage.status = status
            stage.output_data = output_data
            stage.confidence = confidence
            stage.execution_time_seconds = execution_time
            stage.completed_at = datetime.now(timezone.utc)
            await self.db.flush()
