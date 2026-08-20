"""
APPDATA (~/.hermes) を正本としてリポジトリ側の設定 (.hermes) を連接・同期するスクリプト
"""
import shutil
import logging
from pathlib import Path
from typing import List

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_appdata_to_repo")

def sync_appdata_to_repo() -> None:
    appdata_hermes = Path(r"c:\Users\downl\.hermes")
    repo_root = Path(r"c:\Users\downl\Documents\New project\hermes-agent")
    repo_hermes = repo_root / ".hermes"
    repo_cli_skins = repo_root / "hermes_cli" / "skins"

    logger.info("=== STARTING CONNECTION & SYNC: APPDATA (PRIMARY) -> REPOSITORY ===")

    if not appdata_hermes.exists():
        logger.error("APPDATA source %s does not exist!", appdata_hermes)
        return

    repo_hermes.mkdir(parents=True, exist_ok=True)
    repo_cli_skins.mkdir(parents=True, exist_ok=True)

    # 1. 重要設定ファイルの一覧（APPDATA側を正本とする）
    config_files: List[str] = [
        "config.yaml",
        ".env",
        "auth.json",
        "channel_directory.json",
        "SOUL.md",
        "context_length_cache.yaml",
        "provider_models_cache.json"
    ]

    for fname in config_files:
        src = appdata_hermes / fname
        dst = repo_hermes / fname
        if src.exists():
            # バックアップ
            if dst.exists():
                bak = dst.with_suffix(dst.suffix + ".bak-appdata-sync")
                shutil.copy2(dst, bak)
            shutil.copy2(src, dst)
            logger.info("Synchronized config file: %s -> %s", src.name, dst)
        else:
            logger.info("Source file %s not present in APPDATA, skipping", fname)

    # 2. skins ディレクトリの同期（APPDATA -> repo .hermes/skins & repo hermes_cli/skins）
    appdata_skins = appdata_hermes / "skins"
    repo_dot_skins = repo_hermes / "skins"
    repo_dot_skins.mkdir(parents=True, exist_ok=True)

    if appdata_skins.exists():
        for skin_file in appdata_skins.iterdir():
            if skin_file.is_file():
                shutil.copy2(skin_file, repo_dot_skins / skin_file.name)
                shutil.copy2(skin_file, repo_cli_skins / skin_file.name)
                logger.info("Synchronized skin asset: %s", skin_file.name)

    # 3. cron 設定や plugins/skills 定義の同期
    for folder in ["cron", "plugins", "skills", "hooks"]:
        src_f = appdata_hermes / folder
        dst_f = repo_hermes / folder
        if src_f.exists() and src_f.is_dir():
            dst_f.mkdir(parents=True, exist_ok=True)
            for item in src_f.glob("*"):
                if item.is_file():
                    shutil.copy2(item, dst_f / item.name)
                    logger.info("Synchronized %s/%s", folder, item.name)

    logger.info("=== CONNECTION & SYNC COMPLETE: Repository is now fully linked to APPDATA ===")

if __name__ == "__main__":
    sync_appdata_to_repo()
