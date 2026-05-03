"""Tests for pocket waterfall calculations."""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock, patch

from core.engine.pocket_waterfall import (
    PocketWaterfallCalculator, WaterfallResult, RetroactiveDiscountEstimator
)


class MockTransaction:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
        self.transaction_id = kwargs.get("transaction_id", "TX-001")
        self.date = kwargs.get("date", date(2024, 1, 15))
        self.customer_id = kwargs.get("customer_id", "CUST-001")
        self.customer_segment = kwargs.get("customer_segment", "Enterprise")
        self.product_id = kwargs.get("product_id", "PROD-001")
        self.product_category = kwargs.get("product_category", "Software")
        self.list_price = kwargs.get("list_price", Decimal("10000"))
        self.invoice_price = kwargs.get("invoice_price", Decimal("8500"))
        self.net_price = kwargs.get("net_price", Decimal("8000"))
        self.pocket_price = kwargs.get("pocket_price", Decimal("7700"))
        self.gross_margin = kwargs.get("gross_margin", Decimal("2200"))
        self.return_qty = kwargs.get("return_qty", Decimal("0"))
        self.payment_status = kwargs.get("payment_status", "PAID")


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def base_transaction(tenant_id):
    return MockTransaction(
        tenant_id=tenant_id,
        transaction_id="TX-BASE-001",
        customer_id="CUST-001",
        customer_segment="Enterprise",
        product_id="PROD-001",
        product_category="Software",
        list_price=Decimal("10000"),
        invoice_price=Decimal("8500"),
        net_price=Decimal("8000"),
        pocket_price=Decimal("7700"),
        gross_margin=Decimal("2200"),
        return_qty=Decimal("0"),
    )


class TestPocketWaterfallCalculator:
    def test_calculate_waterfall_basic(self, base_transaction):
        calc = PocketWaterfallCalculator()
        result = calc.calculate(base_transaction)

        assert isinstance(result, WaterfallResult)
        assert result.list_price == Decimal("10000")
        assert result.invoice_discounts == Decimal("1500")
        assert result.net_price == Decimal("8500")
        assert result.post_invoice_discounts == Decimal("500")
        assert result.pocket_price == Decimal("8000")
        assert result.allowances == Decimal("300")
        cost_price = base_transaction.list_price - base_transaction.gross_margin
        expected_margin = Decimal("8000") - cost_price
        assert result.gross_margin == expected_margin

    def test_calculate_waterfall_with_no_discounts(self, tenant_id):
        tx = MockTransaction(
            tenant_id=tenant_id,
            transaction_id="TX-NODISC",
            list_price=Decimal("10000"),
            invoice_price=Decimal("10000"),
            net_price=Decimal("10000"),
            pocket_price=Decimal("10000"),
            gross_margin=Decimal("3000"),
        )
        calc = PocketWaterfallCalculator()
        result = calc.calculate(tx)

        assert result.invoice_discounts == Decimal("0")
        assert result.post_invoice_discounts == Decimal("0")
        assert result.allowances == Decimal("0")
        assert result.pocket_price == Decimal("10000")

    def test_calculate_waterfall_with_heavy_discounts(self, tenant_id):
        tx = MockTransaction(
            tenant_id=tenant_id,
            transaction_id="TX-HEAVY",
            list_price=Decimal("10000"),
            invoice_price=Decimal("5000"),
            net_price=Decimal("4000"),
            pocket_price=Decimal("3500"),
            gross_margin=Decimal("2000"),
        )
        calc = PocketWaterfallCalculator()
        result = calc.calculate(tx)

        assert result.invoice_discounts == Decimal("5000")
        assert result.post_invoice_discounts == Decimal("1000")
        assert result.allowances == Decimal("500")

    def test_calculate_batch(self, base_transaction, tenant_id):
        tx2 = MockTransaction(
            tenant_id=tenant_id,
            transaction_id="TX-002",
            list_price=Decimal("20000"),
            invoice_price=Decimal("17000"),
            net_price=Decimal("16000"),
            pocket_price=Decimal("15400"),
            gross_margin=Decimal("4400"),
        )
        calc = PocketWaterfallCalculator()
        results = calc.calculate_batch([base_transaction, tx2])

        assert len(results) == 2
        assert all(isinstance(r, WaterfallResult) for r in results)

    def test_aggregate_waterfall(self, base_transaction, tenant_id):
        tx2 = MockTransaction(
            tenant_id=tenant_id,
            transaction_id="TX-002",
            list_price=Decimal("20000"),
            invoice_price=Decimal("17000"),
            net_price=Decimal("16000"),
            pocket_price=Decimal("15400"),
            gross_margin=Decimal("4400"),
        )
        calc = PocketWaterfallCalculator()
        results = calc.calculate_batch([base_transaction, tx2])
        agg = calc.aggregate_waterfall(results)

        assert agg["total_list_price"] == Decimal("30000")
        assert agg["total_invoice_discounts"] == Decimal("4500")
        assert "total_pocket_price" in agg
        assert "total_gross_margin" in agg

    def test_aggregate_waterfall_empty(self):
        calc = PocketWaterfallCalculator()
        agg = calc.aggregate_waterfall([])
        assert agg == {}

    def test_waterfall_result_to_dict(self, base_transaction):
        calc = PocketWaterfallCalculator()
        result = calc.calculate(base_transaction)
        d = result.to_dict()

        assert isinstance(d, dict)
        assert d["list_price"] == 10000.0
        assert d["invoice_discounts"] == 1500.0
        assert d["pocket_price"] == 8000.0


class TestRetroactiveDiscountEstimator:
    def test_estimate_clawback_no_triggers(self, tenant_id, base_transaction):
        estimator = RetroactiveDiscountEstimator()
        result = estimator.estimate_clawback(
            base_transaction,
            contract_triggers=[],
            current_period_volume=Decimal("50000"),
        )
        assert result == Decimal("0")

    def test_estimate_clawback_volume_tier(self, tenant_id, base_transaction):
        estimator = RetroactiveDiscountEstimator()
        triggers = [
            {
                "type": "VOLUME_TIER",
                "retroactive": True,
                "prior_volume": Decimal("40000"),
                "tiers": [
                    {"threshold": 0, "rate": Decimal("0.03")},
                    {"threshold": 50000, "rate": Decimal("0.05")},
                ],
            }
        ]
        result = estimator.estimate_clawback(
            base_transaction,
            triggers,
            current_period_volume=Decimal("60000"),
        )
        assert isinstance(result, Decimal)

    def test_estimate_clawback_non_retroactive_tier(self, tenant_id, base_transaction):
        estimator = RetroactiveDiscountEstimator()
        triggers = [
            {
                "type": "VOLUME_TIER",
                "retroactive": False,
                "prior_volume": Decimal("40000"),
                "tiers": [
                    {"threshold": 0, "rate": Decimal("0.03")},
                ],
            }
        ]
        result = estimator.estimate_clawback(
            base_transaction,
            triggers,
            current_period_volume=Decimal("60000"),
        )
        assert result == Decimal("0")

    def test_get_applicable_tier(self, tenant_id, base_transaction):
        estimator = RetroactiveDiscountEstimator()
        trigger = {
            "type": "VOLUME_TIER",
            "tiers": [
                {"threshold": 0, "rate": Decimal("0.02")},
                {"threshold": 50000, "rate": Decimal("0.04")},
                {"threshold": 100000, "rate": Decimal("0.06")},
            ],
        }
        tier = estimator._get_applicable_tier(trigger, Decimal("75000"))
        assert tier["rate"] == Decimal("0.04")

    def test_get_applicable_tier_at_threshold(self, tenant_id, base_transaction):
        estimator = RetroactiveDiscountEstimator()
        trigger = {
            "type": "VOLUME_TIER",
            "tiers": [
                {"threshold": 0, "rate": Decimal("0.02")},
                {"threshold": 50000, "rate": Decimal("0.04")},
            ],
        }
        tier = estimator._get_applicable_tier(trigger, Decimal("50000"))
        assert tier["rate"] == Decimal("0.04")
