"""SQLAlchemy database models for PDT."""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Boolean, DECIMAL, DateTime, Date,
    ForeignKey, Index, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    plan = Column(String(50), default="starter")
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="tenant")
    leakage_findings = relationship("LeakageFinding", back_populates="tenant")
    leakage_rules = relationship("LeakageRule", back_populates="tenant")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    transaction_id = Column(String(255), nullable=False)
    date = Column(Date, nullable=False)
    customer_id = Column(String(255), nullable=False)
    customer_segment = Column(String(100))
    product_id = Column(String(255), nullable=False)
    product_category = Column(String(100))
    list_price = Column(DECIMAL(18, 4), nullable=False)
    invoice_price = Column(DECIMAL(18, 4), nullable=False)
    net_price = Column(DECIMAL(18, 4), nullable=False)
    pocket_price = Column(DECIMAL(18, 4), nullable=False)
    gross_margin = Column(DECIMAL(18, 4), nullable=False)
    return_qty = Column(DECIMAL(18, 4), default=Decimal(0))
    payment_status = Column(String(50))
    raw_data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="transactions")
    leakage_findings = relationship("LeakageFinding", back_populates="transaction")

    __table_args__ = (
        Index("idx_transactions_tenant_date", "tenant_id", "date"),
    )


class LeakageFinding(Base):
    __tablename__ = "leakage_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"))
    rule_id = Column(String(50), nullable=False)
    category = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    confidence = Column(DECIMAL(4, 3), nullable=False)
    impact_dollars = Column(DECIMAL(18, 2), nullable=False)
    impact_pct_of_margin = Column(DECIMAL(6, 4))
    description = Column(Text)
    affected_transaction_ids = Column(JSON)
    recommendation = Column(Text)
    recurrence_factor = Column(DECIMAL(4, 3))
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="leakage_findings")
    transaction = relationship("Transaction", back_populates="leakage_findings")

    __table_args__ = (
        Index("idx_findings_tenant_severity", "tenant_id", "severity"),
    )


class LeakageRule(Base):
    __tablename__ = "leakage_rules"

    id = Column(String(50), primary_key=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True)
    name = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    config = Column(JSON)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="leakage_rules")


class RetroactiveDiscount(Base):
    __tablename__ = "retroactive_discounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id"), nullable=False)
    discount_type = Column(String(50))
    trigger_event = Column(String(100))
    original_amount = Column(DECIMAL(18, 4))
    retroactive_amount = Column(DECIMAL(18, 4))
    effective_date = Column(Date)
    settlement_date = Column(Date, nullable=True)

    tenant = relationship("Tenant")
    transaction = relationship("Transaction")


class AnonymizedMapping(Base):
    __tablename__ = "anonymized_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    entity_type = Column(String(50))
    original_id = Column(String(255))
    anonymized_id = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
