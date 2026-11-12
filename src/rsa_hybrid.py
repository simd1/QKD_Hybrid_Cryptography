"""Classical RSA key establishment followed by AES-256-GCM."""

from __future__ import annotations

import os
from time import perf_counter

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from aes_cipher import AESCipher


def rsa_aes_encrypt(plaintext: str, rsa_bits: int = 2048) -> dict[str, bytes | str]:
    """Generate an RSA keypair, wrap a random AES key, and encrypt a message.

    The private key is generated locally for this self-contained experiment;
    a deployed system would provision and authenticate recipient public keys.
    """
    if rsa_bits < 2048 or rsa_bits % 256:
        raise ValueError("rsa_bits must be at least 2048 and a multiple of 256")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=rsa_bits)
    public_key = private_key.public_key()
    aes_key = os.urandom(AESCipher.KEY_SIZE)
    wrapped_key = public_key.encrypt(
        aes_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None),
    )
    aad = b"rsa-aes-gcm-v1"
    encrypted = AESCipher(aes_key).encrypt(plaintext, aad=aad)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    return {
        "ciphertext": encrypted["ciphertext"], "nonce": encrypted["nonce"],
        "aad": aad, "wrapped_key": wrapped_key, "private_key_pem": private_pem,
        "rsa_bits": str(rsa_bits),
    }


def rsa_trial(plaintext: str, rsa_bits: int = 2048) -> dict[str, object]:
    """Benchmark key generation separately from wrap/AES work with a provisioned key."""
    start = perf_counter()
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=rsa_bits)
    keygen_sec = perf_counter() - start
    public_key = private_key.public_key()
    aes_key = os.urandom(AESCipher.KEY_SIZE)
    start = perf_counter()
    wrapped = public_key.encrypt(aes_key, padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    encrypted = AESCipher(aes_key).encrypt(plaintext, aad=b"rsa-aes-gcm-v1")
    operation_sec = perf_counter() - start
    private_pem = private_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    return {"keygen_sec": keygen_sec, "operation_sec": operation_sec, "wrapped_key": wrapped,
            "ciphertext": encrypted["ciphertext"], "nonce": encrypted["nonce"], "aad": encrypted["aad"],
            "private_key_pem": private_pem}


def rsa_aes_decrypt(ciphertext: bytes, nonce: bytes, aad: bytes,
                    wrapped_key: bytes, private_key_pem: bytes) -> str:
    """Unwrap the AES key with RSA-OAEP and decrypt/authenticate with GCM."""
    private_key = serialization.load_pem_private_key(private_key_pem, password=None)
    aes_key = private_key.decrypt(
        wrapped_key,
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None),
    )
    return AESCipher(aes_key).decrypt(ciphertext, nonce, aad)
