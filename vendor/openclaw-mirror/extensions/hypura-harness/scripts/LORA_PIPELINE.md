# Hypura LoRA / curriculum pipeline

## Quick reference (production SFT)

- **Deps**: `cd scripts/hypura && uv sync --extra lora` (torch, transformers, peft, datasets, trl, accelerate).
- **Base model**: set `HAKUA_BASE_MODEL_DIR` to a local Hugging Face–compatible folder (SafeTensors + `config.json` + tokenizer), or the same path in `harness.config.json` under `lora.base_model_dir`.
- **Dataset**: `artifacts/lora/curriculum/latest.jsonl` (from `POST /lora/curriculum/build`) or `dataset_path` on `POST /lora/train`. Rows use `instruction` / `output`, or `messages` for chat templates when the tokenizer defines `chat_template`.
- **Train**: `POST /lora/train` with `{ "dry_run": false }`. **Requires CUDA** unless `lora.sft.allow_cpu` is `true` (debug only). Hyperparameters live under `lora.sft` in [`scripts/hypura/harness.config.json`](scripts/hypura/harness.config.json) (epochs, batch size, LoRA rank, `max_seq_length`, etc.).
- **Outputs**: `artifacts/lora/train_runs/<job_id>/manifest.json`, checkpoints under `train_runs/<job_id>/checkpoints/`, adapter + tokenizer under `train_runs/<job_id>/adapter/`.
- **GRPO**: use `POST /lora/grpo` with `mode: "placeholder"` (default) or `mode: "train"` (manifest + TRL probe). Legacy `POST /lora/grpo/placeholder` is unchanged. See [GRPO (data, rewards, paper)](#grpo-data-rewards-paper) below.

## GRPO: data, rewards, paper {#grpo-data-rewards-paper}

### Reference ([arXiv:2602.04118](https://arxiv.org/abs/2602.04118))

- **Learning to Reason in 13 Parameters** (TinyLoRA line of work) compares **SFT vs RL** on math/reasoning: **RL (e.g. GRPO)** can be effective at **low adapter capacity**, while **SFT** often needs **larger updates** for comparable gains. Hypura uses **SFT LoRA first** (format, tools, templates), then **GRPO as stage 2** for verifiable tasks—aligned with that split.
- **Not in default harness scope**: full **TinyLoRA** parameterization, **VERL**, **vLLM** custom kernels, and **merge-vs-train importance sampling** from the paper. Standard path is **TRL `GRPOTrainer`-style wiring** plus **rule-based / exact-match rewards** where applicable.

### JSONL schema (GRPO-ready rows)

Extend plain `instruction` / `output` with optional fields (one JSON object per line):

| Field                    | Purpose                                                                                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `messages`               | Chat-style turns; use when `tokenizer.chat_template` should drive the prompt (multimodal: image refs as placeholders or IDs your pipeline resolves—do not commit local paths). |
| `tools`                  | Tool **definitions** (OpenAI-style schema fragment) for the session.                                                                                                           |
| `tool_calls`             | Expected or gold **tool invocations** (structured JSON) for scoring / imitation.                                                                                               |
| `answer` or `gold`       | **Verifiable** target: final number, normalized expression, or string for **exact-match** reward.                                                                              |
| `domain`                 | e.g. `math`, `science`, `ai`, `tool_smoke`—for **reward weighting** or filtering (read in `lora.grpo`).                                                                        |
| `instruction` / `output` | Still supported for SFT-style rows; GRPO prompts can be derived the same way as SFT.                                                                                           |

**SOUL.md / Hakua / STEM**: ingest via `POST /lora/curriculum/build` (SOUL + arXiv + extra JSONL). Prefer **rule extracts** from SOUL for system/developer text or reward hooks—not dumping secrets into public datasets.

### Rewards (design)

- **Math / STEM (verifiable)**: **exact match** or **execution** against `gold` (paper-style **exact-match** on GSM8K-class tasks).
- **Tool calling**: **KL** to a **reference** policy (base or SFT adapter) plus **format** rewards (valid JSON/tool schema, required tags). Configure `lora.grpo.reward`, `kl_coef`, `ref_model_dir` in [`scripts/hypura/harness.config.json`](scripts/hypura/harness.config.json).
- **Multimodal (short term)**: assume **frozen vision tower**; GRPO on **text/LoRA** only unless you extend the runner for image+text batches.

### Outputs

- **placeholder** `mode`: `artifacts/lora/grpo_runs/<job_id>/grpo_placeholder.json` (resolved config + dataset stats).
- **train** `mode`: `artifacts/lora/grpo_runs/<job_id>/grpo_train_manifest.json` (manifest + TRL availability; full GPU GRPO requires extra reward wiring—see report `note`).

## Async jobs

- `POST /lora/curriculum/build` → `job_id`; poll `GET /lora/jobs/{job_id}`.
- `POST /lora/train` → `job_id`; uses `artifacts/lora/curriculum/latest.jsonl` when `dataset_path` omitted.
- `POST /lora/grpo` → body `{ "mode": "placeholder" \| "train", "dataset_path": null }`; legacy `POST /lora/grpo/placeholder` → same as `mode: "placeholder"`.

Job state files live under `artifacts/lora/jobs/{uuid}.json` (local only).

## Privacy

- Do not log full operator paths in shared logs. Prefer env vars (`HAKUA_*`) and local-only `harness.config.local.json` (gitignored).
- Never commit API tokens for Hugging Face; use `HF_TOKEN` in the environment for uploads.

## Hugging Face release (checklist)

1. Confirm base model license and attribution on the Model Card.
2. List training data sources (arXiv titles, SOUL excerpt policy, private JSONL — gated if needed).
3. Choose adapter vs merged weights; document merge command if applicable.
4. Set repo visibility (public vs gated) per policy.
5. Run red-team / safety review on sample completions before wide release.

## imatrix

- Typically **post-training**: GGUF quantization with llama.cpp importance matrix.
- Keep separate from GRPO/SFT unless you explicitly calibrate during quant only.

## mHC (2512.24880)

- Paper describes **architecture** (Manifold-Constrained Hyper-Connections). LoRA-SFT does not automatically implement it; align any custom `mHC` label in external scripts separately.

## OpenSpace (optional)

- Runtime skill evolution via MCP: see `skills/hypura-harness/SKILL.md` OpenSpace subsection.
