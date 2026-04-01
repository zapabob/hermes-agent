import json
import pytest
from unittest.mock import patch, MagicMock
from tools.shinka_evolve_tool import shinka_run_batch
from tools.ai_scientist_tool import ai_scientist_research
from model_tools import handle_function_call

def test_shinka_evolve_tool_registration():
    from tools.registry import registry
    assert "shinka_run" in registry.get_all_tool_names()

def test_ai_scientist_tool_registration():
    from tools.registry import registry
    assert "ai_scientist_research" in registry.get_all_tool_names()

@patch("subprocess.run")
def test_shinka_run_dispatch(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Batch completed", stderr="")
    
    result_json = shinka_run_batch(task_dir="examples/test_task", num_generations=1, task_id="test_session")
    result = json.loads(result_json)
    
    assert result["success"] is True
    assert "results_dir" in result
    mock_run.assert_called_once()
    # Check if CUDA_VISIBLE_DEVICES was set (default True)
    assert mock_run.call_args.kwargs["env"]["CUDA_VISIBLE_DEVICES"] == "0"

@patch("subprocess.run")
def test_ai_scientist_research_dispatch(mock_run):
    mock_run.return_value = MagicMock(returncode=0, stdout="Research completed", stderr="")
    
    result_json = ai_scientist_research(experiment="test_exp", num_ideas=1, task_id="test_session")
    result = json.loads(result_json)
    
    assert result["success"] is True
    mock_run.assert_called_once()
    assert "launch_scientist.py" in mock_run.call_args.args[0]
