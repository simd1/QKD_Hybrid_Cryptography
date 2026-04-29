"""Generate comparative benchmark measurements for BB84+AES and E91+AES."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from bb84_pipeline import QBER_THRESHOLD as BB84_QBER_THRESHOLD, run_bb84
from e91_pipeline import CHSH_THRESHOLD as E91_CHSH_THRESHOLD, QBER_THRESHOLD as E91_QBER_THRESHOLD, run_e91


@dataclass(frozen=True)
class ProtocolConfig:
    """Configuration for one benchmarked protocol."""

    name: str
    quantum_units: int
    quantum_unit_label: str
    key_bits: int


BB84_CONFIG = ProtocolConfig(
    name="BB84+AES",
    quantum_units=2048,
    quantum_unit_label="qubits",
    key_bits=256,
)

E91_CONFIG = ProtocolConfig(
    name="E91+AES",
    quantum_units=4096,
    quantum_unit_label="entangled_pairs",
    key_bits=256,
)


def _benchmark_bb84(rate: float, config: ProtocolConfig) -> tuple[bytes | None, dict[str, float | int | bool | str]]:
    """Run one BB84 benchmark trial."""
    return run_bb84(
        n_qubits=config.quantum_units,
        eve_present=rate > 0.0,
        intercept_rate=rate,
        key_bits=config.key_bits,
        verbose=False,
        return_metrics=True,
    )


def _benchmark_e91(rate: float, config: ProtocolConfig) -> tuple[bytes | None, dict[str, float | int | bool | str]]:
    """Run one E91 benchmark trial."""
    return run_e91(
        n_pairs=config.quantum_units,
        eve_present=rate > 0.0,
        intercept_rate=rate,
        key_bits=config.key_bits,
        verbose=False,
        return_metrics=True,
    )


def _write_protocol_rows(
    writer: csv.DictWriter,
    protocol: ProtocolConfig,
    rates: list[float],
    trials: int,
) -> None:
    """Run one protocol over all intercept rates and write aggregate rows."""
    runner = _benchmark_bb84 if protocol.name == "BB84+AES" else _benchmark_e91

    for rate in rates:
        runtimes: list[float] = []
        qbers: list[float] = []
        sifted_ratios: list[float] = []
        bell_scores: list[float] = []
        post_errors: list[float] = []
        eve_intercepts: list[float] = []
        aborted = 0
        successful_trials = 0

        for _ in range(trials):
            start = perf_counter()
            key, metrics = runner(rate, protocol)
            elapsed = perf_counter() - start

            runtimes.append(elapsed)
            qbers.append(float(metrics["qber"]))
            sifted_ratios.append(float(metrics["sifted_ratio"]))
            bell_scores.append(float(metrics.get("chsh_s", 0.0)))
            post_errors.append(float(metrics.get("post_reconciliation_error_rate", 0.0)))
            eve_intercepts.append(
                float(
                    metrics.get(
                        "eve_intercepted_qubits",
                        metrics.get("eve_intercepted_pairs", 0),
                    )
                )
            )

            if bool(metrics["aborted"]):
                aborted += 1
            if key is not None:
                successful_trials += 1

        avg_runtime = sum(runtimes) / len(runtimes)
        avg_qber = sum(qbers) / len(qbers)
        avg_sifted_ratio = sum(sifted_ratios) / len(sifted_ratios)
        avg_bell_score = sum(bell_scores) / len(bell_scores)
        avg_post_error = sum(post_errors) / len(post_errors)
        avg_eve_intercepts = sum(eve_intercepts) / len(eve_intercepts)
        success_rate = successful_trials / trials
        efficiency_key_bits_per_quantum_unit = (protocol.key_bits * success_rate) / protocol.quantum_units
        efficiency_key_bits_per_second = (protocol.key_bits * success_rate) / avg_runtime if avg_runtime > 0 else 0.0
        computational_load_ms_per_quantum_unit = (avg_runtime * 1000.0) / protocol.quantum_units

        writer.writerow(
            {
                "protocol": protocol.name,
                "intercept_rate": f"{rate:.1f}",
                "trials": trials,
                "quantum_units_per_trial": protocol.quantum_units,
                "quantum_unit_label": protocol.quantum_unit_label,
                "avg_runtime_sec": f"{avg_runtime:.6f}",
                "computational_load_ms_per_quantum_unit": f"{computational_load_ms_per_quantum_unit:.6f}",
                "avg_qber": f"{avg_qber:.6f}",
                "avg_sifted_ratio": f"{avg_sifted_ratio:.6f}",
                "avg_bell_score": f"{avg_bell_score:.6f}",
                "avg_post_reconciliation_error": f"{avg_post_error:.6f}",
                "avg_eve_intercepts": f"{avg_eve_intercepts:.2f}",
                "aborted_trials": aborted,
                "successful_trials": successful_trials,
                "success_rate": f"{success_rate:.6f}",
                "efficiency_key_bits_per_quantum_unit": f"{efficiency_key_bits_per_quantum_unit:.6f}",
                "efficiency_key_bits_per_second": f"{efficiency_key_bits_per_second:.6f}",
                "qber_abort_threshold": (
                    f"{BB84_QBER_THRESHOLD:.2f}" if protocol.name == "BB84+AES" else f"{E91_QBER_THRESHOLD:.2f}"
                ),
                "bell_abort_threshold": (
                    "" if protocol.name == "BB84+AES" else f"{E91_CHSH_THRESHOLD:.2f}"
                ),
            }
        )


def sweep_qber(
    trials: int = 3,
    output_path: Path | None = None,
) -> Path:
    """Run a comparative protocol sweep and write aggregate metrics to CSV."""
    if output_path is None:
        output_path = Path(__file__).resolve().parents[1] / "results" / "qber_sweep.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rates = [i / 10 for i in range(11)]

    target_path = output_path
    try:
        handle = target_path.open("w", newline="", encoding="utf-8")
    except PermissionError:
        target_path = output_path.with_name(output_path.stem + "_pending_update.csv")
        handle = target_path.open("w", newline="", encoding="utf-8")

    with handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "protocol",
                "intercept_rate",
                "trials",
                "quantum_units_per_trial",
                "quantum_unit_label",
                "avg_runtime_sec",
                "computational_load_ms_per_quantum_unit",
                "avg_qber",
                "avg_sifted_ratio",
                "avg_bell_score",
                "avg_post_reconciliation_error",
                "avg_eve_intercepts",
                "aborted_trials",
                "successful_trials",
                "success_rate",
                "efficiency_key_bits_per_quantum_unit",
                "efficiency_key_bits_per_second",
                "qber_abort_threshold",
                "bell_abort_threshold",
            ],
        )
        writer.writeheader()
        _write_protocol_rows(writer, BB84_CONFIG, rates, trials)
        _write_protocol_rows(writer, E91_CONFIG, rates, trials)

    return target_path


if __name__ == "__main__":
    path = sweep_qber()
    print(f"Wrote QKD comparison results to {path}")
