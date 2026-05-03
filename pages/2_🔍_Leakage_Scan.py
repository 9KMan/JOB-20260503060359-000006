"""Leakage Scan — Full 14-rule scan + findings."""
import streamlit as st
import pandas as pd
from uuid import uuid4
from decimal import Decimal

st.set_page_config(page_title="Leakage Scan — PDT", page_icon="🔍", layout="wide")

st.title("🔍 Leakage Scan")
st.markdown("Run the full 14-rule diagnostic on your transaction data.")

if "findings" not in st.session_state:
    st.session_state.findings = []

if st.button("▶ Run Full Scan", type="primary"):
    with st.spinner("Running 14 leakage rules..."):
        from core.engine.leakage_engine import LeakageEngine
        from core.rules.base import LeakageFinding

        engine = LeakageEngine()
        txs = st.session_state.get("transactions", [])

        if txs:
            tenant_id = st.session_state.get("tenant_id", str(uuid4()))
            findings = engine.run_all_rules(
                [tx.__class__(**{k: getattr(tx, k, None) for k in ['id','tenant_id','transaction_id','date','customer_id','customer_segment','product_id','product_category','list_price','invoice_price','net_price','pocket_price','gross_margin','return_qty','payment_status']}) for tx in txs],
                uuid4(),
            )
            st.session_state.findings = findings
        else:
            st.info("Upload transaction data first to run scan.")

st.sidebar.header("Filters")

category_filter = st.sidebar.multiselect(
    "Category",
    ["PRICE_STRUCTURE", "CUSTOMER_BEHAVIOR", "PRODUCT_MIX"],
    default=["PRICE_STRUCTURE", "CUSTOMER_BEHAVIOR", "PRODUCT_MIX"],
)

severity_filter = st.sidebar.multiselect(
    "Severity",
    ["HIGH", "MEDIUM", "LOW"],
    default=["HIGH", "MEDIUM", "LOW"],
)

min_impact = st.sidebar.number_input("Min $ Impact", min_value=0, value=0, step=1000)

findings = st.session_state.get("findings", [])
filtered = [
    f for f in findings
    if f.category in category_filter
    and f.severity in severity_filter
    and float(f.impact_dollars) >= min_impact
]

st.markdown(f"**{len(filtered)} findings** matching filters")

if filtered:
    data = []
    for f in filtered:
        data.append({
            "Rule": f.rule_id,
            "Category": f.category,
            "Severity": f.severity,
            "$ Impact": f"${float(f.impact_dollars):,.0f}",
            "Confidence": f"{f.confidence:.0%}",
            "Recurrence": f"{f.recurrence_factor:.0%}",
            "Description": f.description[:80],
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    with st.expander("📋 Export Filtered Results"):
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv.encode(), "leakage_findings.csv", "text/csv")
else:
    st.info("No findings yet. Run a scan or upload data.")

st.markdown("---")
st.markdown("### Severity Breakdown")

severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
for f in findings:
    severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1

col1, col2, col3 = st.columns(3)
for sev, col in zip(["HIGH", "MEDIUM", "LOW"], [col1, col2, col3]):
    count = severity_counts.get(sev, 0)
    color = {"HIGH": "red", "MEDIUM": "amber", "LOW": "off"}.get(sev, "off")
    col.metric(f"{sev} Severity", count, delta_color=color)
