"""Resolve LoRA / curriculum paths from env and harness config.

Local absolute paths must not be committed; use env vars or harness.config.local.json.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _env_path(key: str) -> Path | None:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def resolve_base_model_dir(cfg: dict[str, Any]) -> Path | None:
    """Hugging Face-style local model dir (SafeTensor), e.g. Qwen deployment folder."""
    lora = cfg.get("lora") or {}
    if p := _env_path("HAKUA_BASE_MODEL_DIR"):
        return p
    if p := _env_path("OPENCLAW_HYPURA_BASE_MODEL_DIR"):
        return p
    raw = (lora.get("base_model_dir") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return None


def resolve_curriculum_dirs(cfg: dict[str, Any]) -> dict[str, Path | None]:
    """Optional extra dataset roots (operator-local)."""
    lora = cfg.get("lora") or {}
    out: dict[str, Path | None] = {
        "from_d": None,
        "so8t_data": None,
        "downloads_ghost": None,
    }
    if p := _env_path("HAKUA_FROM_D_DATASET_DIR"):
        out["from_d"] = p
    elif raw := (lora.get("from_d_dataset_dir") or "").strip():
        out["from_d"] = Path(raw).expanduser()

    if p := _env_path("HAKUA_SO8T_DATA_DIR"):
        out["so8t_data"] = p
    elif raw := (lora.get("so8t_data_dir") or "").strip():
        out["so8t_data"] = Path(raw).expanduser()

    if p := _env_path("HAKUA_GHOST_DATASET_PATH"):
        out["downloads_ghost"] = p
    elif raw := (lora.get("ghost_dataset_path") or "").strip():
        out["downloads_ghost"] = Path(raw).expanduser()
    return out


def resolve_artifacts_root(cfg: dict[str, Any]) -> Path:
    lora = cfg.get("lora") or {}
    if p := _env_path("HAKUA_LORA_ARTIFACTS_DIR"):
        return p
    raw = (lora.get("artifacts_dir") or "").strip()
    if raw:
        return Path(raw).expanduser()
    root = Path(__file__).resolve().parent
    return root / "artifacts" / "lora"


def resolve_soul_path(cfg: dict[str, Any], repo_root: Path) -> Path:
    """Default: repo SOUL.md; override with HAKUA_SOUL_PATH."""
    if p := _env_path("HAKUA_SOUL_PATH"):
        return p
    lora = cfg.get("lora") or {}
    raw = (lora.get("soul_path") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return repo_root / "SOUL.md"


def ollama_model_names(cfg: dict[str, Any]) -> dict[str, str]:
    models = cfg.get("models") or {}
    lora = cfg.get("lora") or {}
    return {
        "primary": str(lora.get("ollama_primary") or models.get("primary") or "qwen-hakua-core"),
        "lite": str(lora.get("ollama_lite") or models.get("lite") or "qwen-hakua-core-lite"),
    }


def status_summary(cfg: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """Safe for /status: booleans and relative hints only (no raw secret paths in logs)."""
    base = resolve_base_model_dir(cfg)
    dirs = resolve_curriculum_dirs(cfg)
    soul = resolve_soul_path(cfg, repo_root)
    return {
        "base_model_configured": base is not None and base.exists(),
        "from_d_configured": dirs["from_d"] is not None and dirs["from_d"].exists(),
        "soul_found": soul.exists(),
        "ollama_models": ollama_model_names(cfg),
    }
