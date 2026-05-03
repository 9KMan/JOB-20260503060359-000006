"""Leakage detection engine — runs all 14 rules."""
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed

from core.rules.base import BaseRule, RuleContext, LeakageFinding, RuleCategory
from core.rules.price_structure import get_all_price_structure_rules
from core.rules.customer_behavior import get_all_customer_behavior_rules
from core.rules.product_mix import get_all_product_mix_rules
from core.engine.pocket_waterfall import PocketWaterfallCalculator


class LeakageEngine:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.calculator = PocketWaterfallCalculator()
        self._rules = self._load_rules()

    def _load_rules(self) -> List[BaseRule]:
        rules = []
        rules.extend(get_all_price_structure_rules())
        rules.extend(get_all_customer_behavior_rules())
        rules.extend(get_all_product_mix_rules())
        return rules

    def run_all_rules(
        self,
        transactions: List[Any],
        tenant_id: UUID,
        customer_history: Dict[str, List[Any]] = None,
        product_history: Dict[str, List[Any]] = None,
        contract_data: Dict[str, Any] = None,
    ) -> List[LeakageFinding]:
        ctx = RuleContext(
            tenant_id=tenant_id,
            all_transactions=transactions,
            customer_history=customer_history or self._build_customer_history(transactions),
            product_history=product_history or self._build_product_history(transactions),
            contract_data=contract_data or {},
            config=self.config,
        )

        findings = []
        for rule in self._rules:
            try:
                for tx in transactions:
                    finding = rule.detect(tx, ctx)
                    if finding:
                        finding.impact_dollars = rule.quantify(tx, finding)
                        finding.recurrence_factor = rule.recurrence_factor(tx, ctx)
                        findings.append(finding)
            except Exception:
                continue
        return findings

    def _build_customer_history(self, transactions: List[Any]) -> Dict[str, List[Any]]:
        history: Dict[str, List[Any]] = {}
        for tx in transactions:
            cid = tx.customer_id
            if cid not in history:
                history[cid] = []
            history[cid].append(tx)
        return history

    def _build_product_history(self, transactions: List[Any]) -> Dict[str, List[Any]]:
        history: Dict[str, List[Any]] = {}
        for tx in transactions:
            pid = tx.product_id
            if pid not in history:
                history[pid] = []
            history[pid].append(tx)
        return history

    def get_rule_by_id(self, rule_id: str) -> Optional[BaseRule]:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule
        return None

    def get_findings_by_category(self, findings: List[LeakageFinding], category: str) -> List[LeakageFinding]:
        return [f for f in findings if f.category == category]

    def get_findings_by_severity(self, findings: List[LeakageFinding], severity: str) -> List[LeakageFinding]:
        return [f for f in findings if f.severity == severity]

    def get_findings_by_rule(self, findings: List[LeakageFinding], rule_id: str) -> List[LeakageFinding]:
        return [f for f in findings if f.rule_id == rule_id]
