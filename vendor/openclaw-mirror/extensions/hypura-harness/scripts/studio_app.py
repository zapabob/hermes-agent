"""Optional Gradio UI for LoRA curriculum + train (calls local harness HTTP API).

Run from ``scripts/hypura``::

  uv sync --extra studio
  uv run python studio_app.py

Requires harness on ``127.0.0.1:18794`` (``harness_daemon.py``).
"""
from __future__ import annotations

import json
import os
import time

import httpx

HARNESS = os.environ.get("HYPURA_HARNESS_URL", "http://127.0.0.1:18794").rstrip("/")


def _poll_job(job_id: str) -> dict:
    deadline = time.time() + 120
    while time.time() < deadline:
        r = httpx.get(f"{HARNESS}/lora/jobs/{job_id}", timeout=10.0)
        r.raise_for_status()
        body = r.json()
        if body.get("status") in ("completed", "failed"):
            return body
        time.sleep(0.4)
    return {"status": "timeout", "job_id": job_id}


def main() -> None:
    try:
        import gradio as gr
    except ImportError as e:
        raise SystemExit(
            "gradio not installed. Run: uv sync --extra studio"
        ) from e

    def build_curriculum(arxiv: str, include_soul: bool) -> str:
        ids = [x.strip() for x in arxiv.replace(",", " ").split() if x.strip()]
        r = httpx.post(
            f"{HARNESS}/lora/curriculum/build",
            json={"arxiv_ids": ids, "include_soul": include_soul, "extra_jsonl": []},
            timeout=30.0,
        )
        r.raise_for_status()
        job_id = r.json()["job_id"]
        return json.dumps(_poll_job(job_id), indent=2, ensure_ascii=False)

    def train(dry_run: bool) -> str:
        r = httpx.post(
            f"{HARNESS}/lora/train",
            json={"dry_run": dry_run, "dataset_path": None},
            timeout=30.0,
        )
        r.raise_for_status()
        job_id = r.json()["job_id"]
        return json.dumps(_poll_job(job_id), indent=2, ensure_ascii=False)

    with gr.Blocks(title="Hypura LoRA Studio") as demo:
        gr.Markdown("# Hypura LoRA Studio\nCalls the local harness API.")
        with gr.Row():
            arxiv = gr.Textbox(
                label="arXiv ids (space/comma)",
                value="2603.17187 2602.04118 2512.24880",
            )
            soul = gr.Checkbox(label="Include SOUL.md from repo", value=True)
        b1 = gr.Button("Build curriculum")
        out1 = gr.Textbox(label="Job result", lines=16)
        b1.click(build_curriculum, [arxiv, soul], out1)

        dry = gr.Checkbox(label="Train dry-run (manifest only)", value=True)
        b2 = gr.Button("Run train job")
        out2 = gr.Textbox(label="Train result", lines=16)
        b2.click(train, [dry], out2)

    demo.launch(server_name="127.0.0.1", server_port=int(os.environ.get("HYPURA_STUDIO_PORT", "18792")))


if __name__ == "__main__":
    main()
