# scripts/hypura/tests/test_skill_generator.py
from unittest.mock import MagicMock, patch


def test_create_skill_calls_init_script() -> None:
    with (
        patch("skill_generator.subprocess.run") as mock_run,
        patch("skill_generator.Path.exists", return_value=True),
        patch("pathlib.Path.write_text", MagicMock()),
        patch("skill_generator.Path.mkdir"),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from skill_generator import SkillGenerator

        gen = SkillGenerator()
        gen.create_skill("my-test-skill", "A test skill", ["example 1"])
        assert mock_run.called


def test_create_skill_returns_path_on_success() -> None:
    with (
        patch("skill_generator.subprocess.run") as mock_run,
        patch("skill_generator.Path.exists", return_value=True),
        patch("skill_generator.Path.mkdir"),
        patch("pathlib.Path.write_text", MagicMock()),
    ):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        from skill_generator import SkillGenerator

        gen = SkillGenerator()
        result = gen.create_skill("my-skill", "desc", ["example"])
        assert result["success"] is True
        assert "my-skill" in result.get("skill_path", "")
