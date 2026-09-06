from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

ROOT = Path(__file__).resolve().parent.parent
client = TestClient(app)


def _upload_files():
    return {
        "symptom_file": (
            "test_cases_raw_symptoms.csv",
            (ROOT / "test_cases_raw_symptoms.csv").read_bytes(),
            "text/csv",
        ),
        "lab_file": (
            "test_cases_raw_labs.csv",
            (ROOT / "test_cases_raw_labs.csv").read_bytes(),
            "text/csv",
        ),
    }


def test_demo_returns_reference_scores():
    resp = client.post("/api/predict/demo", params={"threshold": 0.16})
    assert resp.status_code == 200
    data = resp.json()
    scores = {p["patient_id"]: p["score"] for p in data["patients"]}
    assert scores["KJSQ-FY-13"] == pytest.approx(0.80375, abs=1e-6)
    assert scores["KJSQ-SG-106"] == pytest.approx(0.035625, abs=1e-6)
    labels = {p["patient_id"]: p["label"] for p in data["patients"]}
    assert labels == {"KJSQ-FY-13": "肺炎", "KJSQ-SG-106": "上感"}
    assert "PatientID" in data["symptoms_preview"]["columns"]
    assert "patientId" in data["labs_preview"]["columns"]
    assert len(data["symptoms_preview"]["rows"]) <= 5
    detail = next(p for p in data["patients"] if p["patient_id"] == "KJSQ-FY-13")["detail"]
    assert detail["age"] == 91.0
    assert detail["gender"] == "女"
    measured = {lab["name"]: lab["measured"] for lab in detail["labs"]}
    assert measured["白细胞计数"] is True


def test_demo_without_threshold_has_null_labels():
    resp = client.post("/api/predict/demo")
    assert resp.status_code == 200
    assert all(p["label"] is None for p in resp.json()["patients"])


def test_predict_upload_matches_reference():
    resp = client.post("/api/predict", files=_upload_files(), params={"threshold": 0.16})
    assert resp.status_code == 200
    scores = {p["patient_id"]: p["score"] for p in resp.json()["patients"]}
    assert scores["KJSQ-FY-13"] == pytest.approx(0.80375, abs=1e-6)
    assert scores["KJSQ-SG-106"] == pytest.approx(0.035625, abs=1e-6)


def test_predict_rejects_non_csv():
    files = {
        "symptom_file": ("notes.txt", b"hello", "text/plain"),
        "lab_file": ("labs.csv", b"a,b\n1,2\n", "text/csv"),
    }
    resp = client.post("/api/predict", files=files)
    assert resp.status_code == 400


def test_predict_rejects_missing_columns():
    files = {
        "symptom_file": ("symptoms.csv", b"foo,bar\n1,2\n", "text/csv"),
        "lab_file": ("labs.csv", b"foo,bar\n1,2\n", "text/csv"),
    }
    resp = client.post("/api/predict", files=files)
    assert resp.status_code == 400
    assert "缺少必要字段" in resp.json()["detail"]


def test_predict_rejects_out_of_range_threshold():
    resp = client.post("/api/predict", files=_upload_files(), params={"threshold": 1.5})
    assert resp.status_code == 400


def test_demo_file_download():
    resp = client.get("/api/demo/files/symptoms")
    assert resp.status_code == 200
    assert "PatientID" in resp.text
    assert client.get("/api/demo/files/nope").status_code == 404
