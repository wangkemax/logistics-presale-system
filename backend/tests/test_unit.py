"""Unit tests for core backend modules.

Usage:
    cd backend && python -m pytest tests/ -v
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# ──────────────────────────────────────────
# Agent base class tests
# ──────────────────────────────────────────

class TestBaseAgent:
    """Test BaseAgent execute flow."""

    def _make_agent(self):
        from app.agents.base import BaseAgent
        from app.core.llm import LLMClient

        class DummyAgent(BaseAgent):
            name = "test_agent"
            description = "test"
            stage_number = 99
            timeout_minutes = 1

            @property
            def system_prompt(self):
                return "You are a test agent."

            async def _execute(self, input_data, project_context):
                return {"result": "ok", "_confidence": 0.9}

        mock_llm = MagicMock(spec=LLMClient)
        return DummyAgent(mock_llm)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        agent = self._make_agent()
        with patch("app.services.agent_cache.get_agent_cache") as mock_cache:
            mock_cache.return_value.get = AsyncMock(return_value=None)
            mock_cache.return_value.set = AsyncMock()
            output = await agent.execute({"x": 1}, {}, use_cache=False)

        assert output.status == "success"
        assert output.confidence == 0.9
        assert output.data["result"] == "ok"
        assert output.execution_time_seconds >= 0

    @pytest.mark.asyncio
    async def test_execute_timeout(self):
        from app.agents.base import BaseAgent
        from app.core.llm import LLMClient

        class SlowAgent(BaseAgent):
            name = "slow"
            stage_number = 99
            timeout_minutes = 0  # Will cause immediate timeout

            @property
            def system_prompt(self):
                return ""

            async def _execute(self, input_data, project_context):
                await asyncio.sleep(10)
                return {}

        agent = SlowAgent(MagicMock(spec=LLMClient))
        # Set timeout to something very small
        agent.timeout_minutes = 0.001  # ~60ms
        output = await agent.execute({}, {}, use_cache=False)
        assert output.status == "error"
        assert "timed out" in output.data.get("error", "")

    @pytest.mark.asyncio
    async def test_validate_empty_output(self):
        agent = self._make_agent()
        issues = await agent.validate_output({})
        assert len(issues) == 1
        assert issues[0]["severity"] == "P0"

    @pytest.mark.asyncio
    async def test_validate_valid_output(self):
        agent = self._make_agent()
        issues = await agent.validate_output({"key": "value"})
        assert len(issues) == 0


# ──────────────────────────────────────────
# Cost model computation tests
# ──────────────────────────────────────────

class TestCostModelAgent:
    """Test cost model validation logic."""

    def _make_agent(self):
        from app.agents.cost_model import CostModelAgent
        from app.core.llm import LLMClient
        return CostModelAgent(MagicMock(spec=LLMClient))

    @pytest.mark.asyncio
    async def test_validate_missing_indicators(self):
        agent = self._make_agent()
        output = {"financial_indicators": {}, "pricing": {}, "cost_breakdown": {"a": 1, "b": 2, "c": 3}}
        issues = await agent.validate_output(output)
        severities = [i["severity"] for i in issues]
        assert "P0" in severities  # Missing ROI/NPV

    @pytest.mark.asyncio
    async def test_validate_complete_output(self):
        agent = self._make_agent()
        output = {
            "financial_indicators": {"roi_percent": 15, "npv_at_8pct": 100000},
            "pricing": {"recommended_price": 5000000},
            "cost_breakdown": {"labor": {}, "facility": {}, "equipment": {}},
        }
        issues = await agent.validate_output(output)
        p0s = [i for i in issues if i["severity"] == "P0"]
        assert len(p0s) == 0


# ──────────────────────────────────────────
# QA Agent tests
# ──────────────────────────────────────────

class TestQAAgent:

    def _make_agent(self):
        from app.agents.qa_agent import QAAgent
        from app.core.llm import LLMClient
        return QAAgent(MagicMock(spec=LLMClient))

    @pytest.mark.asyncio
    async def test_validate_valid_verdict(self):
        agent = self._make_agent()
        issues = await agent.validate_output({"overall_verdict": "PASS"})
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_validate_invalid_verdict(self):
        agent = self._make_agent()
        issues = await agent.validate_output({"overall_verdict": "MAYBE"})
        assert len(issues) == 1
        assert issues[0]["severity"] == "P0"


# ──────────────────────────────────────────
# Quotation Excel tests
# ──────────────────────────────────────────

class TestQuotationExcel:

    @pytest.mark.asyncio
    async def test_generate_basic_excel(self):
        from app.services.quotation_excel import generate_quotation_excel

        data = {
            "project_name": "Test Project",
            "client_name": "Test Client",
            "scheme_name": "方案A",
            "date": "2026-04-07",
            "cost_breakdown": {
                "labor": {"year1": 2400000, "year2": 2520000, "year3": 2646000, "details": [
                    {"item": "仓管员", "count": 20, "unit_cost": 6000, "annual": 1440000},
                ]},
                "facility": {"year1": 3600000, "year2": 3600000, "year3": 3600000},
                "equipment": {"year1": 500000, "year2": 200000, "year3": 200000},
            },
            "financial_indicators": {"roi_percent": 18.5, "payback_months": 28},
            "pricing": {"per_order": 3.5, "total_annual": 8500000},
        }

        result = await generate_quotation_excel(data)
        assert isinstance(result, bytes)
        assert len(result) > 1000  # Valid XLSX is at least a few KB
        # Check XLSX magic bytes (PK zip header)
        assert result[:2] == b"PK"


# ──────────────────────────────────────────
# Storage service tests
# ──────────────────────────────────────────

class TestStorageService:

    def test_generate_key_uniqueness(self):
        from app.services.storage_service import StorageService
        key1 = StorageService.generate_key("proj-1", "tender.pdf", "tender")
        key2 = StorageService.generate_key("proj-1", "tender.pdf", "tender")
        # Keys should be unique due to timestamp + uuid
        assert key1 != key2
        assert key1.startswith("tender/proj-1/")
        assert key1.endswith("_tender.pdf")

    def test_generate_key_sanitizes_filename(self):
        from app.services.storage_service import StorageService
        key = StorageService.generate_key("p", "bad file (1).pdf")
        assert "(" not in key
        assert " " not in key


# ──────────────────────────────────────────
# Agent cache tests
# ──────────────────────────────────────────

class TestAgentCache:

    def test_make_key_deterministic(self):
        from app.services.agent_cache import AgentCache
        key1 = AgentCache._make_key("agent1", {"a": 1}, {"b": 2})
        key2 = AgentCache._make_key("agent1", {"a": 1}, {"b": 2})
        assert key1 == key2

    def test_make_key_different_inputs(self):
        from app.services.agent_cache import AgentCache
        key1 = AgentCache._make_key("agent1", {"a": 1}, {})
        key2 = AgentCache._make_key("agent1", {"a": 2}, {})
        assert key1 != key2

    def test_make_key_different_agents(self):
        from app.services.agent_cache import AgentCache
        key1 = AgentCache._make_key("agent1", {"a": 1}, {})
        key2 = AgentCache._make_key("agent2", {"a": 1}, {})
        assert key1 != key2


# ──────────────────────────────────────────
# Document service tests
# ──────────────────────────────────────────

class TestDocumentService:

    @pytest.mark.asyncio
    async def test_extract_txt(self):
        from app.services.document_service import extract_text_from_file
        content = await extract_text_from_file(b"Hello World", "test.txt")
        assert content == "Hello World"

    @pytest.mark.asyncio
    async def test_extract_unknown_format(self):
        from app.services.document_service import extract_text_from_file
        content = await extract_text_from_file(b"raw data", "file.xyz")
        assert "raw data" in content


# ──────────────────────────────────────────
# Scheme comparison tests
# ──────────────────────────────────────────

class TestSchemeComparison:

    def test_pick_recommendation(self):
        from app.services.scheme_comparison import _pick_recommendation
        schemes = {
            "A": {"financial_indicators": {"roi_percent": 10}},
            "B": {"financial_indicators": {"roi_percent": 25}},
            "C": {"financial_indicators": {"roi_percent": 18}},
        }
        rec = _pick_recommendation(schemes)
        assert rec["recommended_scheme"] == "B"

    def test_build_matrix(self):
        from app.services.scheme_comparison import _build_matrix
        schemes = {
            "A": {"cost_summary": {"total_capex": 100}, "financial_indicators": {"roi_percent": 10}, "headcount": {"total": 50}},
            "B": {"cost_summary": {"total_capex": 200}, "financial_indicators": {"roi_percent": 20}, "headcount": {"total": 30}},
        }
        matrix = _build_matrix(schemes)
        assert len(matrix) > 0
        capex_row = next(r for r in matrix if r["metric"] == "total_capex")
        assert capex_row["scheme_A"] == 100
        assert capex_row["scheme_B"] == 200


# ──────────────────────────────────────────
# Rate limiter tests
# ──────────────────────────────────────────

class TestRateLimiter:

    def test_get_group(self):
        from app.core.rate_limiter import _get_group
        assert _get_group("/api/v1/projects/123/run-pipeline") == "pipeline"
        assert _get_group("/api/v1/knowledge/search") == "search"
        assert _get_group("/api/v1/projects/123/documents/generate") == "generate"
        assert _get_group("/api/v1/projects") == "default"


# ──────────────────────────────────────────
# Security tests
# ──────────────────────────────────────────

class TestSecurity:

    def test_password_hash_verify(self):
        from app.core.security import hash_password, verify_password
        hashed = hash_password("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)

    def test_jwt_roundtrip(self):
        from app.core.security import create_access_token, decode_access_token
        token = create_access_token({"sub": "user-123", "role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "admin"

    def test_jwt_invalid_token(self):
        from app.core.security import decode_access_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            decode_access_token("invalid.token.here")


# ──────────────────────────────────────────
# Encryption tests
# ──────────────────────────────────────────

class TestEncryption:

    def test_encrypt_decrypt_roundtrip(self):
        from app.core.encryption import FieldEncryptor
        enc = FieldEncryptor("test-secret-key-for-testing")
        plaintext = "sensitive data 123"
        encrypted = enc.encrypt(plaintext)
        assert encrypted != plaintext
        assert enc.decrypt(encrypted) == plaintext

    def test_encrypt_empty_string(self):
        from app.core.encryption import FieldEncryptor
        enc = FieldEncryptor("test-key")
        assert enc.encrypt("") == ""
        assert enc.decrypt("") == ""

    def test_is_encrypted(self):
        from app.core.encryption import FieldEncryptor
        enc = FieldEncryptor("test-key")
        encrypted = enc.encrypt("hello")
        assert enc.is_encrypted(encrypted)
        assert not enc.is_encrypted("plain text")

    def test_different_keys_produce_different_ciphertexts(self):
        from app.core.encryption import FieldEncryptor
        enc1 = FieldEncryptor("key-1")
        enc2 = FieldEncryptor("key-2")
        c1 = enc1.encrypt("same data")
        c2 = enc2.encrypt("same data")
        assert c1 != c2


# ──────────────────────────────────────────
# Template tests
# ──────────────────────────────────────────

class TestTemplates:

    def test_templates_exist(self):
        from app.api.routes.templates import TEMPLATES
        assert len(TEMPLATES) >= 6

    def test_template_has_assumptions(self):
        from app.api.routes.templates import TEMPLATES
        for t in TEMPLATES:
            assert t.assumptions, f"Template {t.id} has no assumptions"
            assert t.industry, f"Template {t.id} has no industry"

    def test_template_ids_unique(self):
        from app.api.routes.templates import TEMPLATES
        ids = [t.id for t in TEMPLATES]
        assert len(ids) == len(set(ids)), "Duplicate template IDs found"
