"""Base rule abstract class and enums."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID


class RuleCategory(str, Enum):
    PRICE_STRUCTURE = "PRICE_STRUCTURE"
    CUSTOMER_BEHAVIOR = "CUSTOMER_BEHAVIOR"
    PRODUCT_MIX = "PRODUCT_MIX"


class Severity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class RuleContext:
    tenant_id: UUID
    all_transactions: List[Any] = field(default_factory=list)
    customer_history: Dict[str, List[Any]] = field(default_factory=dict)
    product_history: Dict[str, List[Any]] = field(default_factory=dict)
    contract_data: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LeakageFinding:
    id: UUID
    tenant_id: UUID
    transaction_id: UUID
    rule_id: str
    category: str
    severity: str
    confidence: float
    impact_dollars: Decimal
    impact_pct_of_margin: float
    description: str
    affected_transaction_ids: List[str]
    recommendation: str
    recurrence_factor: float


class BaseRule(ABC):
    rule_id: str
    name: str
    category: RuleCategory
    severity: Severity

    @abstractmethod
    def detect(self, tx: Any, ctx: RuleContext) -> Optional[LeakageFinding]:
        """Return a Finding if leakage detected, None otherwise."""

    @abstractmethod
    def quantify(self, tx: Any, finding: LeakageFinding) -> Decimal:
        """Calculate dollar impact of this finding."""

    @abstractmethod
    def recurrence_factor(self, tx: Any, ctx: RuleContext) -> float:
        """% of customer's volume likely affected by this pattern."""

    def get_recommendation(self) -> str:
        return f"Review {self.name} — consult the rule definition for remediation steps."
