# SPEC.md — B2B Pricing Diagnostic Tool (PDT)

## 1. Concept & Vision

A **precision pricing intelligence platform** that transforms raw Excel pricing data into a structured diagnostic report — surfacing exactly where margin is leaking, how much it costs, and what to fix first. This is not a generic Excel viewer; it is a **domain expert system** encoded in software: it knows what "pocket margin" means, which rebate structures are retroactive, how to detect a disguised discount buried in a product bundle, and how to rank opportunities by financial impact.

The experience should feel like hiring a world-class pricing analyst who produces a polished MBB-grade deliverable in minutes, not hours.

---

## 2. Design Language

### Aesthetic
- **Professional data intelligence** — Think McKinsey meets Stripe Dashboard. Clean, precise, authoritative.
- Light background with dark navy accents. No decorative elements that distract from data.

### Color Palette
```
--bg-primary:     #FAFBFC   (off-white canvas)
--bg-card:        #FFFFFF   (card surfaces)
--bg-navy:        #0D2137   (header, sidebar)
--accent-blue:    #2563EB   (primary actions, links)
--accent-teal:   #0D9488   (positive metrics, gains)
--accent-red:    #DC2626   (leakage, losses, alerts)
--accent-amber:  #D97706   (warnings, medium risk)
--text-primary:  #111827
--text-secondary:#6B7280
--border:        #E5E7EB
```

### Typography
- **Headings:** Inter (700, 600) — sharp, professional
- **Body/Data:** Inter (400, 500) — highly legible at small sizes for tables
- **Monospace (IDs, code):** JetBrains Mono

### Layout Rhythm
- Sidebar navigation (5 sections)
- Top KPI strip (4 cards) — always visible
- Content area with dense data tables and collapsible detail panels
- Sticky action bars for export buttons

---

## 3. Data Model

### 3.1 Core Domain Objects

```python
class Transaction:
    id: UUID
    tenant_id: UUID
    transaction_id: str          # client's internal ID
    date: date
    customer_id: str
    customer_segment: str
    product_id: str
    product_category: str
    list_price: Decimal
    invoice_price: Decimal       # after invoice discounts
    net_price: Decimal           # after post-invoice rebates → pocket price
    pocket_price: Decimal        # net_price - allowances
    invoice_discounts: List[Discount]
    post_invoice_discounts: List[RetroactiveDiscount]
    margin: Decimal
    return_qty: Decimal
    payment_status: str
    # 14 leakage tags applied post-analysis


class LeakageFinding:
    id: UUID
    tenant_id: UUID
    transaction_id: UUID (FK)
    rule_id: str
    category: str                # PRICE_STRUCTURE | CUSTOMER_BEHAVIOR | PRODUCT_MIX
    severity: HIGH | MEDIUM | LOW
    confidence: float            # 0.0–1.0
    impact_dollars: Decimal
    impact_pct_of_margin: float
    description: str
    affected_rows: List[str]     # transaction IDs
    recommendation: str
    recurrence_factor: float     # 0.0–1.0 (% of volume affected)


class RetroactiveDiscount:
    id: UUID
    tenant_id: UUID
    transaction_id: UUID (FK)
    discount_type: str           # rebate | credit | retroactive_price_adj
    trigger_event: str           # volume_threshold | time_period | contract_clause
    original_amount: Decimal
    retroactive_amount: Decimal  # what was clawed back or should have been
    effective_date: date
    settlement_date: date | None
```

### 3.2 Pocket Price Waterfall

```
Invoice Price (List Price - Invoice Discounts)
    │
    ├── [Invoice Discounts: early payment, volume, promo]
    │
    ▼
Net Invoice Price
    │
    ├── [Post-Invoice Rebates: retroactive volume, GPR, contract clawbacks]
    │
    ▼
Pocket Price
    │
    ├── [Allowances: off-invoice allowances, slotting fees]
    │
    ▼
Gross Margin
```

**Key rule:** Post-invoice rebates are **retroactive**. A transaction that looks profitable at invoice time may have a clawback weeks later. The tool models this by:
1. Flagging transactions with open (unsettled) retroactive discount triggers
2. Estimating expected clawback based on current period performance vs. contract thresholds
3. Showing "realized pocket price" vs. "invoice price" delta

### 3.3 Database Schema (SQLAlchemy)

```sql
-- Multi-tenant: ALL tables have tenant_id
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR,
    plan VARCHAR,               -- starter | professional | enterprise
    created_at TIMESTAMPTZ
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    transaction_id VARCHAR,    -- client's ID, unique per tenant
    date DATE,
    customer_id VARCHAR,
    customer_segment VARCHAR,
    product_id VARCHAR,
    product_category VARCHAR,
    list_price DECIMAL(18,4),
    invoice_price DECIMAL(18,4),
    net_price DECIMAL(18,4),
    pocket_price DECIMAL(18,4),
    gross_margin DECIMAL(18,4),
    return_qty DECIMAL(18,4),
    payment_status VARCHAR,
    raw_data JSONB,            -- original Excel row as JSON for audit
    created_at TIMESTAMPTZ
);

CREATE TABLE leakage_findings (
    id UUID PRIMARY KEY,
    tenant_id UUID REFERENCES tenants(id),
    transaction_id UUID REFERENCES transactions(id),
    rule_id VARCHAR,
    category VARCHAR,
    severity VARCHAR,
    confidence DECIMAL(4,3),
    impact_dollars DECIMAL(18,2),
    impact_pct_of_margin DECIMAL(6,4),
    description TEXT,
    affected_transaction_ids JSONB,
    recommendation TEXT,
    recurrence_factor DECIMAL(4,3),
    created_at TIMESTAMPTZ
);

CREATE TABLE leakage_rules (
    id VARCHAR PRIMARY KEY,      -- e.g., "RULE-001"
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR,
    category VARCHAR,
    config YAML,                -- thresholds, conditions
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ
);

CREATE INDEX idx_transactions_tenant_date ON transactions(tenant_id, date);
CREATE INDEX idx_findings_tenant_severity ON leakage_findings(tenant_id, severity);
```

---

## 4. The 14 Leakage Rules (Domain Model)

Each rule is a **Python class** that inherits from `BaseRule`. Rules are loaded from `config/leakage_rules.yaml` at startup. This makes thresholds client-configurable without code changes.

```python
class BaseRule(ABC):
    rule_id: str
    name: str
    category: RuleCategory      # PRICE_STRUCTURE | CUSTOMER_BEHAVIOR | PRODUCT_MIX
    severity: Severity

    @abstractmethod
    def detect(self, tx: Transaction, ctx: RuleContext) -> Finding | None:
        """Return a Finding if leakage detected, None otherwise."""

    @abstractmethod
    def quantify(self, tx: Transaction, finding: Finding) -> Decimal:
        """Calculate dollar impact of this finding."""

    @abstractmethod
    def recurrence_factor(self, tx: Transaction, ctx: RuleContext) -> float:
        """% of customer's volume likely affected by this pattern."""
```

### Category: PRICE_STRUCTURE (How We Set Prices)

| Rule ID | Name | What it Detects |
|---------|------|----------------|
| R-01 | Undiscounted Baseline | Products never sold at list price — entire price book may be discounted |
| R-02 | Disguised Bundle Discount | Bundle SKU priced below sum of components — hidden discount |
| R-03 | Anchor Price Drift | Current prices never updated relative to cost increases |
| R-04 | Segment Bleed | Enterprise discounts applied to mid-market customers |
| R-05 | Retroactive Cliff | Volume rebate triggers retroactively change pocket price with no notice |

### Category: CUSTOMER_BEHAVIOR (How Customers React)

| Rule ID | Name | What it Detects |
|---------|------|----------------|
| R-06 | Return Velocity | Same customer returns >10% of purchases (inventory gaming) |
| R-07 | Payment Drift | Customers paying 30+ days late — implicit float subsidy |
| R-08 | Return-to-Invoice | Invoiced at one price, credited at a lower "standard" price |
| R-09 | Short-Close Credit | Credit memos issued after normal close period |
| R-10 | Volume Spike Gaming | Customers loading up before price increase, then returning excess |

### Category: PRODUCT_MIX (What We're Selling)

| Rule ID | Name | What it Detects |
|---------|------|----------------|
| R-11 | High-Return SKU | Specific SKUs with >15% return rate — margin erosion |
| R-12 | Zombie Product | Products with zero margin still in price book |
| R-13 | Mix Shift Erosion | Shift toward lower-margin categories not reflected in price |
| R-14 | Promotional Dependency | Same product always sold on promo — baseline price is artificial |

### Confidence Scoring

Each rule returns a confidence score (0.0–1.0):
- **HIGH (≥0.85):** Rule condition clearly met, data quality confirmed
- **MEDIUM (0.60–0.84):** Rule condition met but data quality or boundary issues
- **LOW (<0.60):** Weak signal, needs human judgment

---

## 5. Streamlit UI Architecture

### App Structure

```
streamlit_app.py              # Entry point, session state, auth
├── config/
│   └── settings.yaml         # Tenant config, model settings
├── core/
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── validator.py      # Layer 1/2/3 validation engine
│   │   ├── pocket_waterfall.py
│   │   ├── leakage_engine.py # Runs all 14 rules
│   │   ├── prioritizer.py    # Priority scoring algorithm
│   │   └── anonymizer.py     # PII scrubbing before AI calls
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseRule ABC
│   │   ├── price_structure/  # R-01 to R-05
│   │   ├── customer_behavior/ # R-06 to R-10
│   │   └── product_mix/       # R-11 to R-14
│   ├── reporting/
│   │   ├── excel_report.py   # openpyxl branded Excel export
│   │   └── pptx_report.py    # python-pptx MBB slides (Option B)
│   ├── db/
│   │   ├── models.py         # SQLAlchemy models
│   │   ├── session.py        # SessionFactory
│   │   └── migrations/       # Alembic migrations
│   └── anonymizer.py
├── pages/
│   ├── 1_📊_Dashboard.py     # KPI overview + waterfall
│   ├── 2_🔍_Leakage_Scan.py  # Full 14-rule scan + findings
│   ├── 3_📋_Rule_Details.py  # Drill into individual rules
│   ├── 4_🎯_Prioritizer.py   # Sortable/filterable opportunity list
│   └── 5_📥_Reports.py       # Download center
├── tests/
│   ├── test_rules.py         # Unit test each rule
│   ├── test_waterfall.py     # Waterfall calculations
│   └── test_integration.py   # End-to-end with synthetic data
└── requirements.txt
```

### Page: Dashboard (1_📊_Dashboard.py)

**Layout:**
- Top: 4 KPI cards (Gross Margin %, Pocket Price vs. Invoice Price Δ, # Leakages Found, Total $ at Risk)
- Middle: Pocket Price Waterfall chart (bar chart, side-by-side before/after)
- Bottom: Top 5 leakage categories by $ impact (horizontal bar)

**Behavior:**
- KPIs load with animated counter from 0 to final value
- Waterfall chart interactive: hover shows breakdown
- "Run Full Scan" button → triggers leakage_engine → streams results to Leakage Scan page

### Page: Leakage Scan (2_🔍_Leakage_Scan.py)

**Layout:**
- Left sidebar: Rule filter (category, severity, min_impact)
- Main area: Findings table (sortable by $, severity, confidence)
- Each row: Rule ID | Category badge | Severity pill | $ Impact | Confidence | Expand chevron

**Expanded row:**
- Full description of the leakage pattern
- List of affected transactions (customer_id masked → `CUST-001`, etc.)
- Recommendation text (human-written per rule, not AI-generated in Option A)
- "Mark as Reviewed" / "Dismiss" buttons

**Behavior:**
- Results stream in as each rule completes (not all-at-once)
- Filter state persists in `session_state`
- Export filtered results to CSV

### Page: Rule Details (3_📋_Rule_Details.py)

**Layout:**
- Rule selector dropdown (R-01 through R-14)
- Left: Rule definition + logic description
- Right: Affected transactions table (full detail)
- Below: Historical trend chart (if tenant has prior period data)

### Page: Prioritizer (4_🎯_Prioritizer.py)

**Layout:**
- Strategy selector: Financial Impact | Quick Wins | Risk Reduction | Balanced
- Sortable table: Rank | Opportunity | Category | $ Impact | Ease Score | Confidence | Priority Score
- "Ease" = 1–10 self-assessment input per finding

**Priority Algorithm:**
```
Priority Score = ($ Impact) × (Ease/10) × Confidence × (1 + Recurrence_Factor)

Sort order:
  1. Quick Wins:     Priority ≥ 75th percentile AND Ease ≥ 7
  2. Strategic:      Priority ≥ 75th percentile AND Ease < 7
  3. Nice-to-Have:   Priority 50–75th percentile
  4. Risk:           Priority < 50th percentile (regardless of ease)
```

### Page: Reports (5_📥_Reports.py)

**Layout:**
- "Download Excel Report" button → generates branded .xlsx
- "Download PowerPoint" button (Option B only) → generates .pptx
- Preview panel showing first 3 slides / sheet thumbnails

**Excel Report Structure (3 sheets):**
```
Sheet 1 — Executive Summary
  Logo + date + tenant name
  4 KPI cards (same as dashboard)
  Pocket Price Waterfall table
  Top 10 Opportunities table

Sheet 2 — Leakage Catalog
  All 14 rules with finding counts and $ impact
  Severity breakdown chart

Sheet 3 — Action Plan
  Prioritized list with owner, estimated effort, expected return
```

---

## 6. Pocket Waterfall — Implementation Detail

### Data Flow

```
Raw Excel
    ↓
Layer 1 Validator (structure)
    ↓
Parser → List[Transaction]
    ↓
Retroactive Discount Tracker
    ↓
Pocket Waterfall Calculator
    ↓
Transaction with pocket_price, net_price, gross_margin
    ↓
Leakage Engine (14 rules run in parallel)
    ↓
List[Finding]
    ↓
Prioritizer
    ↓
Report Generator
```

### Waterfall Calculation

```python
def calculate_waterfall(tx: Transaction) -> WaterfallResult:
    invoice_discounts = sum(d.amount for d in tx.invoice_discounts)
    post_invoice_discounts = sum(d.amount for d in tx.post_invoice_discounts)
    allowances = sum(a.amount for a in tx.allowances)

    net_price = tx.list_price - invoice_discounts
    pocket_price = net_price - post_invoice_discounts
    gross_margin = pocket_price - tx.cost_price

    return WaterfallResult(
        list_price=tx.list_price,
        invoice_discounts=invoice_discounts,
        net_price=net_price,
        post_invoice_discounts=post_invoice_discounts,
        pocket_price=pocket_price,
        allowances=allowances,
        gross_margin=gross_margin
    )
```

### Retroactive Discount Handling

Retroactive discounts aren't known at invoice time. They emerge when:
1. A customer hits a volume threshold (quarterly, annually)
2. A contract anniversary triggers a GPR (guaranteed price review)
3. A promotional period ends and pre-negotiated clawbacks apply

```python
class RetroactiveDiscountEstimator:
    def estimate_clawback(
        self,
        tx: Transaction,
        contract: Contract,
        current_period_volume: Decimal
    ) -> Decimal:
        """Estimate expected retroactive adjustment based on contract terms."""

        triggers = contract.get_active_triggers()

        total_estimate = Decimal(0)
        for trigger in triggers:
            if trigger.type == VOLUME_TIER:
                tier = trigger.get_applicable_tier(current_period_volume)
                if tier and tier.retroactive:
                    # Apply retroactive rate to all prior transactions
                    retroactive_base = trigger.get_prior_volume(tx.date)
                    clawback = retroactive_base * tier.rate
                    total_estimate += clawback

        return total_estimate
```

---

## 7. Anonymization Layer

Before any data goes to Claude API, **all PII is scrubbed**:

```python
# Implemented before ANY AI call
from core.anonymizer import Anonymizer

anonymizer = Anonymizer(tenant_id)

# Scrub transaction data
safe_tx = anonymizer.scrub(tx)
safe_tx_list = anonymizer.scrub_batch(transaction_list)

# Reversible: store mapping separately per tenant
mapping = anonymizer.get_mapping()  # {CUST-001: real_customer_id}
# Mapping stored encrypted in tenant-specific DB table
```

Claude API calls receive only: `CUST-001`, `PROD-001`, `SEGMENT-A` — never real names.

---

## 8. Configuration (leakage_thresholds.yaml)

```yaml
tenant_id: "<dynamic>"

rules:
  R-01:
    enabled: true
    params:
      min_discount_to_trigger: 0.05   # 5% minimum discount to count as "discounted"
      lookback_periods: 12            # months to analyze

  R-06:
    enabled: true
    params:
      return_rate_threshold: 0.10      # 10% return rate = suspicious
      min_transaction_value: 1000

  R-07:
    enabled: true
    params:
      late_days_threshold: 30
      min_open_invoice_value: 5000

  # ... all 14 rules fully parameterized
```

---

## 9. Option A vs Option B Scope

### Option A (~$20K / 123–176 hrs)
- Streamlit UI with Excel upload
- 14 leakage rules (fully configured)
- Pocket waterfall calculation
- Basic prioritizer
- Excel export (3-sheet branded)
- SQLite database (single-tenant MVP)
- No AI executive reports
- No PPTX

### Option B (~$35K / 218–311 hrs)
- Everything in Option A, plus:
- Multi-tenant with SQLAlchemy ORM + PostgreSQL
- Layer 2 & 3 validation engine
- Historical trend analysis (prior period comparison)
- PowerPoint export (12–15 MBB-style slides)
- **Claude API executive summary** — AI generates 1-page narrative per finding:
  ```
  "Based on our analysis of 3,247 transactions across 89 customers,
   the most significant margin leakage is in R-05 (Retroactive Cliff),
   concentrated in the pharmaceutical segment. We recommend renegotiating
   GPR clauses before Q3 contract renewals to lock in floor prices..."
  ```
- RBAC (analyst vs. admin roles)
- Data refresh scheduling

---

## 10. Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | Excel upload → validation errors < 5s for 10K rows | Performance test |
| 2 | All 14 rules detect pre-injected synthetic leakages | Unit test per rule |
| 3 | $ impact within 5% of ground truth per rule | Synthetic data benchmark |
| 4 | Quick Wins sorted to top by priority algorithm | Integration test |
| 5 | Excel report: 3 sheets, correct branding, correct totals | Visual + automated check |
| 6 | `tenant_id` present in ALL database writes | Code review + integration test |
| 7 | Claude API calls contain zero PII | Automated regex scan of anonymizer output |
| 8 | All pytest tests pass | `pytest -v` |
| 9 | Option B: PPTX has ≥12 slides, MBB structure | Automated slide count |
| 10 | Option B: AI narrative references specific $ amounts and segments | Integration test |

---

## 11. File Structure (Delivered Code)

```
/
├── streamlit_app.py
├── config/
│   └── leakage_thresholds.yaml
├── core/
│   ├── __init__.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── validator.py
│   │   ├── pocket_waterfall.py
│   │   ├── leakage_engine.py
│   │   ├── prioritizer.py
│   │   └── anonymizer.py
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── price_structure.py      # R-01..R-05
│   │   ├── customer_behavior.py     # R-06..R-10
│   │   └── product_mix.py          # R-11..R-14
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── excel_report.py
│   │   └── pptx_report.py          # Option B
│   └── db/
│       ├── __init__.py
│       ├── models.py
│       └── session.py
├── pages/
│   ├── 1_\U0001F4CA_Dashboard.py
│   ├── 2_\U0001F50D_Leakage_Scan.py
│   ├── 3_\U0001F4CB_Rule_Details.py
│   ├── 4_\U0001F3AF_Prioritizer.py
│   └── 5_\U0001F4E5_Reports.py
├── tests/
│   ├── __init__.py
│   ├── test_rules.py
│   ├── test_waterfall.py
│   ├── test_prioritizer.py
│   └── test_integration.py
├── Dockerfile
├── docker-compose.yml              # Option B multi-service
├── requirements.txt
├── .env.example
└── README.md
```
