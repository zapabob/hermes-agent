"""LoRA curriculum + train orchestration for harness_daemon."""
from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Any

from curriculum_ingest import IngestConfig, build_records, write_jsonl
from grpo_runner import run_grpo_job
from lora_jobs import JobStore
from lora_paths import (
    resolve_artifacts_root,
    resolve_base_model_dir,
    resolve_curriculum_dirs,
    resolve_soul_path,
)
from lora_trainer import train_sft_lora, train_tiny_lora

logger = logging.getLogger(__name__)


def collect_extra_jsonl(cfg: dict[str, Any], repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    dirs = resolve_curriculum_dirs(cfg)
    for key in ("from_d", "so8t_data", "downloads_ghost"):
        p = dirs.get(key)
        if p is None:
            continue
        if p.is_file() and p.suffix == ".jsonl":
            paths.append(p)
        elif p.is_dir():
            for child in sorted(p.glob("*.jsonl")):
                paths.append(child)
    lora = cfg.get("lora") or {}
    for item in lora.get("extra_jsonl_globs") or []:
        # simple paths relative to repo or absolute
        raw = str(item).strip()
        if not raw:
            continue
        pp = Path(raw).expanduser()
        if not pp.is_absolute():
            pp = repo_root / pp
        if pp.is_file():
            paths.append(pp)
    return paths


async def run_build_curriculum(
    job_id: str,
    store: JobStore,
    cfg: dict[str, Any],
    repo_root: Path,
    arxiv_ids: list[str],
    include_soul: bool,
    extra_paths: list[str] | None,
) -> None:
    store.update(job_id, status="running", message="building curriculum")
    try:
        soul = resolve_soul_path(cfg, repo_root) if include_soul else None
        extras = collect_extra_jsonl(cfg, repo_root)
        if extra_paths:
            for e in extra_paths:
                p = Path(e).expanduser()
                if not p.is_absolute():
                    p = repo_root / p
                if p.exists():
                    extras.append(p)
        icfg = IngestConfig(
            arxiv_ids=arxiv_ids,
            soul_path=soul,
            extra_jsonl_paths=extras,
        )
        records = await asyncio.to_thread(build_records, icfg)
        out = resolve_artifacts_root(cfg) / "curriculum" / f"{job_id}.jsonl"
        n = await asyncio.to_thread(write_jsonl, records, out)
        latest = resolve_artifacts_root(cfg) / "curriculum" / "latest.jsonl"
        latest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out, latest)
        store.update(
            job_id,
            status="completed",
            message=f"wrote {n} records",
            result={"output_path": str(out), "records": n, "latest": str(latest)},
        )
    except Exception as e:
        logger.exception("curriculum build failed")
        store.update(job_id, status="failed", error=str(e))


async def run_train_job(
    job_id: str,
    store: JobStore,
    cfg: dict[str, Any],
    dataset_path: Path | None,
    dry_run: bool,
    mode: str = "auto",
    extra_options: dict[str, Any] | None = None,
) -> None:
    """
    LoRA 学習ジョブを実行する。

    mode:
      "auto"      : config の tinylora.enabled フラグで自動選択
      "tinylora"  : TinyLoRA GRPO (arXiv:2602.04118, 13 params, 秒単位)
      "sft"       : 標準 QLoRA SFT (数千 params, 分単位)
    """
    lora_cfg = cfg.get("lora") or {}

    # モード選択
    if mode == "auto":
        tinylora_cfg = lora_cfg.get("tinylora") or {}
        use_tiny = bool(tinylora_cfg.get("enabled", False))
        mode = "tinylora" if use_tiny else "sft"

    store.update(job_id, status="running", message=f"training [{mode}]")
    try:
        base = resolve_base_model_dir(cfg)
        if base is None or not base.exists():
            store.update(
                job_id,
                status="failed",
                error="base model dir not configured or missing (set HAKUA_BASE_MODEL_DIR)",
            )
            return
        art = resolve_artifacts_root(cfg)
        ds = dataset_path or (art / "curriculum" / "latest.jsonl")
        if not ds.exists():
            store.update(
                job_id,
                status="failed",
                error=f"dataset not found: {ds}",
            )
            return
        out = art / "train_runs" / job_id

        if mode == "tinylora":
            tinylora_defaults = lora_cfg.get("tinylora") or {}
            opts = {
                "tinylora_r": tinylora_defaults.get("r", 2),
                "tinylora_u": tinylora_defaults.get("u", 1),
                "tinylora_tying": tinylora_defaults.get("tying", "tile"),
                "grpo_group_size": tinylora_defaults.get("grpo_group_size", 4),
                "learning_rate": tinylora_defaults.get("learning_rate", 1e-3),
                "use_qlora": tinylora_defaults.get("use_qlora_base", True),
                "num_train_epochs": tinylora_defaults.get("n_epochs", 1),
            }
            opts.update(extra_options or {})
            result = await asyncio.to_thread(
                train_tiny_lora,
                base_model_dir=base,
                dataset_path=ds,
                output_dir=out,
                dry_run=dry_run,
                train_options=opts,
            )
        else:
            sft_opts = lora_cfg.get("sft") if isinstance(lora_cfg.get("sft"), dict) else {}
            sft_opts = dict(sft_opts)
            sft_opts.update(extra_options or {})
            result = await asyncio.to_thread(
                train_sft_lora,
                base_model_dir=base,
                dataset_path=ds,
                output_dir=out,
                dry_run=dry_run,
                train_options=sft_opts,
            )

        if result.get("success"):
            store.update(
                job_id,
                status="completed",
                message=f"train [{mode}] finished",
                result=result,
            )
        else:
            store.update(
                job_id,
                status="failed",
                error=str(result.get("error")),
                result=result,
            )
    except Exception as e:
        logger.exception("train failed")
        store.update(job_id, status="failed", error=str(e))


async def run_grpo_job_async(
    job_id: str,
    store: JobStore,
    cfg: dict[str, Any],
    dataset_path: Path | None,
    mode: str,
) -> None:
    label = "grpo placeholder" if mode.strip().lower() == "placeholder" else "grpo train manifest"
    store.update(job_id, status="running", message=label)
    try:
        art = resolve_artifacts_root(cfg)
        ds = dataset_path or (art / "curriculum" / "latest.jsonl")
        if not ds.exists():
            store.update(
                job_id,
                status="failed",
                error=f"dataset not found: {ds}",
            )
            return
        out = art / "grpo_runs" / job_id
        report = await asyncio.to_thread(
            run_grpo_job,
            mode=mode,
            dataset_path=ds,
            output_dir=out,
            cfg=cfg,
            grpo_options=None,
            ref_model_name=None,
        )
        store.update(
            job_id,
            status="completed",
            message=f"grpo {mode} finished",
            result=report,
        )
    except Exception as e:
        store.update(job_id, status="failed", error=str(e))
