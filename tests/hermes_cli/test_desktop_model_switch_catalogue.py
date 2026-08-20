"""Desktop picker catalogue proof for the live model-switch fast path."""

from unittest.mock import patch

from hermes_cli.model_switch import switch_model


def test_catalogue_validated_switch_skips_redundant_remote_model_probe():
    """A server-proven picker pair must not repeat the provider /models call."""
    with (
        patch("hermes_cli.model_switch.resolve_alias", return_value=None),
        patch("hermes_cli.models.validate_requested_model") as validate,
        patch("hermes_cli.model_switch.get_model_info", return_value=None),
        patch("hermes_cli.model_switch.get_model_capabilities", return_value=None),
        patch(
            "hermes_cli.runtime_provider.resolve_runtime_provider",
            return_value={
                "api_key": "test-key",
                "base_url": "https://provider.example/v1",
                "api_mode": "chat_completions",
            },
        ),
    ):
        result = switch_model(
            raw_input="anthropic/claude-sonnet-4.6",
            current_provider="openrouter",
            current_model="old-model",
            current_base_url="https://provider.example/v1",
            current_api_key="test-key",
            explicit_provider="openrouter",
            catalogue_validated=True,
        )

    assert result.success is True
    assert result.new_model == "anthropic/claude-sonnet-4.6"
    validate.assert_not_called()


def test_unproven_switch_retains_remote_model_validation():
    """Typed/non-picker model switches preserve the existing validation gate."""
    accepted = {
        "accepted": True,
        "persist": True,
        "recognized": True,
        "message": None,
    }
    with (
        patch("hermes_cli.model_switch.resolve_alias", return_value=None),
        patch(
            "hermes_cli.models.validate_requested_model",
            return_value=accepted,
        ) as validate,
        patch("hermes_cli.model_switch.get_model_info", return_value=None),
        patch("hermes_cli.model_switch.get_model_capabilities", return_value=None),
        patch(
            "hermes_cli.runtime_provider.resolve_runtime_provider",
            return_value={
                "api_key": "test-key",
                "base_url": "https://provider.example/v1",
                "api_mode": "chat_completions",
            },
        ),
    ):
        result = switch_model(
            raw_input="anthropic/claude-sonnet-4.6",
            current_provider="openrouter",
            current_model="old-model",
            current_base_url="https://provider.example/v1",
            current_api_key="test-key",
            explicit_provider="openrouter",
        )

    assert result.success is True
    validate.assert_called_once()
