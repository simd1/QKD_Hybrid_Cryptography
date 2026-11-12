"""Run BB84+AES and E91+AES demos, then refresh the comparison CSV."""

from __future__ import annotations

from hybrid_encrypt import hybrid_decrypt, hybrid_encrypt, hybrid_encrypt_e91
from qber_sweep import sweep_qber
from rsa_hybrid import rsa_aes_decrypt, rsa_aes_encrypt

MESSAGE = (
    "This message was encrypted using a key generated through "
    "BB84 quantum key distribution and AES-256-GCM."
)


def run_demo() -> None:
    """Run BB84/E91 demo scenarios and update the benchmark CSV."""
    print("\n" + "=" * 60)
    print("SCENARIO 0: RSA-OAEP + AES-GCM classical baseline")
    print("=" * 60)
    rsa_result = rsa_aes_encrypt(MESSAGE)
    assert rsa_aes_decrypt(**{k: rsa_result[k] for k in ("ciphertext", "nonce", "aad", "wrapped_key", "private_key_pem")}) == MESSAGE
    print("[PASS] RSA-wrapped AES key roundtrip succeeded.")

    print("\n" + "=" * 60)
    print("SCENARIO 1: Clean BB84 + AES channel")
    print("=" * 60)
    result = hybrid_encrypt(MESSAGE, n_qubits=1024, eve_present=False)
    if result is None:
        raise RuntimeError("clean channel unexpectedly aborted")
    decrypted = hybrid_decrypt(**result)
    assert decrypted == MESSAGE
    print("[PASS] Encrypt/decrypt succeeded.")

    print("\n" + "=" * 60)
    print("SCENARIO 2: BB84 with Eve intercepting 100% of qubits")
    print("=" * 60)
    result = hybrid_encrypt(MESSAGE, n_qubits=1024, eve_present=True, intercept_rate=1.0)
    if result is None:
        print("[PASS] Session aborted because QBER detected Eve.")
    else:
        print("[WARN] Session did not abort; rerun because this is probabilistic.")

    print("\n" + "=" * 60)
    print("SCENARIO 3: Clean E91 + AES channel")
    print("=" * 60)
    result = hybrid_encrypt_e91(MESSAGE, n_pairs=4096, eve_present=False)
    if result is None:
        raise RuntimeError("clean E91 channel unexpectedly aborted")
    decrypted = hybrid_decrypt(**result)
    assert decrypted == MESSAGE
    print("[PASS] E91-derived AES roundtrip succeeded.")

    print("\n" + "=" * 60)
    print("SCENARIO 4: E91 with Eve intercepting 100% of Bob's qubits")
    print("=" * 60)
    result = hybrid_encrypt_e91(MESSAGE, n_pairs=4096, eve_present=True, intercept_rate=1.0)
    if result is None:
        print("[PASS] E91 session aborted due to poor key/Bell statistics.")
    else:
        print("[WARN] Session did not abort; rerun because this is probabilistic.")

    print("\n" + "=" * 60)
    print("CSV UPDATE: BB84 + AES vs E91 + AES benchmark export")
    print("=" * 60)
    output_path = sweep_qber(trials=3)
    print(f"[PASS] Updated comparative benchmark CSV: {output_path}")


if __name__ == "__main__":
    run_demo()
