import pytest

from hermes_cli.auth import PROVIDER_REGISTRY, resolve_api_key_provider_credentials
from hermes_cli.models import CANONICAL_PROVIDERS, _PROVIDER_MODELS
from hermes_cli.provider_catalog import provider_catalog_by_slug
from providers import get_provider_profile


UPSTREAM_PROVIDER_SLUGS = {
    "actual",
    "ai-gateway",
    "alibaba",
    "alibaba-cn",
    "alibaba-coding-plan",
    "alibaba-coding-plan-cn",
    "alibaba-token-plan",
    "alibaba-token-plan-cn",
    "anthropic",
    "arcee",
    "azure-foundry",
    "bedrock",
    "commandcode",
    "commandcode-anthropic",
    "copilot",
    "copilot-acp",
    "custom",
    "deepinfra",
    "deepseek",
    "fireworks",
    "gemini",
    "gmi",
    "huggingface",
    "kilocode",
    "kimi-coding",
    "kimi-coding-cn",
    "lmstudio",
    "meta-ai",
    "minimax",
    "minimax-cn",
    "minimax-oauth",
    "moa",
    "nebius-token-factory",
    "nous",
    "novita",
    "nvidia",
    "ollama-cloud",
    "openai-api",
    "openai-codex",
    "opencode-free",
    "opencode-go",
    "opencode-zen",
    "openrouter",
    "qwen-oauth",
    "router",
    "stepfun",
    "tencent-tokenhub",
    "tencent-tokenplan",
    "upstage",
    "vertex",
    "xai",
    "xai-oauth",
    "xiaomi",
    "zai",
}


@pytest.mark.parametrize(
    "slug,base_url,api_mode,env_vars",
    [
        (
            "alibaba-cn",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "chat_completions",
            ("DASHSCOPE_API_KEY", "DASHSCOPE_CN_BASE_URL"),
        ),
        (
            "alibaba-coding-plan-cn",
            "https://coding.dashscope.aliyuncs.com/v1",
            "chat_completions",
            (
                "ALIBABA_CODING_PLAN_API_KEY",
                "DASHSCOPE_API_KEY",
                "ALIBABA_CODING_PLAN_CN_BASE_URL",
            ),
        ),
        (
            "alibaba-token-plan",
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            "chat_completions",
            ("ALIBABA_TOKEN_PLAN_API_KEY", "ALIBABA_TOKEN_PLAN_BASE_URL"),
        ),
        (
            "alibaba-token-plan-cn",
            "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
            "chat_completions",
            ("ALIBABA_TOKEN_PLAN_API_KEY", "ALIBABA_TOKEN_PLAN_CN_BASE_URL"),
        ),
        (
            "nebius-token-factory",
            "https://api.tokenfactory.nebius.com/v1",
            "chat_completions",
            ("NEBIUS_API_KEY", "NEBIUS_TOKEN_FACTORY_API_KEY", "NEBIUS_BASE_URL"),
        ),
        (
            "router",
            "https://api.router.com/v1",
            "codex_responses",
            ("RAMP_ROUTER_API_KEY", "ROUTER_API_KEY", "RAMP_ROUTER_BASE_URL"),
        ),
    ],
)
def test_current_upstream_profiles_are_routable(slug, base_url, api_mode, env_vars):
    profile = get_provider_profile(slug)

    assert profile is not None
    assert profile.base_url == base_url
    assert profile.api_mode == api_mode
    assert profile.env_vars == env_vars
    assert slug in PROVIDER_REGISTRY


def test_current_upstream_provider_universe_is_preserved():
    actual = {entry.slug for entry in CANONICAL_PROVIDERS}

    assert UPSTREAM_PROVIDER_SLUGS <= actual


def test_current_upstream_changed_model_catalogs_are_aligned():
    assert _PROVIDER_MODELS["alibaba"] == [
        "qwen3.8-max",
        "qwen3.7-max",
        "qwen3.7-plus",
        "qwen3.6-plus",
        "qwen3.6-flash",
        "kimi-k2.5",
        "qwen3.5-plus",
        "qwen3-coder-plus",
        "qwen3-coder-next",
        "glm-5.2",
        "glm-5",
        "glm-4.7",
        "deepseek-v4-pro",
        "deepseek-v4-flash-0731",
        "MiniMax-M2.5",
    ]
    assert _PROVIDER_MODELS["tencent-tokenhub"] == [
        "hy4-preview",
        "hy3",
        "hy3-preview",
    ]
    assert _PROVIDER_MODELS["tencent-tokenplan"] == [
        "hy4-preview",
        "hy3",
        "hy3-preview",
    ]
    assert "glm-5.3-flash" in _PROVIDER_MODELS["zai"]
    assert "glm-5.3-flash" in _PROVIDER_MODELS["opencode-zen"]
    assert "glm-5.3-flash" in _PROVIDER_MODELS["opencode-go"]
    assert _PROVIDER_MODELS["opencode-free"] == [
        "deepseek-v4-flash-free",
        "hy3-free",
        "mimo-v2.5-free",
        "laguna-s-2.1-free",
        "nemotron-3-ultra-free",
        "nemotron-3.5-lightning-free",
        "muse-spark-1.2-contributor-free",
    ]
    assert "qwen/qwen3.8-flash" in _PROVIDER_MODELS["nous"]
    assert "z-ai/glm-5.3-flash" in _PROVIDER_MODELS["nous"]
    assert "tencent/hy4-preview" in _PROVIDER_MODELS["nous"]


def test_xai_uses_current_upstream_responses_transport():
    assert get_provider_profile("xai").api_mode == "codex_responses"


def test_nvidia_and_opencode_additions_keep_api_key_and_free_access(monkeypatch):
    monkeypatch.delenv("NOUS_API_KEY", raising=False)
    monkeypatch.setenv("NVIDIA_API_KEY", "test-nvidia-key")
    monkeypatch.setenv("OPENCODE_API_KEY", "test-opencode-key")

    nvidia = resolve_api_key_provider_credentials("nvidia")
    zen = resolve_api_key_provider_credentials("opencode-zen")
    go = resolve_api_key_provider_credentials("opencode-go")
    catalog = provider_catalog_by_slug()

    assert nvidia["api_key"] == "test-nvidia-key"
    assert zen["api_key"] == "test-opencode-key"
    assert go["api_key"] == "test-opencode-key"
    assert catalog["opencode-free"].keyless is True
    assert catalog["opencode-free"].api_key_env_vars == ()
    assert PROVIDER_REGISTRY["nous"].auth_type == "oauth_device_code"
