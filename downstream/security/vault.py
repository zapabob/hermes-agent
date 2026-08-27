from __future__ import annotations

import hashlib
import importlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Callable

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .models import ScanResult, Verdict
from .store import SecurityStore, utc_now


_MAGIC = b"HERMESQ1"


def _restrict_windows_acl(path: Path, directory: bool = False) -> None:
    if sys.platform != "win32":
        os.chmod(path, 0o700 if directory else 0o600)
        return
    ntsecuritycon = importlib.import_module("ntsecuritycon")
    win32api = importlib.import_module("win32api")
    win32security = importlib.import_module("win32security")

    owner_name = win32api.GetUserNameEx(2)
    owner_sid, _, _ = win32security.LookupAccountName(None, owner_name)
    system_sid = win32security.CreateWellKnownSid(win32security.WinLocalSystemSid, None)
    acl = win32security.ACL()
    inheritance = 0
    if directory:
        inheritance = win32security.CONTAINER_INHERIT_ACE | win32security.OBJECT_INHERIT_ACE
    acl.AddAccessAllowedAceEx(win32security.ACL_REVISION, inheritance, ntsecuritycon.FILE_ALL_ACCESS, owner_sid)
    acl.AddAccessAllowedAceEx(win32security.ACL_REVISION, inheritance, ntsecuritycon.FILE_ALL_ACCESS, system_sid)
    descriptor = win32security.SECURITY_DESCRIPTOR()
    descriptor.SetSecurityDescriptorOwner(owner_sid, False)
    descriptor.SetSecurityDescriptorDacl(1, acl, 0)
    flags = win32security.OWNER_SECURITY_INFORMATION | win32security.DACL_SECURITY_INFORMATION
    flags |= win32security.PROTECTED_DACL_SECURITY_INFORMATION
    win32security.SetFileSecurity(str(path), flags, descriptor)


class VaultKey:
    def __init__(self, root: Path) -> None:
        self.path = root / "vault-key.dpapi"

    def load_or_create(self) -> bytes:
        if self.path.exists():
            protected = self.path.read_bytes()
            if sys.platform == "win32":
                win32crypt = importlib.import_module("win32crypt")

                return bytes(win32crypt.CryptUnprotectData(protected, None, None, None, 0)[1])
            return protected
        key = AESGCM.generate_key(bit_length=256)
        protected = key
        if sys.platform == "win32":
            win32crypt = importlib.import_module("win32crypt")

            protected = bytes(win32crypt.CryptProtectData(key, "Hermes Security Vault", None, None, None, 0))
        self.path.write_bytes(protected)
        _restrict_windows_acl(self.path)
        return key


class QuarantineVault:
    def __init__(self, store: SecurityStore) -> None:
        self.store = store
        self.root = store.root / "quarantine"
        self.root.mkdir(parents=True, exist_ok=True)
        _restrict_windows_acl(self.root, directory=True)
        self.key = VaultKey(store.root).load_or_create()

    def _encrypt(self, source: Path, destination: Path, sha256: str) -> None:
        nonce = os.urandom(12)
        ciphertext = AESGCM(self.key).encrypt(nonce, source.read_bytes(), sha256.encode("ascii"))
        destination.write_bytes(_MAGIC + nonce + ciphertext)
        _restrict_windows_acl(destination)

    def _decrypt(self, source: Path, sha256: str) -> bytes:
        payload = source.read_bytes()
        if not payload.startswith(_MAGIC) or len(payload) < len(_MAGIC) + 28:
            raise ValueError("invalid quarantine blob")
        offset = len(_MAGIC)
        return AESGCM(self.key).decrypt(payload[offset:offset + 12], payload[offset + 12:], sha256.encode("ascii"))

    def quarantine(self, source: Path, result: ScanResult) -> str:
        item_id = str(uuid.uuid4())
        blob_name = f"{item_id}.blob"
        staging = self.root / f".{item_id}.staging"
        destination = self.root / blob_name
        before = source.stat()
        self._encrypt(source, staging, result.sha256)
        plaintext = self._decrypt(staging, result.sha256)
        if hashlib.sha256(plaintext).hexdigest() != result.sha256:
            staging.unlink(missing_ok=True)
            raise ValueError("quarantine verification failed")
        after = source.stat()
        identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
        if identity_before != identity_after or after.st_size != result.size:
            staging.unlink(missing_ok=True)
            raise RuntimeError("file changed during quarantine")
        os.replace(staging, destination)
        findings = json.dumps([item.to_dict() for item in result.findings], ensure_ascii=False, sort_keys=True)
        versions = json.dumps(result.engine_versions, ensure_ascii=False, sort_keys=True)
        with self.store.connection() as con:
            con.execute(
                "INSERT INTO quarantine_items(id,blob_name,original_path,original_filename,sha256,size,verdict,"
                "findings_json,engine_versions_json,original_atime_ns,original_mtime_ns,original_ctime_ns,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    blob_name,
                    str(source),
                    source.name,
                    result.sha256,
                    result.size,
                    result.verdict.value,
                    findings,
                    versions,
                    before.st_atime_ns,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                    utc_now(),
                ),
            )
        source.unlink()
        self.store.event("quarantine", item_id, result.verdict.value, "quarantined", {"sha256": result.sha256, "original_path": str(source)})
        return item_id

    def inspect(self, item_id: str) -> dict[str, object]:
        with self.store.connection() as con:
            row = con.execute("SELECT * FROM quarantine_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise KeyError(item_id)
        item = dict(row)
        item["findings"] = json.loads(item.pop("findings_json"))
        item["blob_present"] = (self.root / str(item["blob_name"])).is_file()
        return item

    def restore(self, item_id: str, scan: Callable[[Path], ScanResult], destination: Path | None = None, force: bool = False) -> Path:
        item = self.inspect(item_id)
        if item["deleted_at"]:
            raise ValueError("quarantine item was deleted")
        target = destination or Path(str(item["original_path"]))
        if target.exists():
            raise FileExistsError(str(target))
        plaintext = self._decrypt(self.root / str(item["blob_name"]), str(item["sha256"]))
        if hashlib.sha256(plaintext).hexdigest() != item["sha256"]:
            raise ValueError("quarantine blob hash mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        handle, temp_name = tempfile.mkstemp(prefix=".hermes-restore-", dir=target.parent)
        os.close(handle)
        temp_path = Path(temp_name)
        try:
            temp_path.write_bytes(plaintext)
            _restrict_windows_acl(temp_path)
            current = scan(temp_path)
            if current.verdict == Verdict.MALICIOUS and not force:
                raise PermissionError("current signatures still classify this item as malicious")
            os.replace(temp_path, target)
            atime_ns = item.get("original_atime_ns")
            mtime_ns = item.get("original_mtime_ns")
            if isinstance(atime_ns, int) and isinstance(mtime_ns, int):
                os.utime(target, ns=(atime_ns, mtime_ns))
        finally:
            temp_path.unlink(missing_ok=True)
        with self.store.connection() as con:
            con.execute(
                "UPDATE quarantine_items SET restored_at=?,restore_state='restored' WHERE id=?",
                (utc_now(), item_id),
            )
        self.store.event("restore", item_id, current.verdict.value, "restored", {"destination": str(target), "forced": force})
        return target

    def delete(self, item_id: str) -> None:
        item = self.inspect(item_id)
        blob = self.root / str(item["blob_name"])
        blob.unlink(missing_ok=True)
        with self.store.connection() as con:
            con.execute(
                "UPDATE quarantine_items SET deleted_at=?,restore_state='deleted' WHERE id=?",
                (utc_now(), item_id),
            )
        self.store.event("quarantine_delete", item_id, str(item["verdict"]), "deleted", {"sha256": item["sha256"]})
