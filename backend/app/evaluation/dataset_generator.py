"""Configurable ground-truth benchmark dataset generator.

Creates controlled synthetic financial scenarios with deterministic reproducibility
via random_seed. Ground truth is stored separately from generated data.

Default distribution (configurable):
  55% clean_match
  10% fee_variance
   8% amount_mismatch
   7% duplicate
   6% missing_invoice
   5% missing_settlement
   4% refund_mismatch
   3% date_mismatch
   2% ambiguous

Usage:
  python -m app.evaluation generate_dataset --records 1000 --seed 42
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from app.evaluation.ground_truth import GroundTruthCase, SCENARIO_GROUND_TRUTH

# Default scenario distribution (must sum to 1.0)
DEFAULT_DISTRIBUTION = {
    "clean_match": 0.55,
    "fee_variance": 0.10,
    "amount_mismatch": 0.08,
    "duplicate": 0.07,
    "missing_invoice": 0.06,
    "missing_settlement": 0.05,
    "refund_mismatch": 0.04,
    "date_mismatch": 0.03,
    "ambiguous": 0.02,
}

# Typical amounts for synthetic cases (INR)
AMOUNT_RANGES = {
    "clean_match": (1000, 50000),
    "fee_variance": (5000, 20000),
    "amount_mismatch": (2000, 100000),
    "duplicate": (1000, 30000),
    "missing_invoice": (500, 15000),
    "missing_settlement": (1000, 25000),
    "refund_mismatch": (500, 10000),
    "date_mismatch": (1000, 40000),
    "ambiguous": (5000, 50000),
}

FEE_RATE = 0.018  # 1.8% gateway fee


class BenchmarkDatasetGenerator:
    """Generate reproducible synthetic financial benchmark datasets."""

    def __init__(
        self,
        records: int = 1000,
        seed: int = 42,
        distribution: Optional[dict[str, float]] = None,
        dataset_name: str = "benchmark",
        version: str = "v1",
    ):
        self.records = records
        self.seed = seed
        self.distribution = distribution or DEFAULT_DISTRIBUTION
        self.dataset_name = dataset_name
        self.version = version
        self._validate_distribution()
        self.rng = random.Random(seed)

    def _validate_distribution(self) -> None:
        total = sum(self.distribution.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Distribution must sum to 1.0, got {total:.4f}")

    def _pick_scenario(self) -> str:
        """Pick a scenario type according to the distribution."""
        r = self.rng.random()
        cumulative = 0.0
        for scenario, prob in self.distribution.items():
            cumulative += prob
            if r < cumulative:
                return scenario
        return list(self.distribution.keys())[-1]

    def _generate_amount(self, scenario: str) -> float:
        lo, hi = AMOUNT_RANGES.get(scenario, (1000, 50000))
        return round(self.rng.uniform(lo, hi), 2)

    def _generate_date(self, base_date: Optional[datetime] = None) -> str:
        if base_date is None:
            base_date = datetime.now(timezone.utc) - timedelta(days=self.rng.randint(1, 90))
        return base_date.isoformat()

    def generate(self) -> dict:
        """Generate the complete benchmark dataset.

        Returns:
            dict with:
              - metadata: dataset info
              - cases: list of GroundTruthCase dicts
              - synthetic_records: list of synthetic financial records per case
        """
        cases = []
        synthetic_records = []

        for i in range(self.records):
            case_id = f"CASE_{i + 1:05d}"
            scenario = self._pick_scenario()
            amount = self._generate_amount(scenario)
            gt_template = SCENARIO_GROUND_TRUTH[scenario]

            # Build ground truth
            gt = GroundTruthCase(
                case_id=case_id,
                scenario_type=scenario,
                expected_match_status=gt_template["expected_match_status"],
                expected_exception_type=gt_template["expected_exception_type"],
                expected_root_cause=gt_template["expected_root_cause"],
                expected_action_class=gt_template["expected_action_class"],
                amount=amount,
                financial_impact=amount,
                transaction_id=str(uuid.UUID(int=self.rng.getrandbits(128))),
                invoice_id=str(uuid.UUID(int=self.rng.getrandbits(128))),
                settlement_id=str(uuid.UUID(int=self.rng.getrandbits(128))),
            )
            cases.append(gt.to_dict())

            # Build synthetic records (these are what the system would process)
            synthetic_records.append(
                self._build_records(case_id, scenario, amount, gt)
            )

        # Compute actual distribution
        scenario_counts: dict[str, int] = {}
        for c in cases:
            s = c["scenario_type"]
            scenario_counts[s] = scenario_counts.get(s, 0) + 1

        return {
            "metadata": {
                "dataset_name": self.dataset_name,
                "version": self.version,
                "record_count": self.records,
                "random_seed": self.seed,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "distribution_config": self.distribution,
                "actual_distribution": {
                    k: v / self.records for k, v in scenario_counts.items()
                },
                "scenario_counts": scenario_counts,
            },
            "cases": cases,
            "synthetic_records": synthetic_records,
        }

    def _build_records(
        self,
        case_id: str,
        scenario: str,
        amount: float,
        gt: GroundTruthCase,
    ) -> dict:
        """Build a set of synthetic financial records for a given scenario."""
        fee = round(amount * FEE_RATE, 2)
        settlement_amount = round(amount - fee, 2)
        base_date = datetime.now(timezone.utc) - timedelta(days=self.rng.randint(1, 60))

        record = {
            "case_id": case_id,
            "scenario": scenario,
            "transaction": {
                "id": gt.transaction_id,
                "amount": amount,
                "currency": "INR",
                "date": self._generate_date(base_date),
                "description": f"Payment for order {case_id}",
                "reference": f"TXN-{case_id}",
            },
            "invoice": None,
            "settlement": None,
            "bank_record": None,
        }

        if scenario == "clean_match":
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": settlement_amount, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": settlement_amount, "date": self._generate_date(base_date + timedelta(days=3))}

        elif scenario == "fee_variance":
            # Fee is slightly different from expected
            actual_fee = round(fee * self.rng.uniform(0.95, 1.10), 2)
            actual_settlement = round(amount - actual_fee, 2)
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": actual_settlement, "fee": actual_fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": actual_settlement, "date": self._generate_date(base_date + timedelta(days=3))}
            record["variance"] = round(abs(actual_fee - fee), 2)

        elif scenario == "amount_mismatch":
            mismatch_amount = round(amount * self.rng.uniform(0.70, 0.95), 2)
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": mismatch_amount - fee, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": mismatch_amount - fee, "date": self._generate_date(base_date + timedelta(days=3))}
            record["mismatch_amount"] = round(amount - mismatch_amount, 2)

        elif scenario == "duplicate":
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": settlement_amount, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": settlement_amount, "date": self._generate_date(base_date + timedelta(days=3))}
            record["duplicate_transaction_id"] = str(uuid.UUID(int=self.rng.getrandbits(128)))

        elif scenario == "missing_invoice":
            record["settlement"] = {"id": gt.settlement_id, "amount": settlement_amount, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": settlement_amount, "date": self._generate_date(base_date + timedelta(days=3))}

        elif scenario == "missing_settlement":
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["bank_record"] = {"amount": settlement_amount, "date": self._generate_date(base_date + timedelta(days=3))}

        elif scenario == "refund_mismatch":
            refund_amount = round(amount * self.rng.uniform(0.85, 1.15), 2)
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": -refund_amount, "fee": 0, "type": "REFUND", "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": -refund_amount, "date": self._generate_date(base_date + timedelta(days=3))}
            record["refund_variance"] = round(abs(refund_amount - amount), 2)

        elif scenario == "date_mismatch":
            late_days = self.rng.randint(3, 10)
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": settlement_amount, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2 + late_days))}
            record["bank_record"] = {"amount": settlement_amount, "date": self._generate_date(base_date + timedelta(days=3 + late_days))}
            record["days_late"] = late_days

        elif scenario == "ambiguous":
            # Multiple possible matches — amounts slightly different, hard to determine
            alt_amount = round(amount * self.rng.uniform(0.97, 1.03), 2)
            record["invoice"] = {"id": gt.invoice_id, "amount": amount, "date": self._generate_date(base_date)}
            record["settlement"] = {"id": gt.settlement_id, "amount": alt_amount - fee, "fee": fee, "date": self._generate_date(base_date + timedelta(days=2))}
            record["bank_record"] = {"amount": alt_amount - fee, "date": self._generate_date(base_date + timedelta(days=3))}
            record["ambiguity_note"] = "Multiple possible matches with similar amounts"

        return record
