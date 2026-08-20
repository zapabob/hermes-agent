"""SSRF and credential-boundary coverage for GitHub Skills Hub fetches."""

from unittest.mock import MagicMock, patch

import httpx


def _resp(status: int, *, location: str | None = None, json_data=None):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    response.headers = {"location": location} if location else {}
    response.json.return_value = json_data or {}
    return response


class TestGuardedHttpGetAuthStrip:
    def test_strips_authorization_on_cross_origin_redirect(self):
        from tools.skills_hub import _guarded_http_get

        seen = []

        def fake_ssrf_get(url, *, timeout=20, headers=None, params=None):
            seen.append({
                "url": url,
                "headers": dict(headers or {}),
                "params": params,
            })
            if len(seen) == 1:
                return _resp(302, location="https://cdn.example.com/blob")
            return _resp(200, json_data={"ok": True})

        with patch("tools.skills_hub.is_safe_url", return_value=True), patch(
            "tools.skills_hub.check_website_access", return_value=None
        ), patch(
            "tools.skills_hub._ssrf_safe_http_get", side_effect=fake_ssrf_get
        ):
            response = _guarded_http_get(
                "https://api.github.com/repos/org/repo",
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "Authorization": "token ghp_secret",
                },
                params={"recursive": "1"},
                timeout=15,
            )

        assert response is not None
        assert seen[0]["headers"]["Authorization"] == "token ghp_secret"
        assert "Authorization" not in seen[1]["headers"]
        assert seen[1]["headers"]["Accept"] == "application/vnd.github.v3+json"
        assert seen[0]["params"] == {"recursive": "1"}
        assert seen[1]["params"] is None

    def test_strips_authorization_on_https_to_http_downgrade(self):
        from tools.skills_hub import _guarded_http_get

        seen = []

        def fake_ssrf_get(url, *, timeout=20, headers=None, params=None):
            seen.append(dict(headers or {}))
            if len(seen) == 1:
                return _resp(302, location="http://api.github.com/blob")
            return _resp(200)

        with patch("tools.skills_hub.is_safe_url", return_value=True), patch(
            "tools.skills_hub.check_website_access", return_value=None
        ), patch(
            "tools.skills_hub._ssrf_safe_http_get", side_effect=fake_ssrf_get
        ):
            response = _guarded_http_get(
                "https://api.github.com/repos/org/repo",
                headers={"Authorization": "token ghp_secret"},
            )

        assert response is not None
        assert "Authorization" in seen[0]
        assert "Authorization" not in seen[1]

    def test_same_origin_redirect_preserves_authorization(self):
        from tools.skills_hub import _guarded_http_get

        seen = []

        def fake_ssrf_get(url, *, timeout=20, headers=None, params=None):
            seen.append(dict(headers or {}))
            if len(seen) == 1:
                return _resp(302, location="/repos/org/repo/contents")
            return _resp(200)

        with patch("tools.skills_hub.is_safe_url", return_value=True), patch(
            "tools.skills_hub.check_website_access", return_value=None
        ), patch(
            "tools.skills_hub._ssrf_safe_http_get", side_effect=fake_ssrf_get
        ):
            response = _guarded_http_get(
                "https://api.github.com/repos/org/repo",
                headers={"Authorization": "token ghp_secret"},
            )

        assert response is not None
        assert seen == [
            {"Authorization": "token ghp_secret"},
            {"Authorization": "token ghp_secret"},
        ]

    def test_blocks_private_redirect_target(self):
        from tools.skills_hub import _guarded_http_get

        redirect = _resp(
            302,
            location="http://169.254.169.254/latest/meta-data/",
        )

        with patch(
            "tools.skills_hub.is_safe_url",
            side_effect=lambda url: "169.254.169.254" not in url,
        ), patch(
            "tools.skills_hub.check_website_access", return_value=None
        ), patch(
            "tools.skills_hub._ssrf_safe_http_get", return_value=redirect
        ) as safe_get:
            response = _guarded_http_get(
                "https://api.github.com/repos/org/repo",
                headers={"Authorization": "token ghp_secret"},
            )

        assert response is None
        safe_get.assert_called_once()


class TestGetRepoTreeUsesGuardedFetch:
    def test_get_repo_tree_does_not_call_raw_httpx_get(self):
        from tools.skills_hub import GitHubAuth, GitHubSource

        source = GitHubSource(auth=GitHubAuth())

        def fake_guarded(url, **_kwargs):
            if "git/trees" in url:
                return _resp(
                    200,
                    json_data={
                        "sha": "abc",
                        "truncated": False,
                        "tree": [{"path": "SKILL.md", "type": "blob"}],
                    },
                )
            return _resp(200, json_data={"default_branch": "main"})

        with patch(
            "tools.skills_hub._guarded_http_get", side_effect=fake_guarded
        ) as guarded_get, patch("tools.skills_hub.httpx.get") as raw_get:
            result = source._get_repo_tree("org/repo")

        assert result is not None
        assert guarded_get.call_count == 2
        raw_get.assert_not_called()
