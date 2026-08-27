# Encrypted Quarantine

Quarantine is rooted at `<HERMES_HOME>/security/quarantine`. Blob names are opaque UUIDs ending in `.blob`; original names and paths exist only in the SQLite metadata store.

Each file is encrypted with AES-256-GCM using a fresh 96-bit nonce and SHA-256 as authenticated associated data. On Windows, the 256-bit vault key is protected with the current-user Windows Data Protection API. The security directory, key file, staging files, and blobs receive a protected discretionary ACL containing only the current owner and LocalSystem with full control.

Quarantine writes an encrypted staging blob, decrypts and authenticates it, verifies the plaintext SHA-256, atomically promotes the blob, records metadata, and only then removes the original. A failure leaves the original in place and records a scan error; automatic permanent deletion is not used.

## Restore

Restore decrypts into a restricted temporary file beside the requested destination, verifies the stored SHA-256, and scans the current bytes with current definitions without using the cache. An existing destination is never overwritten. A current malicious verdict refuses restoration unless the operator supplied the explicit `--force` option or confirmed the equivalent Desktop action.

Restore and permanent quarantine deletion create durable detection events. Allowlisting is not implied by restoration.

## Inspection and deletion

```powershell
hermes security quarantine list --json
hermes security quarantine inspect ITEM_ID --json
hermes security quarantine restore ITEM_ID --json
hermes security quarantine restore ITEM_ID --force --json
hermes security quarantine delete ITEM_ID --json
```

Deletion removes only the encrypted blob and marks the metadata row deleted. The audit event remains.
