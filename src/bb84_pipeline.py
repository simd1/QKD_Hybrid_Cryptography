"""Qiskit-based BB84 key distribution pipeline."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from privacy_amplification import privacy_amplification
from quantum_utils import make_rng, measure_single_qubit_in_basis, prepare_bb84_state
from reconciliation import estimate_qber, parity_reconciliation, wilson_upper_bound

QBER_THRESHOLD = 0.11


def run_bb84(
    n_qubits: int = 4096,
    eve_present: bool = False,
    intercept_rate: float = 1.0,
    key_bits: int = 256,
    verbose: bool = True,
    return_metrics: bool = False,
    seed: int | None = None,
    bit_flip_rate: float = 0.0,
    phase_flip_rate: float = 0.0,
    loss_rate: float = 0.0,
) -> bytes | None | tuple[bytes | None, dict[str, float | int | bool | str]]:
    """Run Qiskit-based BB84 and return a symmetric key, or None if QBER aborts."""
    if n_qubits <= 0:
        raise ValueError("n_qubits must be positive")
    if key_bits <= 0 or key_bits % 8 != 0:
        raise ValueError("key_bits must be a positive multiple of 8")
    if any(not 0.0 <= x <= 1.0 for x in (intercept_rate, bit_flip_rate, phase_flip_rate, loss_rate)):
        raise ValueError("attack/noise/loss rates must be between 0 and 1")

    if verbose:
        print("\n" + "=" * 60)
        print(f"Qiskit BB84 key distribution: {n_qubits} qubits")
        print(f"Eve present: {eve_present}", end="")
        if eve_present:
            print(f" (intercept rate: {intercept_rate:.0%})")
        else:
            print()
        print("=" * 60)

    rng = make_rng(seed)
    alice_bits = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    alice_bases = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    bob_bases = rng.integers(0, 2, size=n_qubits, dtype=np.uint8)
    bob_bits = np.zeros(n_qubits, dtype=np.uint8)
    eve_events = 0
    lost = 0

    if verbose:
        print(f"[1/7] Alice prepared {n_qubits} Qiskit quantum states.")

    for idx in range(n_qubits):
        state = prepare_bb84_state(int(alice_bits[idx]), int(alice_bases[idx]))

        if eve_present and rng.random() < intercept_rate:
            eve_basis = int(rng.integers(0, 2))
            eve_bit, _ = measure_single_qubit_in_basis(state, eve_basis)
            state = prepare_bb84_state(eve_bit, eve_basis)
            eve_events += 1

        # Independent Pauli channel noise, applied after Eve and before Bob.
        if rng.random() < bit_flip_rate:
            qc_noise = QuantumCircuit(1)
            qc_noise.x(0)
            state = state.evolve(qc_noise)
        if rng.random() < phase_flip_rate:
            qc_noise = QuantumCircuit(1)
            qc_noise.z(0)
            state = state.evolve(qc_noise)
        if rng.random() < loss_rate:
            lost += 1
            bob_bits[idx] = 255  # sentinel excluded from sifting
            continue

        bob_bit, _ = measure_single_qubit_in_basis(state, int(bob_bases[idx]))
        bob_bits[idx] = bob_bit

    if verbose:
        print("[2/7] States transmitted through the quantum simulation.")
        print("[3/7] Bob measured the incoming states with Qiskit basis rotations.")

    matching = (alice_bases == bob_bases) & (bob_bits != 255)
    alice_sifted = alice_bits[matching]
    bob_sifted = bob_bits[matching]
    sifted_len = len(alice_sifted)
    if verbose:
        print(f"[4/7] Sifted key length: {sifted_len} bits ({sifted_len / n_qubits:.1%}).")

    qber, alice_remaining, bob_remaining, test_bits = estimate_qber(alice_sifted, bob_sifted, seed=None if seed is None else seed + 1)
    sample_errors = int(round(qber * test_bits))
    qber_upper = wilson_upper_bound(sample_errors, test_bits)
    if verbose:
        print(f"[5/7] Estimated QBER: {qber:.2%}")

    metrics: dict[str, float | int | bool | str] = {
        "n_qubits": n_qubits,
        "sent_qubits": n_qubits,
        "detected_qubits": n_qubits - lost,
        "lost_qubits": lost,
        "bit_flip_rate": bit_flip_rate,
        "phase_flip_rate": phase_flip_rate,
        "loss_rate": loss_rate,
        "eve_present": eve_present,
        "intercept_rate": intercept_rate,
        "eve_intercepted_qubits": eve_events,
        "key_security_status": "educational_simulation_no_finite_key_proof",
        "sifted_bits": sifted_len,
        "sifted_ratio": sifted_len / n_qubits,
        "qber": qber,
        "qber_upper_99.9999": qber_upper,
        "qber_test_bits": test_bits,
        "aborted": qber_upper > QBER_THRESHOLD,
    }

    if qber_upper > QBER_THRESHOLD:
        if verbose:
            print(f"[ABORT] QBER upper bound {qber_upper:.2%} exceeds threshold {QBER_THRESHOLD:.2%}.")
            print("[ABORT] Eve or excessive channel noise detected.")
        return (None, metrics) if return_metrics else None

    bob_corrected, leakage_bits, reconciled = parity_reconciliation(
        alice_remaining, bob_remaining, seed=None if seed is None else seed + 2
    )
    post_error_rate = float(np.mean(alice_remaining != bob_corrected)) if len(alice_remaining) else 0.0
    metrics["reconciliation_leakage_bits"] = leakage_bits
    metrics["reconciliation_success"] = reconciled
    metrics["post_reconciliation_error_rate"] = post_error_rate
    if verbose:
        print(f"[6/7] Post-reconciliation error rate: {post_error_rate:.4%}")

    # Conservative BB84 asymptotic single-photon secret fraction used only as a
    # planning bound here; this is not a finite-key/composable proof.
    q = min(qber_upper, 0.5 - 1e-12)
    h2 = -q * np.log2(q) - (1 - q) * np.log2(1 - q) if q > 0 else 0.0
    estimated_secret_bits = max(0.0, len(bob_corrected) * (1.0 - 2.0 * h2) - leakage_bits)
    metrics["estimated_secret_bits"] = estimated_secret_bits
    metrics["security_model"] = "asymptotic_ideal_single_photon_heuristic_not_composable"
    if not reconciled or estimated_secret_bits < key_bits:
        metrics["aborted"] = True
        metrics["abort_reason"] = "reconciliation_failed_or_insufficient_secret_bits"
        if verbose:
            print(f"[ABORT] Reconciliation agreement={reconciled}; estimated secret bits={estimated_secret_bits:.1f}.")
        return (None, metrics) if return_metrics else None

    final_key = privacy_amplification(
        bob_corrected, output_bits=key_bits, seed=b"bb84-aes-v2", estimated_secret_bits=estimated_secret_bits
    )
    metrics["final_key_bits"] = key_bits
    if verbose:
        print("[7/7] Privacy amplification complete.")
        print(f"[SUCCESS] Final {key_bits}-bit key: {final_key.hex()[:32]}...")

    return (final_key, metrics) if return_metrics else final_key
