"""Contract coverage for the bundled Scrapling web provider."""

from __future__ import annotations

from pathlib import Path

import yaml

from plugins.web.scrapling import provider as scrapling_provider


def test_manifest_declares_current_plugin_api_and_runtime_dependencies() -> None:
    manifest_path = Path(__file__).resolve().parents[3] / "plugins" / "web" / "scrapling" / "plugin.yaml"
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 2
    assert manifest["api_version"] == 1
    assert set(manifest["python_dependencies"]) >= {
        "scrapling>=0.4,<1",
        "markdownify>=1,<2",
    }


def test_availability_requires_every_runtime_dependency(monkeypatch) -> None:
    provider = scrapling_provider.ScraplingWebProvider()
    monkeypatch.setattr(scrapling_provider, "_load_dependencies", lambda: (object, object))

    assert provider.is_available() is True

    def missing_dependency():
        raise ImportError("markdownify missing")

    monkeypatch.setattr(scrapling_provider, "_load_dependencies", missing_dependency)
    assert provider.is_available() is False


def test_extract_blocks_unsafe_url_before_loading_the_fetcher(monkeypatch) -> None:
    provider = scrapling_provider.ScraplingWebProvider()
    monkeypatch.setattr(scrapling_provider, "is_safe_url", lambda _: False)
    monkeypatch.setattr(
        scrapling_provider,
        "_load_dependencies",
        lambda: (_ for _ in ()).throw(AssertionError("fetcher must not load")),
    )

    result = provider.extract(["http://127.0.0.1/internal"])

    assert result == [
        {
            "url": "http://127.0.0.1/internal",
            "title": "",
            "content": "",
            "error": "URL blocked by safety policy: http://127.0.0.1/internal",
        }
    ]


def test_setup_schema_exposes_local_dependency_requirement() -> None:
    schema = scrapling_provider.ScraplingWebProvider().get_setup_schema()

    assert schema["env_vars"] == []
    assert "Scrapling" in schema["name"]
    assert "dependencies" in schema["tag"]
