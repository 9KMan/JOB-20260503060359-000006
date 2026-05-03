"""Pytest configuration and fixtures."""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

from core.rules.base import RuleContext


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
        self.gross_margin = kwargs.get("gross_margin", Decimal("2700"))
        self.return_qty = kwargs.get("return_qty", Decimal("0"))
        self.payment_status = kwargs.get("payment_status", "PAID")
        self.raw_data = kwargs.get("raw_data", {})

    def __repr__(self):
        return f"<MockTransaction {self.transaction_id}>"


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


@pytest.fixture
def mock_transaction(tenant_id):
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


@pytest.fixture
def mock_rule_context(tenant_id, mock_transaction):
    return RuleContext(
        tenant_id=tenant_id,
        all_transactions=[mock_transaction],
        customer_history={mock_transaction.customer_id: [mock_transaction]},
        product_history={mock_transaction.product_id: [mock_transaction]},
        contract_data={},
        config={},
    )


@pytest.fixture
def transactions_list(tenant_id):
    base = MockTransaction(tenant_id=tenant_id)
    return [base]


@pytest.fixture
def config():
    return {
        "R-01": {"enabled": True, "params": {"min_discount_to_trigger": 0.05, "lookback_periods": 12}},
        "R-06": {"enabled": True, "params": {"return_rate_threshold": 0.10, "min_transaction_value": 1000}},
        "R-07": {"enabled": True, "params": {"late_days_threshold": 30, "min_open_invoice_value": 5000}},
        "segments": {"enterprise": ["Enterprise", "Enterprise A"], "midmarket": ["Mid-Market", "MidMarket"]},
    }
