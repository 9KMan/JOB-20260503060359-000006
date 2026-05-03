"""Product Mix Rules (R-11 through R-14)."""
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4

from core.rules.base import BaseRule, RuleCategory, Severity, RuleContext, LeakageFinding


class R11HighReturnSKU(BaseRule):
    rule_id = "R-11"
    name = "High-Return SKU"
    category = RuleCategory.PRODUCT_MIX
    severity = Severity.HIGH

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        threshold = ctx.config.get("R-11", {}).get("params", {}).get("return_rate_threshold", 0.15)

        product_txs = ctx.product_history.get(tx.product_id, [])
        if len(product_txs) < 5:
            return None

        total_qty = sum(float(getattr(t, "qty", 1)) for t in product_txs)
        return_qty = sum(float(t.return_qty) for t in product_txs)
        return_rate = return_qty / total_qty if total_qty > 0 else 0

        if return_rate >= threshold:
            total_value = sum(float(t.invoice_price) for t in product_txs)
            margin_erosion = total_value * return_rate * 0.40
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.85,
                impact_dollars=Decimal(str(margin_erosion)),
                impact_pct_of_margin=return_rate * 0.5,
                description=f"SKU {tx.product_id} with {return_rate:.1%} return rate — margin erosion.",
                affected_transaction_ids=[t.transaction_id for t in product_txs if float(t.return_qty) > 0],
                recommendation="Discontinue or reprice high-return SKUs.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.85


class R12ZombieProduct(BaseRule):
    rule_id = "R-12"
    name = "Zombie Product"
    category = RuleCategory.PRODUCT_MIX
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        margin = float(tx.gross_margin) / float(tx.list_price) if float(tx.list_price) > 0 else 0

        if margin <= 0.01:
            product_txs = ctx.product_history.get(tx.product_id, [])
            if len(product_txs) > 10:
                return LeakageFinding(
                    id=uuid4(),
                    tenant_id=ctx.tenant_id,
                    transaction_id=tx.id,
                    rule_id=self.rule_id,
                    category=self.category.value,
                    severity=self.severity.value,
                    confidence=0.78,
                    impact_dollars=Decimal(str(sum(float(t.invoice_price) * 0.02 for t in product_txs))),
                    impact_pct_of_margin=0.02,
                    description=f"Product {tx.product_id} with zero margin still in price book.",
                    affected_transaction_ids=[tx.transaction_id],
                    recommendation="Reprice or remove zombie products from active price book.",
                    recurrence_factor=self.recurrence_factor(tx, ctx)
                )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return tx.invoice_price * Decimal("0.02")

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.90


class R13MixShiftErosion(BaseRule):
    rule_id = "R-13"
    name = "Mix Shift Erosion"
    category = RuleCategory.PRODUCT_MIX
    severity = Severity.MEDIUM

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        category = tx.product_category
        all_txs = ctx.all_transactions

        category_txs = [t for t in all_txs if t.product_category == category]
        if len(category_txs) < 20:
            return None

        current_margin = sum(float(t.gross_margin) for t in category_txs) / sum(float(t.list_price) for t in category_txs)
        prior_margin = ctx.config.get("prior_margins", {}).get(category, current_margin)

        if current_margin < prior_margin * 0.90:
            shift_pct = (prior_margin - current_margin) / prior_margin
            return LeakageFinding(
                id=uuid4(),
                tenant_id=ctx.tenant_id,
                transaction_id=tx.id,
                rule_id=self.rule_id,
                category=self.category.value,
                severity=self.severity.value,
                confidence=0.72,
                impact_dollars=Decimal(str(sum(float(t.invoice_price) for t in category_txs) * shift_pct * 0.3)),
                impact_pct_of_margin=shift_pct,
                description="Shift toward lower-margin categories not reflected in price.",
                affected_transaction_ids=[t.transaction_id for t in category_txs],
                recommendation="Reprice category or shift mix toward higher-margin products.",
                recurrence_factor=self.recurrence_factor(tx, ctx)
            )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.65


class R14PromotionalDependency(BaseRule):
    rule_id = "R-14"
    name = "Promotional Dependency"
    category = RuleCategory.PRODUCT_MIX
    severity = Severity.LOW

    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        product_txs = ctx.product_history.get(tx.product_id, [])
        if len(product_txs) < 10:
            return None

        promo_txs = [t for t in product_txs if getattr(t, "is_promo", False)]
        non_promo_txs = [t for t in product_txs if not getattr(t, "is_promo", False)]

        if len(promo_txs) / len(product_txs) >= 0.70 and len(non_promo_txs) > 0:
            avg_non_promo_price = sum(float(t.invoice_price) for t in non_promo_txs) / len(non_promo_txs)
            avg_promo_price = sum(float(t.invoice_price) for t in promo_txs) / len(promo_txs)
            discount_pct = (avg_non_promo_price - avg_promo_price) / avg_non_promo_price

            if discount_pct > 0.15:
                return LeakageFinding(
                    id=uuid4(),
                    tenant_id=ctx.tenant_id,
                    transaction_id=tx.id,
                    rule_id=self.rule_id,
                    category=self.category.value,
                    severity=self.severity.value,
                    confidence=0.68,
                    impact_dollars=Decimal(str(sum(float(t.invoice_price) for t in promo_txs) * discount_pct * 0.5)),
                    impact_pct_of_margin=discount_pct * 0.5,
                    description="Same product always sold on promo — baseline price is artificial.",
                    affected_transaction_ids=[t.transaction_id for t in promo_txs],
                    recommendation="Establish a sustainable non-promo price point.",
                    recurrence_factor=self.recurrence_factor(tx, ctx)
                )
        return None

    def quantify(self, tx: Any, finding: Optional[LeakageFinding]) -> Decimal:
        return Decimal(str(finding.impact_dollars)) if finding else Decimal(0)

    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        return 0.80


def get_all_product_mix_rules() -> List[BaseRule]:
    return [R11HighReturnSKU(), R12ZombieProduct(), R13MixShiftErosion(), R14PromotionalDependency()]
