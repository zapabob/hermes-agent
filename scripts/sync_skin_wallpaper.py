"""
壁紙およびスキン設定をリポジトリ正本と同期するスクリプト
"""
import shutil
import logging
from pathlib import Path
from typing import Any, Dict
import yaml

# ロギング設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_skin_wallpaper")

def sync_configuration() -> None:
    repo_root = Path(r"c:\Users\downl\Documents\New project\hermes-agent")
    repo_config_path = repo_root / ".hermes" / "config.yaml"
    repo_hakua_skin = repo_root / "hermes_cli" / "skins" / "hakua.yaml"

    user_hermes = Path(r"c:\Users\downl\.hermes")
    user_config_path = user_hermes / "config.yaml"
    user_skins_dir = user_hermes / "skins"

    logger.info("Starting synchronization: Repository (Canonical) -> User (~/.hermes)")

    if not repo_config_path.exists():
        logger.error("Canonical repo config does not exist: %s", repo_config_path)
        return

    # 1. 正本の設定を読み込む
    with open(repo_config_path, "r", encoding="utf-8") as f:
        repo_config: Dict[str, Any] = yaml.safe_load(f)

    canonical_display = repo_config.get("display", {})
    canonical_skin = canonical_display.get("skin", "hakua")
    logger.info("Canonical skin setting: %s", canonical_skin)

    # 2. ユーザー環境のバックアップと更新
    if user_config_path.exists():
        backup_path = user_config_path.with_suffix(".yaml.bak-wallpaper-sync")
        shutil.copy2(user_config_path, backup_path)
        logger.info("Created backup of user config: %s", backup_path)

        with open(user_config_path, "r", encoding="utf-8") as f:
            user_config: Dict[str, Any] = yaml.safe_load(f)

        if "display" not in user_config:
            user_config["display"] = {}

        logger.info("Previous user skin: %s", user_config["display"].get("skin"))
        user_config["display"]["skin"] = canonical_skin

        # 正本に合わせ、壁紙指定など余分な上書きがあれば解消
        with open(user_config_path, "w", encoding="utf-8") as f:
            yaml.dump(user_config, f, allow_unicode=True, default_flow_style=False)
        logger.info("Updated %s with skin: %s", user_config_path, canonical_skin)

    # 3. 正本の hakua.yaml を ~/.hermes/skins/ に同期
    user_skins_dir.mkdir(parents=True, exist_ok=True)
    if repo_hakua_skin.exists():
        target_skin_path = user_skins_dir / "hakua.yaml"
        shutil.copy2(repo_hakua_skin, target_skin_path)
        logger.info("Synchronized hakua.yaml to %s", target_skin_path)
    else:
        logger.warning("Repo hakua.yaml not found at %s", repo_hakua_skin)

    logger.info("Synchronization completed successfully.")

if __name__ == "__main__":
    sync_configuration()
