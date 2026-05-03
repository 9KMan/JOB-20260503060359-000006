# PROPOSAL — B2B Pricing Diagnostic Tool

## 1. Concrete Example of Similar Python Data Product

**AI Data Cleaning Automation Tool** — https://github.com/9KMan/JOB-20260503022550-freelancer

Built a Streamlit-based data cleaning tool that:
- Accepts Excel/CSV uploads via drag-and-drop
- Runs a pipeline of cleaning rules (text normalization, numeric outlier detection, deduplication)
- Displays a cleaning report with before/after metrics
- Generates a downloadable cleaned Excel file
- Uses pandas for data processing and openpyxl for Excel output
- YAML-configurable cleaning thresholds

This demonstrates: Streamlit production-grade UX, pandas data pipelines, Excel I/O, configurable rule engine, and downloadable report generation — all core requirements for the Pricing Diagnostic Tool.

---

## 2. Pocket Price Waterfall Implementation

**The core challenge:** Invoice discounts are applied at the moment of sale. Post-invoice rebates are applied retrospectively (e.g., quarterly retro rebates, annual volume rebates). These behave differently in a waterfall.

**Implementation approach:**

```
Transaction Ledger (per transaction):
  ├── transaction_id
  ├── base_price
  ├── invoice_discount_pct     (applied immediately)
  ├── invoice_discount_amt    (calculated)
  ├── post_invoice_rebates[]  (list of retroactive adjustments)
  │   ├── rebate_type          (quarterly_volume | annual | promotional)
  │   ├── rebate_pct
  │   └── rebate_amt
  └── pocket_price            (calculated)
```

**Waterfall calculation (in order):**

```python
def calculate_waterfall(transaction):
    # Step 1: Apply invoice discounts
    net_price = transaction.base_price * (1 - transaction.invoice_discount_pct)

    # Step 2: Apply post-invoice rebates (retrospective, per period)
    pocket_price = net_price
    for rebate in transaction.post_invoice_rebates:
        pocket_price -= rebate.rebate_amt  # These REDUCE pocket margin

    # Step 3: Pocket price per unit
    pocket_price_per_unit = pocket_price / transaction.volume

    # Step 4: Gross margin (pocket - cost)
    gross_margin = pocket_price_per_unit - transaction.unit_cost

    return {
        'list_price': transaction.base_price,
        'net_price': net_price,
        'invoice_discount': transaction.base_price - net_price,
        'post_invoice_rebates': sum(r.rebate_amt for r in transaction.post_invoice_rebates),
        'pocket_price': pocket_price,
        'gross_margin': gross_margin,
        'pocket_margin_pct': gross_margin / transaction.base_price
    }
```

**Key insight:** Post-invoice rebates are non-commutative — applying a 5% retro rebate before vs after a 3% invoice discount gives different results. **Always apply invoice discounts first (at sale), then retro rebates (at period close).**

**Aggregation:** For portfolio-level waterfall, sum pocket prices across transactions grouped by dimension (client/SKU/channel). Weighted average pocket margin % = Σ(pocket_margin) / Σ(revenue).

---

## 3. Cost Estimates

### OPTION A — Lite Version (~123-176 hours)

| Sprint | Description | Hours |
|--------|-------------|-------|
| Sprint 2 LITE | Structural Validator | 18 |
| Sprint 4 | 14 Leakage Rules + Prioritizer | 95 |
| Sprint 5 LITE | Simple Excel Report | 25 |
| Architectural patterns (embedded in sprints) | tenant_id, core/app, ORM, anonymizer | 12 |
| Testing + code review | pytest, peer review per milestone | included |
| **TOTAL** | | **150 hrs** |

**Budget cap: $50 × 150 = $7,500** (or rate negotiation)

---

### OPTION B — Complete Version (~218-311 hours)

| Sprint | Description | Hours |
|--------|-------------|-------|
| Sprint 2 FULL | Complete Validator (Layer 1+2+3) | 50 |
| Sprint 3 | KPI Engine + Waterfall | 55 |
| Sprint 4 | 14 Leakage Rules + Prioritizer | 95 |
| Sprint 5 FULL | Executive Reports (PPT + Claude) | 35 |
| Architectural patterns (embedded) | tenant_id, core/app, ORM, anonymizer | 12 |
| Testing + code review | pytest, peer review per milestone | included |
| **TOTAL** | | **247 hrs** |

**Budget cap: $50 × 247 = $12,350** (or rate negotiation)

*Note: Estimates slightly above client ranges due to the 4 architectural patterns and SQLAlchemy ORM layer which add upfront investment but prevent the 200-400 hrs of future rework they mention.*

---

## 4. Availability

- **Hourly rate:** $50/hr (negotiable for Option B long-term)
- **Availability:** 20-25 hrs/week
- **Timezone:** UTC+8 (flexible for LATAM sync — can align to morning LATAM hours)
- **Preferred engagement:** Option B preferred — architectural patterns make sense at that scale
- **First milestone:** Sprint 2 LITE as paid trial (Option A or B Lite)

---

## 5. Why Us

1. **Senior Python + Streamlit depth** — 10+ years Python, production Streamlit apps with complex state management
2. **Data pipeline expertise** — pandas, numpy, scipy; ETL pipelines processing 100K+ rows
3. **Excel/BI tooling** — openpyxl for branded multi-sheet reports, python-pptx for MBB-style decks
4. **LLM integration** — Anthropic Claude API and OpenAI API in production (data products, not just chat)
5. **Methodology alignment** — We read the Marn-Rosiello framework; understand pocket price vs gross margin distinction
6. **Long-term collaborator mindset** — We build for extensibility (tenant_id, core/app separation) not throwaway code

---

PREXIA-2026
