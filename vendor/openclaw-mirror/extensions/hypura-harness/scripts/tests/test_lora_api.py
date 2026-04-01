# scripts/hypura/tests/test_lora_api.py
import json
import time

from fastapi.testclient import TestClient


def test_lora_status_endpoint() -> None:
    from harness_daemon import app

    client = TestClient(app)
    r = client.get("/lora/status")
    assert r.status_code == 200
    body = r.json()
    assert "lora" in body


def test_curriculum_build_job_completes(tmp_path, monkeypatch) -> None:
    import harness_daemon as hd

    cfg_path = tmp_path / "harness.config.json"
    art = tmp_path / "artifacts" / "lora"
    cfg_path.write_text(
        json.dumps(
            {
                "daemon_port": 18794,
                "lora": {"artifacts_dir": str(art)},
            }
        )
    )
    monkeypatch.setattr(hd, "CONFIG_PATH", cfg_path)
    hd.load_config()
    hd.job_store = None

    client = TestClient(hd.app)
    resp = client.post(
        "/lora/curriculum/build",
        json={"arxiv_ids": [], "include_soul": False, "extra_jsonl": []},
    )
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]
    for _ in range(50):
        jr = client.get(f"/lora/jobs/{job_id}").json()
        if jr.get("status") in ("completed", "failed"):
            assert jr["status"] == "completed"
            assert jr.get("result", {}).get("records") == 0
            return
        time.sleep(0.05)
    raise AssertionError("job did not complete")


def test_train_job_fails_without_base(tmp_path, monkeypatch) -> None:
    import harness_daemon as hd

    cfg_path = tmp_path / "harness.config.json"
    art = tmp_path / "artifacts" / "lora"
    cfg_path.write_text(
        json.dumps(
            {
                "daemon_port": 18794,
                "lora": {"artifacts_dir": str(art)},
            }
        )
    )
    monkeypatch.setattr(hd, "CONFIG_PATH", cfg_path)
    hd.load_config()
    hd.job_store = None

    # create dummy dataset
    cur = art / "curriculum"
    cur.mkdir(parents=True, exist_ok=True)
    sample = cur / "latest.jsonl"
    sample.write_text(
        json.dumps({"instruction": "x" * 100, "output": "y" * 100, "source": "t"})
        + "\n"
    )

    client = TestClient(hd.app)
    resp = client.post("/lora/train", json={"dry_run": True, "dataset_path": None})
    job_id = resp.json()["job_id"]
    for _ in range(50):
        jr = client.get(f"/lora/jobs/{job_id}").json()
        if jr.get("status") in ("completed", "failed"):
            assert jr["status"] == "failed"
            err = (jr.get("error") or "").lower()
            assert "base" in err or "configured" in err
            return
        time.sleep(0.05)
    raise AssertionError("train job did not finish")


def test_grpo_job_placeholder_completes(tmp_path, monkeypatch) -> None:
    import harness_daemon as hd

    cfg_path = tmp_path / "harness.config.json"
    art = tmp_path / "artifacts" / "lora"
    cur = art / "curriculum"
    cur.mkdir(parents=True, exist_ok=True)
    (cur / "latest.jsonl").write_text(
        json.dumps({"instruction": "q", "output": "a", "domain": "math"}) + "\n"
    )
    cfg_path.write_text(
        json.dumps(
            {
                "daemon_port": 18794,
                "lora": {"artifacts_dir": str(art), "grpo": {"reward": "exact_match"}},
            }
        )
    )
    monkeypatch.setattr(hd, "CONFIG_PATH", cfg_path)
    hd.load_config()
    hd.job_store = None

    client = TestClient(hd.app)
    resp = client.post("/lora/grpo", json={"mode": "placeholder", "dataset_path": None})
    assert resp.status_code == 200
    assert resp.json().get("mode") == "placeholder"
    job_id = resp.json()["job_id"]
    for _ in range(50):
        jr = client.get(f"/lora/jobs/{job_id}").json()
        if jr.get("status") in ("completed", "failed"):
            assert jr["status"] == "completed"
            res = jr.get("result") or {}
            assert res.get("grpo_config", {}).get("reward") == "exact_match"
            return
        time.sleep(0.05)
    raise AssertionError("grpo job did not complete")


def test_grpo_job_train_manifest_completes(tmp_path, monkeypatch) -> None:
    import harness_daemon as hd

    cfg_path = tmp_path / "harness.config.json"
    art = tmp_path / "artifacts" / "lora"
    cur = art / "curriculum"
    cur.mkdir(parents=True, exist_ok=True)
    (cur / "latest.jsonl").write_text(json.dumps({"gold": "1"}) + "\n")
    cfg_path.write_text(
        json.dumps({"daemon_port": 18794, "lora": {"artifacts_dir": str(art)}})
    )
    monkeypatch.setattr(hd, "CONFIG_PATH", cfg_path)
    hd.load_config()
    hd.job_store = None

    client = TestClient(hd.app)
    resp = client.post("/lora/grpo", json={"mode": "train", "dataset_path": None})
    assert resp.status_code == 200
    assert resp.json().get("mode") == "train"
    job_id = resp.json()["job_id"]
    for _ in range(50):
        jr = client.get(f"/lora/jobs/{job_id}").json()
        if jr.get("status") in ("completed", "failed"):
            assert jr["status"] == "completed"
            assert (jr.get("result") or {}).get("mode") == "train"
            return
        time.sleep(0.05)
    raise AssertionError("grpo train job did not complete")


def test_curriculum_ingest_dedupe(tmp_path) -> None:
    from pathlib import Path

    from curriculum_ingest import IngestConfig, build_records, write_jsonl

    tmp = Path(tmp_path) / "c.jsonl"
    cfg = IngestConfig(
        arxiv_ids=[],
        soul_path=None,
        extra_jsonl_paths=[],
    )
    recs = build_records(cfg)
    n = write_jsonl(recs, tmp)
    assert n == 0
