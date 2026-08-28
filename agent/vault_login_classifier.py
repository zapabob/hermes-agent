"""Login-form control classifier for vault autofill.

Python port (~170 LOC) of Merit-Systems/OpenInstinct's
``lib/manager/server/kernel-login-autofill.ts`` (MIT). Classifies visible
input controls on a page into login-autofill tokens and selects at most one
field per token, anchored to the form containing the best password field.

Scoring:
- exact autocomplete-token match ................ 100
- type=password (not new/confirm/create/repeat) .. 90
- type=email / type=tel .......................... 85
- label/name regex heuristics .................. 70-75
Hard exclusions: autocomplete ``new-password`` / ``one-time-code``, and
label/name text matching ``(new|confirm|create|repeat)\\s*password``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

LOGIN_AUTOFILL_TOKENS = ("username", "email", "tel", "current-password")

_EXCLUDED_AUTOCOMPLETE = {"new-password", "one-time-code"}

_RE_EXCLUDED_PASSWORD = re.compile(r"\b(?:new|confirm|create|repeat)\s*password\b")
_RE_EMAIL = re.compile(r"\b(?:e[\s-]?mail|email address)\b")
_RE_TEL = re.compile(r"\b(?:phone|telephone|mobile)\b")
_RE_USERNAME = re.compile(
    r"\b(?:user\s*name|username|login|account|member|membership|mileageplus)\b"
)


def _normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).lower()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


@dataclass(frozen=True)
class LoginControl:
    """Descriptor of a visible input control, as inspected in the page."""

    autocomplete: str
    form_index: Optional[int]
    index: int
    label: str
    name: str
    type: str

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "LoginControl":
        form_index = raw.get("formIndex", raw.get("form_index"))
        return cls(
            autocomplete=str(raw.get("autocomplete") or ""),
            form_index=int(form_index) if form_index is not None else None,
            index=int(raw.get("index") or 0),
            label=str(raw.get("label") or ""),
            name=str(raw.get("name") or ""),
            type=str(raw.get("type") or ""),
        )


@dataclass(frozen=True)
class ClassifiedLoginControl:
    control: LoginControl
    score: int
    token: str


def classify_login_control(control: LoginControl) -> Optional[ClassifiedLoginControl]:
    """Classify one control, or return None if it is not a login fill target."""
    autocomplete_tokens = [
        t for t in control.autocomplete.lower().split() if t
    ]
    if any(t in _EXCLUDED_AUTOCOMPLETE for t in autocomplete_tokens):
        return None

    for token in LOGIN_AUTOFILL_TOKENS:
        if token in autocomplete_tokens:
            return ClassifiedLoginControl(control, 100, token)

    searchable = _normalize_text(
        " ".join(part for part in (control.name, control.label) if part)
    )
    if _RE_EXCLUDED_PASSWORD.search(searchable):
        return None
    if control.type == "password":
        return ClassifiedLoginControl(control, 90, "current-password")
    if control.type == "email":
        return ClassifiedLoginControl(control, 85, "email")
    if control.type == "tel":
        return ClassifiedLoginControl(control, 85, "tel")
    if _RE_EMAIL.search(searchable):
        return ClassifiedLoginControl(control, 75, "email")
    if _RE_TEL.search(searchable):
        return ClassifiedLoginControl(control, 75, "tel")
    if _RE_USERNAME.search(searchable):
        return ClassifiedLoginControl(control, 70, "username")
    return None


def select_login_fills(
    classified: List[ClassifiedLoginControl],
    claims: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Select fills anchored to the form containing the best password field.

    ``claims`` maps autofill tokens (``username``/``email``/``tel``/
    ``current-password``) to values. Only fields sharing the best password
    field's form are considered; at most one field per token is filled.
    Returns ``[{"index": int, "token": str, "value": str}, ...]``.
    """
    passwords = [c for c in classified if c.token == "current-password"]
    if not passwords:
        return []
    best_password = sorted(
        passwords, key=lambda c: (-c.score, c.control.index)
    )[0]

    same_form = sorted(
        (c for c in classified if c.control.form_index == best_password.control.form_index),
        key=lambda c: (-c.score, c.control.index),
    )

    selected: List[Dict[str, Any]] = []
    identifier = next(
        (
            c
            for c in same_form
            if c.token != "current-password"
            and (c.token in claims or "username" in claims)
        ),
        None,
    )
    if identifier is not None:
        value = claims.get(identifier.token, claims.get("username"))
        if value is not None:
            selected.append(
                {"index": identifier.control.index, "token": identifier.token, "value": value}
            )

    if "current-password" in claims:
        selected.append(
            {
                "index": best_password.control.index,
                "token": "current-password",
                "value": claims["current-password"],
            }
        )
    return selected


# JS expression evaluated in the page to inspect candidate input controls.
# Ported from OpenInstinct's nativeLoginControlInspectionExpression.
LOGIN_CONTROL_INSPECTION_JS = """(() => {
  const elements = Array.from(document.querySelectorAll("input"));
  const forms = Array.from(document.forms);
  const out = elements.flatMap((element, index) => {
    if (element.disabled || element.readOnly) return [];
    if (["hidden", "submit", "button", "reset", "file", "image", "checkbox", "radio"].includes(element.type)) return [];
    const style = getComputedStyle(element);
    if (style.display === "none" || style.visibility === "hidden" || element.getClientRects().length === 0) return [];
    const labels = element.labels ? Array.from(element.labels, (l) => l.textContent || "") : [];
    const ariaText = (element.getAttribute("aria-labelledby") || "")
      .split(/\\s+/).filter(Boolean)
      .map((id) => { const n = document.getElementById(id); return n ? (n.textContent || "") : ""; })
      .join(" ");
    const resolvedFormIndex = element.form ? forms.indexOf(element.form) : -1;
    return [{
      autocomplete: element.autocomplete || "",
      formIndex: resolvedFormIndex >= 0 ? resolvedFormIndex : null,
      index,
      label: [
        ...labels,
        element.getAttribute("aria-label") || "",
        ariaText,
        element.getAttribute("placeholder") || "",
        element.getAttribute("title") || "",
      ].join(" "),
      name: [element.name, element.id].join(" "),
      type: element.type || "",
    }];
  });
  return JSON.stringify(out);
})()"""


def build_fill_js(fills: List[Dict[str, Any]]) -> str:
    """Build a JS expression that fills the selected inputs and reports
    only a count. The returned expression never echoes the values back."""
    payload = json.dumps(
        [{"index": f["index"], "value": f["value"]} for f in fills]
    )
    return (
        "(() => {\n"
        f"  const fills = {payload};\n"
        "  const elements = Array.from(document.querySelectorAll(\"input\"));\n"
        "  let filled = 0;\n"
        "  for (const f of fills) {\n"
        "    const el = elements[f.index];\n"
        "    if (!el) continue;\n"
        "    try {\n"
        "      el.dataset.vaultSecret = \"true\";\n"
        "      el.focus();\n"
        "      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, \"value\");\n"
        "      if (setter && setter.set) { setter.set.call(el, f.value); } else { el.value = f.value; }\n"
        "      el.dispatchEvent(new InputEvent(\"input\", { bubbles: true, inputType: \"insertText\" }));\n"
        "      el.dispatchEvent(new Event(\"change\", { bubbles: true }));\n"
        "      if (el.value.length > 0) filled += 1;\n"
        "    } catch (e) { /* skip */ }\n"
        "  }\n"
        "  return JSON.stringify({ filled });\n"
        "})()"
    )
