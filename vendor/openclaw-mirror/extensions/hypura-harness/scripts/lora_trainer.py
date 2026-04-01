"""LoRA SFT training entrypoint — optional torch/peft/trl; dry-run without GPU."""
from __future__ import annotations

import importlib.util
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_LORA_TARGETS = (
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
)


def optional_training_stack_available() -> dict[str, bool]:
    def has(name: str) -> bool:
        return importlib.util.find_spec(name) is not None

    return {
        "torch": has("torch"),
        "peft": has("peft"),
        "transformers": has("transformers"),
        "trl": has("trl"),
        "datasets": has("datasets"),
    }


def validate_dataset_jsonl(path: Path) -> dict[str, Any]:
    """Light validation: count rows, min keys."""
    if not path.exists():
        return {"ok": False, "error": "dataset missing", "rows": 0}
    rows = 0
    with path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                return {"ok": False, "error": f"invalid json: {e}", "rows": rows}
            rows += 1
            if "instruction" not in obj and "messages" not in obj:
                pass  # curriculum_ingest uses instruction/output
    return {"ok": True, "rows": rows}


def _row_to_text(row: dict[str, Any], tokenizer: Any) -> str:
    """Build a single training string from instruction/output or chat messages."""
    msgs = row.get("messages")
    if msgs and isinstance(msgs, list):
        tmpl = getattr(tokenizer, "apply_chat_template", None)
        chat_tmpl = getattr(tokenizer, "chat_template", None)
        if callable(tmpl) and chat_tmpl:
            try:
                return tmpl(msgs, tokenize=False, add_generation_prompt=False)
            except Exception:
                logger.warning("chat_template failed; falling back to plain text")
    inst = str(row.get("instruction", ""))
    out = str(row.get("output", ""))
    return f"### Instruction:\n{inst}\n\n### Response:\n{out}"


def _run_sft_lora_training(
    *,
    base_model_dir: Path,
    dataset_path: Path,
    output_dir: Path,
    train_options: dict[str, Any],
) -> dict[str, Any]:
    import torch
    from datasets import load_dataset
    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    allow_cpu = bool(train_options.get("allow_cpu", False))
    if not torch.cuda.is_available() and not allow_cpu:
        return {
            "success": False,
            "error": (
                "CUDA not available; set lora.sft.allow_cpu=true for tiny debug only "
                "(large models need a GPU)"
            ),
        }

    stack = optional_training_stack_available()
    if not all(stack.get(k) for k in ("torch", "peft", "transformers", "datasets")):
        return {
            "success": False,
            "error": "missing torch/peft/transformers/datasets",
            "stack": stack,
        }

    max_seq_length = int(train_options.get("max_seq_length", 2048))
    trust_remote_code = bool(train_options.get("trust_remote_code", True))

    tokenizer = AutoTokenizer.from_pretrained(
        str(base_model_dir),
        trust_remote_code=trust_remote_code,
    )
    if tokenizer.pad_token is None and tokenizer.eos_token is not None:
        tokenizer.pad_token = tokenizer.eos_token

    ds = load_dataset("json", data_files=str(dataset_path), split="train")

    def add_text(batch: dict[str, list[Any]]) -> dict[str, list[str]]:
        texts: list[str] = []
        if not batch:
            return {"text": []}
        keys = list(batch.keys())
        n = len(batch[keys[0]])
        for i in range(n):
            row = {k: batch[k][i] for k in keys}
            texts.append(_row_to_text(row, tokenizer))
        return {"text": texts}

    ds = ds.map(add_text, batched=True, remove_columns=ds.column_names)

    def tokenize_batch(examples: dict[str, list[str]]) -> dict[str, Any]:
        return tokenizer(
            examples["text"],
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )

    tokenized = ds.map(
        tokenize_batch,
        batched=True,
        remove_columns=ds.column_names,
        desc="tokenize",
    )

    if torch.cuda.is_available():
        torch_dtype = (
            torch.bfloat16
            if torch.cuda.is_bf16_supported()
            else torch.float16
        )
        device_map: str | None = "auto"
    else:
        torch_dtype = torch.float32
        device_map = None

    # QLoRA 4-bit 量子化ロード (RTX 3060 12GB 対応: ~5.6 GB → 学習込み ~9.1 GB)
    # bitsandbytes が利用可能な場合は NF4 量子化を使用
    bnb_config = None
    if torch.cuda.is_available() and bool(train_options.get("use_qlora", True)):
        try:
            from transformers import BitsAndBytesConfig
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            )
            logger.info("QLoRA: NF4 4-bit quantization enabled (~5.6 GB for 9B model)")
        except ImportError:
            logger.warning("bitsandbytes not available; falling back to BF16 load (~18 GB)")
            bnb_config = None

    model_kwargs: dict = {
        "trust_remote_code": trust_remote_code,
        "device_map": device_map,
        "low_cpu_mem_usage": True,
    }
    if bnb_config is not None:
        model_kwargs["quantization_config"] = bnb_config
    else:
        model_kwargs["torch_dtype"] = torch_dtype

    model = AutoModelForCausalLM.from_pretrained(
        str(base_model_dir),
        **model_kwargs,
    )

    target_modules = train_options.get("lora_target_modules")
    if isinstance(target_modules, str):
        target_modules = [s.strip() for s in target_modules.split(",") if s.strip()]
    if not target_modules:
        target_modules = list(_DEFAULT_LORA_TARGETS)

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=int(train_options.get("lora_r", 16)),
        lora_alpha=int(train_options.get("lora_alpha", 32)),
        lora_dropout=float(train_options.get("lora_dropout", 0.05)),
        bias="none",
        target_modules=target_modules,
    )
    model = get_peft_model(model, peft_config)
    if hasattr(model, "gradient_checkpointing_enable"):
        model.gradient_checkpointing_enable()

    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    out_final = Path(output_dir) / "adapter"
    out_final.mkdir(parents=True, exist_ok=True)

    use_bf16 = bool(
        torch.cuda.is_available()
        and torch.cuda.is_bf16_supported()
        and train_options.get("bf16", True)
    )
    use_fp16 = bool(
        torch.cuda.is_available()
        and not use_bf16
        and train_options.get("fp16", True)
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=float(train_options.get("num_train_epochs", 1)),
        per_device_train_batch_size=int(
            train_options.get("per_device_train_batch_size", 1)
        ),
        gradient_accumulation_steps=int(
            train_options.get("gradient_accumulation_steps", 8)
        ),
        learning_rate=float(train_options.get("learning_rate", 2e-4)),
        warmup_ratio=float(train_options.get("warmup_ratio", 0.03)),
        logging_steps=int(train_options.get("logging_steps", 10)),
        save_steps=int(train_options.get("save_steps", 500)),
        save_total_limit=int(train_options.get("save_total_limit", 2)),
        bf16=use_bf16,
        fp16=use_fp16,
        gradient_checkpointing=True,
        optim=str(train_options.get("optim", "adamw_torch")),
        report_to="none",
        max_grad_norm=float(train_options.get("max_grad_norm", 1.0)),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=collator,
        tokenizer=tokenizer,
    )

    trainer.train()
    model.save_pretrained(str(out_final))
    tokenizer.save_pretrained(str(out_final))

    return {
        "success": True,
        "mode": "sft_lora",
        "adapter_dir": str(out_final),
        "rows": len(tokenized),
        "train_options": {k: v for k, v in train_options.items() if k != "hf_token"},
    }


def train_sft_lora(
    *,
    base_model_dir: Path,
    dataset_path: Path,
    output_dir: Path,
    dry_run: bool = True,
    extra_env: dict[str, str] | None = None,
    train_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run SFT LoRA training or dry-run manifest.

    When ``dry_run`` is True, only writes ``manifest.json`` and does not load torch.
    When ``dry_run`` is False, requires torch/peft/transformers/datasets and a CUDA GPU
    unless ``train_options.allow_cpu`` is true.
    """
    _ = extra_env  # reserved for subprocess-based runners
    opts = dict(train_options or {})

    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "base_model_dir": str(base_model_dir),
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "dry_run": dry_run,
        "stack": optional_training_stack_available(),
        "train_options": opts,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    val = validate_dataset_jsonl(dataset_path)
    if not val.get("ok"):
        return {"success": False, "error": val.get("error"), "manifest": manifest}

    if dry_run:
        return {
            "success": True,
            "mode": "dry_run",
            "rows": val.get("rows"),
            "message": (
                "manifest written; set dry_run=false and install extras "
                "(uv sync --extra lora) to run GPU training"
            ),
        }

    stack = optional_training_stack_available()
    if not all(stack.get(k) for k in ("torch", "peft", "transformers", "datasets")):
        return {
            "success": False,
            "error": "missing torch/peft/transformers/datasets",
            "stack": stack,
            "manifest": manifest,
        }

    try:
        result = _run_sft_lora_training(
            base_model_dir=base_model_dir,
            dataset_path=dataset_path,
            output_dir=output_dir,
            train_options=opts,
        )
    except Exception as e:
        logger.exception("SFT LoRA training failed")
        return {
            "success": False,
            "error": str(e),
            "manifest": manifest,
            "rows": val.get("rows"),
        }

    out = {**result, "manifest": manifest, "rows": val.get("rows")}
    return out


def run_llamacpp_imatrix_quantize(
    *,
    gguf_path: Path,
    output_gguf: Path,
    imatrix_path: Path | None,
) -> dict[str, Any]:
    """Optional wrapper to call llama.cpp quantize with imatrix (if binaries on PATH)."""
    # Placeholder: llama-quantize location varies by install
    return {
        "success": False,
        "message": "imatrix quantization is host-specific; run llama.cpp tools manually or pass script path in future.",
        "gguf": str(gguf_path),
        "out": str(output_gguf),
        "imatrix": str(imatrix_path) if imatrix_path else None,
    }


def train_tiny_lora(
    *,
    base_model_dir: Path,
    dataset_path: Path,
    output_dir: Path,
    dry_run: bool = True,
    train_options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    TinyLoRA (arXiv:2602.04118) による学習。

    標準 LoRA の代わりに TinyLoRA パラメータ化を使用:
      ΔW = A · diag(P @ v) · B
      A, B: frozen (SVD), P: fixed random, v: trainable (u=1 → 1 param/module)

    GRPO (Group Relative Policy Optimization) で学習する。
    SFT は極小パラメータ数では機能しない（論文 Section 4 参照）。

    RTX 3060 12GB 向け:
      - 4-bit base (QLoRA): ~5.6 GB
      - TinyLoRA 学習オーバーヘッド: ~0.1 GB (13 パラメータ = 26 bytes)
      - 合計: ~5.7 GB (通常 LoRA の 9.1 GB より大幅に少ない)
    """
    opts = dict(train_options or {})
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "base_model_dir": str(base_model_dir),
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "dry_run": dry_run,
        "mode": "tinylora_grpo",
        "train_options": opts,
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    val = validate_dataset_jsonl(dataset_path)
    if not val.get("ok"):
        return {"success": False, "error": val.get("error"), "manifest": manifest}

    if dry_run:
        return {
            "success": True,
            "mode": "tinylora_dry_run",
            "rows": val.get("rows"),
            "message": (
                "TinyLoRA manifest written; set dry_run=false to run. "
                "Requires torch + transformers. "
                "Training: ΔW = A·diag(P@v)·B, GRPO reward=execution_success"
            ),
        }

    stack = optional_training_stack_available()
    if not stack.get("torch") or not stack.get("transformers"):
        return {
            "success": False,
            "error": "torch/transformers required for TinyLoRA",
            "stack": stack,
        }

    try:
        import json as json_module
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        from tiny_lora import TinyLoRAModel, TinyLoRAGRPOTrainer

        r = int(opts.get("tinylora_r", 2))
        u = int(opts.get("tinylora_u", 1))
        tying = str(opts.get("tinylora_tying", "tile"))
        group_size = int(opts.get("grpo_group_size", 4))
        lr = float(opts.get("learning_rate", 1e-3))
        n_epochs = int(opts.get("num_train_epochs", 1))

        # ベースモデルを QLoRA 4-bit でロード (RTX 3060 対応)
        bnb_config = None
        if torch.cuda.is_available() and bool(opts.get("use_qlora", True)):
            try:
                from transformers import BitsAndBytesConfig
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                    bnb_4bit_compute_dtype=torch.bfloat16,
                )
            except ImportError:
                pass

        model_kwargs: dict = {
            "trust_remote_code": True,
            "device_map": "auto" if torch.cuda.is_available() else None,
        }
        if bnb_config is not None:
            model_kwargs["quantization_config"] = bnb_config
        else:
            model_kwargs["torch_dtype"] = torch.bfloat16

        base_model = AutoModelForCausalLM.from_pretrained(str(base_model_dir), **model_kwargs)
        tokenizer = AutoTokenizer.from_pretrained(str(base_model_dir), trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # TinyLoRA を適用 (v ベクトルのみ学習可能になる)
        tinylora = TinyLoRAModel(
            base_model,
            r=r,
            u=u,
            tying=tying,
        )
        total_params = tinylora.trainable_parameter_count()
        logger.info("TinyLoRA trainable parameters: %d", total_params)

        # データセットを読み込む
        examples = []
        with dataset_path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        examples.append(json_module.loads(line))
                    except json.JSONDecodeError:
                        pass

        # 報酬関数: コード実行成功率をベースにした簡易報酬
        def reward_fn(prompt: str, response: str) -> float:
            import ast
            # Python コードブロックを抽出して構文チェック
            import re
            match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
            code = match.group(1) if match else response.strip()
            try:
                ast.parse(code)
                return 1.0
            except SyntaxError:
                return 0.0

        # GRPO トレーナーで学習
        trainer = TinyLoRAGRPOTrainer(
            model=tinylora,
            tokenizer=tokenizer,
            reward_fn=reward_fn,
            lr=lr,
            group_size=group_size,
        )
        result = trainer.train(examples, n_epochs=n_epochs)

        # アダプターを保存 (JSON 形式; GGUF 変換は不要)
        out_dir = output_dir / "tinylora_adapter"
        adapter_data = tinylora.save_adapter(out_dir)

        return {
            "success": True,
            "mode": "tinylora_grpo",
            "adapter_dir": str(out_dir),
            "rows": len(examples),
            "trainable_params": total_params,
            "train_result": result,
            "adapter_data": adapter_data,
        }

    except Exception as e:
        logger.exception("TinyLoRA training failed")
        return {"success": False, "error": str(e), "manifest": manifest}


def try_subprocess(cmd: list[str]) -> dict[str, Any]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        return {
            "success": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout[-4000:],
            "stderr": p.stderr[-4000:],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
