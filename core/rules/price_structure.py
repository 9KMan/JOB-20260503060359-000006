"""Price Structure Rules (R-01 through R-05)."""
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from core.rules.base import BaseRule, RuleCategory, Severity, RuleContext, LeakageFinding


class R01UndiscountedBaseline(BaseRule):
    rule_id = "R-01"
    name = "Undiscounted Baseline"
    category = RuleCategory.PRICE_STRUCTURE
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        discount_pct = 1 - (float(tx.invoice_price) / float(tx.list_price)) if float(tx.list_price) > 0 else 0
        threshold = ctx.config.get("R-01", {}).get("params", {}).get("min_discount_to_trigger", 0.05)

        if discount_pct < threshold:
            return None

        product_txs = ctx.product_history.get(tx.product_id, [])
        undiscounted_count = sum(
            1 for t in product_txs
            if (float(t.list_price) - float(t.invoice_price)) / float(t.list_price) < threshold
        )
        total_count = len(product_txs)

        if total_count > 0 and undiscounted_count / total_count < 0.1:
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.90 if undiscounted_count == 0 else 0.75,
                impact_dollars=self.quantify(tx, None),
                impact_pct_of_margin=0.05,
                description=f"Product {tx.product_id} never sold at list price. Entire price book may be discounted.",
                affected_transaction_ids=[tx.transaction_id],
                recommendation="Audit price book — ensure list price reflects value, not just historical discounting.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return (tx.list_price - tx.invoice_price) * Decimal("0.05")

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 1.0


class R02DisguisedBundleDiscount(BaseRule):
    rule_id = "R-02"
    name = "Disguised Bundle Discount"
    category = RuleCategory.PRICE_STRUCTURE
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        bundle_components = ctx.config.get("bundles", {}).get(tx.product_id, [])
        if not bundle_components:
            return None

        component_prices = [
            next((float(t.invoice_price) for t in ctx.product_history.get(pid, []) if t.product_id == pid), 0)
            for pid in bundle_components
        ]
        if not component_prices:
            return None

        sum_components = sum(component_prices)
        bundle_price = float(tx.invoice_price)
        discount = sum_components - bundle_price

        if discount / sum_components > 0.10:
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.88,
                impact_dollars=Decimal(str(discount)),
                impact_pct_of_margin=discount / sum_components,
                description=f"Bundle SKU priced {discount/sum_components:.1%} below sum of components — hidden discount.",
                affected_transaction_ids=[tx.transaction_id],
                recommendation="Unbundle pricing or align bundle price with component sum.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.80


class R03AnchorPriceDrift(BaseRule):
    rule_id = "R-03"
    name = "Anchor Price Drift"
    category = RuleCategory.PRICE_STRUCTURE
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        lookback = ctx.config.get("R-03", {}).get("params", {}).get("lookback_periods", 12)
        product_txs = sorted(ctx.product_history.get(tx.product_id, []), key=lambda t: t.date)

        if len(product_txs) < lookback:
            return None

        recent_txs = product_txs[-lookback:]
        earliest = recent_txs[0]
        latest = recent_txs[-1]

        cost_change_pct = 0.0
        price_change_pct = 0.0

        if float(earliest.list_price) > 0:
            price_change_pct = (float(latest.list_price) - float(earliest.list_price)) / float(earliest.list_price)

        if price_change_pct < 0.02 and cost_change_pct > 0.10:
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.72,
                impact_dollars=self.quantify(tx, None),
                impact_pct_of_margin=0.03,
                description="Current prices never updated relative to cost increases. Anchor price stale.",
                affected_transaction_ids=[tx.transaction_id],
                recommendation="Update anchor prices to reflect current cost structure.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return tx.invoice_price * Decimal("0.03")

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.60


class R04SegmentBleed(BaseRule):
    rule_id = "R-04"
    name = "Segment Bleed"
    category = RuleCategory.PRICE_STRUCTURE
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        enterprise_segments = ctx.config.get("segments", {}).get("enterprise", ["Enterprise", "Enterprise A"])
        midmarket_segments = ctx.config.get("segments", {}).get("midmarket", ["Mid-Market", "MidMarket"])

        if tx.customer_segment in enterprise_segments:
            customer_txs = ctx.customer_history.get(tx.customer_id, [])
            midmarket_discounts = [
                t for t in customer_txs
                if t.customer_segment in midmarket_segments
            ]
            if len(midmarket_discounts) > 0:
                avg_discount = sum(float(t.list_price) - float(t.invoice_price) for t in midmarket_discounts) / len(midmarket_discounts)
                if avg_discount > 0.15:
                    return LeakageFinding(
                        id=uuid4(),
                        tenant_id=ctx.tenant_id,
                        transaction_id=tx.id,
                        rule_id=self.rule_id,
                        category=self.category.value,
                        severity=self.severity.value,
                        confidence=0.85,
                        impact_dollars=self.quantify(tx, None),
                        impact_pct_of_margin=avg_discount,
                        description="Enterprise discounts applied to mid-market customers — segment bleed detected.",
                        affected_transaction_ids=[t.transaction_id for t in midmarket_discounts],
                        recommendation="Enforce segment-specific pricing guards.",
                        recurrence_factor=self.recurrence_factor(tx, ctx)
                    )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return tx.invoice_price * Decimal("0.15")

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.70


class R05RetroactiveCliff(BaseRule):
    rule_id = "R-05"
    name = "Retroactive Cliff"
    category = RuleCategory.PRICE_STRUCTURE
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        triggers = ctx.contract_data.get(tx.customer_id, {}).get("active_triggers", [])
        retroactive_triggers = [t for t in triggers if t.get("retroactive", False)]

        if not retroactive_triggers:
            return None

        for trigger in retroactive_triggers:
            if trigger.get("type") == "VOLUME_TIER":
                tier = trigger.get("applicable_tier")
                if tier:
                    clawback = float(tx.invoice_price) * float(tier.get("rate", 0))
                    if clawback > 500:
                        return LeakageFinding(
                            id=uuid4(),
                            tenant_id=ctx.tenant_id,
                            transaction_id=tx.id,
                            rule_id=self.rule_id,
                            category=self.category.value,
                            severity=self.severity.value,
                            confidence=0.92,
                            impact_dollars=Decimal(str(clawback)),
                            impact_pct_of_margin=0.10,
                            description="Volume rebate triggers retroactively change pocket price with no notice.",
                            affected_transaction_ids=[tx.transaction_id],
                            recommendation="Renegotiate GPR clauses before Q3 contract renewals to lock in floor prices.",
                            recurrence_factor=self.recurrence_factor(tx, ctx)
                        )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.90


def get_all_price_structure_rules() -> List[BaseRule]:
    return [R01UndiscountedBaseline(), R02DisguisedBundleDiscount(), R03AnchorPriceDrift(), R04SegmentBleed(), R05RetroactiveCliff()]
