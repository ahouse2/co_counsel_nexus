import time
from typing import Callable

import pytest
import requests


@pytest.fixture(scope="session")
def wait_for_service() -> Callable[[str, str, int], None]:
    def _wait(name: str, url: str, timeout: int = 120) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code < 500:
                    return
            except requests.RequestException:
                pass
            time.sleep(3)
        raise TimeoutError(f"Service {name} not ready at {url}")

    return _wait


def test_api_health(wait_for_service: Callable[[str, str, int], None]) -> None:
    wait_for_service("api", "http://localhost:8000/health")
    response = requests.get("http://localhost:8000/health", timeout=5)
    response.raise_for_status()
    body = response.json()
    assert body.get("status") == "ok"


def test_qdrant_health(wait_for_service: Callable[[str, str, int], None]) -> None:
    wait_for_service("qdrant", "http://localhost:6333/healthz")
    response = requests.get("http://localhost:6333/healthz", timeout=5)
    response.raise_for_status()
    assert response.json().get("status") in {"ok", "operational"}


def test_neo4j_browser(wait_for_service: Callable[[str, str, int], None]) -> None:
    wait_for_service("neo4j", "http://localhost:7474")
    response = requests.get("http://localhost:7474", timeout=5)
    assert response.status_code < 500
    assert "Neo4j" in response.text


def test_audio_services(wait_for_service: Callable[[str, str, int], None]) -> None:
    wait_for_service("stt", "http://localhost:9000")
    wait_for_service("tts", "http://localhost:5002")
    stt_response = requests.get("http://localhost:9000", timeout=5)
    tts_response = requests.get("http://localhost:5002", timeout=5)
    assert stt_response.status_code < 500
    assert tts_response.status_code < 500
