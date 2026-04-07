"""End-to-end test script — tests the full workflow.

Usage:
    # Start the backend first: make dev-backend
    python -m pytest backend/tests/test_e2e.py -v -s

    # Or run directly:
    python backend/tests/test_e2e.py
"""

import asyncio
import sys
import httpx

BASE = "http://localhost:8000"
EMAIL = "test@e2e.com"
PASSWORD = "test123456"


async def run_e2e():
    async with httpx.AsyncClient(base_url=BASE, timeout=60) as c:
        print("=" * 60)
        print("E2E Test: Logistics Presale System")
        print("=" * 60)

        # ── 1. Health check ──
        print("\n[1/10] Health check...")
        r = await c.get("/health")
        assert r.status_code == 200
        data = r.json()
        print(f"  Status: {data['status']}")
        assert data["status"] in ("healthy", "degraded")

        # ── 2. Register ──
        print("\n[2/10] Register user...")
        r = await c.post("/api/v1/auth/register", json={
            "email": EMAIL, "name": "E2E Tester", "password": PASSWORD, "role": "admin",
        })
        if r.status_code == 400:
            print("  User already exists, skipping")
        else:
            assert r.status_code == 201
            print(f"  Created user: {r.json()['email']}")

        # ── 3. Login ──
        print("\n[3/10] Login...")
        r = await c.post("/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print(f"  Token: {token[:20]}...")

        # ── 4. Create project ──
        print("\n[4/10] Create project...")
        r = await c.post("/api/v1/projects", json={
            "name": "E2E 测试项目 — 华东电商仓储",
            "client_name": "测试客户",
            "industry": "电商",
            "description": "E2E 自动化测试用项目",
        }, headers=headers)
        assert r.status_code == 201
        project = r.json()
        project_id = project["id"]
        print(f"  Project ID: {project_id}")
        print(f"  Status: {project['status']}")

        # ── 5. List projects ──
        print("\n[5/10] List projects...")
        r = await c.get("/api/v1/projects", headers=headers)
        assert r.status_code == 200
        print(f"  Found {len(r.json())} project(s)")

        # ── 6. Get project detail ──
        print("\n[6/10] Get project detail...")
        r = await c.get(f"/api/v1/projects/{project_id}", headers=headers)
        assert r.status_code == 200
        detail = r.json()
        print(f"  Stages: {len(detail.get('stages', []))}")
        assert len(detail.get("stages", [])) == 12

        # ── 7. Get stages ──
        print("\n[7/10] Get pipeline stages...")
        r = await c.get(f"/api/v1/projects/{project_id}/stages", headers=headers)
        assert r.status_code == 200
        stages = r.json()
        print(f"  {len(stages)} stages, all pending: {all(s['status'] == 'pending' for s in stages)}")

        # ── 8. Knowledge base ──
        print("\n[8/10] Knowledge base operations...")
        r = await c.get("/api/v1/knowledge", headers=headers)
        assert r.status_code == 200
        print(f"  Existing entries: {len(r.json())}")

        # Create entry
        r = await c.post("/api/v1/knowledge", json={
            "category": "logistics_case",
            "title": "E2E Test Case",
            "content": "This is a test knowledge entry for E2E testing.",
            "tags": ["test", "e2e"],
        }, headers=headers)
        if r.status_code == 201:
            entry_id = r.json()["id"]
            print(f"  Created entry: {entry_id}")

            # Delete it
            r = await c.delete(f"/api/v1/knowledge/{entry_id}", headers=headers)
            assert r.status_code == 204
            print("  Deleted test entry")

        # ── 9. QA issues (should be empty) ──
        print("\n[9/10] QA issues...")
        r = await c.get(f"/api/v1/projects/{project_id}/qa-issues", headers=headers)
        assert r.status_code == 200
        print(f"  Issues: {len(r.json())}")

        # ── 10. Prompt management ──
        print("\n[10/10] Prompt management...")
        r = await c.get("/api/v1/prompts", headers=headers)
        assert r.status_code == 200
        prompts = r.json()
        print(f"  {len(prompts)} agent prompts loaded")
        for p in prompts[:3]:
            print(f"    - {p['agent_name']} (Stage {p['stage_number']}): {p['prompt_length']} chars")

        # ── Summary ──
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print(f"\nAPI endpoints tested: 10")
        print(f"Project created: {project_id}")
        print(f"Note: Pipeline execution not tested (requires LLM API key)")

        return True


def main():
    try:
        result = asyncio.run(run_e2e())
        sys.exit(0 if result else 1)
    except httpx.ConnectError:
        print("ERROR: Cannot connect to backend at", BASE)
        print("Start the backend first: make dev-backend")
        sys.exit(1)
    except AssertionError as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
