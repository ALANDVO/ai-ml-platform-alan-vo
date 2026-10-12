import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from api.schemas import Role
from api.auth import _sign

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert "active_runs" in data
        assert "registered_models" in data
        assert "uptime_s" in data

@pytest.mark.asyncio
async def test_auth_login_and_me():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Login
        res = await client.post("/api/auth/login?email=test@alanvo.com")
        assert res.status_code == 200
        token = res.json()["token"]
        assert token

        # Call /me with valid token
        res_me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert res_me.status_code == 200
        user = res_me.json()
        assert user["email"] == "test@alanvo.com"
        assert user["role"] == "admin"

@pytest.mark.asyncio
async def test_auth_unauthorized():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/auth/me")
        assert res.status_code == 401

@pytest.mark.asyncio
async def test_experiment_creation_and_listing():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = _sign("engineer@domain.com", "Engineer", Role.ml_engineer.value)
        headers = {"Authorization": f"Bearer {token}"}

        # Create experiment
        create_res = await client.post(
            "/api/experiments",
            json={
                "name": "Integration-Exp",
                "description": "Integration test run",
                "dataset": "cifar10",
                "framework": "pytorch",
            },
            headers=headers,
        )
        assert create_res.status_code == 201
        exp_data = create_res.json()
        assert exp_data["name"] == "Integration-Exp"
        exp_id = exp_data["id"]

        # List experiments
        list_res = await client.get("/api/experiments")
        assert list_res.status_code == 200
        exps = list_res.json()
        assert any(e["id"] == exp_id for e in exps)

        # Get runs for experiment
        runs_res = await client.get(f"/api/experiments/{exp_id}/runs")
        assert runs_res.status_code == 200
        assert isinstance(runs_res.json(), list)

@pytest.mark.asyncio
async def test_viewer_cannot_create_experiment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token = _sign("viewer@domain.com", "Viewer", Role.viewer.value)
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/experiments",
            json={
                "name": "Viewer-Exp",
                "description": "Should fail",
                "dataset": "cifar10",
                "framework": "pytorch",
            },
            headers=headers,
        )
        assert res.status_code == 403
