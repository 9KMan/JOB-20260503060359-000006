"""Pocket Price Waterfall Calculator."""
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Optional
from core.db.models import Transaction


@dataclass
class WaterfallResult:
    list_price: Decimal
    invoice_discounts: Decimal
    net_price: Decimal
    post_invoice_discounts: Decimal
    pocket_price: Decimal
    allowances: Decimal
    gross_margin: Decimal
    cost_price: Decimal

    def to_dict(self) -> dict:
        return {
            "list_price": float(self.list_price),
            "invoice_discounts": float(self.invoice_discounts),
            "net_price": float(self.net_price),
            "post_invoice_discounts": float(self.post_invoice_discounts),
            "pocket_price": float(self.pocket_price),
            "allowances": float(self.allowances),
            "gross_margin": float(self.gross_margin),
            "cost_price": float(self.cost_price),
        }


@dataclass
class DiscountComponent:
    name: str
    amount: Decimal
    discount_type: str


class PocketWaterfallCalculator:
    def calculate(self, tx: Transaction) -> WaterfallResult:
        invoice_discounts = self._sum_invoice_discounts(tx)
        post_invoice_discounts = self._sum_post_invoice_discounts(tx)
        allowances = self._sum_allowances(tx)
        cost_price = self._get_cost_price(tx)

        list_price = tx.list_price
        net_price = list_price - invoice_discounts
        pocket_price = net_price - post_invoice_discounts
        gross_margin = pocket_price - cost_price

        return WaterfallResult(
            list_price=list_price,
            invoice_discounts=invoice_discounts,
            net_price=net_price,
            post_invoice_discounts=post_invoice_discounts,
            pocket_price=pocket_price,
            allowances=allowances,
            gross_margin=gross_margin,
            cost_price=cost_price,
        )

    def _sum_invoice_discounts(self, tx: Transaction) -> Decimal:
        return tx.list_price - tx.invoice_price

    def _sum_post_invoice_discounts(self, tx: Transaction) -> Decimal:
        return tx.invoice_price - tx.net_price

    def _sum_allowances(self, tx: Transaction) -> Decimal:
        return tx.net_price - tx.pocket_price

    def _get_cost_price(self, tx: Transaction) -> Decimal:
        return tx.list_price - tx.gross_margin

    def calculate_batch(self, transactions: List[Transaction]) -> List[WaterfallResult]:
        return [self.calculate(tx) for tx in transactions]

    def aggregate_waterfall(self, results: List[WaterfallResult]) -> dict:
        if not results:
            return {}
        return {
            "total_list_price": sum(r.list_price for r in results),
            "total_invoice_discounts": sum(r.invoice_discounts for r in results),
            "total_net_price": sum(r.net_price for r in results),
            "total_post_invoice_discounts": sum(r.post_invoice_discounts for r in results),
            "total_pocket_price": sum(r.pocket_price for r in results),
            "total_allowances": sum(r.allowances for r in results),
            "total_gross_margin": sum(r.gross_margin for r in results),
            "avg_gross_margin_pct": (
                sum(r.gross_margin for r in results) / sum(r.list_price for r in results) * 100
                if sum(r.list_price for r in results) > 0 else Decimal(0)
            ),
        }


class RetroactiveDiscountEstimator:
    def estimate_clawback(
        self,
        tx: Transaction,
        contract_triggers: List[dict],
        current_period_volume: Decimal,
    ) -> Decimal:
        total_estimate = Decimal(0)
        for trigger in contract_triggers:
            trigger_type = trigger.get("type")
            if trigger_type == "VOLUME_TIER":
                tier = self._get_applicable_tier(trigger, current_period_volume)
                if tier and tier.get("retroactive"):
                    retroactive_base = trigger.get("prior_volume", Decimal(0))
                    rate = tier.get("rate", Decimal(0))
                    clawback = retroactive_base * rate
                    total_estimate += clawback
        return total_estimate

    def _get_applicable_tier(self, trigger: dict, volume: Decimal) -> Optional[dict]:
        tiers = trigger.get("tiers", [])
        applicable = None
        for tier in sorted(tiers, key=lambda t: t.get("threshold", 0), reverse=True):
            if volume >= tier.get("threshold", 0):
                applicable = tier
                break
        return applicable
