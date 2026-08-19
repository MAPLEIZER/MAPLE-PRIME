from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt


class VaultDecryptionError(ValueError):
    pass


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    if len(passphrase) < 12:
        raise ValueError("vault passphrase must be at least 12 characters")
    return Scrypt(salt=salt, length=32, n=2**14, r=8, p=1).derive(passphrase.encode("utf-8"))


def encrypt_json(payload: dict[str, Any], passphrase: str) -> str:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(passphrase, salt)
    plaintext = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, b"kdr-vault-v1")
    envelope = {
        "version": 1,
        "kdf": "scrypt-n16384-r8-p1",
        "salt": base64.urlsafe_b64encode(salt).decode("ascii"),
        "nonce": base64.urlsafe_b64encode(nonce).decode("ascii"),
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode("ascii"),
    }
    return json.dumps(envelope, sort_keys=True, separators=(",", ":"))


def decrypt_json(envelope_json: str, passphrase: str) -> dict[str, Any]:
    try:
        envelope = json.loads(envelope_json)
        if envelope.get("version") != 1:
            raise VaultDecryptionError("unsupported vault envelope version")
        salt = base64.urlsafe_b64decode(envelope["salt"])
        nonce = base64.urlsafe_b64decode(envelope["nonce"])
        ciphertext = base64.urlsafe_b64decode(envelope["ciphertext"])
        key = _derive_key(passphrase, salt)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, b"kdr-vault-v1")
        decoded = json.loads(plaintext)
        if not isinstance(decoded, dict):
            raise VaultDecryptionError("vault payload must be a JSON object")
        return decoded
    except VaultDecryptionError:
        raise
    except (InvalidTag, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise VaultDecryptionError("vault authentication or decoding failed") from exc
