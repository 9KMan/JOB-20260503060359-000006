"""Integration tests for end-to-end pipeline."""
import pytest
import uuid
from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock

from core.engine.pocket_waterfall import PocketWaterfallCalculator
from core.engine.leakage_engine import LeakageEngine
from core.engine.anonymizer import Anonymizer
from core.engine.validator import Validator
from core.engine.prioritizer import Prioritizer


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


class MockFinding:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
        self.transaction_id = kwargs.get("transaction_id", uuid.uuid4())
        self.rule_id = kwargs.get("rule_id", "R-01")
        self.category = kwargs.get("category", "PRICE_STRUCTURE")
        self.severity = kwargs.get("severity", "HIGH")
        self.confidence = kwargs.get("confidence", 0.85)
        self.impact_dollars = kwargs.get("impact_dollars", Decimal("5000"))
        self.impact_pct_of_margin = kwargs.get("impact_pct_of_margin", 0.10)
        self.description = kwargs.get("description", "Test finding.")
        self.affected_transaction_ids = kwargs.get("affected_transaction_ids", [])
        self.recommendation = kwargs.get("recommendation", "Review.")
        self.recurrence_factor = kwargs.get("recurrence_factor", 0.75)


class MockFinding2:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
        self.transaction_id = kwargs.get("transaction_id", uuid.uuid4())
        self.rule_id = kwargs.get("rule_id", "R-01")
        self.category = kwargs.get("category", "PRICE_STRUCTURE")
        self.severity = kwargs.get("severity", "HIGH")
        self.confidence = kwargs.get("confidence", 0.85)
        self.impact_dollars = kwargs.get("impact_dollars", Decimal("5000"))
        self.impact_pct_of_margin = kwargs.get("impact_pct_of_margin", 0.10)
        self.description = kwargs.get("description", "Test finding.")
        self.affected_transaction_ids = kwargs.get("affected_transaction_ids", [])
        self.recommendation = kwargs.get("recommendation", "Review.")
        self.recurrence_factor = kwargs.get("recurrence_factor", 0.75)


class TestIntegrationPipeline:
    def test_waterfall_plus_anonymizer_pipeline(self, tenant_id):
        tx = MockTransaction(
            tenant_id=tenant_id,
            customer_id="REAL-CUSTOMER-001",
            product_id="REAL-PRODUCT-001",
            list_price=Decimal("10000"),
            invoice_price=Decimal("8500"),
            net_price=Decimal("8000"),
            pocket_price=Decimal("7700"),
            gross_margin=Decimal("2200"),
        )
        calc = PocketWaterfallCalculator()
        result = calc.calculate(tx)

        assert result.pocket_price == Decimal("8000")
        assert result.gross_margin is not None

        anon = Anonymizer(tenant_id=str(tenant_id))
        safe = anon.anonymize({
            "customer_id": "REAL-CUSTOMER-001",
            "product_id": "REAL-PRODUCT-001",
            "amount": 5000,
        })

        assert safe["customer_id"] != "REAL-CUSTOMER-001"
        assert safe["product_id"] != "REAL-PRODUCT-001"
        assert "CUST" in safe["customer_id"] or "PROD" in safe["product_id"]

    def test_leakage_engine_with_empty_transactions(self, tenant_id):
        engine = LeakageEngine()
        findings = engine.run_all_rules([], tenant_id)
        assert findings == []

    def test_anonymizer_batch(self, tenant_id):
        anon = Anonymizer(tenant_id=str(tenant_id))
        data_list = [
            {"customer_id": "CUST-A", "product_id": "PROD-A", "amount": 1000},
            {"customer_id": "CUST-B", "product_id": "PROD-B", "amount": 2000},
        ]
        anonymized = anon.anonymize_batch(data_list)
        assert len(anonymized) == 2
        assert anonymized[0]["customer_id"] != "CUST-A"
        assert anonymized[1]["customer_id"] != "CUST-B"
        mapping = anon.get_mapping()
        assert "customer" in mapping
        assert len(mapping["customer"]) == 2

    def test_validator_required_columns(self):
        import pandas as pd
        validator = Validator()
        df = pd.DataFrame({
            "transaction_id": ["TX1"],
            "date": ["2024-01-01"],
        })
        errors = validator.validate_structure(df)
        col_names = [e.column for e in errors]
        assert "list_price" in col_names
        assert "invoice_price" in col_names

    def test_prioritizer_with_findings(self, tenant_id):
        p = Prioritizer()
        findings = [
            MockFinding(impact_dollars=Decimal("50000"), rule_id="R-05"),
            MockFinding(impact_dollars=Decimal("30000"), rule_id="R-04"),
        ]
        opps = p.get_top_opportunities(findings, ease_scores={str(f.id): 7.0 for f in findings})
        assert len(opps) == 2
        assert opps[0]["impact"] >= opps[1]["impact"]

    def test_leakage_engine_get_rule_by_id(self, tenant_id):
        engine = LeakageEngine()
        rule = engine.get_rule_by_id("R-05")
        assert rule is not None
        assert rule.rule_id == "R-05"

    def test_leakage_engine_filters(self, tenant_id):
        engine = LeakageEngine()
        findings = [
            MockFinding(rule_id="R-01", category="PRICE_STRUCTURE", severity="HIGH"),
            MockFinding(rule_id="R-06", category="CUSTOMER_BEHAVIOR", severity="HIGH"),
            MockFinding(rule_id="R-11", category="PRODUCT_MIX", severity="MEDIUM"),
        ]
        ps_findings = engine.get_findings_by_category(findings, "PRICE_STRUCTURE")
        assert len(ps_findings) == 1
        high_findings = engine.get_findings_by_severity(findings, "HIGH")
        assert len(high_findings) == 2
