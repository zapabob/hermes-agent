# scripts/hypura/tests/test_shinka_adapter.py
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_adapter_initializes_with_ollama_env() -> None:
    with patch.dict(os.environ, {}, clear=False):
        from shinka_adapter import ShinkaAdapter

        _ = ShinkaAdapter()
        assert os.environ.get("OLLAMA_BASE_URL") == "http://127.0.0.1:11434"


@pytest.mark.asyncio
async def test_evolve_code_returns_result() -> None:
    with patch("shinka_adapter.AsyncLLMClient") as MockLLM, \
         patch("shinka_adapter._check_fitness", new=AsyncMock(return_value=True)):
        mock_client = MagicMock()
        mock_client.query = AsyncMock(
            return_value=MagicMock(content='```python\nprint("evolved")\n```')
        )
        MockLLM.return_value = mock_client
        from shinka_adapter import ShinkaAdapter

        adapter = ShinkaAdapter()
        result = await adapter.evolve_code("print('hello')", "print more", generations=1)
        assert result is not None


@pytest.mark.asyncio
async def test_evolve_code_improves_when_fitness_passes() -> None:
    responses = [
        MagicMock(content='```python\nprint("bad")\n```'),   # gen 0: fitness False
        MagicMock(content='```python\nprint("good")\n```'),  # gen 1: fitness True
    ]
    fitness_results = [False, True]
    call_count = {"n": 0}

    async def fake_fitness(_code: str) -> bool:
        i = call_count["n"]
        call_count["n"] += 1
        return fitness_results[i] if i < len(fitness_results) else False

    with patch("shinka_adapter.AsyncLLMClient") as MockLLM, \
         patch("shinka_adapter._check_fitness", side_effect=fake_fitness):
        mock_client = MagicMock()
        mock_client.query = AsyncMock(side_effect=responses)
        MockLLM.return_value = mock_client
        from shinka_adapter import ShinkaAdapter

        adapter = ShinkaAdapter()
        result = await adapter.evolve_code("print('seed')", "fix it", generations=2)
        assert result == 'print("good")'


@pytest.mark.asyncio
async def test_evolve_code_returns_seed_when_no_improvement() -> None:
    with patch("shinka_adapter.AsyncLLMClient") as MockLLM, \
         patch("shinka_adapter._check_fitness", new=AsyncMock(return_value=False)):
        mock_client = MagicMock()
        mock_client.query = AsyncMock(
            return_value=MagicMock(content='```python\nprint("x")\n```')
        )
        MockLLM.return_value = mock_client
        from shinka_adapter import ShinkaAdapter

        adapter = ShinkaAdapter()
        result = await adapter.evolve_code("print('seed')", "fix", generations=3)
        assert result == "print('seed')"


@pytest.mark.asyncio
async def test_evolve_skill_loops_each_generation() -> None:
    with patch("shinka_adapter.AsyncLLMClient") as MockLLM:
        mock_client = MagicMock()
        mock_client.query = AsyncMock(return_value=MagicMock(content="# improved skill"))
        MockLLM.return_value = mock_client
        from shinka_adapter import ShinkaAdapter

        adapter = ShinkaAdapter()
        result = await adapter.evolve_skill("# original", ["example1", "example2"], generations=3)
        assert mock_client.query.call_count == 3
        assert result == "# improved skill"


@pytest.mark.asyncio
async def test_evolve_code_stubs_when_client_none() -> None:
    with patch("shinka_adapter.AsyncLLMClient", None):
        from shinka_adapter import ShinkaAdapter

        adapter = ShinkaAdapter()
        result = await adapter.evolve_code("print('seed')", "fix", generations=5)
        assert result == "print('seed')"
