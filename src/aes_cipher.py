"""AES-256-GCM encryption wrapper."""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESCipher:
    """Encrypt and decrypt UTF-8 strings using AES-256-GCM."""

    NONCE_SIZE = 12
    KEY_SIZE = 32

    def __init__(self, key: bytes) -> None:
        if len(key) != self.KEY_SIZE:
            raise ValueError("AES-256-GCM requires a 32-byte key")
        self.key = key
        self._aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str, aad: bytes = b"") -> dict[str, bytes]:
        """Encrypt plaintext and return ciphertext, nonce, and AAD."""
        nonce = os.urandom(self.NONCE_SIZE)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)
        return {"ciphertext": ciphertext, "nonce": nonce, "aad": aad}

    def decrypt(self, ciphertext: bytes, nonce: bytes, aad: bytes = b"") -> str:
        """Decrypt ciphertext and verify the GCM authentication tag."""
        if len(nonce) != self.NONCE_SIZE:
            raise ValueError("AES-GCM nonce must be 12 bytes")
        plaintext = self._aesgcm.decrypt(nonce, ciphertext, aad)
        return plaintext.decode("utf-8")

