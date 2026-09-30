from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_summary_success():
    """Verify GET /summary returns HTTP 200 and expected summary for sample.jsonl."""
    response = client.get("/summary")

    assert response.status_code == 200
    data = response.json()

    assert data["accepted"] == 3
    assert data["duplicates"] == 1
    assert data["errors"] == [{"line": 4, "code": "BAD_JSON"}]
    assert data["devices"] == [
        {
            "device_id": "D01",
            "ok": 1,
            "error": 1,
            "last_sequence": 3,
            "last_status": "error",
        },
        {
            "device_id": "D02",
            "ok": 0,
            "error": 1,
            "last_sequence": 2,
            "last_status": "error",
        },
    ]


def test_api_summary_file_not_found_returns_500(monkeypatch):
    """Verify that a missing input file returns HTTP 500 rather than empty success."""
    monkeypatch.setenv("DATA_FILE_PATH", "data/non_existent_file.jsonl")

    response = client.get("/summary")

    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Input file not found" in data["detail"]


def test_api_summary_empty_file(tmp_path, monkeypatch):
    """Verify that an existing empty file returns HTTP 200 with empty summary."""
    empty_file = tmp_path / "empty.jsonl"
    empty_file.write_text("")
    monkeypatch.setenv("DATA_FILE_PATH", str(empty_file))

    response = client.get("/summary")

    assert response.status_code == 200
    assert response.json() == {
        "accepted": 0,
        "duplicates": 0,
        "errors": [],
        "devices": [],
    }
