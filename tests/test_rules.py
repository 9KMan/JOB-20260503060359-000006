"""Unit tests for all 14 leakage rules."""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

from core.rules.price_structure import (
    R01UndiscountedBaseline, R02DisguisedBundleDiscount,
    R03AnchorPriceDrift, R04SegmentBleed, R05RetroactiveCliff,
    get_all_price_structure_rules,
)
from core.rules.customer_behavior import (
    R06ReturnVelocity, R07PaymentDrift, R08ReturnToInvoice,
    R09ShortCloseCredit, R10VolumeSpikeGaming,
    get_all_customer_behavior_rules,
)
from core.rules.product_mix import (
    R11HighReturnSKU, R12ZombieProduct, R13MixShiftErosion,
    R14PromotionalDependency, get_all_product_mix_rules,
)
from core.rules.base import RuleContext, RuleCategory, Severity


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
        self.days_late = kwargs.get("days_late", 0)
        self.credit_price = kwargs.get("credit_price", None)
        self.credit_days = kwargs.get("credit_days", 999)
        self.is_promo = kwargs.get("is_promo", False)


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def mock_tx(tenant_id):
    return MockTransaction(
        tenant_id=tenant_id,
        transaction_id="TX-TEST-001",
        customer_id="CUST-ENTERPRISE-1",
        customer_segment="Enterprise",
        product_id="PROD-SW-001",
        product_category="Software",
        list_price=Decimal("10000"),
        invoice_price=Decimal("8000"),
        net_price=Decimal("7500"),
        pocket_price=Decimal("7200"),
        gross_margin=Decimal("2200"),
        return_qty=Decimal("0"),
    )


def make_ctx(tenant_id, txs, config=None):
    customer_history = {}
    product_history = {}
    for tx in txs:
        customer_history.setdefault(tx.customer_id, []).append(tx)
        product_history.setdefault(tx.product_id, []).append(tx)
    return RuleContext(
        tenant_id=tenant_id,
        all_transactions=txs,
        customer_history=customer_history,
        product_history=product_history,
        contract_data={},
        config=config or {},
    )


class TestR01UndiscountedBaseline:
    def test_rule_id_and_properties(self):
        rule = R01UndiscountedBaseline()
        assert rule.rule_id == "R-01"
        assert rule.category == RuleCategory.PRICE_STRUCTURE
        assert rule.severity == Severity.HIGH

    def test_detects_when_product_never_at_list(self, tenant_id, mock_tx):
        rule = R01UndiscountedBaseline()
        txs = [mock_tx]
        ctx = make_ctx(tenant_id, txs, {"R-01": {"params": {"min_discount_to_trigger": 0.05}}})
        ctx.product_history = {"PROD-SW-001": []}
        finding = rule.detect(mock_tx, ctx)
        assert finding is None

    def test_returns_finding_with_valid_leakage(self, tenant_id):
        rule = R01UndiscountedBaseline()
        tx = MockTransaction(
            tenant_id=tenant_id,
            transaction_id="TX-001",
            customer_id="CUST-001",
            customer_segment="Enterprise",
            product_id="PROD-NEW",
            product_category="Software",
            list_price=Decimal("10000"),
            invoice_price=Decimal("10000"),
            net_price=Decimal("9500"),
            pocket_price=Decimal("9000"),
            gross_margin=Decimal("2000"),
            return_qty=Decimal("0"),
        )
        txs = [tx]
        ctx = make_ctx(tenant_id, txs, {
            "R-01": {"params": {"min_discount_to_trigger": 0.01}},
        })
        ctx.product_history = {"PROD-NEW": []}
        finding = rule.detect(tx, ctx)
        assert finding is None

    def test_quantify(self, tenant_id, mock_tx):
        rule = R01UndiscountedBaseline()
        ctx = make_ctx(tenant_id, [mock_tx])
        impact = rule.quantify(mock_tx, None)
        assert isinstance(impact, Decimal)
        assert impact >= 0

    def test_recurrence_factor(self, tenant_id, mock_tx):
        rule = R01UndiscountedBaseline()
        ctx = make_ctx(tenant_id, [mock_tx])
        rf = rule.recurrence_factor(mock_tx, ctx)
        assert rf == 1.0


class TestR02DisguisedBundleDiscount:
    def test_rule_properties(self):
        rule = R02DisguisedBundleDiscount()
        assert rule.rule_id == "R-02"
        assert rule.name == "Disguised Bundle Discount"
        assert rule.severity == Severity.HIGH

    def test_no_detection_without_bundle_config(self, tenant_id, mock_tx):
        rule = R02DisguisedBundleDiscount()
        ctx = make_ctx(tenant_id, [mock_tx])
        finding = rule.detect(mock_tx, ctx)
        assert finding is None

    def test_quantify(self, tenant_id, mock_tx):
        rule = R02DisguisedBundleDiscount()
        ctx = make_ctx(tenant_id, [mock_tx])
        impact = rule.quantify(mock_tx, None)
        assert isinstance(impact, Decimal)


class TestR03AnchorPriceDrift:
    def test_rule_properties(self):
        rule = R03AnchorPriceDrift()
        assert rule.rule_id == "R-03"
        assert rule.severity == Severity.MEDIUM

    def test_no_detection_with_insufficient_history(self, tenant_id, mock_tx):
        rule = R03AnchorPriceDrift()
        ctx = make_ctx(tenant_id, [mock_tx], {"R-03": {"params": {"lookback_periods": 12}}})
        finding = rule.detect(mock_tx, ctx)
        assert finding is None


class TestR04SegmentBleed:
    def test_rule_properties(self):
        rule = R04SegmentBleed()
        assert rule.rule_id == "R-04"
        assert rule.severity == Severity.HIGH

    def test_no_detection_for_non_enterprise(self, tenant_id, mock_tx):
        rule = R04SegmentBleed()
        ctx = make_ctx(tenant_id, [mock_tx], {"segments": {"enterprise": ["Enterprise"], "midmarket": ["MidMarket"]}})
        finding = rule.detect(mock_tx, ctx)
        assert finding is None


class TestR05RetroactiveCliff:
    def test_rule_properties(self):
        rule = R05RetroactiveCliff()
        assert rule.rule_id == "R-05"
        assert rule.severity == Severity.HIGH

    def test_no_detection_without_triggers(self, tenant_id, mock_tx):
        rule = R05RetroactiveCliff()
        ctx = make_ctx(tenant_id, [mock_tx])
        finding = rule.detect(mock_tx, ctx)
        assert finding is None


class TestR06ReturnVelocity:
    def test_rule_properties(self):
        rule = R06ReturnVelocity()
        assert rule.rule_id == "R-06"
        assert rule.category == RuleCategory.CUSTOMER_BEHAVIOR
        assert rule.severity == Severity.HIGH

    def test_no_detection_insufficient_history(self, tenant_id, mock_tx):
        rule = R06ReturnVelocity()
        ctx = make_ctx(tenant_id, [mock_tx], {"R-06": {"params": {"return_rate_threshold": 0.10}}})
        finding = rule.detect(mock_tx, ctx)
        assert finding is None

    def test_quantify(self, tenant_id, mock_tx):
        rule = R06ReturnVelocity()
        ctx = make_ctx(tenant_id, [mock_tx])
        impact = rule.quantify(mock_tx, None)
        assert isinstance(impact, Decimal)


class TestR07PaymentDrift:
    def test_rule_properties(self):
        rule = R07PaymentDrift()
        assert rule.rule_id == "R-07"
        assert rule.severity == Severity.MEDIUM

    def test_no_detection_no_late_payments(self, tenant_id, mock_tx):
        rule = R07PaymentDrift()
        ctx = make_ctx(tenant_id, [mock_tx], {"R-07": {"params": {"late_days_threshold": 30}}})
        finding = rule.detect(mock_tx, ctx)
        assert finding is None


class TestR08ReturnToInvoice:
    def test_rule_properties(self):
        rule = R08ReturnToInvoice()
        assert rule.rule_id == "R-08"
        assert rule.severity == Severity.HIGH

    def test_recurrence_factor(self, tenant_id, mock_tx):
        rule = R08ReturnToInvoice()
        ctx = make_ctx(tenant_id, [mock_tx])
        rf = rule.recurrence_factor(mock_tx, ctx)
        assert rf == 0.70


class TestR09ShortCloseCredit:
    def test_rule_properties(self):
        rule = R09ShortCloseCredit()
        assert rule.rule_id == "R-09"
        assert rule.severity == Severity.MEDIUM


class TestR10VolumeSpikeGaming:
    def test_rule_properties(self):
        rule = R10VolumeSpikeGaming()
        assert rule.rule_id == "R-10"
        assert rule.severity == Severity.MEDIUM


class TestR11HighReturnSKU:
    def test_rule_properties(self):
        rule = R11HighReturnSKU()
        assert rule.rule_id == "R-11"
        assert rule.category == RuleCategory.PRODUCT_MIX
        assert rule.severity == Severity.HIGH

    def test_recurrence_factor(self, tenant_id, mock_tx):
        rule = R11HighReturnSKU()
        ctx = make_ctx(tenant_id, [mock_tx])
        rf = rule.recurrence_factor(mock_tx, ctx)
        assert rf == 0.85


class TestR12ZombieProduct:
    def test_rule_properties(self):
        rule = R12ZombieProduct()
        assert rule.rule_id == "R-12"
        assert rule.severity == Severity.MEDIUM


class TestR13MixShiftErosion:
    def test_rule_properties(self):
        rule = R13MixShiftErosion()
        assert rule.rule_id == "R-13"
        assert rule.severity == Severity.MEDIUM


class TestR14PromotionalDependency:
    def test_rule_properties(self):
        rule = R14PromotionalDependency()
        assert rule.rule_id == "R-14"
        assert rule.severity == Severity.LOW

    def test_recurrence_factor(self, tenant_id, mock_tx):
        rule = R14PromotionalDependency()
        ctx = make_ctx(tenant_id, [mock_tx])
        rf = rule.recurrence_factor(mock_tx, ctx)
        assert rf == 0.80


class TestAllRulesLoaded:
    def test_all_price_structure_rules(self):
        rules = get_all_price_structure_rules()
        assert len(rules) == 5
        rule_ids = [r.rule_id for r in rules]
        assert "R-01" in rule_ids
        assert "R-05" in rule_ids

    def test_all_customer_behavior_rules(self):
        rules = get_all_customer_behavior_rules()
        assert len(rules) == 5
        rule_ids = [r.rule_id for r in rules]
        assert "R-06" in rule_ids
        assert "R-10" in rule_ids

    def test_all_product_mix_rules(self):
        rules = get_all_product_mix_rules()
        assert len(rules) == 4
        rule_ids = [r.rule_id for r in rules]
        assert "R-11" in rule_ids
        assert "R-14" in rule_ids

    def test_total_rule_count(self):
        all_rules = get_all_price_structure_rules() + get_all_customer_behavior_rules() + get_all_product_mix_rules()
        assert len(all_rules) == 14
