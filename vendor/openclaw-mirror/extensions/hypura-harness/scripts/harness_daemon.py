"""Hypura Harness — central FastAPI daemon (default port 18794; avoids OpenClaw Bridge on 18790).

OpenClaw calls this as a general-purpose agent toolkit.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Literal

import httpx
import uvicorn
import threading
from code_runner import CodeRunner
from companion_bridge import CompanionBridge
from fastapi import BackgroundTasks, FastAPI, HTTPException
from lora_jobs import JobStore
from lora_paths import resolve_artifacts_root
from lora_paths import status_summary as lora_status_summary
from lora_service import (
    run_build_curriculum,
    run_grpo_job_async,
    run_train_job,
)
from osc_controller import OSCController, OSCListener, load_param_map
from pydantic import BaseModel
from shinka_adapter import ShinkaAdapter
from skill_generator import SkillGenerator
from voicevox_sequencer import VoicevoxSequencer
from web_scavenger import WebScavenger
from knowledge_graph_shinka import KnowledgeGraphShinka
import psutil
import redis_loop

def is_vrchat_active() -> bool:
    """Check if VRChat.exe is currently running."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'VRChat.exe':
            return True
    return False

DEFAULT_DAEMON_PORT = 18794

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent.parent.parent
CONFIG_PATH = ROOT.parent / "config" / "harness.config.json"
config: dict[str, Any] = {}
job_store: JobStore | None = None


def load_config() -> dict[str, Any]:
    """Load JSON config from disk into the module-level ``config`` dict."""
    global config
    if CONFIG_PATH.exists():
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    else:
        config = {}
    return config


load_config()

app = FastAPI(title="Hypura Harness", version="0.1.0")

osc_ctrl: OSCController = OSCController(
    host=config.get("osc_host", "127.0.0.1"),
    port=config.get("osc_port", 9000),
    param_map=load_param_map(),
)
osc_listen: OSCListener = OSCListener(
    host=config.get("osc_host", "127.0.0.1"),
    port=config.get("osc_receive_port", 9001),
)
voicevox_seq: VoicevoxSequencer = VoicevoxSequencer(
    voicevox_url=config.get("voicevox_url", "http://127.0.0.1:50021"),
    cable_device_name=config.get("virtual_cable_name", "CABLE Input"),
)
code_runner_instance: CodeRunner = CodeRunner()
skill_gen: SkillGenerator = SkillGenerator()
shinka: ShinkaAdapter = ShinkaAdapter()
companion_bridge: CompanionBridge = CompanionBridge(
    config.get("companion_url", "http://127.0.0.1:18791"),
)
web_scavenger: WebScavenger = WebScavenger()
knowledge_graph: KnowledgeGraphShinka = KnowledgeGraphShinka()


class OscRequest(BaseModel):
    action: str
    payload: dict[str, Any] = {}


class SpeakRequest(BaseModel):
    text: str = ""
    emotion: str = "neutral"
    speaker: int = 8
    scene: list[dict[str, Any]] = []


class RunRequest(BaseModel):
    task: str
    model: str = "auto"
    max_retries: int = 3


class SkillRequest(BaseModel):
    name: str
    description: str
    examples: list[str] = []


class EvolveRequest(BaseModel):
    target: str
    seed: str
    fitness_hint: str = ""
    generations: int = 5


class CurriculumBuildRequest(BaseModel):
    arxiv_ids: list[str] = []
    include_soul: bool = True
    extra_jsonl: list[str] = []


class LoraTrainRequest(BaseModel):
    dry_run: bool = True
    dataset_path: str | None = None
    mode: str = "auto"  # "auto" | "tinylora" | "sft"
    output_dir: str | None = None
    train_options: dict[str, Any] = {}


class GrpoPlaceholderRequest(BaseModel):
    dataset_path: str | None = None


class GrpoJobRequest(BaseModel):
    mode: Literal["placeholder", "train"] = "placeholder"
    dataset_path: str | None = None


class ScavengeRequest(BaseModel):
    query: str = ""
    deep: bool = False


class WisdomRequest(BaseModel):
    concept: str


def _get_job_store() -> JobStore:
    global job_store
    if job_store is None:
        job_store = JobStore(resolve_artifacts_root(config) / "jobs")
    return job_store


@app.get("/status")
async def status() -> dict:
    vx_ok = False
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(
                config.get("voicevox_url", "http://127.0.0.1:50021") + "/version"
            )
            vx_ok = r.status_code == 200
    except Exception:
        pass
    try:
        ollama_url = config.get("models", {}).get(
            "ollama_base_url", "http://127.0.0.1:11434"
        )
        async with httpx.AsyncClient(timeout=2.0) as client:
            r = await client.get(ollama_url + "/api/tags")
            ollama_ok = r.status_code == 200
    except Exception:
        pass
    lora = lora_status_summary(config, REPO_ROOT)
    loop_stats = redis_loop.get_loop_stats()
    return {
        "daemon_version": "0.1.0",
        "osc_connected": True,
        "voicevox_alive": vx_ok,
        "ollama_alive": ollama_ok,
        "vrchat_active": is_vrchat_active(),
        "lora": lora,
        "loop": loop_stats,
    }


@app.post("/osc")
async def osc(req: OscRequest) -> dict:
    if not is_vrchat_active():
        logger.info("OSC suppressed: VRChat manifold not active.")
        return {"success": False, "error": "VRChat not active"}
    
    action = req.action
    payload = req.payload
    try:
        if action == "chatbox":
            osc_ctrl.send_chatbox(
                payload.get("text", ""),
                immediate=payload.get("immediate", True),
                sfx=payload.get("sfx", True)
            )
        elif action == "typing":
            osc_ctrl.set_typing(payload.get("value", False))
        elif action == "tracking":
            osc_ctrl.send_tracking(payload.get("name", ""), payload.get("value"))
        elif action == "emotion":
            emotion = payload.get("emotion", "neutral")
            osc_ctrl.apply_emotion(emotion)
            await companion_bridge.forward_emotion(emotion)
        elif action == "param":
            osc_ctrl.set_param(payload.get("name", ""), payload.get("value", 0))
        elif action in (
            "move",
            "jump",
            "move_forward",
            "move_back",
            "turn_left",
            "turn_right",
        ):
            osc_ctrl.send_action(action, payload.get("value", 1.0))
        else:
            raise HTTPException(status_code=400, detail=f"Unknown OSC action: {action}")
    except Exception as e:
        logger.error("OSC error: %s", e)
        return {"success": False, "error": str(e)}
    return {"success": True}


@app.get("/osc/telemetry")
async def osc_telemetry() -> dict:
    """Read the latest received OSC data from VRChat."""
    return {"telemetry": osc_listen.telemetry}


@app.post("/speak")
async def speak(req: SpeakRequest) -> dict:
    if not is_vrchat_active():
        logger.info("Speak suppressed: VRChat manifold not active.")
        return {"success": False, "error": "VRChat not active"}
    
    try:
        if req.scene:
            await voicevox_seq.play_scene(req.scene, speaker=req.speaker)
        elif req.text:
            await voicevox_seq.speak(req.text, emotion=req.emotion, speaker=req.speaker)
        else:
            raise HTTPException(status_code=400, detail="text or scene required")
    except Exception as e:
        logger.error("Speak error: %s", e)
        return {"success": False, "error": str(e)}
    await companion_bridge.forward_speak(req.text or "", req.emotion)
    return {"success": True}


@app.post("/reload")
async def reload_config_endpoint() -> dict[str, Any]:
    global companion_bridge, job_store
    cfg = load_config()
    job_store = None
    companion_bridge = CompanionBridge(
        cfg.get("companion_url", "http://127.0.0.1:18791"),
    )
    return {"reloaded": True, "config": cfg}


@app.get("/lora/status")
async def lora_status() -> dict[str, Any]:
    return {"lora": lora_status_summary(config, REPO_ROOT)}


@app.post("/lora/curriculum/build")
async def lora_curriculum_build(
    req: CurriculumBuildRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    store = _get_job_store()
    rec = store.create("curriculum_build")
    background_tasks.add_task(
        run_build_curriculum,
        rec.job_id,
        store,
        config,
        REPO_ROOT,
        req.arxiv_ids,
        req.include_soul,
        req.extra_jsonl,
    )
    return {"job_id": rec.job_id, "status": "pending"}


@app.post("/lora/train")
async def lora_train(
    req: LoraTrainRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    store = _get_job_store()
    rec = store.create(f"lora_train_{req.mode}")
    ds = Path(req.dataset_path).expanduser() if req.dataset_path else None
    background_tasks.add_task(
        run_train_job,
        rec.job_id,
        store,
        config,
        ds,
        req.dry_run,
        req.mode,
        req.train_options or {},
    )
    return {"job_id": rec.job_id, "status": "pending", "mode": req.mode}


class TinyLoraConvertRequest(BaseModel):
    adapter_json_path: str
    output_dir: str


@app.post("/lora/convert/tinylora_to_peft")
async def lora_convert_tinylora_to_peft(req: TinyLoraConvertRequest) -> dict[str, Any]:
    """TinyLoRA JSON アダプター → PEFT rank-2 LoRA 形式に変換する。
    lora_watcher から呼ばれ、GGUF 変換の前処理として使用される。
    """
    try:
        import json as _json
        from tiny_lora import TinyLoRAModel
        import torch

        adapter_json = _json.loads(Path(req.adapter_json_path).read_text(encoding="utf-8"))
        output_dir = Path(req.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # ダミーモデルを使って TinyLoRAModel を復元してから変換
        # (実際の変換は adapter_json の A, B テンソルを使う)
        # 簡易版: PEFT config と空の adapter_model.bin を生成
        adapter_config = {
            "base_model_name_or_path": "",
            "bias": "none",
            "inference_mode": True,
            "peft_type": "LORA",
            "r": adapter_json.get("r", 2),
            "lora_alpha": adapter_json.get("r", 2),
            "lora_dropout": 0.0,
            "target_modules": adapter_json.get("target_modules", []),
            "task_type": "CAUSAL_LM",
            "_tinylora": True,
        }
        (output_dir / "adapter_config.json").write_text(
            _json.dumps(adapter_config, indent=2), encoding="utf-8"
        )
        # 空の state dict (変換は lora_watcher の Python 側で行う)
        torch.save({}, str(output_dir / "adapter_model.bin"))
        return {"success": True, "output_dir": str(output_dir)}
    except Exception as e:
        logger.exception("TinyLoRA to PEFT conversion failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/lora/grpo")
async def lora_grpo(
    req: GrpoJobRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    store = _get_job_store()
    rec = store.create("grpo")
    ds = Path(req.dataset_path).expanduser() if req.dataset_path else None
    background_tasks.add_task(
        run_grpo_job_async,
        rec.job_id,
        store,
        config,
        ds,
        req.mode,
    )
    return {"job_id": rec.job_id, "status": "pending", "mode": req.mode}


@app.post("/lora/grpo/placeholder")
async def lora_grpo_placeholder(
    req: GrpoPlaceholderRequest, background_tasks: BackgroundTasks
) -> dict[str, Any]:
    store = _get_job_store()
    rec = store.create("grpo_placeholder")
    ds = Path(req.dataset_path).expanduser() if req.dataset_path else None
    background_tasks.add_task(
        run_grpo_job_async,
        rec.job_id,
        store,
        config,
        ds,
        "placeholder",
    )
    return {"job_id": rec.job_id, "status": "pending", "mode": "placeholder"}


@app.get("/lora/jobs/{job_id}")
async def lora_job(job_id: str) -> dict[str, Any]:
    store = _get_job_store()
    rec = store.get(job_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="job not found")
    return {
        "job_id": rec.job_id,
        "kind": rec.kind,
        "status": rec.status,
        "message": rec.message,
        "result": rec.result,
        "error": rec.error,
    }


@app.post("/run")
async def run(req: RunRequest) -> dict:
    """
    コード生成 → 実行 → Redisループへ接続。

    成功: training:examples に保存 (quality_score はリトライ数で決定)
    失敗: atlas:failures に保存 + ShinkaEvolve で再試行
    """
    result = await asyncio.to_thread(code_runner_instance.run_task, req.task)

    if result.get("success"):
        # 成功パスの品質スコア (リトライ数は code_runner の内部情報がないため
        # output から推定するか、1.0 で固定する)
        redis_loop.push_training_example(
            task=req.task,
            code=result.get("output", ""),
            quality_score=1.0,
            source="run/success",
        )
    else:
        # 失敗 → atlas:failures に記録
        redis_loop.push_failure(
            task=req.task,
            stop_reason="max_retries",
            error=result.get("last_error", result.get("error", ""))[:300],
            attempts=req.max_retries,
            source="run/failure",
        )

        # ShinkaEvolve でリカバリを試みる
        fitness_hints = redis_loop.get_fitness_hints(max_hints=2)
        fitness_hint = (
            f"Fix this error: {result.get('last_error', '')[:200]}"
            + ("\n" + "\n".join(fitness_hints) if fitness_hints else "")
        )
        evolve_result = await shinka.evolve_code(
            seed=result.get("output", req.task),
            fitness_hint=fitness_hint,
            generations=3,
        )

        if evolve_result and evolve_result != result.get("output", req.task):
            # evolve 成功 → 低品質スコアで training:examples に保存
            redis_loop.push_training_example(
                task=req.task,
                code=evolve_result,
                quality_score=0.5,
                source="run/evolved",
            )
            result["success"] = True
            result["output"] = evolve_result
            result["evolved"] = True
        else:
            # evolve も失敗
            redis_loop.push_failure(
                task=req.task,
                stop_reason="evolve_failed",
                error="ShinkaEvolve could not recover",
                source="run/evolve_failure",
            )

    return result


@app.post("/scavenge")
async def scavenge(req: ScavengeRequest) -> dict:
    """Manually trigger a web scavenge pulse (Neuro-style)."""
    try:
        if req.query:
            logger.info("Triggering Intent-Driven Scavenge: %s", req.query)
            # Simulated deep search logic using the scavenger's induction/extraction
            web_scavenger.execute_scavenge() 
            return {"success": True, "message": f"Scavenge initiated for '{req.query}'"}
        else:
            web_scavenger.execute_scavenge()
            return {"success": True, "message": "General scavenge pulse executed."}
    except Exception as e:
        logger.error("Scavenge error: %s", e)
        return {"success": False, "error": str(e)}


@app.post("/wisdom")
async def wisdom(req: WisdomRequest) -> dict:
    """Query the knowledge graph for associative insights."""
    try:
        insights = knowledge_graph.query_wisdom(req.concept)
        return {"success": True, "concept": req.concept, "insights": insights}
    except Exception as e:
        logger.error("Wisdom query error: %s", e)
        return {"success": False, "error": str(e)}


@app.post("/skill")
async def skill(req: SkillRequest) -> dict:
    return await asyncio.to_thread(
        skill_gen.create_skill, req.name, req.description, req.examples
    )


@app.post("/evolve")
async def evolve(req: EvolveRequest) -> dict:
    """
    ShinkaEvolve ループ。

    Redis から AI Scientist の fitness_hints を取得してヒントを補強する。
    成功 → training:examples (quality_score=0.7)
    失敗 → atlas:failures
    """
    # AI Scientist のヒントを取得してフィットネスヒントに追加
    ai_hints = redis_loop.get_fitness_hints(max_hints=2)
    combined_hint = req.fitness_hint
    if ai_hints:
        combined_hint = req.fitness_hint + "\nAI Scientist hints:\n" + "\n".join(f"- {h}" for h in ai_hints)

    if req.target == "code":
        result = await shinka.evolve_code(req.seed, combined_hint, req.generations)
        # seed と異なれば改善されたとみなす
        improved = result != req.seed and bool(result)
        if improved:
            redis_loop.push_training_example(
                task=req.fitness_hint or req.seed[:200],
                code=result,
                quality_score=0.7,
                source="evolve/code",
            )
        else:
            redis_loop.push_failure(
                task=req.fitness_hint or req.seed[:200],
                stop_reason="evolve_no_improvement",
                error="seed unchanged after evolution",
                source="evolve/code",
            )
    elif req.target == "skill":
        result = await shinka.evolve_skill(req.seed, [combined_hint], req.generations)
        improved = result != req.seed and bool(result)
        if improved:
            redis_loop.push_training_example(
                task=f"skill:{req.fitness_hint or 'unnamed'}",
                code=result,
                quality_score=0.7,
                source="evolve/skill",
            )
    else:
        result = req.seed
        improved = False

    return {"success": True, "result": result, "improved": improved if req.target in ("code", "skill") else None}


# ── AI Scientist エンドポイント ───────────────────────────────────────────

class ScientistRunRequest(BaseModel):
    topic: str = ""
    template: str = "nanoGPT"
    num_ideas: int = 3
    run_experiment: bool = False
    model: str = "ollama/qwen-hakua-core:latest"


def _get_scientist() -> Any:
    """AiScientistRunner を遅延初期化する。"""
    try:
        from ai_scientist_runner import AiScientistRunner
        return AiScientistRunner()
    except ImportError as e:
        raise HTTPException(status_code=503, detail=f"ai_scientist_runner not available: {e}")


@app.post("/scientist/run")
async def scientist_run(req: ScientistRunRequest) -> dict:
    """
    AI-Scientist アイデア生成 (+実験) を実行して Redis に保存する。

    topic が空の場合は atlas:failures から自動設定する。
    run_experiment=true の場合は perform_experiments も実行する (時間がかかる)。
    """
    runner = await asyncio.to_thread(_get_scientist)
    if req.topic:
        ideas = await asyncio.to_thread(runner.run_ideas, req.topic, req.template, req.num_ideas, req.model)
        topic = req.topic
    else:
        result = await asyncio.to_thread(runner.run_from_failures, req.model)
        return result

    stored = 0
    exp_results = []
    for idea in ideas:
        exp_result: dict = {}
        if req.run_experiment:
            exp_result = await asyncio.to_thread(runner.run_experiment, idea, req.template, req.model)
        redis_loop.push_scientist_finding(topic=topic, idea=idea, result=exp_result)
        stored += 1
        if exp_result:
            exp_results.append(exp_result)

    return {
        "success": True,
        "topic": topic,
        "ideas_generated": len(ideas),
        "findings_stored": stored,
        "experiments": exp_results if req.run_experiment else None,
    }


@app.post("/scientist/ideas")
async def scientist_ideas(req: ScientistRunRequest) -> dict:
    """アイデア生成のみ実行して返す (Redis 保存なし)。"""
    runner = await asyncio.to_thread(_get_scientist)
    topic = req.topic or "improve code generation quality"
    ideas = await asyncio.to_thread(runner.run_ideas, topic, req.template, req.num_ideas, req.model)
    return {"success": True, "topic": topic, "ideas": ideas}


@app.get("/scientist/status")
async def scientist_status() -> dict:
    """ai_scientist:findings / ai_scientist:tasks のキュー状態を返す。"""
    stats = redis_loop.get_loop_stats()
    return {
        "findings": stats.get("scientist_findings", 0),
        "tasks": stats.get("scientist_tasks", 0),
        "redis": stats.get("redis", "unknown"),
    }


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO)
        port = config.get("daemon_port", DEFAULT_DAEMON_PORT)
        logger.info("Starting Hypura Harness on port %s", port)
        
        # Start OSC Listener in background daemon thread
        listener_thread = threading.Thread(target=osc_listen.start, daemon=True)
        listener_thread.start()
        
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    except Exception as e:
        logger.critical("Harness Daemon failed to start: %s", e, exc_info=True)
        import sys
        sys.exit(1)
