"""Hybrid BB84 key exchange plus AES-256-GCM encryption."""

from __future__ import annotations

from aes_cipher import AESCipher
from bb84_pipeline import run_bb84

SESSION_AAD = b"hybrid-bb84-aes-session-v1"


def hybrid_encrypt(
    plaintext: str,
    n_qubits: int = 4096,
    eve_present: bool = False,
    intercept_rate: float = 1.0,
    verbose: bool = True,
) -> dict[str, bytes | str] | None:
    """Generate a BB84-derived key and encrypt plaintext with AES-256-GCM."""
    key = run_bb84(
        n_qubits=n_qubits,
        eve_present=eve_present,
        intercept_rate=intercept_rate,
        key_bits=256,
        verbose=verbose,
    )

    if key is None:
        return None

    cipher = AESCipher(key)
    result = cipher.encrypt(plaintext, aad=SESSION_AAD)

    if verbose:
        preview = plaintext[:60] + ("..." if len(plaintext) > 60 else "")
        print(f"\n[AES] Plaintext : {preview}")
        print(f"[AES] Ciphertext: {result['ciphertext'].hex()[:64]}...")
        print(f"[AES] Nonce     : {result['nonce'].hex()}")

    return {
        "ciphertext": result["ciphertext"],
        "nonce": result["nonce"],
        "aad": result["aad"],
        "key_hex": key.hex(),
    }


def hybrid_decrypt(
    ciphertext: bytes,
    nonce: bytes,
    aad: bytes,
    key_hex: str,
    verbose: bool = True,
) -> str:
    """Decrypt a message encrypted by hybrid_encrypt."""
    cipher = AESCipher(bytes.fromhex(key_hex))
    plaintext = cipher.decrypt(ciphertext, nonce, aad)
    if verbose:
        print(f"\n[AES] Decrypted : {plaintext}")
    return plaintext

