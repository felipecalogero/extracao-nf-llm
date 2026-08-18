"""Testes de integração do endpoint de health check."""

from fastapi.testclient import TestClient

from extracao_nf.main import app


def test_health_retorna_ok() -> None:
    """GET /health deve responder 200 com status ok."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
