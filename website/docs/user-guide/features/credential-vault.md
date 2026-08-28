# Credential Vault (Model-Blind Autofill)

Store site logins in a locally encrypted vault and let the agent log into
websites **without ever seeing the password**. The model only receives
opaque handles and metadata; secret values are resolved server-side and
injected directly into the page.

## How it works

1. You add a credential with `hermes vault add` (interactive; the password
   is read with a hidden prompt and never echoed or passed on the command
   line).
2. The item is encrypted at rest under `~/.hermes/vault/` (Fernet key +
   vault file, both `0600`) and bound to an exact **origin**
   (`scheme://host[:port]`).
3. When the vault has at least one item, two browser tools appear in the
   agent's toolset (they add zero schema cost otherwise):
   - `browser_vault_list` — opaque handles + metadata only.
   - `browser_vault_fill(handle)` — fills the current page's login form.
4. On fill, Hermes checks that the **current page origin exactly matches**
   the credential's bound origin, classifies visible login fields (ported
   from OpenInstinct's login-control classifier — autocomplete tokens win,
   `new-password` / `one-time-code` fields are hard-excluded), injects the
   values via in-page JavaScript, and returns only
   `{filled_fields, kind, origin, success}`.

The secret never appears in tool results, logs, or the session database.

## CLI

```bash
# Add a login (interactive wizard; password is hidden)
hermes vault add

# List items — metadata only, values are never shown
hermes vault list

# Remove an item by handle
hermes vault rm vault_ab12cd34ef56
```

Item kinds: `login`, `payment`, and `address` are all stored; Phase 1
browser fill supports `login` items only.

## Example agent flow

```
User: log into example.com and check my dashboard
Agent: browser_navigate("https://example.com/login")
Agent: browser_vault_list()          → [{handle: "vault_…", label: "Example", origin: "https://example.com"}]
Agent: browser_vault_fill("vault_…") → {"success": true, "filled_fields": 2, "kind": "login", "origin": "https://example.com"}
Agent: browser_click(<submit>)
```

## Security properties

- **Model-blind:** the agent never sees identifier or password values —
  only handles, labels, and origins.
- **Origin-bound:** fills are refused unless the page origin exactly
  matches (scheme + host + port) the origin the credential was saved for,
  so a phishing page on another host cannot receive the fill.
- **No signup/OTP capture:** fields marked `autocomplete="new-password"`
  or `one-time-code`, and fields labeled *new/confirm/create/repeat
  password*, are never filled.
- **Encrypted at rest:** vault file and key are created `0600` in your
  Hermes home; nothing is sent to any server.

## Notes

- No configuration is needed; the tools activate automatically once the
  vault has an item.
- The fill targets the form containing the best password field and fills
  at most one field per autofill token.
- Design ported from Merit-Systems/OpenInstinct's opaque-handle vault
  autofill (MIT).
