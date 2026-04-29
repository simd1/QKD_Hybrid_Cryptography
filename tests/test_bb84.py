from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from cryptography.exceptions import InvalidTag

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aes_cipher import AESCipher
from bb84_pipeline import run_bb84
from e91_pipeline import run_e91
from hybrid_encrypt import compare_protocols, hybrid_decrypt, hybrid_encrypt, hybrid_encrypt_e91
from privacy_amplification import bits_to_bytes, privacy_amplification
from qber_sweep import sweep_qber
from quantum_utils import (
    E91Angles,
    measure_qubit_at_angle,
    measure_single_qubit_in_basis,
    prepare_bb84_state,
    prepare_bell_state,
)
from reconciliation import cascade_reconciliation, estimate_qber


class TestQiskitHelpers:
    def test_bb84_preparation_and_measurement(self) -> None:
        state = prepare_bb84_state(bit=1, basis=0)
        bit, _ = measure_single_qubit_in_basis(state, basis=0)
        assert bit == 1

    def test_bell_pair_has_perfect_z_correlation(self) -> None:
        state = prepare_bell_state()
        alice_bit, state = measure_qubit_at_angle(state, 0, 0.0)
        bob_bit, _ = measure_qubit_at_angle(state, 1, 0.0)
        assert alice_bit == bob_bit

    def test_e91_angles_are_expected(self) -> None:
        angles = E91Angles()
        assert angles.key == 0.0
        assert angles.a1 > angles.a0


class TestBB84Pipeline:
    def test_run_bb84_returns_32_byte_key(self) -> None:
        key = run_bb84(n_qubits=1024, eve_present=False, verbose=False)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_bb84_clean_channel_metrics(self) -> None:
        key, metrics = run_bb84(n_qubits=1024, eve_present=False, verbose=False, return_metrics=True)
        assert key is not None
        assert metrics["qber"] == 0.0
        assert 0.40 < metrics["sifted_ratio"] < 0.60

    def test_bb84_aborts_with_full_eavesdropping(self) -> None:
        result = run_bb84(n_qubits=1024, eve_present=True, intercept_rate=1.0, verbose=False)
        assert result is None


class TestE91Pipeline:
    def test_run_e91_returns_32_byte_key(self) -> None:
        key = run_e91(n_pairs=4096, eve_present=False, verbose=False)
        assert isinstance(key, bytes)
        assert len(key) == 32

    def test_e91_clean_channel_metrics(self) -> None:
        key, metrics = run_e91(n_pairs=4096, eve_present=False, verbose=False, return_metrics=True)
        assert key is not None
        assert metrics["qber"] == 0.0
        assert metrics["chsh_s"] > 2.2

    def test_e91_aborts_with_full_eavesdropping(self) -> None:
        result = run_e91(n_pairs=4096, eve_present=True, intercept_rate=1.0, verbose=False)
        assert result is None


class TestReconciliation:
    def test_estimate_qber_removes_sample(self) -> None:
        alice = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=np.uint8)
        bob = np.array([0, 1, 1, 1, 1, 0, 0, 0], dtype=np.uint8)
        qber, alice_remaining, bob_remaining = estimate_qber(alice, bob, sample_fraction=0.25)
        assert 0.0 <= qber <= 1.0
        assert len(alice_remaining) == 6
        assert len(bob_remaining) == 6

    def test_reconciliation_corrects_bob_key(self) -> None:
        alice = np.array([0, 1, 0, 1, 1, 0, 1, 0], dtype=np.uint8)
        bob = np.array([0, 1, 1, 1, 1, 0, 0, 0], dtype=np.uint8)
        corrected = cascade_reconciliation(alice, bob)
        assert np.array_equal(corrected, alice)


class TestAES:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        cipher = AESCipher(b"A" * 32)
        result = cipher.encrypt("Hello, quantum world!")
        decrypted = cipher.decrypt(result["ciphertext"], result["nonce"], result["aad"])
        assert decrypted == "Hello, quantum world!"

    def test_wrong_key_raises(self) -> None:
        cipher1 = AESCipher(b"A" * 32)
        cipher2 = AESCipher(b"B" * 32)
        result = cipher1.encrypt("secret")
        with pytest.raises(InvalidTag):
            cipher2.decrypt(result["ciphertext"], result["nonce"])

    def test_tampered_ciphertext_raises(self) -> None:
        cipher = AESCipher(b"C" * 32)
        result = cipher.encrypt("tamper me")
        tampered = bytearray(result["ciphertext"])
        tampered[0] ^= 0xFF
        with pytest.raises(InvalidTag):
            cipher.decrypt(bytes(tampered), result["nonce"])


class TestPrivacyAmplification:
    def test_bits_to_bytes(self) -> None:
        bits = np.array([1, 0, 1, 0, 0, 0, 0, 1], dtype=np.uint8)
        assert bits_to_bytes(bits) == b"\xA1"

    def test_output_length(self) -> None:
        bits = np.random.randint(0, 2, 512, dtype=np.uint8)
        key = privacy_amplification(bits, output_bits=256)
        assert len(key) == 32

    def test_insufficient_bits_raises(self) -> None:
        bits = np.random.randint(0, 2, 100, dtype=np.uint8)
        with pytest.raises(ValueError):
            privacy_amplification(bits, output_bits=256)


class TestHybridEncryption:
    def test_hybrid_bb84_encrypt_decrypt_roundtrip(self) -> None:
        message = "BB84 generated this AES key through Qiskit."
        result = hybrid_encrypt(message, n_qubits=1024, eve_present=False, verbose=False)
        assert result is not None
        assert hybrid_decrypt(**result, verbose=False) == message

    def test_hybrid_e91_encrypt_decrypt_roundtrip(self) -> None:
        message = "E91 generated this AES key through Qiskit."
        result = hybrid_encrypt_e91(message, n_pairs=4096, eve_present=False, verbose=False)
        assert result is not None
        assert hybrid_decrypt(**result, verbose=False) == message

    def test_compare_protocols_reports_both_flows(self) -> None:
        result = compare_protocols("protocol compare", bb84_qubits=1024, e91_pairs=4096)
        assert result["bb84_aes"]["success"] is True
        assert result["e91_aes"]["success"] is True
        assert result["comparison"]["shared_aes_mode"] == "AES-256-GCM"


class TestBenchmarkSweep:
    def test_sweep_qber_writes_both_protocols(self, tmp_path: Path) -> None:
        output = tmp_path / "qber_sweep.csv"
        sweep_qber(trials=1, output_path=output)
        content = output.read_text(encoding="utf-8")
        assert "BB84+AES" in content
        assert "E91+AES" in content
        assert "computational_load_ms_per_quantum_unit" in content
