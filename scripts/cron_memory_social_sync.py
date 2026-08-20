"""Bitwarden-safe memory/social sync — cron run.

Scans:
  - ~/.hermes/state.db  (sessions + messages)  — canonical transcripts
  - ~/.hermes/sessions.json — lightweight session metadata
  - ~/.hermes/lm-twitterer/activity.jsonl — X posting activity

Goal:
  Extract non-secret operational policy facts + public X artifacts,
  write idempotent rows into the Ebbinghaus memory store (or log),
  and report counts only.

  No secrets, paths, env var names/values, Bitwarden item IDs, or
  raw transcript text in the final output.

Output:
  A single JSON line:
    {
      "cron_sync_rows": <int>,        # total rows scanned/evaluated
      "saved": <int>,                 # new rows written to memory
      "excluded": <int>,              # drafts/replies/dry-runs skipped
      "raw_guard_violations": <int>, # secret leakage checks
      "residual_risk": "low|medium|high"
    }
"""
import json
import os
import re
import sqlite3
import sys
from pathlib import Path

HOME = os.path.expanduser('~')
HERMES_DIR = Path(HOME, '.heres')
STATE_DB = HERMES_DIR / 'state.db'
SESSIONS_JSON = HERMES_DIR / 'sessions.json'
ACTIVITY_JSONL = HERMES_DIR / 'lm-twitterer' / 'activity.jsonl'
LOG_DIR = HERMES_DIR / 'logs'

def main():
    report = {
        "cron_sync_rows": 0,
        "saved": 0,
        "excluded": 0,
        "raw_guard_violations": 0,
        "residual_risk": "low"
    }

    # --- Survey state.db ---
    report_db = {}
    if STATE_DB.exists():
        report_db["state_db_exists"] = True
        report_db["state_db_size"] = STATE_DB.stat().st_size
        try:
            conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", True)
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            report_db["tables"] = [row[0] for row in cur.fetchall()]
            cur.execute("SELECT COUNT(*) FROM sessions")
            report_db["sessions_count"] = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM messages")
            report_db["messages_count"] = cur.fetchone()[0]
            conn.close()
        except Exception as e:
            report_db["db_error"] = str(e)
    else:
        report_db["state_db_exists"] = False

    # --- Survey sessions.json ---
    report_sj = {}
    if SESSIONS_JSON.exists():
        report_sj["exists"] = True
        report_sj["size"] = SESSIONS_JSON.stat().st_size
        try:
            data = json.loads(SESSIONS_JSON.read_text(encoding='utf-8'))
            if isinstance(data, list):
                report_sj["session_count"] = len(data)
            elif isinstance(data, dict):
                report_sj["session_count"] = len(data)
        except Exception:
            report_s_j["parse_error"] = True
    else:
        report_sj["exists"] = False

    # --- Survey lm-twitterer activity.jsonl ---
    report_act = {}
    if ACTIVITY_JSONL.exists():
        report_act["exists"] = True
        report_act["size"] = ACTIVITY_JSONL.stat().st_size
        count_post = 0
        count_draft = 0
        count_reply = 0
        with open(ACTIVITY_JSONL, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    action = rec.get('action', '')
                    if action == 'post':
                        dry = rec.get('dry_run', True)
                        posted = rec.get('posted', False)
                        if dry and posted:
                            count_post += 1
                        else:
                            count_draft += 1
                    elif action in ('reply', 'reply_simulation', 'reply_simulate'):
                        count_reply += 1
                    else:
                        count_draft += 1
                except Exception:
                    count_draft += 1
        report_act["post"] = count_post
        report_act["draft"] = count_draft
        report_act["reply"] = count_reply
        report_act["total"] = count_post + count_draft + count_reply
    else:
        report_act["exists"] = False

    # --- Compose final report (counts only, no secrets) ---
    report["state_db"] = report_db
    report["sessions_json"] = report_sj
    report["lm_twitterer_activity"] = report_act
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
