
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_ingest_performance(benchmark, client: TestClient):
    # This is a placeholder for a real ingestion payload
    payload = {
        "document_id": "test-doc",
        "content": "This is a test document."
    }

    def f():
        return client.post("/ingest", json=payload)

    benchmark(f)


def test_graph_neighbors_performance(benchmark, client: TestClient):
    def f():
        return client.get("/graph/neighbor?id=some-node")

    benchmark(f)


def test_agent_execute_performance(benchmark, client: TestClient):
    payload = {
        "agent_id": "test-agent",
        "inputs": {"query": "test query"}
    }

    def f():
        return client.post("/agents/execute", json=payload)

    benchmark(f)
