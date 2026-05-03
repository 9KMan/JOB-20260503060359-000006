"""Dashboard — KPI overview + waterfall."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from decimal import Decimal

st.set_page_config(page_title="Dashboard — PDT", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.markdown("### Key Performance Indicators")

kpis = {
    "gross_margin_pct": 32.4,
    "pocket_vs_invoice_delta": -12400,
    "leakages_found": 0,
    "total_at_risk": 0,
}

if "findings" in st.session_state and st.session_state.findings:
    findings = st.session_state.findings
    kpis["leakages_found"] = len(findings)
    kpis["total_at_risk"] = sum(f.impact_dollars for f in findings if hasattr(f, "impact_dollars"))

if "transactions" in st.session_state and st.session_state.transactions:
    txs = st.session_state.transactions
    total_list = sum(float(t.list_price) for t in txs)
    total_margin = sum(float(t.gross_margin) for t in txs)
    if total_list > 0:
        kpis["gross_margin_pct"] = round(total_margin / total_list * 100, 1)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Gross Margin %",
        f"{kpis['gross_margin_pct']:.1f}%",
        delta="",
        delta_color="off"
    )
with col2:
    st.metric(
        "Pocket Δ vs Invoice",
        f"${kpis['pocket_vs_invoice_delta']:,.0f}",
        delta="",
        delta_color="off"
    )
with col3:
    st.metric(
        "Leakages Found",
        kpis["leakages_found"],
        delta="",
        delta_color="off"
    )
with col4:
    st.metric(
        "Total $ at Risk",
        f"${kpis['total_at_risk']:,.0f}",
        delta="",
        delta_color="off"
    )

st.markdown("---")
st.markdown("### Pocket Price Waterfall")

waterfall_data = [
    {"stage": "List Price", "amount": 100000, "pct_of_list": 100.0, "delta": 0},
    {"stage": "Invoice Discounts", "amount": -15000, "pct_of_list": -15.0, "delta": -15000},
    {"stage": "Net Invoice Price", "amount": 85000, "pct_of_list": 85.0, "delta": 85000},
    {"stage": "Post-Invoice Rebates", "amount": -8000, "pct_of_list": -8.0, "delta": -8000},
    {"stage": "Pocket Price", "amount": 77000, "pct_of_list": 77.0, "delta": 77000},
    {"stage": "Allowances", "amount": -3500, "pct_of_list": -3.5, "delta": -3500},
    {"stage": "Gross Margin", "amount": 73500, "pct_of_list": 73.5, "delta": 73500},
]

fig = go.Figure()
colors = ["#2563EB", "#93C5FD", "#2563EB", "#93C5FD", "#0D9488", "#5EEAD4", "#0D9488"]
labels = [w["stage"] for w in waterfall_data]
values = [w["amount"] for w in waterfall_data]

fig.add_trace(go.Bar(
    x=list(range(len(labels))),
    y=values,
    marker_color=colors,
    text=[f"${v:,.0f}" for v in values],
    textposition="outside",
    hovertemplate="<b>%{label}</b><br>$%{y:,.0f}<extra></extra>",
))

fig.update_layout(
    xaxis=dict(tickvals=list(range(len(labels))), ticktext=labels, tickangle=-30),
    yaxis=dict(title="USD", tickprefix="$", tickformat=","),
    showlegend=False,
    height=400,
    margin=dict(b=80),
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("### Top Leakage Categories by $ Impact")

top_categories = [
    {"category": "Retroactive Cliff (R-05)", "impact": 45000},
    {"category": "Segment Bleed (R-04)", "impact": 32000},
    {"category": "Return Velocity (R-06)", "impact": 21000},
    {"category": "Promotional Dependency (R-14)", "impact": 15000},
    {"category": "High-Return SKU (R-11)", "impact": 12000},
]

fig2 = go.Figure(go.Bar(
    x=[c["impact"] for c in top_categories],
    y=[c["category"] for c in top_categories],
    orientation="h",
    marker_color="#DC2626",
    text=[f"${v:,.0f}" for v in [c['impact'] for c in top_categories]],
    textposition="outside",
))
fig2.update_layout(
    yaxis=dict(title=""),
    xaxis=dict(title="USD Impact", tickprefix="$", tickformat=","),
    showlegend=False,
    height=300,
    margin=dict(l=200),
)
st.plotly_chart(fig2, use_container_width=True)
