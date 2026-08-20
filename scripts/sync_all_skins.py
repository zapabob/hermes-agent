"""
~/.hermes/skins のテーマ・壁紙一式をリポジトリ正本（hermes_cli/skins, .hermes/skins）へ同期
"""
import shutil
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_twilight_hakua")

def sync_all_skins() -> None:
    src_dir = Path(r"c:\Users\downl\.hermes\skins")
    dst_repo_cli_skins = Path(r"c:\Users\downl\Documents\New project\hermes-agent\hermes_cli\skins")
    dst_repo_dot_skins = Path(r"c:\Users\downl\Documents\New project\hermes-agent\.hermes\skins")

    dst_repo_cli_skins.mkdir(parents=True, exist_ok=True)
    dst_repo_dot_skins.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        logger.error("Source dir %s does not exist", src_dir)
        return

    for item in src_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, dst_repo_cli_skins / item.name)
            shutil.copy2(item, dst_repo_dot_skins / item.name)
            logger.info("Copied %s -> %s and %s", item.name, dst_repo_cli_skins, dst_repo_dot_skins)

    logger.info("Sync complete. Items in repo hermes_cli/skins: %s", [f.name for f in dst_repo_cli_skins.iterdir()])

if __name__ == "__main__":
    sync_all_skins()
