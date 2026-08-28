"""Tests for the vault-backed model-blind browser autofill feature.

Covers:
- VaultStore: encrypt/decrypt round-trip, file perms, metadata-only listing
- login-control classifier: scoring + new-password/one-time-code exclusion
- origin-binding refusal in browser_vault_fill
- tool gating: check_fn False when the vault is empty
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.vault_login_classifier import (  # noqa: E402
    ClassifiedLoginControl,
    LoginControl,
    build_fill_js,
    classify_login_control,
    select_login_fills,
)
from agent.vault_store import (  # noqa: E402
    VaultError,
    VaultStore,
    normalize_origin,
    scrub_secret_from_text,
)


@pytest.fixture()
def store(tmp_path):
    return VaultStore(base_dir=tmp_path / "vault")


def _add_login(store, origin="https://example.com", password="s3cret-pw"):
    return store.add_item(
        kind="login",
        label="Example login",
        origin=origin,
        secret={
            "identifier_type": "email",
            "identifier": "user@example.com",
            "password": password,
            "origin": origin,
        },
    )


# ---------------------------------------------------------------------------
# VaultStore
# ---------------------------------------------------------------------------

class TestVaultStore:
    def test_roundtrip_encrypt_decrypt(self, store):
        meta = _add_login(store)
        secret = store.resolve_secret(meta.id)
        assert secret["identifier"] == "user@example.com"
        assert secret["password"] == "s3cret-pw"

    def test_vault_file_is_encrypted_at_rest(self, store, tmp_path):
        _add_login(store)
        blob = (tmp_path / "vault" / "vault.json.enc").read_bytes()
        assert b"s3cret-pw" not in blob
        assert b"user@example.com" not in blob

    def test_file_permissions_0600(self, store, tmp_path):
        _add_login(store)
        for name in ("vault.json.enc", "vault.key"):
            mode = stat.S_IMODE(os.stat(tmp_path / "vault" / name).st_mode)
            assert mode == 0o600, f"{name} has mode {oct(mode)}"

    def test_listing_is_metadata_only(self, store):
        meta = _add_login(store)
        items = store.list_items()
        assert len(items) == 1
        dumped = json.dumps(items[0].to_dict())
        assert "s3cret-pw" not in dumped
        assert "password" not in dumped
        assert items[0].id == meta.id
        assert items[0].origin == "https://example.com"

    def test_remove_item(self, store):
        meta = _add_login(store)
        assert store.remove_item(meta.id) is True
        assert store.remove_item(meta.id) is False
        assert store.list_items() == []

    def test_login_requires_origin(self, store):
        with pytest.raises(VaultError):
            store.add_item(
                kind="login",
                label="x",
                secret={
                    "identifier_type": "email",
                    "identifier": "a@b.c",
                    "password": "p",
                },
            )

    def test_all_kinds_supported(self, store):
        store.add_item(kind="payment", label="Card", secret={"number": "4111"})
        store.add_item(kind="address", label="Home", secret={"street": "1 Main St"})
        kinds = {m.kind for m in store.list_items()}
        assert kinds == {"payment", "address"}

    def test_unknown_kind_rejected(self, store):
        with pytest.raises(VaultError):
            store.add_item(kind="totp", label="x", secret={})

    def test_has_items(self, store):
        assert store.has_items() is False
        _add_login(store)
        assert store.has_items() is True

    def test_normalize_origin(self):
        assert normalize_origin("https://Example.com:443/login?x=1") == "https://example.com"
        assert normalize_origin("http://localhost:8931/") == "http://localhost:8931"
        assert normalize_origin("http://site.test:80") == "http://site.test"
        with pytest.raises(VaultError):
            normalize_origin("example.com")

    def test_scrub_secret_from_text(self):
        secret = {"password": "hunter22x", "identifier": "me@x.io"}
        out = scrub_secret_from_text("boom hunter22x at me@x.io", secret)
        assert "hunter22x" not in out
        assert "me@x.io" not in out


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

def _ctrl(**kw):
    base = dict(autocomplete="", form_index=0, index=0, label="", name="", type="text")
    base.update(kw)
    return LoginControl(**base)


class TestClassifier:
    def test_autocomplete_exact_match_scores_100(self):
        for token in ("username", "email", "tel", "current-password"):
            res = classify_login_control(_ctrl(autocomplete=token))
            assert res is not None and res.score == 100 and res.token == token

    def test_new_password_autocomplete_excluded(self):
        assert classify_login_control(
            _ctrl(autocomplete="new-password", type="password")
        ) is None

    def test_one_time_code_excluded(self):
        assert classify_login_control(_ctrl(autocomplete="one-time-code")) is None

    def test_label_new_password_excluded(self):
        for label in ("New password", "Confirm Password", "create-password", "Repeat  password"):
            assert classify_login_control(_ctrl(type="password", label=label)) is None, label

    def test_password_type_scores_90(self):
        res = classify_login_control(_ctrl(type="password"))
        assert res.score == 90 and res.token == "current-password"

    def test_email_tel_types_score_85(self):
        assert classify_login_control(_ctrl(type="email")).score == 85
        res = classify_login_control(_ctrl(type="tel"))
        assert res.score == 85 and res.token == "tel"

    def test_label_heuristics(self):
        assert classify_login_control(_ctrl(label="E-mail address")).token == "email"
        assert classify_login_control(_ctrl(name="mobile_number")).token == "tel"
        res = classify_login_control(_ctrl(label="Username or account"))
        assert res.token == "username" and res.score == 70

    def test_unmatched_returns_none(self):
        assert classify_login_control(_ctrl(label="Search the docs")) is None

    def test_select_fills_same_form_only(self):
        user = ClassifiedLoginControl(_ctrl(index=0, form_index=0, autocomplete="username"), 100, "username")
        pw = ClassifiedLoginControl(_ctrl(index=1, form_index=0, type="password"), 90, "current-password")
        other = ClassifiedLoginControl(_ctrl(index=5, form_index=1, autocomplete="email"), 100, "email")
        fills = select_login_fills([user, pw, other], {"username": "u", "current-password": "p"})
        assert [(f["index"], f["token"]) for f in fills] == [(0, "username"), (1, "current-password")]

    def test_select_fills_requires_password_field(self):
        user = ClassifiedLoginControl(_ctrl(index=0, autocomplete="username"), 100, "username")
        assert select_login_fills([user], {"username": "u", "current-password": "p"}) == []

    def test_one_field_per_token(self):
        u1 = ClassifiedLoginControl(_ctrl(index=0, autocomplete="email"), 100, "email")
        u2 = ClassifiedLoginControl(_ctrl(index=1, autocomplete="email"), 100, "email")
        pw = ClassifiedLoginControl(_ctrl(index=2, type="password"), 90, "current-password")
        fills = select_login_fills([u1, u2, pw], {"email": "e", "current-password": "p"})
        identifier_fills = [f for f in fills if f["token"] == "email"]
        assert len(identifier_fills) == 1 and identifier_fills[0]["index"] == 0

    def test_build_fill_js_contains_events(self):
        js = build_fill_js([{"index": 0, "token": "email", "value": "x"}])
        assert "InputEvent" in js and '"change"' in js and "filled" in js


# ---------------------------------------------------------------------------
# Browser tool: origin binding + gating
# ---------------------------------------------------------------------------

class TestBrowserVaultTools:
    def test_check_fn_false_when_vault_empty(self, tmp_path):
        from tools import browser_vault_tool

        empty = VaultStore(base_dir=tmp_path / "empty-vault")
        with patch("agent.vault_store.get_vault_store", return_value=empty):
            assert browser_vault_tool._check_vault_available() is False

    def test_check_fn_true_with_items(self, store):
        from tools import browser_vault_tool

        _add_login(store)
        with patch("agent.vault_store.get_vault_store", return_value=store):
            assert browser_vault_tool._check_vault_available() is True

    def test_list_returns_handles_never_values(self, store):
        from tools import browser_vault_tool

        _add_login(store)
        with patch("agent.vault_store.get_vault_store", return_value=store):
            out = json.loads(browser_vault_tool.browser_vault_list())
        assert out["success"] is True
        assert out["items"][0]["handle"].startswith("vault_")
        assert "s3cret-pw" not in json.dumps(out)

    def test_fill_refused_on_origin_mismatch(self, store):
        from tools import browser_vault_tool

        meta = _add_login(store, origin="https://example.com")
        with patch("agent.vault_store.get_vault_store", return_value=store), \
             patch.object(browser_vault_tool, "_current_page_origin", return_value="https://evil.com"):
            out = json.loads(browser_vault_tool.browser_vault_fill(meta.id))
        assert out["success"] is False
        assert "Refused" in out["error"]
        assert "s3cret-pw" not in json.dumps(out)

    def test_fill_unknown_handle(self, store):
        from tools import browser_vault_tool

        with patch("agent.vault_store.get_vault_store", return_value=store):
            out = json.loads(browser_vault_tool.browser_vault_fill("vault_nope"))
        assert out["success"] is False

    def test_fill_success_returns_counts_only(self, store):
        from tools import browser_vault_tool

        meta = _add_login(store, origin="https://example.com")
        controls = [
            {"autocomplete": "email", "formIndex": 0, "index": 0, "label": "", "name": "email", "type": "email"},
            {"autocomplete": "current-password", "formIndex": 0, "index": 1, "label": "", "name": "pw", "type": "password"},
        ]

        def fake_eval(task_id, expression):
            if "location.href" in expression:
                return {"success": True, "result": "https://example.com/login"}
            if "querySelectorAll" in expression and "filled" not in expression:
                return {"success": True, "result": json.dumps(controls)}
            return {"success": True, "result": json.dumps({"filled": 2})}

        with patch("agent.vault_store.get_vault_store", return_value=store), \
             patch.object(browser_vault_tool, "_eval_js", side_effect=fake_eval):
            raw = browser_vault_tool.browser_vault_fill(meta.id)
        out = json.loads(raw)
        assert out == {
            "success": True,
            "filled_fields": 2,
            "kind": "login",
            "origin": "https://example.com",
        }
        assert "s3cret-pw" not in raw
        assert "user@example.com" not in raw

    def test_fill_rejects_non_login_kind(self, store):
        from tools import browser_vault_tool

        meta = store.add_item(kind="payment", label="Card", secret={"number": "4111"})
        with patch("agent.vault_store.get_vault_store", return_value=store):
            out = json.loads(browser_vault_tool.browser_vault_fill(meta.id))
        assert out["success"] is False
        assert "login" in out["error"]
