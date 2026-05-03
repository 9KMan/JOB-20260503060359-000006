"""Prioritizer — Sortable/filterable opportunity list."""
import streamlit as st
import pandas as pd
from uuid import uuid4

st.set_page_config(page_title="Prioritizer — PDT", page_icon="🎯", layout="wide")

st.title("🎯 Opportunity Prioritizer")
st.markdown("Rank findings by financial impact, quick wins, risk reduction, or balanced approach.")

strategy = st.selectbox(
    "Strategy",
    ["Balanced", "Financial Impact", "Quick Wins", "Risk Reduction"],
)

findings = st.session_state.get("findings", [])

if not findings:
    st.info("Run a leakage scan first to prioritize findings.")
else:
    from core.engine.prioritizer import Prioritizer
    prioritizer = Prioritizer()

    if "ease_scores" not in st.session_state:
        st.session_state.ease_scores = {}

    ease_inputs = {}
    for f in findings:
        fid = str(f.id)
        default = st.session_state.ease_scores.get(fid, 5.0)
        ease_inputs[fid] = st.slider(
            f"Ease Score ({f.rule_id})",
            min_value=1.0,
            max_value=10.0,
            value=float(default),
            step=0.5,
        )

    st.session_state.ease_scores = ease_inputs

    opportunities = prioritizer.get_top_opportunities(findings, ease_scores=ease_inputs)

    df = pd.DataFrame(opportunities)
    if not df.empty:
        df = df.sort_values("priority_score", ascending=False)
        df["priority_score"] = df["priority_score"].apply(lambda x: f"{x:,.1f}")
        df["impact"] = df["impact"].apply(lambda x: f"${x:,.0f}")

        st.dataframe(
            df.rename(columns={
                "rank": "Rank",
                "name": "Opportunity",
                "category": "Category",
                "impact": "$ Impact",
                "ease": "Ease",
                "confidence": "Confidence",
                "priority_score": "Priority Score",
                "priority_category": "Priority Category",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("---")
        st.markdown("### Priority Classification")

        cats = {}
        for opp in opportunities:
            cat = opp.get("priority_category", "Risk")
            cats[cat] = cats.get(cat, 0) + 1

        for cat, count in sorted(cats.items()):
            color = {"Quick Win": "green", "Strategic": "blue", "Nice-to-Have": "off", "Risk": "red"}.get(cat, "off")
            st.metric(cat, count, delta_color=color)
