"""GRPO + KL — config-driven manifest; optional TRL GRPOTrainer probe (stage-2 after SFT)."""
from __future__ import annotations

import importlib.util
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GRPO: dict[str, Any] = {
    "reward": "exact_match",
    "kl_coef": 0.001,
    "ref_model_dir": "",
    "gold_column": "gold",
    "answer_column": "answer",
    "domain_column": "domain",
    "tool_calls_column": "tool_calls",
    "tools_column": "tools",
    "execute_train": False,
}


def trl_available() -> bool:
    return importlib.util.find_spec("trl") is not None


def grpo_trainer_available() -> bool:
    if not trl_available():
        return False
    try:
        import trl  # noqa: PLC0415

        return hasattr(trl, "GRPOTrainer") or hasattr(trl, "GRPOConfig")
    except Exception:
        return False


def merge_grpo_config(cfg: dict[str, Any] | None) -> dict[str, Any]:
    """Merge ``lora.grpo`` from harness config with defaults."""
    out = dict(DEFAULT_GRPO)
    lora = (cfg or {}).get("lora") or {}
    raw = lora.get("grpo")
    if isinstance(raw, dict):
        out.update({k: v for k, v in raw.items() if v is not None})
    return out


def _dataset_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "rows": 0, "sample_keys": []}
    rows = 0
    sample_keys: list[str] = []
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows += 1
            if not sample_keys:
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        sample_keys = sorted(obj.keys())
                except json.JSONDecodeError:
                    sample_keys = ["<invalid json>"]
    return {"exists": True, "rows": rows, "sample_keys": sample_keys}


def _trl_probe() -> dict[str, Any]:
    return {
        "trl_installed": trl_available(),
        "grpo_trainer_symbol": grpo_trainer_available(),
    }


def run_grpo_kl_placeholder(
    *,
    dataset_path: Path,
    output_dir: Path,
    ref_model_name: str | None = None,
    grpo_options: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write placeholder report + merged GRPO config (stage-2 prep)."""
    merged = {**merge_grpo_config(cfg), **(grpo_options or {})}
    if ref_model_name:
        merged["ref_model_name"] = ref_model_name
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = _dataset_stats(dataset_path)
    report = {
        "status": "not_executed",
        "mode": "placeholder",
        "trl": _trl_probe(),
        "grpo_config": merged,
        "dataset_path": str(dataset_path),
        "dataset": stats,
        "output_dir": str(output_dir),
        "note": (
            "SFT LoRA first, then GRPO for verifiable rewards (see arXiv:2602.04118). "
            "Wire TRL GRPOTrainer + reward_funcs when ready; use POST /lora/grpo mode=train for manifest."
        ),
    }
    (output_dir / "grpo_placeholder.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def run_grpo_train_manifest(
    *,
    dataset_path: Path,
    output_dir: Path,
    grpo_options: dict[str, Any] | None = None,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write train manifest: resolved config, dataset stats, TRL/GRPO availability.

    Full GPU GRPO requires reward functions and reference policy; this harness records
    config and probes TRL without starting multi-hour training unless ``execute_train``
    is true and a future implementation is added.
    """
    merged = {**merge_grpo_config(cfg), **(grpo_options or {})}
    output_dir.mkdir(parents=True, exist_ok=True)
    stats = _dataset_stats(dataset_path)
    probe = _trl_probe()
    execute = bool(merged.get("execute_train", False))

    report: dict[str, Any] = {
        "status": "manifest_only",
        "mode": "train",
        "trl": probe,
        "grpo_config": merged,
        "dataset_path": str(dataset_path),
        "dataset": stats,
        "output_dir": str(output_dir),
        "execute_train_requested": execute,
        "note": (
            "Default: manifest only. Set lora.grpo.execute_train=true only after "
            "reward_funcs and reference model paths are validated; full GRPOTrainer "
            "loop is environment-specific (see TRL docs)."
        ),
    }

    if execute and not probe["trl_installed"]:
        report["status"] = "skipped"
        report["error"] = "execute_train set but trl not installed (uv sync --extra lora)"
    elif execute and not probe["grpo_trainer_symbol"]:
        report["status"] = "skipped"
        report["error"] = "TRL has no GRPOTrainer/GRPOConfig in this version"
    elif execute:
        report["status"] = "not_implemented"
        report["note"] = (
            "execute_train acknowledged; harness does not launch full GRPOTrainer yet—"
            "use manifest + external VERL/TRL script or extend grpo_runner."
        )
        logger.warning("grpo execute_train requested but full trainer loop not wired")

    (output_dir / "grpo_train_manifest.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def run_grpo_job(
    *,
    mode: str,
    dataset_path: Path,
    output_dir: Path,
    cfg: dict[str, Any] | None = None,
    grpo_options: dict[str, Any] | None = None,
    ref_model_name: str | None = None,
) -> dict[str, Any]:
    """Dispatch placeholder vs train manifest."""
    m = (mode or "placeholder").strip().lower()
    if m == "train":
        return run_grpo_train_manifest(
            dataset_path=dataset_path,
            output_dir=output_dir,
            grpo_options=grpo_options,
            cfg=cfg,
        )
    return run_grpo_kl_placeholder(
        dataset_path=dataset_path,
        output_dir=output_dir,
        ref_model_name=ref_model_name,
        grpo_options=grpo_options,
        cfg=cfg,
    )
