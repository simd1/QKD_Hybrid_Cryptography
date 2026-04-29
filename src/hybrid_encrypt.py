"""Hybrid BB84/E91 key exchange plus AES-256-GCM encryption."""

from __future__ import annotations

from aes_cipher import AESCipher
from bb84_pipeline import run_bb84
from e91_pipeline import run_e91

# An AAD is Additional Authenticated Data
SESSION_AAD_BB84 = b"hybrid-bb84-aes-session-v2-qiskit"
SESSION_AAD_E91 = b"hybrid-e91-aes-session-v1-qiskit"

# The string "hybrid-bb84-aes-session-v2-qiskit" uniquely identifies 
# a session that was built from a BB84‑derived key and the 
# v2 version of the hybrid protocol 
# (the E91 counterpart uses a different constant).

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
    result = cipher.encrypt(plaintext, aad=SESSION_AAD_BB84)

    if verbose:
        preview = plaintext[:60] + ("..." if len(plaintext) > 60 else "")
        print(f"\n[BB84+AES] Plaintext : {preview}")
        print(f"[BB84+AES] Ciphertext: {result['ciphertext'].hex()[:64]}...")
        print(f"[BB84+AES] Nonce     : {result['nonce'].hex()}")

    return {
        "ciphertext": result["ciphertext"],
        "nonce": result["nonce"],
        "aad": result["aad"],
        "key_hex": key.hex(),
    }


def hybrid_encrypt_e91(
    plaintext: str,
    n_pairs: int = 4096,
    eve_present: bool = False,
    intercept_rate: float = 1.0,
    verbose: bool = True,
) -> dict[str, bytes | str] | None:
    """Generate an E91-derived key and encrypt plaintext with AES-256-GCM."""
    key = run_e91(
        n_pairs=n_pairs,
        eve_present=eve_present,
        intercept_rate=intercept_rate,
        key_bits=256,
        verbose=verbose,
    )

    if key is None:
        return None

    cipher = AESCipher(key)
    result = cipher.encrypt(plaintext, aad=SESSION_AAD_E91)

    if verbose:
        preview = plaintext[:60] + ("..." if len(plaintext) > 60 else "")
        print(f"\n[E91+AES] Plaintext : {preview}")
        print(f"[E91+AES] Ciphertext: {result['ciphertext'].hex()[:64]}...")
        print(f"[E91+AES] Nonce     : {result['nonce'].hex()}")

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


def compare_protocols(
    message: str,
    bb84_qubits: int = 1024,
    e91_pairs: int = 4096,
) -> dict[str, dict[str, object]]:
    """Run both hybrid paths once and return a concise comparison bundle."""
    bb84_result = hybrid_encrypt(message, n_qubits=bb84_qubits, verbose=False)
    e91_result = hybrid_encrypt_e91(message, n_pairs=e91_pairs, verbose=False)
    return {
        "bb84_aes": {
            "success": bb84_result is not None,
            "key_bits": 256 if bb84_result else 0,
            "aad": SESSION_AAD_BB84,
        },
        "e91_aes": {
            "success": e91_result is not None,
            "key_bits": 256 if e91_result else 0,
            "aad": SESSION_AAD_E91,
        },
        "comparison": {
            "bb84_uses_prepare_and_measure": True,
            "e91_uses_entanglement": True,
            "shared_aes_mode": "AES-256-GCM",
        },
    }
