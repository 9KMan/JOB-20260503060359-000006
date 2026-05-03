"""Streamlit entry point — B2B Pricing Diagnostic Tool."""
import streamlit as st
import uuid
from datetime import datetime

st.set_page_config(
    page_title="PDT — Pricing Diagnostic Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "tenant_id" not in st.session_state:
    st.session_state["tenant_id"] = str(uuid.uuid4())
if "transactions" not in st.session_state:
    st.session_state["transactions"] = []
if "findings" not in st.session_state:
    st.session_state["findings"] = []
if "validated" not in st.session_state:
    st.session_state["validated"] = False

st.markdown("""
<style>
    :root {
        --bg-primary: #FAFBFC;
        --bg-card: #FFFFFF;
        --bg-navy: #0D2137;
        --accent-blue: #2563EB;
        --accent-teal: #0D9488;
        --accent-red: #DC2626;
        --accent-amber: #D97706;
        --text-primary: #111827;
        --text-secondary: #6B7280;
        --border: #E5E7EB;
    }
    .stApp { background: var(--bg-primary); }
    .kpi-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .kpi-label { font-size: 12px; color: var(--text-secondary); font-family: Inter, sans-serif; }
    .kpi-value { font-size: 28px; font-weight: 700; color: var(--text-primary); font-family: Inter, sans-serif; }
    .metric-teal { color: var(--accent-teal); }
    .metric-red { color: var(--accent-red); }
    .metric-blue { color: var(--accent-blue); }
    .metric-amber { color: var(--accent-amber); }
    .nav-btn {
        background: var(--accent-blue);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        cursor: pointer;
        font-family: Inter, sans-serif;
    }
    div[data-testid="stSidebar"] { background: var(--bg-navy); color: white; }
    .stMetric { background: var(--bg-card); border-radius: 8px; padding: 12px; }
</style>
""", unsafe_allow_html=True)


def getTenantId():
    return st.session_state.get("tenant_id", str(uuid.uuid4()))


def setTenantId(tid):
    st.session_state["tenant_id"] = tid


st.title("Pricing Diagnostic Tool")
st.caption("Precision pricing intelligence for B2B enterprises")

st.sidebar.title("Navigation")
st.sidebar.markdown("---")

pages = {
    "📊 Dashboard": "dashboard",
    "🔍 Leakage Scan": "leakage",
    "📋 Rule Details": "rules",
    "🎯 Prioritizer": "prioritizer",
    "📥 Reports": "reports",
}

for label, page in pages.items():
    st.sidebar.page_link(f"pages/{page}.py", label=label)

st.sidebar.markdown("---")
st.sidebar.caption(f"Tenant: {getTenantId()[:8]}...")
