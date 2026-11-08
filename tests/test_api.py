"""Run from the project root:  pytest -v
RAGTruth and SMD tests adapt to whatever is installed (mock mode / missing models are skipped, not failed)."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import main  # noqa: E402


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:       # the "with" runs startup, so models load once
        yield c


@pytest.fixture(autouse=True)
def clean_alerts(client):
    client.delete("/alerts")
    yield


NORMAL = [22, 24, 23, 25, 22, 23, 24, 22, 23, 25, 24, 23,
          22, 24, 23, 25, 23, 22, 24, 23, 24, 22, 25, 23, 24, 23]
SPIKE = NORMAL[:-1] + [91]


# ---------- health / modes
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok" and "engines" in r.json()


def test_modes(client):
    d = client.get("/modes").json()
    assert set(d["tasks"]) == {"Summary", "QA", "Data2txt"} and d["modes"]


# ---------- RAGTruth (text)
RAG = {"task_type": "QA", "source_info": "Question: When was the Eiffel Tower completed? Passage: It was completed in 1889.",
       "response": "It was completed in 1889.", "sensitivity_mode": "Balanced detection"}


def test_rag_schema(client):
    d = client.post("/predict", json=RAG).json()
    assert 0.0 <= d["probability"] <= 1.0
    assert isinstance(d["hallucinated"], bool) and d["engine"] in (
        "mock", "model")


def test_rag_threshold_logic(client):
    d = client.post("/predict", json=RAG).json()
    assert d["hallucinated"] == (d["probability"] >= d["threshold"])


def test_rag_bad_task(client):
    assert client.post(
        "/predict", json={**RAG, "task_type": "Poetry"}).status_code == 422


def test_rag_bad_sensitivity(client):
    assert client.post(
        "/predict", json={**RAG, "sensitivity_mode": "Whatever"}).status_code == 422


def test_rag_empty_text(client):
    assert client.post(
        "/predict", json={**RAG, "response": ""}).status_code == 422


def test_rag_batch_limit(client):
    assert client.post("/predict/batch", json=[RAG] * 51).status_code == 422


def test_rag_batch_ok(client):
    r = client.post("/predict/batch", json=[RAG, RAG])
    assert r.status_code == 200 and len(r.json()) == 2


# ---------- NAB (one metric over time)
def test_nab_spike_flagged(client):
    d = client.post("/predict/nab", json={"values": SPIKE}).json()
    assert d["flags"][-1] is True and len(d["scores"]) == len(SPIKE)


def test_nab_normal_not_flagged(client):
    d = client.post("/predict/nab", json={"values": NORMAL}).json()
    assert d["anomalous_points"] == 0


def test_nab_drop_flagged(client):
    vals = [61, 63, 60, 62, 64, 61, 63, 62, 60, 63,
            61, 62, 64, 63, 61, 62, 60, 63, 62, 61, 4]
    assert client.post(
        "/predict/nab", json={"values": vals}).json()["flags"][-1] is True


def test_nab_too_few_values(client):
    assert client.post(
        "/predict/nab", json={"values": [1, 2, 3]}).status_code == 422


def test_nab_non_numeric(client):
    assert client.post(
        "/predict/nab", json={"values": ["a"] * 20}).status_code == 422


def test_nab_replay_unknown_series(client):
    assert client.get(
        "/nab/replay", params={"name": "does_not_exist"}).status_code == 404


def test_nab_replay_known_series(client):
    names = client.get("/nab/series").json()["series"]
    if not names:
        pytest.skip("no NAB sample data on this machine")
    d = client.get("/nab/replay", params={"name": names[0]}).json()
    assert len(d["values"]) == len(d["scores"]) == len(d["flags"])


# ---------- SMD (21 metrics at once)
@pytest.fixture(scope="module")
def smd_machine(client):
    machines = client.get("/smd/machines").json()
    if not machines:
        pytest.skip("no SMD models on this machine")
    return sorted(machines)[0]


def test_smd_wrong_machine(client, smd_machine):
    assert client.post(
        "/predict/smd", json={"machine": "machine-9-9", "rows": [[0.0] * 38]}).status_code == 404


def test_smd_too_few_columns(client, smd_machine):
    assert client.post(
        "/predict/smd", json={"machine": smd_machine, "rows": [[0.0] * 5]}).status_code == 422


def test_smd_unknown_model(client, smd_machine):
    r = client.post(
        "/predict/smd", json={"machine": smd_machine, "model": "nope", "rows": [[0.0] * 38]})
    assert r.status_code == 422


def test_smd_scores_shape(client, smd_machine):
    rows = [[0.0] * 38, [1.0] * 38, [5.0] * 38]
    d = client.post(
        "/predict/smd", json={"machine": smd_machine, "rows": rows}).json()
    assert len(d["scores"]) == len(d["flags"]) == 3
    assert all(f == (s >= d["threshold"])
               for s, f in zip(d["scores"], d["flags"]))


def test_smd_extreme_row_is_flagged(client, smd_machine):
    d = client.post(
        "/predict/smd", json={"machine": smd_machine, "rows": [[0.0] * 38, [1e4] * 38]}).json()
    assert d["scores"][1] >= d["scores"][0]
    assert d["flags"][1] is True


def test_smd_demo_window(client, smd_machine):
    r = client.get(
        "/smd/demo", params={"machine": smd_machine, "start": 0, "length": 200})
    if r.status_code == 404:
        pytest.skip("no SMD sample data on this machine")
    d = r.json()
    assert len(d["scores"]) == 200 and len(d["flags"]) == 200


# ---------- alerts (the shared feed)
def test_alert_created_and_cleared(client):
    client.post("/predict/nab", json={"values": SPIKE})
    alerts = client.get("/alerts").json()
    assert alerts and alerts[0]["source"] == "nab" and alerts[0]["severity"] in (
        "low", "medium", "high")
    client.delete("/alerts")
    assert client.get("/alerts").json() == []


def test_no_alert_for_normal(client):
    client.post("/predict/nab", json={"values": NORMAL})
    assert client.get("/alerts").json() == []
