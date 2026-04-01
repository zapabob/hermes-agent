# scripts/hypura/tests/test_grpo_runner.py
import json
from pathlib import Path

from grpo_runner import merge_grpo_config, run_grpo_job, run_grpo_train_manifest


def test_merge_grpo_config_defaults() -> None:
    m = merge_grpo_config({})
    assert m["reward"] == "exact_match"
    assert m["kl_coef"] == 0.001
    assert m["gold_column"] == "gold"


def test_merge_grpo_config_from_lora() -> None:
    cfg = {
        "lora": {
            "grpo": {
                "kl_coef": 0.01,
                "reward": "tool_format",
            }
        }
    }
    m = merge_grpo_config(cfg)
    assert m["kl_coef"] == 0.01
    assert m["reward"] == "tool_format"
    assert m["answer_column"] == "answer"


def test_run_grpo_placeholder_writes_file(tmp_path: Path) -> None:
    ds = tmp_path / "d.jsonl"
    ds.write_text(
        json.dumps({"instruction": "a", "output": "b", "gold": "42"}) + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    r = run_grpo_job(
        mode="placeholder",
        dataset_path=ds,
        output_dir=out,
        cfg={"lora": {"grpo": {"kl_coef": 0.002}}},
    )
    assert r["status"] == "not_executed"
    assert (out / "grpo_placeholder.json").is_file()
    loaded = json.loads((out / "grpo_placeholder.json").read_text(encoding="utf-8"))
    assert loaded["grpo_config"]["kl_coef"] == 0.002
    assert loaded["dataset"]["rows"] == 1


def test_run_grpo_train_manifest_writes_file(tmp_path: Path) -> None:
    ds = tmp_path / "d.jsonl"
    ds.write_text(json.dumps({"gold": "x"}) + "\n", encoding="utf-8")
    out = tmp_path / "out2"
    r = run_grpo_train_manifest(dataset_path=ds, output_dir=out, cfg={})
    assert r["mode"] == "train"
    assert (out / "grpo_train_manifest.json").is_file()
    assert r["status"] in ("manifest_only", "skipped", "not_implemented")


def test_run_grpo_train_execute_train_without_trl(tmp_path: Path) -> None:
    ds = tmp_path / "d.jsonl"
    ds.write_text("{}\n", encoding="utf-8")
    out = tmp_path / "out3"
    r = run_grpo_train_manifest(
        dataset_path=ds,
        output_dir=out,
        cfg={"lora": {"grpo": {"execute_train": True}}},
    )
    # Either trl missing or GRPO symbol missing in this env
    assert r["status"] in ("skipped", "not_implemented", "manifest_only")

