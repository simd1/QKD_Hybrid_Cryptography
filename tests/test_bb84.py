from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from cryptography.exceptions import InvalidTag

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aes_cipher import AESCipher
from alice import Alice
from bb84_pipeline import run_bb84
from bob import Bob
from channel import QuantumChannel
from hybrid_encrypt import hybrid_decrypt, hybrid_encrypt
from privacy_amplification import bits_to_bytes, privacy_amplification
from reconciliation import cascade_reconciliation, estimate_qber


class TestAlice:
    def test_generates_correct_shape(self) -> None:
        alice = Alice(500)
        alice.generate_bits_and_bases()
        assert alice.bits.shape == (500,)
        assert alice.bases.shape == (500,)

    def test_bits_and_bases_are_binary(self) -> None:
        alice = Alice(500)
        alice.generate_bits_and_bases()
        assert set(alice.bits).issubset({0, 1})
        assert set(alice.bases).issubset({0, 1})

    def test_qubit_encoding(self) -> None:
        alice = Alice(1000)
        alice.generate_bits_and_bases()
        qubits = alice.encode_qubits()
        assert qubits.shape == (1000,)
        assert set(qubits).issubset({0, 1, 2, 3})


class TestBB84Clean:
    def test_sifted_keys_match_on_clean_channel(self) -> None:
        n = 2000
        alice = Alice(n)
        alice.generate_bits_and_bases()
        qubits = alice.encode_qubits()

        channel = QuantumChannel(eve_present=False)
        received = channel.transmit(qubits)

        bob = Bob(n)
        bob.choose_bases()
        bob.measure(received)

        alice_sifted = alice.sift_key(bob.get_bases())
        bob_sifted = bob.sift_key(alice.get_bases())

        assert len(alice_sifted) == len(bob_sifted)
        assert np.mean(alice_sifted != bob_sifted) == 0.0

    def test_sifted_length_approximately_half(self) -> None:
        n = 4000
        alice = Alice(n)
        alice.generate_bits_and_bases()
        qubits = alice.encode_qubits()

        bob = Bob(n)
        bob.choose_bases()
        bob.measure(QuantumChannel().transmit(qubits))

        ratio = len(alice.sift_key(bob.get_bases())) / n
        assert 0.40 < ratio < 0.60

    def test_run_bb84_returns_32_byte_key(self) -> None:
        key = run_bb84(n_qubits=4096, eve_present=False, verbose=False)
        assert isinstance(key, bytes)
        assert len(key) == 32


class TestEavesdropping:
    def test_eve_raises_qber(self) -> None:
        n = 4000
        alice = Alice(n)
        alice.generate_bits_and_bases()
        qubits = alice.encode_qubits()

        channel = QuantumChannel(eve_present=True, intercept_rate=1.0)
        received = channel.transmit(qubits)

        bob = Bob(n)
        bob.choose_bases()
        bob.measure(received)

        alice_sifted = alice.sift_key(bob.get_bases())
        bob_sifted = bob.sift_key(alice.get_bases())

        qber, _, _ = estimate_qber(alice_sifted, bob_sifted, sample_fraction=0.2)
        assert qber > 0.11

    def test_pipeline_aborts_when_eve_intercepts_everything(self) -> None:
        result = run_bb84(n_qubits=4096, eve_present=True, intercept_rate=1.0, verbose=False)
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
    def test_hybrid_encrypt_decrypt_roundtrip(self) -> None:
        message = "BB84 generated this AES key."
        result = hybrid_encrypt(message, n_qubits=4096, eve_present=False, verbose=False)
        assert result is not None
        assert hybrid_decrypt(**result, verbose=False) == message

