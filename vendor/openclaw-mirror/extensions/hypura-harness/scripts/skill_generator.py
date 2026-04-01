"""Skill generator — uses OpenClaw to design and create new skills."""
from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)
ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SKILL_CREATOR_INIT = REPO_ROOT / "skills" / "skill-creator" / "scripts" / "init_skill.py"
SKILL_CREATOR_PKG = REPO_ROOT / "skills" / "skill-creator" / "scripts" / "package_skill.py"
CONFIG_PATH = ROOT / "harness.config.json"
_config: dict = {}
if CONFIG_PATH.exists():
    _config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
_OPENCLAW_CLI = _config.get("openclaw", {}).get("cli_binary", "openclaw")


def _generate_skill_body(name: str, description: str, examples: list[str]) -> str:
    """Ask OpenClaw to write the SKILL.md body."""
    prompt = (
        f"Write the body section of a SKILL.md for a skill named '{name}'.\n"
        f"Description: {description}\n"
        f"Usage examples:\n" + "\n".join(f"- {e}" for e in examples)
        + "\n\nReturn only the markdown body (no frontmatter). Be concise."
    )
    for cli in [_OPENCLAW_CLI, "claude"]:
        try:
            if cli == _OPENCLAW_CLI:
                cmd = [cli, "run", "--", prompt]
            else:
                cmd = [cli, "-p", prompt, "--output-format", "text"]
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return (
        f"# {name}\n\n{description}\n\n## Examples\n\n"
        + "\n".join(f"- {e}" for e in examples)
    )


class SkillGenerator:
    def create_skill(self, name: str, description: str, examples: list[str]) -> dict:
        skill_dir = SKILLS_DIR / name

        if SKILL_CREATOR_INIT.exists():
            r = subprocess.run(
                ["py", "-3", str(SKILL_CREATOR_INIT), name, "--path", str(SKILLS_DIR)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if r.returncode != 0:
                logger.warning("init_skill failed: %s", r.stderr)

        skill_dir.mkdir(parents=True, exist_ok=True)
        skill_md_path = skill_dir / "SKILL.md"
        body = _generate_skill_body(name, description, examples)
        frontmatter = (
            f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n"
        )
        skill_md_path.write_text(frontmatter + body, encoding="utf-8")

        if SKILL_CREATOR_PKG.exists():
            subprocess.run(
                ["py", "-3", str(SKILL_CREATOR_PKG), str(skill_dir)],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

        return {"success": True, "skill_path": str(skill_dir), "name": name}
