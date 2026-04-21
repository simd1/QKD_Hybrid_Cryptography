"""Run three BB84 + AES demo scenarios."""

from __future__ import annotations

from hybrid_encrypt import hybrid_decrypt, hybrid_encrypt

MESSAGE = (
    "This message was encrypted using a key generated through "
    "BB84 quantum key distribution and AES-256-GCM."
)


def run_demo() -> None:
    """Run clean, full interception, and partial interception scenarios."""
    print("\n" + "=" * 60)
    print("SCENARIO 1: Clean channel")
    print("=" * 60)
    result = hybrid_encrypt(MESSAGE, n_qubits=4096, eve_present=False)
    if result is None:
        raise RuntimeError("clean channel unexpectedly aborted")
    decrypted = hybrid_decrypt(**result)
    assert decrypted == MESSAGE
    print("[PASS] Encrypt/decrypt succeeded.")

    print("\n" + "=" * 60)
    print("SCENARIO 2: Eve intercepts 100% of qubits")
    print("=" * 60)
    result = hybrid_encrypt(MESSAGE, n_qubits=4096, eve_present=True, intercept_rate=1.0)
    if result is None:
        print("[PASS] Session aborted because QBER detected Eve.")
    else:
        print("[WARN] Session did not abort; rerun because this is probabilistic.")

    print("\n" + "=" * 60)
    print("SCENARIO 3: Eve intercepts 30% of qubits")
    print("=" * 60)
    result = hybrid_encrypt(MESSAGE, n_qubits=4096, eve_present=True, intercept_rate=0.3)
    if result is None:
        print("[PASS] Session aborted at partial interception.")
    else:
        print("[NOTE] Low interception can fall below the abort threshold in some runs.")


if __name__ == "__main__":
    run_demo()

