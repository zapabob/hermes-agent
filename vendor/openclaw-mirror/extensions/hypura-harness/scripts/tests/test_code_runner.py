# scripts/hypura/tests/test_code_runner.py
from unittest.mock import MagicMock, patch


def test_generate_code_uses_agent_first_when_gateway_enabled(monkeypatch) -> None:
    recorded: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        recorded.append(list(cmd))
        return MagicMock(
            returncode=0,
            stdout='```python\n# /// script\n# dependencies = []\n# ///\nprint("x")\n```',
            stderr="",
        )

    monkeypatch.setattr("code_runner.subprocess.run", fake_run)
    monkeypatch.setattr("code_runner._USE_GATEWAY_AGENT", True)
    from code_runner import _generate_code

    out = _generate_code("sample task")
    assert "print" in out
    assert recorded[0][0:3] == ["openclaw", "agent", "-m"]


def test_generate_code_skips_agent_when_gateway_disabled(monkeypatch) -> None:
    recorded: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        recorded.append(list(cmd))
        return MagicMock(
            returncode=0,
            stdout='```python\nprint("y")\n```',
            stderr="",
        )

    monkeypatch.setattr("code_runner.subprocess.run", fake_run)
    monkeypatch.setattr("code_runner._USE_GATEWAY_AGENT", False)
    from code_runner import _generate_code

    _generate_code("task")
    assert recorded[0][0:3] == ["openclaw", "run", "--"]


def test_run_task_succeeds_on_first_try() -> None:
    with patch("code_runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout='```python\n# /// script\n# dependencies = []\n# ///\nprint("ok")\n```',
                stderr="",
            ),
            MagicMock(returncode=0, stdout="ok", stderr=""),
        ]
        from code_runner import CodeRunner

        runner = CodeRunner()
        result = runner.run_task("print hello")
        assert result["success"] is True
        assert result["output"] == "ok"


def test_run_task_retries_on_failure() -> None:
    with patch("code_runner.subprocess.run") as mock_run:
        mock_run.side_effect = [
            MagicMock(
                returncode=0,
                stdout='```python\n# /// script\n# dependencies=[]\n# ///\nraise ValueError("oops")\n```',
                stderr="",
            ),
            MagicMock(returncode=1, stdout="", stderr="ValueError: oops"),
            MagicMock(
                returncode=0,
                stdout='```python\n# /// script\n# dependencies=[]\n# ///\nprint("fixed")\n```',
                stderr="",
            ),
            MagicMock(returncode=0, stdout="fixed", stderr=""),
        ]
        from code_runner import CodeRunner

        runner = CodeRunner(max_retries=2)
        result = runner.run_task("print hello")
        assert result["success"] is True


def test_extract_python_code_from_markdown() -> None:
    from code_runner import extract_code_block

    md = '```python\n# /// script\nprint("hi")\n```'
    code = extract_code_block(md)
    assert 'print("hi")' in code


def test_run_task_fails_after_max_retries() -> None:
    with patch("code_runner.subprocess.run") as mock_run:
        fail_gen = MagicMock(
            returncode=0, stdout='```python\nprint("x")\n```', stderr=""
        )
        fail_run = MagicMock(returncode=1, stdout="", stderr="error")
        mock_run.side_effect = [fail_gen, fail_run] * 5
        from code_runner import CodeRunner

        runner = CodeRunner(max_retries=2)
        result = runner.run_task("bad task")
        assert result["success"] is False
