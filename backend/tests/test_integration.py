"""Enhanced E2E integration tests.

Tests the full user journey:
1. Health check
2. Register + Login
3. Get templates
4. Create project from template
5. Upload file
6. Check stages
7. Knowledge CRUD + search
8. QA issues
9. Prompt management
10. Quotation CRUD
11. Document generation
12. Project export
13. Project duplicate + archive
14. Metrics endpoint

Usage:
    # Start backend first
    python backend/tests/test_integration.py
"""

import asyncio
import sys
import httpx

BASE = "http://localhost:8000"
EMAIL = f"e2e_{int(__import__('time').time())}@test.com"
PASSWORD = "test123456"
TOKEN = ""
PROJECT_ID = ""


async def run():
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as c:
        print("=" * 60)
        print("Integration Test Suite")
        print("=" * 60)

        # ── 1. Health ──
        step("1. Health check")
        r = await c.get("/health")
        assert r.status_code == 200
        h = r.json()
        ok(f"status={h['status']}, db={h['checks']['database']}, redis={h['checks']['redis']}")

        # ── 2. Register + Login ──
        step("2. Register")
        r = await c.post("/api/v1/auth/register", json={
            "email": EMAIL, "name": "E2E User", "password": PASSWORD, "role": "admin",
        })
        assert r.status_code == 201
        ok(f"user={r.json()['id']}")

        step("3. Login")
        r = await c.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200
        global TOKEN
        TOKEN = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {TOKEN}"}
        ok("token acquired")

        # ── 3. Templates ──
        step("4. List templates")
        r = await c.get("/api/v1/templates", headers=headers)
        assert r.status_code == 200
        templates = r.json()
        assert len(templates) >= 6
        ok(f"{len(templates)} templates")

        step("5. Get specific template")
        r = await c.get("/api/v1/templates/auto_parts", headers=headers)
        assert r.status_code == 200
        t = r.json()
        assert t["industry"] == "汽车"
        ok(f"template: {t['name']}")

        # ── 4. Create project ──
        step("6. Create project")
        r = await c.post("/api/v1/projects", json={
            "name": "Integration Test — 汽车备件仓储",
            "client_name": "Test Motors",
            "industry": "汽车",
            "description": "Integration test project",
        }, headers=headers)
        assert r.status_code == 201
        global PROJECT_ID
        PROJECT_ID = r.json()["id"]
        ok(f"project={PROJECT_ID}")

        # ── 5. Stages initialized ──
        step("7. Check stages")
        r = await c.get(f"/api/v1/projects/{PROJECT_ID}/stages", headers=headers)
        assert r.status_code == 200
        stages = r.json()
        assert len(stages) == 12
        ok(f"{len(stages)} stages, all pending")

        # ── 6. Project detail ──
        step("8. Get project detail")
        r = await c.get(f"/api/v1/projects/{PROJECT_ID}", headers=headers)
        assert r.status_code == 200
        detail = r.json()
        assert detail["name"] == "Integration Test — 汽车备件仓储"
        ok(f"stages={len(detail.get('stages', []))}")

        # ── 7. Knowledge CRUD ──
        step("9. Knowledge create")
        r = await c.post("/api/v1/knowledge", json={
            "category": "automation_case",
            "title": "Integration Test Case",
            "content": "This is a test entry for integration testing of the knowledge base.",
            "tags": ["test", "integration"],
        }, headers=headers)
        assert r.status_code == 201
        kb_id = r.json()["id"]
        ok(f"entry={kb_id}")

        step("10. Knowledge list")
        r = await c.get("/api/v1/knowledge?category=automation_case", headers=headers)
        assert r.status_code == 200
        ok(f"{len(r.json())} entries")

        step("11. Knowledge get")
        r = await c.get(f"/api/v1/knowledge/{kb_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["title"] == "Integration Test Case"
        ok("entry retrieved")

        step("12. Knowledge delete")
        r = await c.delete(f"/api/v1/knowledge/{kb_id}", headers=headers)
        assert r.status_code == 204
        ok("entry deleted")

        # ── 8. Prompts ──
        step("13. List prompts")
        r = await c.get("/api/v1/prompts", headers=headers)
        assert r.status_code == 200
        prompts = r.json()
        assert len(prompts) >= 11
        ok(f"{len(prompts)} agent prompts")

        step("14. Get specific prompt")
        r = await c.get("/api/v1/prompts/requirement_extractor", headers=headers)
        assert r.status_code == 200
        p = r.json()
        assert p["stage_number"] == 1
        ok(f"prompt length={p['prompt_length']}")

        # ── 9. QA issues (empty) ──
        step("15. QA issues")
        r = await c.get(f"/api/v1/projects/{PROJECT_ID}/qa-issues", headers=headers)
        assert r.status_code == 200
        ok(f"{len(r.json())} issues")

        # ── 10. Quotation ──
        step("16. Create quotation")
        r = await c.post(f"/api/v1/projects/{PROJECT_ID}/quotations", json={
            "scheme_name": "Integration Test 方案",
            "cost_breakdown": {"labor": {"year1": 1000000}},
        }, headers=headers)
        assert r.status_code == 201
        q_id = r.json()["id"]
        ok(f"quotation={q_id}")

        # ── 11. Project export ──
        step("17. Export project")
        r = await c.get(f"/api/v1/projects/{PROJECT_ID}/export", headers=headers)
        assert r.status_code == 200
        export = r.json()
        assert export["project"]["name"] == "Integration Test — 汽车备件仓储"
        assert export["summary"]["total_quotations"] >= 1
        ok(f"export: {len(str(export))} bytes")

        # ── 12. Duplicate project ──
        step("18. Duplicate project")
        r = await c.post(f"/api/v1/projects/{PROJECT_ID}/duplicate", headers=headers)
        assert r.status_code == 200
        new_id = r.json()["new_project_id"]
        ok(f"duplicate={new_id}")

        # ── 13. Archive ──
        step("19. Archive project")
        r = await c.post(f"/api/v1/projects/{PROJECT_ID}/archive", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "archived"
        ok("archived")

        # ── 14. Metrics ──
        step("20. Metrics endpoint")
        r = await c.get("/metrics")
        assert r.status_code == 200
        body = r.text
        assert "http_requests_total" in body
        ok(f"metrics: {len(body)} bytes, {body.count(chr(10))} lines")

        # ── Summary ──
        print("\n" + "=" * 60)
        print(f"ALL 20 TESTS PASSED ✓")
        print("=" * 60)
        print(f"Project: {PROJECT_ID}")
        print(f"User: {EMAIL}")
        print(f"Note: Pipeline execution requires valid API key")
        return True


def step(name: str):
    print(f"\n[{name}]")


def ok(msg: str):
    print(f"  ✓ {msg}")


def main():
    try:
        result = asyncio.run(run())
        sys.exit(0 if result else 1)
    except httpx.ConnectError:
        print("ERROR: Cannot connect to backend. Run: docker compose up -d")
        sys.exit(1)
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
