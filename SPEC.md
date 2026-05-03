# SPEC.md — B2B Pricing Diagnostic Tool

## 1. Project Overview

**Project Name:** Pricing Diagnostic Tool (PDT)
**What it does:** Web-based tool that analyzes client Excel pricing data, detects margin leakage patterns, quantifies financial impact, and generates prioritized remediation reports.
**Client:** B2B Pricing SaaS — targeting LATAM mid-market ($5M-$50M revenue)
**Budget:** $50-100/hr (Option A: ~123-176 hrs, Option B: ~218-311 hrs)
**GitHub Repo:** https://github.com/9KMan/JOB-20260503060359-000006

## 2. Technical Stack

- **Language:** Python 3.11+
- **UI Framework:** Streamlit (production-grade, multi-tab)
- **Data Processing:** pandas, numpy, scipy
- **Excel I/O:** openpyxl (multi-sheet, branded formatting)
- **Presentation:** python-pptx (Option B)
- **AI Integration:** Anthropic Claude API (Option B executive reports)
- **ORM:** SQLAlchemy (all DB access)
- **Testing:** pytest
- **Config:** YAML-based rule thresholds

## 3. Architecture

```
streamlit_app.py (main entry point)
├── pages/
│   ├── 1_Upload_Validate.py
│   ├── 2_KPI_Waterfall.py      # Option B
│   ├── 3_Leakage_Detection.py
│   ├── 4_Prioritizer.py
│   └── 5_Reports.py
├── core/
│   ├── validators/             # Layer 1/2/3 validation
│   ├── engine/                 # Leakage rules, quantifier, prioritizer, waterfall
│   ├── reporting/              # Excel + PPTX generation
│   ├── db/                    # SQLAlchemy models (tenant_id in ALL)
│   └── anonymizer.py          # AI prompt PII removal
├── config/
│   └── leakage_thresholds.yaml
├── tests/
└── requirements.txt
```

## 4. Core Features

### 4.1 Excel Validation Engine
- Layer 1: Structural (sheets, columns, version)
- Layer 2: Data integrity (types, ranges, referential) — Option B
- Layer 3: Business coherence — Option B

### 4.2 Pocket Price Waterfall
```
Invoice Price
  - Invoice Discounts → Net Price
  - Post-Invoice Rebates → Pocket Price
  - Allowances → Gross Margin
```
Post-invoice rebates are retroactive. Transaction ledger tracks stage (invoice vs. post_invoice).

### 4.3 Leakage Detection (14 Rules)
Configurable YAML thresholds. Each rule returns: detected rows, $ impact, confidence (HIGH/MEDIUM/LOW), recurrence.

### 4.4 Priority Score
```
Priority = Impact × Ease × Confidence × (1 + Recurrence_Factor)
```
Categorized: Quick Wins, Strategic, Nice-to-Have, Risk.

### 4.5 Reporting
- Excel: 3-sheet (Summary, Leakages Catalog, Top-10 Opportunities)
- PowerPoint: 12-15 slides MBB-style + Claude API narrative (Option B)

## 5. Architectural Patterns (Required Both Options)

1. tenant_id in all data structures
2. Strict core/app separation
3. SQLAlchemy ORM for all DB access
4. Anonymization layer for AI prompts

## 6. Acceptance Criteria

1. Excel upload → validation errors < 5 seconds
2. All 14 rules detect pre-injected leakages in synthetic dataset
3. $ impact within 5% of ground truth
4. Quick Wins appear first in priority ranking
5. Excel report with correct branding + 3 sheets
6. tenant_id present in all data structures
7. All DB access via SQLAlchemy ORM
8. Claude API calls contain no PII
9. All pytest tests pass
