#!/usr/bin/env python3
"""Vault-backed model-blind browser autofill tools.

Two model-facing tools, gated on the local vault having at least one item
(zero schema cost otherwise, same ``check_fn`` pattern as the Home Assistant
tools):

- ``browser_vault_list``  → opaque handles + metadata only, never values.
- ``browser_vault_fill``  → server-side fill of the CURRENT page's login
  form from a vault handle. The secret is resolved locally, the page origin
  must EXACTLY match the item's bound origin (scheme+host+port), fields are
  chosen by the ported login-control classifier, and the tool result reports
  only ``{filled_fields, kind, origin, success}`` — the secret value never
  appears in tool results, logs, or the session DB.

Ported design from Merit-Systems/OpenInstinct (MIT): opaque-handle vault
autofill (kernel-login-autofill.ts / fill_from_vault.ts).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Availability check
# ---------------------------------------------------------------------------

def _check_vault_available() -> bool:
    """Tools are only in the schema when the local vault has ≥1 item."""
    try:
        from agent.vault_store import get_vault_store

        return get_vault_store().has_items()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JS evaluation plumbing (server-side; results never carry secret values)
# ---------------------------------------------------------------------------

def _eval_js(task_id: str, expression: str) -> Dict[str, Any]:
    """Evaluate JS on the current page. Prefers the supervisor's persistent
    CDP WebSocket (keeps the expression out of any subprocess argv), falls
    back to the agent-browser CLI ``eval`` command."""
    try:
        from tools.browser_supervisor import SUPERVISOR_REGISTRY

        supervisor = SUPERVISOR_REGISTRY.get(task_id)
        if supervisor is not None:
            sup = supervisor.evaluate_runtime(expression)
            if sup.get("ok"):
                return {"success": True, "result": sup.get("result")}
            err = str(sup.get("error") or "")
            if "supervisor" not in err.lower():
                return {"success": False, "error": err}
    except ImportError:
        pass
    except Exception as exc:  # pragma: no cover — defensive
        logger.debug("vault fill: supervisor eval unavailable (%s)", exc)

    from tools.browser_tool import _last_session_key, _run_browser_command

    effective = _last_session_key(task_id)
    result = _run_browser_command(effective, "eval", [expression])
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "eval failed")}
    return {"success": True, "result": result.get("data", {}).get("result")}


def _parse_json_result(raw: Any) -> Any:
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return raw
    return raw


def _current_page_origin(task_id: str) -> Optional[str]:
    res = _eval_js(task_id, "window.location.href")
    if not res.get("success"):
        return None
    href = str(res.get("result") or "").strip().strip('"').strip("'")
    if not href or href == "about:blank":
        return None
    try:
        from agent.vault_store import normalize_origin

        return normalize_origin(href)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def browser_vault_list() -> str:
    """List vault items as opaque handles + metadata. Never returns values."""
    from agent.vault_store import get_vault_store

    items = []
    for meta in get_vault_store().list_items():
        items.append(
            {
                "handle": meta.id,
                "label": meta.label,
                "kind": meta.kind,
                "origin": meta.origin,
                # Phase 1: only login items are fillable.
                "available": meta.kind == "login",
            }
        )
    return json.dumps({"success": True, "items": items}, ensure_ascii=False)


def browser_vault_fill(handle: str, task_id: Optional[str] = None) -> str:
    """Fill the current page's login form from a vault handle.

    The secret is resolved server-side and injected via in-page JS; the
    result reports only counts and metadata.
    """
    from agent.vault_login_classifier import (
        LOGIN_CONTROL_INSPECTION_JS,
        ClassifiedLoginControl,
        LoginControl,
        build_fill_js,
        classify_login_control,
        select_login_fills,
    )
    from agent.vault_store import VaultError, get_vault_store, scrub_secret_from_text

    effective_task_id = task_id or "default"
    store = get_vault_store()

    meta = store.get_meta(handle)
    if meta is None:
        return json.dumps(
            {"success": False, "error": f"No vault item with handle {handle!r}. Use browser_vault_list."}
        )
    if meta.kind != "login":
        return json.dumps(
            {"success": False, "error": f"Vault item {handle!r} is kind={meta.kind!r}; only login items can be filled in Phase 1."}
        )

    # ── Origin binding: current page origin must EXACTLY match ──────────────
    page_origin = _current_page_origin(effective_task_id)
    if not page_origin:
        return json.dumps(
            {"success": False, "error": "Could not determine the current page origin. Navigate to the login page first."}
        )
    if page_origin != meta.origin:
        return json.dumps(
            {
                "success": False,
                "error": (
                    f"Refused: current page origin ({page_origin}) does not match "
                    f"the vault item's bound origin ({meta.origin}). Vault fills "
                    "only run on the exact origin the credential was saved for."
                ),
            }
        )

    # ── Inspect + classify page controls ────────────────────────────────────
    inspect = _eval_js(effective_task_id, LOGIN_CONTROL_INSPECTION_JS)
    if not inspect.get("success"):
        return json.dumps(
            {"success": False, "error": f"Could not inspect page inputs: {inspect.get('error', 'eval failed')}"}
        )
    raw_controls = _parse_json_result(inspect.get("result"))
    if isinstance(raw_controls, str):
        raw_controls = _parse_json_result(raw_controls)
    if not isinstance(raw_controls, list):
        return json.dumps({"success": False, "error": "Page input inspection returned no usable controls."})

    classified: list[ClassifiedLoginControl] = []
    for raw in raw_controls:
        if not isinstance(raw, dict):
            continue
        result = classify_login_control(LoginControl.from_dict(raw))
        if result is not None:
            classified.append(result)
    if not classified:
        return json.dumps({"success": False, "error": "No login form fields were found on the current page."})

    # ── Resolve secret and fill (secret never enters any logged string) ─────
    secret = store.resolve_secret(handle)
    identifier_token = {"email": "email", "phone": "tel", "username": "username"}.get(
        str(secret.get("identifier_type") or "username"), "username"
    )
    claims = {
        identifier_token: str(secret.get("identifier") or ""),
        # username is the generic identifier fallback token
        "username": str(secret.get("identifier") or ""),
        "current-password": str(secret.get("password") or ""),
    }
    fills = select_login_fills(classified, claims)
    if not fills:
        return json.dumps(
            {"success": False, "error": "No fillable login fields matched (is there a password field on this page?)."}
        )

    try:
        fill_result = _eval_js(effective_task_id, build_fill_js(fills))
    except Exception as exc:
        # Strip any secret material from exception text before surfacing.
        return json.dumps(
            {"success": False, "error": scrub_secret_from_text(str(exc), secret)}
        )
    if not fill_result.get("success"):
        err = scrub_secret_from_text(str(fill_result.get("error") or "fill failed"), secret)
        return json.dumps({"success": False, "error": err})

    parsed = _parse_json_result(fill_result.get("result"))
    if isinstance(parsed, str):
        parsed = _parse_json_result(parsed)
    filled = parsed.get("filled", 0) if isinstance(parsed, dict) else 0

    return json.dumps(
        {
            "success": bool(filled),
            "filled_fields": int(filled),
            "kind": meta.kind,
            "origin": meta.origin,
        }
    )


# ---------------------------------------------------------------------------
# Schemas + registration
# ---------------------------------------------------------------------------

BROWSER_VAULT_LIST_SCHEMA = {
    "name": "browser_vault_list",
    "description": (
        "List credentials stored in the local encrypted vault as opaque "
        "handles with metadata (label, kind, bound origin). Values are "
        "NEVER returned. Use a handle with browser_vault_fill to log into "
        "a site without ever seeing the password."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}

BROWSER_VAULT_FILL_SCHEMA = {
    "name": "browser_vault_fill",
    "description": (
        "Fill the CURRENT browser page's login form from a vault handle "
        "(see browser_vault_list). The secret is resolved and injected "
        "server-side; it never appears in the conversation. Refused unless "
        "the page origin exactly matches the credential's bound origin. "
        "Navigate to the site's login page first, then call this."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "handle": {
                "type": "string",
                "description": "Vault item handle from browser_vault_list (e.g. vault_ab12cd34ef56)",
            }
        },
        "required": ["handle"],
    },
}


def _handle_vault_list(args: Dict[str, Any], **kwargs) -> str:
    return browser_vault_list()


def _handle_vault_fill(args: Dict[str, Any], **kwargs) -> str:
    return browser_vault_fill(
        handle=str(args.get("handle") or ""), task_id=kwargs.get("task_id")
    )


from tools.registry import registry  # noqa: E402

registry.register(
    name="browser_vault_list",
    toolset="browser",
    schema=BROWSER_VAULT_LIST_SCHEMA,
    handler=_handle_vault_list,
    check_fn=_check_vault_available,
    emoji="🔐",
)

registry.register(
    name="browser_vault_fill",
    toolset="browser",
    schema=BROWSER_VAULT_FILL_SCHEMA,
    handler=_handle_vault_fill,
    check_fn=_check_vault_available,
    emoji="🔐",
)
