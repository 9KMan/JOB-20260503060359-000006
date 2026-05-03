"""Reports — Download center for Excel export."""
import streamlit as st
from io import BytesIO
import pandas as pd
from uuid import uuid4

st.set_page_config(page_title="Reports — PDT", page_icon="📥", layout="wide")

st.title("📥 Reports")
st.markdown("Download branded diagnostic reports.")

tenant_name = st.text_input("Tenant Name", value="Acme Corp")
generate = st.button("Generate Excel Report", type="primary")

if generate:
    with st.spinner("Generating 3-sheet branded Excel report..."):
        from core.reporting.excel_report import ExcelReportGenerator

        data = {
            "kpis": {
                "gross_margin_pct": 32.4,
                "pocket_vs_invoice_delta": -12400,
                "leakages_found": len(st.session_state.get("findings", [])),
                "total_at_risk": sum(f.impact_dollars for f in st.session_state.get("findings", []) if hasattr(f, "impact_dollars")),
            },
            "waterfall": [
                {"stage": "List Price", "amount": 100000, "pct_of_list": 100.0, "delta": 0},
                {"stage": "Invoice Discounts", "amount": 85000, "pct_of_list": 85.0, "delta": -15000},
                {"stage": "Net Invoice Price", "amount": 77000, "pct_of_list": 77.0, "delta": -8000},
                {"stage": "Pocket Price", "amount": 73500, "pct_of_list": 73.5, "delta": -3500},
                {"stage": "Gross Margin", "amount": 73500, "pct_of_list": 73.5, "delta": 0},
            ],
            "top_opportunities": [
                {"name": "R-05: Retroactive Cliff", "category": "PRICE_STRUCTURE", "impact": 45000, "ease": 4, "priority_score": 820},
                {"name": "R-04: Segment Bleed", "category": "PRICE_STRUCTURE", "impact": 32000, "ease": 6, "priority_score": 750},
                {"name": "R-06: Return Velocity", "category": "CUSTOMER_BEHAVIOR", "impact": 21000, "ease": 7, "priority_score": 680},
            ],
            "rule_summary": [
                {"rule_id": "R-01", "name": "Undiscounted Baseline", "category": "PRICE_STRUCTURE", "severity": "HIGH", "finding_count": 3, "total_impact": 12000, "avg_confidence": 0.82},
                {"rule_id": "R-05", "name": "Retroactive Cliff", "category": "PRICE_STRUCTURE", "severity": "HIGH", "finding_count": 8, "total_impact": 45000, "avg_confidence": 0.92},
                {"rule_id": "R-06", "name": "Return Velocity", "category": "CUSTOMER_BEHAVIOR", "severity": "HIGH", "finding_count": 5, "total_impact": 21000, "avg_confidence": 0.88},
            ],
            "action_plan": [
                {"item": "Renegotiate GPR clauses", "owner": "Pricing Team", "effort": "High", "expected_return": 45000},
                {"item": "Implement restocking fees", "owner": "Operations", "effort": "Medium", "expected_return": 21000},
                {"item": "Segment pricing guards", "owner": "Sales", "effort": "Medium", "expected_return": 32000},
            ],
        }

        generator = ExcelReportGenerator(tenant_name=tenant_name)
        buffer = generator.generate(data)

        st.success("Report generated successfully!")
        st.download_button(
            "📊 Download Excel Report",
            buffer.getvalue(),
            file_name=f"PDT_Report_{tenant_name.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

st.markdown("---")
st.markdown("### Report Preview")

st.info("3-sheet Excel report includes: Executive Summary · Leakage Catalog · Action Plan")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown("**Sheet 1 — Executive Summary**")
    st.caption("Logo + KPIs + Waterfall table + Top 10 opportunities")
with col2:
    st.markdown("**Sheet 2 — Leakage Catalog**")
    st.caption("All 14 rules with finding counts, $ impact, severity breakdown")
with col3:
    st.markdown("**Sheet 3 — Action Plan**")
    st.caption("Prioritized list with owner, effort, expected return")
