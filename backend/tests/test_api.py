from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_endpoint() -> None:
    response = client.post(
        "/profiles/parse",
        json={"raw_input": "Academics:\n- UW GPA: 3.9\nExtracurriculars:\n- Tennis team"},
    )
    assert response.status_code == 200
    assert response.json()["academics"]["gpa_unweighted"] == 3.9
