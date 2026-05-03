"""Customer Behavior Rules (R-06 through R-10)."""
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from core.rules.base import BaseRule, RuleCategory, Severity, RuleContext, LeakageFinding


class R06ReturnVelocity(BaseRule):
    rule_id = "R-06"
    name = "Return Velocity"
    category = RuleCategory.CUSTOMER_BEHAVIOR
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        threshold = ctx.config.get("R-06", {}).get("params", {}).get("return_rate_threshold", 0.10)
        min_value = ctx.config.get("R-06", {}).get("params", {}).get("min_transaction_value", 1000)

        customer_txs = ctx.customer_history.get(tx.customer_id, [])
        if len(customer_txs) < 3:
            return None

        total_qty = sum(float(t.return_qty) for t in customer_txs)
        total_purchase_qty = sum(float(t.invoice_price) / float(t.list_price) for t in customer_txs if float(t.list_price) > 0)
        return_rate = total_qty / total_purchase_qty if total_purchase_qty > 0 else 0

        if return_rate >= threshold:
            impacted_value = sum(float(t.invoice_price) for t in customer_txs if float(t.invoice_price) >= min_value)
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.88,
                impact_dollars=Decimal(str(impacted_value * return_rate * 0.5)),
                impact_pct_of_margin=return_rate,
                description=f"Customer {tx.customer_id} returns >10% of purchases (inventory gaming).",
                affected_transaction_ids=[t.transaction_id for t in customer_txs],
                recommendation="Implement restocking fee or cap returns at 5% of purchase volume.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.75


class R07PaymentDrift(BaseRule):
    rule_id = "R-07"
    name = "Payment Drift"
    category = RuleCategory.CUSTOMER_BEHAVIOR
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        late_threshold = ctx.config.get("R-07", {}).get("params", {}).get("late_days_threshold", 30)
        min_value = ctx.config.get("R-07", {}).get("params", {}).get("min_open_invoice_value", 5000)

        customer_txs = ctx.customer_history.get(tx.customer_id, [])
        late_txs = [t for t in customer_txs if getattr(t, "days_late", 0) >= late_threshold]

        if len(late_txs) >= 2:
            late_value = sum(float(t.invoice_price) for t in late_txs if float(t.invoice_price) >= min_value)
            if late_value > 0:
                float_cost = late_value * 0.05
                return LeakageFinding(
                    id=uuid4(),
                    tenant_id=ctx.tenant_id,
                    transaction_id=tx.id,
                    rule_id=self.rule_id,
                    category=self.category.value,
                    severity=self.severity.value,
                    confidence=0.80,
                    impact_dollars=Decimal(str(float_cost)),
                    impact_pct_of_margin=0.05,
                    description=f"Customer paying 30+ days late — implicit float subsidy.",
                    affected_transaction_ids=[t.transaction_id for t in late_txs],
                    recommendation="Offer early payment discount or tighten payment terms.",
                    recurrence_factor=self.recurrence_factor(tx, ctx)
                )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.65


class R08ReturnToInvoice(BaseRule):
    rule_id = "R-08"
    name = "Return-to-Invoice"
    category = RuleCategory.CUSTOMER_BEHAVIOR
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        customer_txs = ctx.customer_history.get(tx.customer_id, [])
        return_txs = [t for t in customer_txs if float(t.return_qty) > 0]

        if len(return_txs) < 2:
            return None

        for rt in return_txs:
            invoice_price = float(rt.invoice_price)
            credit_price = float(getattr(rt, "credit_price", invoice_price * 0.9))
            if credit_price < invoice_price * 0.85:
                return LeakageFinding(
                    id=uuid4(),
                    tenant_id=ctx.tenant_id,
                    transaction_id=tx.id,
                    rule_id=self.rule_id,
                    category=self.category.value,
                    severity=self.severity.value,
                    confidence=0.85,
                    impact_dollars=Decimal(str(invoice_price - credit_price)),
                    impact_pct_of_margin=0.08,
                    description="Invoiced at one price, credited at a lower standard price.",
                    affected_transaction_ids=[rt.transaction_id],
                    recommendation="Standardize return credit process to match original invoice price.",
                    recurrence_factor=self.recurrence_factor(tx, ctx)
                )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.70


class R09ShortCloseCredit(BaseRule):
    rule_id = "R-09"
    name = "Short-Close Credit"
    category = RuleCategory.CUSTOMER_BEHAVIOR
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        customer_txs = ctx.customer_history.get(tx.customer_id, [])
        close_window = ctx.config.get("R-09", {}).get("params", {}).get("close_window_days", 30)

        late_credits = [
            t for t in customer_txs
            if getattr(t, "credit_days", 999) < close_window
            and float(getattr(t, "return_qty", 0)) > 0
        ]

        if len(late_credits) >= 2:
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.75,
                impact_dollars=Decimal(str(sum(float(t.invoice_price) * 0.05 for t in late_credits))),
                impact_pct_of_margin=0.05,
                description="Credit memos issued after normal close period.",
                affected_transaction_ids=[t.transaction_id for t in late_credits],
                recommendation="Enforce close window policy strictly.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.55


class R10VolumeSpikeGaming(BaseRule):
    rule_id = "R-10"
    name = "Volume Spike Gaming"
    category = RuleCategory.CUSTOMER_BEHAVIOR
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        customer_txs = sorted(ctx.customer_history.get(tx.customer_id, []), key=lambda t: t.date)
        if len(customer_txs) < 4:
            return None

        mid = len(customer_txs) // 2
        first_half = customer_txs[:mid]
        second_half = customer_txs[mid:]

        avg_first = sum(float(t.invoice_price) for t in first_half) / len(first_half)
        avg_second = sum(float(t.invoice_price) for t in second_half) / len(second_half)

        if avg_second > avg_first * 1.50:
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.70,
                impact_dollars=Decimal(str((avg_second - avg_first) * len(second_half) * 0.10)),
                impact_pct_of_margin=0.05,
                description="Customers loading up before price increase, then returning excess.",
                affected_transaction_ids=[t.transaction_id for t in second_half],
                recommendation="Implement pre-order limits and restocking fees.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.50


def get_all_customer_behavior_rules() -> List[BaseRule]:
    return [R06ReturnVelocity(), R07PaymentDrift(), R08ReturnToInvoice(), R09ShortCloseCredit(), R10VolumeSpikeGaming()]
