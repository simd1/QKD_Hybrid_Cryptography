"""Generate QBER measurements across Eve intercept rates."""

from __future__ import annotations

import csv
from pathlib import Path

from bb84_pipeline import QBER_THRESHOLD, run_bb84


def sweep_qber(
    n_qubits: int = 8192,
    trials: int = 5,
    output_path: Path | None = None,
) -> Path:
    """Run a QBER sweep and write average measurements to CSV."""
    if output_path is None:
        output_path = Path(__file__).resolve().parents[1] / "results" / "qber_sweep.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    rates = [i / 10 for i in range(11)]

    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "intercept_rate",
                "trials",
                "avg_qber",
                "avg_sifted_ratio",
                "abort_threshold",
                "aborted_trials",
            ],
        )
        writer.writeheader()

        for rate in rates:
            qbers: list[float] = []
            sifted_ratios: list[float] = []
            aborted = 0

            for _ in range(trials):
                _, metrics = run_bb84(
                    n_qubits=n_qubits,
                    eve_present=rate > 0.0,
                    intercept_rate=rate,
                    verbose=False,
                    return_metrics=True,
                )
                qbers.append(float(metrics["qber"]))
                sifted_ratios.append(float(metrics["sifted_ratio"]))
                aborted += int(bool(metrics["aborted"]))

            writer.writerow(
                {
                    "intercept_rate": f"{rate:.1f}",
                    "trials": trials,
                    "avg_qber": f"{sum(qbers) / len(qbers):.6f}",
                    "avg_sifted_ratio": f"{sum(sifted_ratios) / len(sifted_ratios):.6f}",
                    "abort_threshold": f"{QBER_THRESHOLD:.2f}",
                    "aborted_trials": aborted,
                }
            )

    return output_path


if __name__ == "__main__":
    path = sweep_qber()
    print(f"Wrote QBER sweep results to {path}")

