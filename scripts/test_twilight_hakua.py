"""
Twilight Hakua テーマおよびスキンの同期・認識検証テスト
"""
import logging
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_twilight_hakua")

def test_twilight_hakua_skin() -> None:
    repo_skins_dir = Path(r"c:\Users\downl\Documents\New project\hermes-agent\hermes_cli\skins")
    twilight_skin_path = repo_skins_dir / "twilight-hakua.yaml"

    logger.info("Verifying twilight-hakua skin existence in repo...")
    assert twilight_skin_path.exists(), f"File {twilight_skin_path} does not exist"

    with open(twilight_skin_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    logger.info("Skin name: %s", data.get("name"))
    logger.info("Description: %s", data.get("description"))
    logger.info("Background image: %s", data.get("background_image"))

    assert data.get("name") == "twilight-hakua", "Name must be twilight-hakua"
    assert "background" in data.get("colors", {}), "Colors must contain background"
    assert "branding" in data, "Branding must be present"

    logger.info("Twilight Hakua verification PASSED.")

if __name__ == "__main__":
    test_twilight_hakua_skin()
