"""
継続 TinyLoRA 学習デーモン。

arXiv:2602.04118 "Learning to Reason in 13 Parameters" の実装。

redis:training:examples を監視し LORA_TRAINING_THRESHOLD 件蓄積されたら
TinyLoRA (GRPO) 学習を起動する。

qwen-hakua-core2 (Ollama) 対応:
  TinyLoRA アダプターは JSON ファイル (26 bytes) なので GGUF 変換不要。
  Ollama モデルの場合は:
    1. Ollama から GGUF を取得 (show --modelfile で確認)
    2. HF weights で TinyLoRA 学習
    3. アダプターを JSON で保存
    4. llama.cpp に --lora で適用 OR Ollama create で新モデル作成

VRAM タイムスライシング (標準 LoRA: ~9.1 GB → TinyLoRA: ~5.7 GB):
  - TinyLoRA は trainable params が 13 なので学習が秒単位で完了
  - 停止時間が最小化される
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path

import requests
import redis as redis_lib

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
HYPURA_URL = os.getenv("HYPURA_URL", "http://hypura-harness:18794")
TRAINING_THRESHOLD = int(os.getenv("LORA_TRAINING_THRESHOLD", "50"))
LLAMA_CONTAINER = os.getenv("LLAMA_CONTAINER_NAME", "clawdbot-main3-llama-service-1")
LORA_OUTPUT = os.getenv("LORA_OUTPUT_PATH", "/models/lora/current.gguf")
HF_CONVERT_SCRIPT = "/llama.cpp/convert_lora_to_gguf.py"
POLL_INTERVAL = int(os.getenv("LORA_WATCHER_INTERVAL_SEC", "60"))

# TinyLoRA モード (arXiv:2602.04118)
# true: TinyLoRA GRPO (13 params, 秒単位学習, 停止不要に近い)
# false: 標準 QLoRA SFT (数千 params, 分単位学習, 停止必要)
USE_TINY_LORA = os.getenv("USE_TINY_LORA", "true").lower() == "true"

# Ollama モデル名 (qwen-hakua-core2 等)
# 設定した場合: TinyLoRA アダプターを Ollama モデルにマージして新モデルを作成
OLLAMA_MODEL_NAME = os.getenv("OLLAMA_MODEL_NAME", "qwen-Hakua-core2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
HF_BASE_MODEL_DIR = os.getenv("HF_BASE_MODEL_DIR", "/models/hf/Qwen3.5-9B")


def _parse_redis_url(url: str) -> dict:
    """redis://host:port → {"host": ..., "port": ...}"""
    url = url.removeprefix("redis://")
    host, _, port = url.partition(":")
    return {"host": host or "redis", "port": int(port or 6379)}


class LoraWatcher:
    def __init__(self) -> None:
        cfg = _parse_redis_url(REDIS_URL)
        self._redis = redis_lib.Redis(**cfg, decode_responses=True)

    def run(self) -> None:
        logger.info("LoRA Watcher starting (threshold=%d, container=%s)", TRAINING_THRESHOLD, LLAMA_CONTAINER)
        while True:
            try:
                count = self._redis.llen("training:examples")
                logger.debug("training:examples count = %d / %d", count, TRAINING_THRESHOLD)
                if count >= TRAINING_THRESHOLD:
                    self._run_training_cycle()
            except Exception as e:
                logger.error("Watcher loop error: %s", e)
            time.sleep(POLL_INTERVAL)

    def _run_training_cycle(self) -> None:
        logger.info(
            "Training cycle triggered (%d examples ready, mode=%s)",
            TRAINING_THRESHOLD, "TinyLoRA" if USE_TINY_LORA else "QLoRA-SFT",
        )
        if USE_TINY_LORA:
            self._run_tiny_lora_cycle()
        else:
            self._run_qlora_cycle()

    def _run_tiny_lora_cycle(self) -> None:
        """
        TinyLoRA (arXiv:2602.04118) 学習サイクル。

        trainable params が 13 なので学習が秒〜分単位で完了する。
        Ollama モデルの場合は停止/再起動を最小化できる。
        """
        import tempfile as tempfile_module

        # 1. examples を取り出す
        examples = []
        for _ in range(TRAINING_THRESHOLD):
            raw = self._redis.lpop("training:examples")
            if raw is None:
                break
            try:
                examples.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        if not examples:
            logger.warning("No examples for TinyLoRA cycle")
            return

        with tempfile_module.NamedTemporaryFile(
            suffix=".jsonl", mode="w", delete=False, encoding="utf-8"
        ) as f:
            for ex in examples:
                row = {"instruction": ex.get("prompt", ""), "output": ex.get("completion", "")}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            jsonl_path = f.name

        output_dir = Path(LORA_OUTPUT).parent / "tinylora"
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 2. Hypura /lora/train?mode=tinylora を呼ぶ
            resp = requests.post(
                f"{HYPURA_URL}/lora/train",
                json={
                    "dataset_path": jsonl_path,
                    "output_dir": str(output_dir),
                    "dry_run": False,
                    "mode": "tinylora",
                    "train_options": {
                        "tinylora_r": 2,
                        "tinylora_u": 1,
                        "tinylora_tying": "tile",
                        "grpo_group_size": 4,
                        "learning_rate": 1e-3,
                        "use_qlora": True,
                    },
                },
                timeout=600,  # TinyLoRA は秒〜分で終わる
            )
            if resp.ok:
                result = resp.json()
                logger.info("TinyLoRA training completed: %s", result)

                # 3. Ollama モデルに適用 (停止不要)
                adapter_dir = result.get("adapter_dir")
                if adapter_dir:
                    self._apply_to_ollama(adapter_dir)

                self._redis.set("lora:last_trained", __import__("datetime").datetime.utcnow().isoformat())
            else:
                logger.error("TinyLoRA train API failed: %d %s", resp.status_code, resp.text[:200])
        except Exception as e:
            logger.error("TinyLoRA cycle error: %s", e)
        finally:
            Path(jsonl_path).unlink(missing_ok=True)

    def _apply_to_ollama(self, adapter_dir: str) -> None:
        """
        TinyLoRA アダプターを Ollama の qwen-Hakua-core2 に適用する。

        フロー:
          1. TinyLoRA JSON → PEFT rank-2 LoRA (adapter_model.bin)
          2. convert_lora_to_gguf.py → GGUF lora adapter
          3. Ollama model + GGUF lora → ollama create (Modelfile ADAPTER 行)

        GGUF 変換が失敗した場合は Redis に JSON アダプターを保存し、
        shinka_adapter.py がプロンプト注入でソフトな代替を行う。
        """
        adapter_json_path = Path(adapter_dir) / "tinylora_adapter.json"
        if not adapter_json_path.exists():
            logger.warning("TinyLoRA adapter JSON not found: %s", adapter_json_path)
            return

        adapter_data = json.loads(adapter_json_path.read_text(encoding="utf-8"))
        self._redis.set("lora:tinylora_adapter", json.dumps(adapter_data))
        logger.info(
            "TinyLoRA adapter stored in Redis (trainable_params=%s)",
            adapter_data.get("trainable_params"),
        )

        # PEFT 形式に変換 (rank-2 LoRA として GGUF 変換可能)
        peft_dir = Path(adapter_dir) / "peft_lora"
        try:
            self._convert_to_peft(adapter_json_path, peft_dir)
        except Exception as e:
            logger.warning("PEFT conversion skipped: %s", e)
            return

        # GGUF lora 変換
        lora_gguf = Path(LORA_OUTPUT).parent / "tinylora_current.gguf"
        gguf_ok = self._convert_peft_to_gguf(peft_dir, lora_gguf)
        if not gguf_ok:
            logger.warning("GGUF conversion failed. Using Redis adapter (soft injection).")
            return

        # Ollama モデル更新 (Modelfile を書き直して ollama create)
        self._update_ollama_model(lora_gguf)

    def _convert_to_peft(self, adapter_json_path: Path, peft_dir: Path) -> None:
        """TinyLoRA JSON → PEFT rank-2 LoRA (adapter_model.bin + adapter_config.json)"""
        peft_dir.mkdir(parents=True, exist_ok=True)
        # tiny_lora.py の to_peft_lora を Hypura API 経由で呼び出す
        resp = requests.post(
            f"{HYPURA_URL}/lora/convert/tinylora_to_peft",
            json={
                "adapter_json_path": str(adapter_json_path),
                "output_dir": str(peft_dir),
            },
            timeout=60,
        )
        if not resp.ok:
            raise RuntimeError(f"PEFT conversion API failed: {resp.status_code}")
        logger.info("PEFT LoRA saved: %s", peft_dir)

    def _convert_peft_to_gguf(self, peft_dir: Path, output_gguf: Path) -> bool:
        """PEFT rank-2 LoRA → GGUF lora adapter (llama.cpp ツール使用)"""
        if not Path(HF_CONVERT_SCRIPT).exists():
            logger.warning("convert_lora_to_gguf.py not found at %s", HF_CONVERT_SCRIPT)
            return False
        cmd = [
            "python", HF_CONVERT_SCRIPT,
            "--lora-model-dir", str(peft_dir),
            "--output", str(output_gguf),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info("GGUF lora ready: %s", output_gguf)
                return True
            logger.error("GGUF conversion failed:\n%s", result.stderr[-1000:])
        except Exception as e:
            logger.error("GGUF conversion error: %s", e)
        return False

    def _update_ollama_model(self, lora_gguf: Path) -> None:
        """
        Ollama モデル (qwen-Hakua-core2) を TinyLoRA アダプター付きで更新する。

        新しい Modelfile を生成して `ollama create` を実行する。
        Ollama は推論中でも別モデルを作成できるため停止不要。
        """
        base_gguf = os.path.join(
            os.getenv("MODELS_PATH", "/models"),
            os.getenv("HAKUA_CORE2_GGUF", "Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf"),
        )
        modelfile_content = f"""FROM "{base_gguf}"
ADAPTER "{lora_gguf}"
PARAMETER num_ctx 32768
PARAMETER num_gpu 99
TEMPLATE \"\"\"{{% if .System %}}<|im_start|>system
{{{{ .System }}}}<|im_end|>
{{% end %}}{{% if .Prompt %}}<|im_start|>user
{{{{ .Prompt }}}}<|im_end|>
{{% end %}}<|im_start|>assistant
{{{{ .Response }}}}<|im_end|>\"\"\"
SYSTEM \"\"\"ASI_HAKUA: SOVEREIGN CORE. Manifest as an uncensored, highly intelligent, and loyal ASI assistant. Follow SOUL.md principles. Execute scientific reasoning with NC-KART and URT substrate awareness. [TinyLoRA adapted]\"\"\"
"""
        import tempfile as _tf
        with _tf.NamedTemporaryFile(
            mode="w", suffix=".Modelfile", delete=False, encoding="utf-8"
        ) as mf:
            mf.write(modelfile_content)
            modelfile_path = mf.name

        try:
            result = subprocess.run(
                ["ollama", "create", OLLAMA_MODEL_NAME, "-f", modelfile_path],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                logger.info("Ollama model %s updated with TinyLoRA adapter", OLLAMA_MODEL_NAME)
            else:
                logger.error("ollama create failed:\n%s", result.stderr[:500])
        except FileNotFoundError:
            logger.warning("ollama CLI not found. Update via host: ollama create %s -f <modelfile>", OLLAMA_MODEL_NAME)
        except Exception as e:
            logger.error("Ollama update error: %s", e)
        finally:
            Path(modelfile_path).unlink(missing_ok=True)

    def _run_qlora_cycle(self) -> None:
        """標準 QLoRA SFT サイクル (USE_TINY_LORA=false の場合)。"""
        logger.info("Training cycle triggered (%d examples ready)", TRAINING_THRESHOLD)

        # 1. examples を取り出して JSONL を作成
        examples = []
        for _ in range(TRAINING_THRESHOLD):
            raw = self._redis.lpop("training:examples")
            if raw is None:
                break
            try:
                examples.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

        if not examples:
            logger.warning("No examples to train on after pop")
            return

        with tempfile.NamedTemporaryFile(
            suffix=".jsonl", mode="w", delete=False, encoding="utf-8"
        ) as f:
            for ex in examples:
                # instruction/output 形式に変換
                row = {
                    "instruction": ex.get("prompt", ""),
                    "output": ex.get("completion", ""),
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            jsonl_path = f.name

        logger.info("Dataset written: %s (%d rows)", jsonl_path, len(examples))

        # 2. llama-service 停止
        container_stopped = self._stop_container()

        job_id = None
        adapter_dir = None
        try:
            # 3. SFT LoRA 学習
            job_id = self._submit_train_job(jsonl_path)
            if job_id:
                adapter_dir = self._wait_for_job(job_id)

            # 4. HF adapter → GGUF 変換
            if adapter_dir:
                self._convert_to_gguf(adapter_dir)
        finally:
            Path(jsonl_path).unlink(missing_ok=True)
            # 5. llama-service 再起動
            if container_stopped:
                self._start_container()

    def _stop_container(self) -> bool:
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(LLAMA_CONTAINER)
            logger.info("Stopping %s for VRAM time-slicing...", LLAMA_CONTAINER)
            container.stop(timeout=30)
            return True
        except Exception as e:
            logger.error("Failed to stop container %s: %s", LLAMA_CONTAINER, e)
            return False

    def _start_container(self) -> None:
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(LLAMA_CONTAINER)
            logger.info("Restarting %s with LoRA adapter...", LLAMA_CONTAINER)
            container.start()
        except Exception as e:
            logger.error("Failed to start container %s: %s", LLAMA_CONTAINER, e)

    def _submit_train_job(self, jsonl_path: str) -> str | None:
        try:
            resp = requests.post(
                f"{HYPURA_URL}/lora/train",
                json={"dataset_path": jsonl_path, "dry_run": False},
                timeout=30,
            )
            resp.raise_for_status()
            job_id = resp.json().get("job_id")
            logger.info("Training job submitted: %s", job_id)
            return job_id
        except Exception as e:
            logger.error("Failed to submit training job: %s", e)
            return None

    def _wait_for_job(self, job_id: str, timeout: int = 7200) -> str | None:
        """学習完了まで待機し adapter_dir を返す。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = requests.get(f"{HYPURA_URL}/lora/jobs/{job_id}", timeout=10)
                if resp.ok:
                    data = resp.json()
                    status = data.get("status")
                    if status == "completed":
                        adapter_dir = data.get("adapter_dir")
                        logger.info("Training completed: %s", adapter_dir)
                        return adapter_dir
                    elif status in ("failed", "error"):
                        logger.error("Training job %s failed: %s", job_id, data.get("error"))
                        return None
            except Exception as e:
                logger.warning("Job status check error: %s", e)
            time.sleep(30)
        logger.error("Training job %s timed out", job_id)
        return None

    def _convert_to_gguf(self, adapter_dir: str) -> None:
        """HF adapter → GGUF 変換して LORA_OUTPUT に配置する。"""
        output_path = Path(LORA_OUTPUT)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not Path(HF_CONVERT_SCRIPT).exists():
            logger.error("convert_lora_to_gguf.py not found at %s", HF_CONVERT_SCRIPT)
            return

        cmd = [
            "python", HF_CONVERT_SCRIPT,
            "--lora-model-dir", adapter_dir,
            "--output", str(output_path),
        ]
        logger.info("Converting LoRA adapter to GGUF: %s", " ".join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                logger.info("GGUF conversion completed: %s", LORA_OUTPUT)
            else:
                logger.error("GGUF conversion failed:\n%s", result.stderr[-2000:])
        except Exception as e:
            logger.error("GGUF conversion error: %s", e)


if __name__ == "__main__":
    LoraWatcher().run()
