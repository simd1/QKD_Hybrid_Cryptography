# Hybrid BB84 + AES-256-GCM Lab Report

## 1. Introduction

This project demonstrates how quantum key distribution can be paired with classical authenticated encryption. BB84 is used to derive a shared secret key, and AES-256-GCM is used to encrypt application data with confidentiality and integrity.

## 2. BB84 Protocol Walkthrough

Alice generates random bits and random bases, then sends encoded qubit states over a simulated quantum channel. Bob measures each received qubit using randomly selected bases. Alice and Bob publicly compare only their bases, discard mismatched positions, and keep the matching positions as the sifted key.

The implementation estimates QBER by sacrificing a sample of sifted bits and applies a conservative Wilson upper confidence bound before deciding whether to continue. Reconciliation now exchanges simulated block parities and binary-search parity information; it no longer gives Bob direct access to Alice's undisclosed bits. The simulator counts disclosed parity bits and aborts if reconciliation fails or its heuristic secret-bit budget is below 256 bits. SHAKE-256 remains an educational extractor placeholder, not a proven universal-hash privacy-amplification implementation.

## 3. Security Analysis

A full intercept-resend Eve creates an expected sifted-key QBER near 25%. This happens because Eve chooses the wrong measurement basis about half the time, and those wrong-basis measurements produce incorrect downstream bits about half the time.

Partial interception creates a lower QBER. That makes Eve harder to detect in a single run, but it also limits how much information Eve can learn. Privacy amplification is still required because reconciliation and any Eve observations may leak partial information about the sifted key.

## 4. AES-GCM Design Choices

AES-GCM is used instead of CBC because it provides authenticated encryption. The GCM tag detects wrong keys, ciphertext tampering, nonce/AAD mismatch, and accidental corruption. AAD binds public session metadata to the ciphertext without encrypting that metadata.

## 5. QBER vs Intercept Rate

Run:

```powershell
python src\qber_sweep.py
```

Record the generated values from `results/qber_sweep.csv`.

| Intercept Rate | Expected QBER |
| --- | --- |
| 0% | Approximately 0% |
| 50% | Approximately 12.5% |
| 100% | Approximately 25% |

## 6. Limitations

This is a software simulation, not a real photon-based QKD implementation. The QBER bound and asymptotic entropy estimate are conservative educational heuristics, not composable finite-key security proofs; the E91 estimate is not validated for E91 security. The public parity exchange is simulated in one process and the classical channel is not authenticated. Production QKD requires a protocol-specific security proof, authenticated classical communication, device and channel models, and physical quantum hardware.

## 7. Post-Quantum Comparison

QKD and NIST post-quantum cryptography solve related but different deployment problems. QKD needs specialized physical infrastructure, while schemes such as ML-KEM can be deployed over existing networks. In practice, PQC is easier to deploy broadly, while QKD is best suited to specialized high-security links where dedicated hardware is available.

