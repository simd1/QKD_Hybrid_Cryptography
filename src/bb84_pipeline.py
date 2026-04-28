"""Qiskit-based BB84 key distribution pipeline."""

from __future__ import annotations

import numpy as np

from privacy_amplification import privacy_amplification
from quantum_utils import make_rng, measure_single_qubit_in_basis, prepare_bb84_state
from reconciliation import cascade_reconciliation, estimate_qber

QBER_THRESHOLD = 0.11


def run_bb84(
    n_qubits: int = 4096,
    eve_present: bool = False,
    intercept_rate: float = 1.0,
    key_bits: int = 256,
    verbose: bool = True,
    return_metrics: bool = False,
) -> bytes | None | tuple[bytes | None, dict[str, float | int | bool | str]]:
    """Run Qiskit-based BB84 and return a symmetric key, or None if QBER aborts."""
    if n_qubits <= 0:
        raise ValueError("n_qubits must be positive")
    if key_bits <= 0 or key_bits % 8 != 0:
        raise ValueError("key_bits must be a positive multiple of 8")
    if not 0.0 <= intercept_rate <= 1.0:
        raise ValueError("intercept_rate must be between 0.0 and 1.0")

    if verbose:
        print("\n" + "=" * 60)
        print(f"Qiskit BB84 key distribution: {n_qubits} qubits")
        print(f"Eve present: {eve_present}", end="")
        if eve_present:
            print(f" (intercept rate: {intercept_rate:.0%})")
        else:
            print()
        print("=" * 60)

    rng = make_rng()
    alice_bits = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    alice_bases = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    bob_bases = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    bob_bits = np.zeros(n_qubits, dtype=np.uint8)
    eve_events = 0

    if verbose:
        print(f"[1/7] Alice prepared {n_qubits} Qiskit quantum states.")

    for idx in range(n_qubits):
        state = prepare_bb84_state(int(alice_bits[idx]), int(alice_bases[idx]))

        if eve_present and rng.random() < intercept_rate:
            eve_basis = int(rng.integers(0, 2))
            eve_bit, _ = measure_single_qubit_in_basis(state, eve_basis)
            state = prepare_bb84_state(eve_bit, eve_basis)
            eve_events += 1

        bob_bit, _ = measure_single_qubit_in_basis(state, int(bob_bases[idx]))
        bob_bits[idx] = bob_bit

    if verbose:
        print("[2/7] States transmitted through the quantum simulation.")
        print("[3/7] Bob measured the incoming states with Qiskit basis rotations.")

    matching = alice_bases == bob_bases
    alice_sifted = alice_bits[matching]
    bob_sifted = bob_bits[matching]
    sifted_len = len(alice_sifted)
    if verbose:
        print(f"[4/7] Sifted key length: {sifted_len} bits ({sifted_len / n_qubits:.1%}).")

    qber, alice_remaining, bob_remaining = estimate_qber(alice_sifted, bob_sifted)
    if verbose:
        print(f"[5/7] Estimated QBER: {qber:.2%}")

    metrics: dict[str, float | int | bool | str] = {
        "n_qubits": n_qubits,
        "eve_present": eve_present,
        "intercept_rate": intercept_rate,
        "eve_intercepted_qubits": eve_events,
        "sifted_bits": sifted_len,
        "sifted_ratio": sifted_len / n_qubits,
        "qber": qber,
        "aborted": qber > QBER_THRESHOLD,
    }

    if qber > QBER_THRESHOLD:
        if verbose:
            print(f"[ABORT] QBER {qber:.2%} exceeds threshold {QBER_THRESHOLD:.2%}.")
            print("[ABORT] Eve or excessive channel noise detected.")
        return (None, metrics) if return_metrics else None

    if len(alice_remaining) < key_bits:
        metrics["aborted"] = True
        metrics["abort_reason"] = "insufficient_key_bits"
        if verbose:
            print(f"[ABORT] Only {len(alice_remaining)} remaining bits for a {key_bits}-bit key.")
        return (None, metrics) if return_metrics else None

    bob_corrected = cascade_reconciliation(alice_remaining, bob_remaining)
    post_error_rate = float(np.mean(alice_remaining != bob_corrected)) if len(alice_remaining) else 0.0
    metrics["post_reconciliation_error_rate"] = post_error_rate
    if verbose:
        print(f"[6/7] Post-reconciliation error rate: {post_error_rate:.4%}")

    final_key = privacy_amplification(bob_corrected, output_bits=key_bits)
    metrics["final_key_bits"] = key_bits
    if verbose:
        print("[7/7] Privacy amplification complete.")
        print(f"[SUCCESS] Final {key_bits}-bit key: {final_key.hex()[:32]}...")

    return (final_key, metrics) if return_metrics else final_key
