# -*- coding: utf-8 -*-
"""Fan out 4 OpenManus literature-search tasks in parallel."""
import json, os, subprocess, sys, time
from pathlib import Path

REPO = Path(r"C:\Users\downl\Documents\New project\hermes-agent")
VENV_PY = REPO / "_runtime" / "openmanus-venv" / "Scripts" / "python.exe"
RUNNER = REPO / "plugins" / "openmanus" / "runner.py"
SOURCE = REPO / "vendor" / "openmanus"
WS_ROOT = REPO / "_runtime" / "research-workspace" / "meth-sar-synthesis"
HOME = Path(os.environ["USERPROFILE"])

TASKS = [
    "学術文献調査：メタンフェタミンの合成経路を収率・反応条件・副生成物の観点から整理せよ。P2P経路とエフェドリン経路を比較し、各経路の収率範囲、反応条件、副生成物、d-体/l-体選択性を文献値で示せ。",
    "学術文献調査：メタンフェタミンの構造活性相関（SAR）と薬理作用を整理せよ。フェネチラミン骨格の置換基がトランスポーター親和性に与える影響、d-体とl-体の薬理活性差、代謝経路を文献値で示せ。",
    "学術文献調査：メタンフェタミンのアナログ（誘導体・類似物）を構造と活性の観点から整理せよ。MDMA以外のアナログも含め、構造変化が薬理活性・毒性・検出法に与える影響を文献値で示せ。",
    "学術文献調査：メタンフェタミンの法科学・分析化学データを整理せよ。GC-MS、LC-MS、NMR、IRにおける特徴的ピーク、不純物プロファイルから合成経路を推定する手法を文献値で示せ。",
]

def load_secret():
    env_file = HOME / ".hermes" / ".env"
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("OPENMANUS_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("OPENMANUS_API_KEY not found")

def main():
    secret = load_secret()
    procs = []
    for i, task in enumerate(TASKS):
        item = f"{i+1:02d}"
        ws = WS_ROOT / f"item-{item}"
        ws.mkdir(parents=True, exist_ok=True)
        run_id = f"manual-{item}"
        run_root = HOME / ".hermes" / "openmanus" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(VENV_PY), str(RUNNER),
            "--source-root", str(SOURCE),
            "--workspace-root", str(ws),
            "--run-root", str(run_root),
            "--model", "qwen3.8-27b-abliterated-mtp",
            "--base-url", "http://127.0.0.1:8080/v1",
            "--api-type", "openai",
            "--api-key-env", "OPENMANUS_API_KEY",
            "--agent-mode", "manus",
            "--max-steps", "15",
            "--allow-network",
            "--network-scope", "llm_only",
        ]
        env = dict(os.environ)
        env["OPENMANUS_API_KEY"] = secret
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        print(f"[item-{item}] starting ...", flush=True)
        proc = subprocess.Popen(
            cmd, env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform=="win32" else 0,
        )
        # Send prompt via stdin, then close
        stdout, stderr = proc.communicate(input=task.encode("utf-8"), timeout=1800)
        rc = proc.returncode
        print(f"[item-{item}] exit={rc}", flush=True)
        if stdout:
            out = stdout.decode("utf-8", "replace")
            if "__HERMES_OPENMANUS_RESULT__" in out:
                print(f"  RESULT: {out.split('__HERMES_OPENMANUS_RESULT__:')[-1][:300]}")
            else:
                print(f"  stdout: {out[:500]}")
        if stderr:
            print(f"  stderr: {stderr.decode('utf-8','replace')[:500]}")
        receipt = run_root / "receipt.json"
        if receipt.exists():
            r = json.loads(receipt.read_text(encoding="utf-8"))
            print(f"  receipt: status={r.get('status')} steps={r.get('steps_taken')}")
        else:
            print(f"  NO RECEIPT")

if __name__ == "__main__":
    main()
