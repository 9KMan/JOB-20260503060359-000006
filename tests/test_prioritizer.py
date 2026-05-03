"""Tests for prioritizer."""
import pytest
import uuid
from decimal import Decimal
from datetime import date

from core.engine.prioritizer import Prioritizer
from core.rules.base import LeakageFinding, Severity, RuleCategory


@pytest.fixture
def tenant_id():
    return uuid.uuid4()


class MockFinding:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.tenant_id = kwargs.get("tenant_id", uuid.uuid4())
        self.transaction_id = kwargs.get("transaction_id", uuid.uuid4())
        self.rule_id = kwargs.get("rule_id", "R-05")
        self.category = kwargs.get("category", RuleCategory.PRICE_STRUCTURE.value)
        self.severity = kwargs.get("severity", Severity.HIGH.value)
        self.confidence = kwargs.get("confidence", 0.85)
        self.impact_dollars = kwargs.get("impact_dollars", Decimal("50000"))
        self.impact_pct_of_margin = kwargs.get("impact_pct_of_margin", 0.10)
        self.description = kwargs.get("description", "Retroactive cliff detected.")
        self.affected_transaction_ids = kwargs.get("affected_transaction_ids", [])
        self.recommendation = kwargs.get("recommendation", "Renegotiate GPR.")
        self.recurrence_factor = kwargs.get("recurrence_factor", 0.80)


class TestPrioritizer:
    def test_calculate_priority_score_basic(self):
        p = Prioritizer()
        finding = MockFinding(
            impact_dollars=Decimal("50000"),
            confidence=0.85,
            recurrence_factor=0.80,
        )
        score = p.calculate_priority_score(finding, ease_score=8.0)
        assert score > 0
        assert isinstance(score, float)

    def test_calculate_priority_score_ease_scaling(self):
        p = Prioritizer()
        finding = MockFinding(
            impact_dollars=Decimal("50000"),
            confidence=0.85,
            recurrence_factor=0.80,
        )
        score_high_ease = p.calculate_priority_score(finding, ease_score=10.0)
        score_low_ease = p.calculate_priority_score(finding, ease_score=2.0)
        assert score_high_ease > score_low_ease

    def test_calculate_priority_score_ease_clamped(self):
        p = Prioritizer()
        finding = MockFinding(impact_dollars=Decimal("10000"), confidence=0.8, recurrence_factor=0.5)
        score = p.calculate_priority_score(finding, ease_score=15.0)
        score_clamped = p.calculate_priority_score(finding, ease_score=10.0)
        assert score == score_clamped

    def test_rank_findings_returns_tuples(self):
        p = Prioritizer()
        findings = [
            MockFinding(impact_dollars=Decimal("50000"), rule_id="R-05"),
            MockFinding(impact_dollars=Decimal("30000"), rule_id="R-04"),
            MockFinding(impact_dollars=Decimal("80000"), rule_id="R-06"),
        ]
        ease_scores = {str(f.id): 7.0 for f in findings}
        ranked = p.rank_findings(findings, ease_scores=ease_scores)

        assert len(ranked) == 3
        assert all(len(t) == 3 for t in ranked)
        assert all(isinstance(t[0], MockFinding) for t in ranked)
        assert all(isinstance(t[1], float) for t in ranked)
        assert all(isinstance(t[2], str) for t in ranked)

    def test_rank_findings_sorted_by_priority(self):
        p = Prioritizer()
        findings = [
            MockFinding(impact_dollars=Decimal("10000"), rule_id="R-01", confidence=0.7, recurrence_factor=0.5),
            MockFinding(impact_dollars=Decimal("50000"), rule_id="R-05", confidence=0.9, recurrence_factor=0.8),
            MockFinding(impact_dollars=Decimal("30000"), rule_id="R-04", confidence=0.8, recurrence_factor=0.6),
        ]
        ease_scores = {str(f.id): 5.0 for f in findings}
        ranked = p.rank_findings(findings, ease_scores=ease_scores)
        priorities = [r[1] for r in ranked]
        assert priorities == sorted(priorities, reverse=True)

    def test_get_top_opportunities(self):
        p = Prioritizer()
        findings = [
            MockFinding(
                impact_dollars=Decimal("50000"),
                rule_id="R-05",
                category=RuleCategory.PRICE_STRUCTURE.value,
                severity=Severity.HIGH.value,
            ),
            MockFinding(
                impact_dollars=Decimal("30000"),
                rule_id="R-04",
                category=RuleCategory.PRICE_STRUCTURE.value,
                severity=Severity.HIGH.value,
            ),
        ]
        ease_scores = {str(f.id): 7.0 for f in findings}
        opps = p.get_top_opportunities(findings, ease_scores=ease_scores, top_n=2)

        assert len(opps) == 2
        assert all("rank" in o for o in opps)
        assert all("priority_score" in o for o in opps)
        assert opps[0]["impact"] >= opps[1]["impact"]

    def test_get_top_opportunities_respects_top_n(self):
        p = Prioritizer()
        findings = [MockFinding(impact_dollars=Decimal("10000"), rule_id=f"R-{i:02d}") for i in range(20)]
        ease_scores = {str(f.id): 5.0 for f in findings}
        opps = p.get_top_opportunities(findings, ease_scores=ease_scores, top_n=5)
        assert len(opps) == 5

    def test_empty_findings(self):
        p = Prioritizer()
        opps = p.get_top_opportunities([], ease_scores={})
        assert opps == []
