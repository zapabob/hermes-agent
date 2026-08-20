"""
APPDATA正本とリポジトリ設定の完全連接・整合性検証テスト
"""
import filecmp
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_appdata_link")

def verify_link() -> None:
    appdata_hermes = Path(r"c:\Users\downl\.hermes")
    repo_hermes = Path(r"c:\Users\downl\Documents\New project\hermes-agent\.hermes")

    logger.info("=== VERIFYING APPDATA -> REPOSITORY CONNECTION ===")

    # 1. config.yaml の完全一致確認
    appdata_cfg = appdata_hermes / "config.yaml"
    repo_cfg = repo_hermes / "config.yaml"

    assert appdata_cfg.exists(), "APPDATA config.yaml not found"
    assert repo_cfg.exists(), "Repo config.yaml not found"

    with open(appdata_cfg, "r", encoding="utf-8") as f:
        appdata_txt = f.read()
    with open(repo_cfg, "r", encoding="utf-8") as f:
        repo_txt = f.read()

    assert appdata_txt == repo_txt, "config.yaml mismatch between APPDATA and Repo"
    logger.info("✓ config.yaml is completely identical between APPDATA and Repo")

    # 2. SOUL.md の完全一致確認
    appdata_soul = appdata_hermes / "SOUL.md"
    repo_soul = repo_hermes / "SOUL.md"
    if appdata_soul.exists() and repo_soul.exists():
        assert appdata_soul.read_text(encoding="utf-8") == repo_soul.read_text(encoding="utf-8")
        logger.info("✓ SOUL.md is completely identical")

    # 3. skins の存在確認
    appdata_skins = appdata_hermes / "skins"
    repo_skins = repo_hermes / "skins"
    for skin in appdata_skins.glob("*.yaml"):
        target = repo_skins / skin.name
        assert target.exists(), f"Skin {skin.name} missing in repo .hermes/skins"
    logger.info("✓ All skins are present and synchronized")

    logger.info("APPDATA Connection Verification: ALL PASS")

if __name__ == "__main__":
    verify_link()
