"""Rule Details — Drill into individual rules."""
import streamlit as st
import pandas as pd
from uuid import uuid4

st.set_page_config(page_title="Rule Details — PDT", page_icon="📋", layout="wide")

st.title("📋 Rule Details")
st.markdown("Explore the logic and affected transactions for each of the 14 leakage rules.")

all_rules = [
    {"rule_id": "R-01", "name": "Undiscounted Baseline", "category": "PRICE_STRUCTURE", "severity": "HIGH"},
    {"rule_id": "R-02", "name": "Disguised Bundle Discount", "category": "PRICE_STRUCTURE", "severity": "HIGH"},
    {"rule_id": "R-03", "name": "Anchor Price Drift", "category": "PRICE_STRUCTURE", "severity": "MEDIUM"},
    {"rule_id": "R-04", "name": "Segment Bleed", "category": "PRICE_STRUCTURE", "severity": "HIGH"},
    {"rule_id": "R-05", "name": "Retroactive Cliff", "category": "PRICE_STRUCTURE", "severity": "HIGH"},
    {"rule_id": "R-06", "name": "Return Velocity", "category": "CUSTOMER_BEHAVIOR", "severity": "HIGH"},
    {"rule_id": "R-07", "name": "Payment Drift", "category": "CUSTOMER_BEHAVIOR", "severity": "MEDIUM"},
    {"rule_id": "R-08", "name": "Return-to-Invoice", "category": "CUSTOMER_BEHAVIOR", "severity": "HIGH"},
    {"rule_id": "R-09", "name": "Short-Close Credit", "category": "CUSTOMER_BEHAVIOR", "severity": "MEDIUM"},
    {"rule_id": "R-10", "name": "Volume Spike Gaming", "category": "CUSTOMER_BEHAVIOR", "severity": "MEDIUM"},
    {"rule_id": "R-11", "name": "High-Return SKU", "category": "PRODUCT_MIX", "severity": "HIGH"},
    {"rule_id": "R-12", "name": "Zombie Product", "category": "PRODUCT_MIX", "severity": "MEDIUM"},
    {"rule_id": "R-13", "name": "Mix Shift Erosion", "category": "PRODUCT_MIX", "severity": "MEDIUM"},
    {"rule_id": "R-14", "name": "Promotional Dependency", "category": "PRODUCT_MIX", "severity": "LOW"},
]

rule_descriptions = {
    "R-01": "Products never sold at list price — entire price book may be discounted. Detects when discount rate falls below threshold across the product history.",
    "R-02": "Bundle SKU priced below sum of components — hidden discount. Detects when bundle price is significantly below component prices.",
    "R-03": "Current prices never updated relative to cost increases. Detects anchor price staleness over lookback periods.",
    "R-04": "Enterprise discounts applied to mid-market customers. Detects segment bleed when enterprise pricing leaks to non-enterprise segments.",
    "R-05": "Volume rebate triggers retroactively change pocket price with no notice. Detects retroactive clawback exposure from active triggers.",
    "R-06": "Same customer returns >10% of purchases (inventory gaming). Detects excessive return velocity relative to purchase volume.",
    "R-07": "Customers paying 30+ days late — implicit float subsidy. Detects late payment patterns creating financing cost.",
    "R-08": "Invoiced at one price, credited at a lower standard price. Detects return-to-invoice price mismatches.",
    "R-09": "Credit memos issued after normal close period. Detects shortened close window credits.",
    "R-10": "Customers loading up before price increase, then returning excess. Detects volume spike patterns before price changes.",
    "R-11": "Specific SKUs with >15% return rate — margin erosion. Detects high-return SKUs eroding margin.",
    "R-12": "Products with zero margin still in price book. Detects zombie products consuming resources.",
    "R-13": "Shift toward lower-margin categories not reflected in price. Detects mix shift margin erosion.",
    "R-14": "Same product always sold on promo — baseline price is artificial. Detects promotional dependency.",
}

rule_recommendations = {
    "R-01": "Audit price book — ensure list price reflects value, not just historical discounting.",
    "R-02": "Unbundle pricing or align bundle price with component sum.",
    "R-03": "Update anchor prices to reflect current cost structure.",
    "R-04": "Enforce segment-specific pricing guards.",
    "R-05": "Renegotiate GPR clauses before Q3 contract renewals to lock in floor prices.",
    "R-06": "Implement restocking fee or cap returns at 5% of purchase volume.",
    "R-07": "Offer early payment discount or tighten payment terms.",
    "R-08": "Standardize return credit process to match original invoice price.",
    "R-09": "Enforce close window policy strictly.",
    "R-10": "Implement pre-order limits and restocking fees.",
    "R-11": "Discontinue or reprice high-return SKUs.",
    "R-12": "Reprice or remove zombie products from active price book.",
    "R-13": "Reprice category or shift mix toward higher-margin products.",
    "R-14": "Establish a sustainable non-promo price point.",
}

selected_rule_id = st.selectbox("Select Rule", [r["rule_id"] for r in all_rules])
selected_rule = next(r for r in all_rules if r["rule_id"] == selected_rule_id)

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("#### Rule Definition")
    st.markdown(f"**{selected_rule['name']}**")
    st.markdown(f"**Category:** {selected_rule['category']}")
    st.markdown(f"**Severity:** `{selected_rule['severity']}`")
    st.markdown(f"**Description:**")
    st.info(rule_descriptions.get(selected_rule_id, ""))
    st.markdown("**Recommendation:**")
    st.success(rule_recommendations.get(selected_rule_id, ""))

with col2:
    st.markdown("#### Affected Transactions")
    findings = st.session_state.get("findings", [])
    rule_findings = [f for f in findings if f.rule_id == selected_rule_id]

    if rule_findings:
        data = []
        for f in rule_findings:
            data.append({
                "Finding ID": str(f.id)[:8],
                "$ Impact": f"${float(f.impact_dollars):,.0f}",
                "Confidence": f"{f.confidence:.0%}",
                "Severity": f.severity,
                "Description": f.description[:60],
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No findings for this rule yet.")
