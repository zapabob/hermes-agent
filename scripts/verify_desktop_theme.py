"""
デスクトップ反映検証スクリプト
"""
import yaml
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("desktop_verifier")

def verify() -> None:
    repo_cfg = Path(r"c:\Users\downl\Documents\New project\hermes-agent\.hermes\config.yaml")
    user_cfg = Path(r"c:\Users\downl\.hermes\config.yaml")
    repo_presets = Path(r"c:\Users\downl\Documents\New project\hermes-agent\apps\desktop\src\themes\presets.ts")

    with open(repo_cfg, "r", encoding="utf-8") as f:
        rc = yaml.safe_load(f)
    logger.info("Repo config skin: %s", rc.get("display", {}).get("skin"))

    with open(user_cfg, "r", encoding="utf-8") as f:
        uc = yaml.safe_load(f)
    logger.info("User config skin: %s", uc.get("display", {}).get("skin"))

    with open(repo_presets, "r", encoding="utf-8") as f:
        presets_content = f.read()

    assert "twilight-hakua" in presets_content, "twilight-hakua must be in presets.ts"
    assert "hakuaTheme" in presets_content, "hakuaTheme must be in presets.ts"
    assert "twilight-hakua-portrait-bg.png" in presets_content, "wallpaper path must be in presets.ts"

    logger.info("Desktop presets and config verification PASSED!")

if __name__ == "__main__":
    verify()
