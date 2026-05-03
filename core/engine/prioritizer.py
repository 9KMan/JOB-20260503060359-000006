"""Priority scoring algorithm."""
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple
from core.rules.base import LeakageFinding


class Prioritizer:
    SORT_STRATEGIES = {
        "Financial Impact": lambda f: f.impact_dollars,
        "Quick Wins": lambda f: float(f.impact_dollars) * (f.recurrence_factor or 0.5),
        "Risk Reduction": lambda f: float(f.impact_dollars) * (1.0 if f.severity == "HIGH" else 0.5),
        "Balanced": lambda f: float(f.impact_dollars) * (f.recurrence_factor or 0.5) * (0.8 if f.severity == "HIGH" else 1.0),
    }

    def calculate_priority_score(
        self,
        finding: LeakageFinding,
        ease_score: float = 5.0,
    ) -> float:
        impact = float(finding.impact_dollars)
        confidence = finding.confidence or 0.5
        recurrence = finding.recurrence_factor or 0.5
        ease = max(1.0, min(10.0, ease_score)) / 10.0

        score = impact * ease * confidence * (1.0 + recurrence)
        return round(score, 2)

    def rank_findings(
        self,
        findings: List[LeakageFinding],
        ease_scores: Dict[str, float] = None,
        strategy: str = "Balanced",
    ) -> List[Tuple[LeakageFinding, float, str]]:
        ease_scores = ease_scores or {}

        scored = []
        for f in findings:
            ease = ease_scores.get(str(f.id), 5.0)
            score = self.calculate_priority_score(f, ease)
            category = self._classify_priority(score, ease)
            scored.append((f, score, category))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _classify_priority(self, score: float, ease: float) -> str:
        if score >= self._percentile(scored_scores, 0.75) and ease >= 7:
            return "Quick Win"
        elif score >= self._percentile(scored_scores, 0.75):
            return "Strategic"
        elif score >= self._percentile(scored_scores, 0.50):
            return "Nice-to-Have"
        else:
            return "Risk"

    def _percentile(self, values: List[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values, reverse=True)
        idx = int(len(sorted_vals) * pct)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    def get_top_opportunities(
        self,
        findings: List[LeakageFinding],
        ease_scores: Dict[str, float] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        ranked = self.rank_findings(findings, ease_scores)
        opportunities = []
        for rank, (finding, score, category) in enumerate(ranked[:top_n], start=1):
            opportunities.append({
                "rank": rank,
                "name": f"{finding.rule_id}: {finding.description[:50]}",
                "category": finding.category,
                "rule_id": finding.rule_id,
                "severity": finding.severity,
                "impact": float(finding.impact_dollars),
                "ease": ease_scores.get(str(finding.id), 5.0),
                "confidence": finding.confidence,
                "priority_score": score,
                "priority_category": category,
            })
        return opportunities


scored_scores = []
