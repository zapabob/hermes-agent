"""
同期後の設定整合性検証スクリプト
"""
import os
import sys
import yaml
import logging
from pathlib import Path

# ログファイルにも出力
log_file = Path(r"c:\Users\downl\Documents\New project\hermes-agent\_docs\sync_verification.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="w", encoding="utf-8")
    ]
)
logger = logging.getLogger("sync_verifier")

def verify_sync() -> None:
    repo_config_path = Path(r"c:\Users\downl\Documents\New project\hermes-agent\.hermes\config.yaml")
    user_config_path = Path(r"c:\Users\downl\.hermes\config.yaml")
    repo_skin_path = Path(r"c:\Users\downl\Documents\New project\hermes-agent\hermes_cli\skins\hakua.yaml")
    user_skin_path = Path(r"c:\Users\downl\.hermes\skins\hakua.yaml")

    logger.info("=== VERIFICATION OF CONFIG SYNCHRONIZATION ===")

    # 1. ユーザー設定確認
    with open(user_config_path, "r", encoding="utf-8") as f:
        user_cfg = yaml.safe_load(f)
    user_skin = user_cfg.get("display", {}).get("skin")
    logger.info("User config skin setting: %s", user_skin)
    assert user_skin == "hakua", f"Expected skin 'hakua', got '{user_skin}'"

    # 2. 正本設定確認
    with open(repo_config_path, "r", encoding="utf-8") as f:
        repo_cfg = yaml.safe_load(f)
    repo_skin = repo_cfg.get("display", {}).get("skin")
    logger.info("Repo config skin setting: %s", repo_skin)
    assert repo_skin == "hakua", f"Expected skin 'hakua', got '{repo_skin}'"

    # 3. スキンファイル確認
    assert user_skin_path.exists(), f"User skin file does not exist at {user_skin_path}"
    assert repo_skin_path.exists(), f"Repo skin file does not exist at {repo_skin_path}"

    with open(user_skin_path, "r", encoding="utf-8") as f:
        user_skin_data = yaml.safe_load(f)
    with open(repo_skin_path, "r", encoding="utf-8") as f:
        repo_skin_data = yaml.safe_load(f)

    assert user_skin_data["name"] == repo_skin_data["name"], "Skin name mismatch"
    assert user_skin_data.get("background_image") == repo_skin_data.get("background_image"), "Background image setting mismatch"

    logger.info("Skin verification successful: user and repo configs are aligned with no unwanted wallpaper overrides.")
    logger.info("Verification result: PASS")

if __name__ == "__main__":
    verify_sync()
