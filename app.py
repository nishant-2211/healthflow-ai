import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient

import streamlit as st

# Must be first Streamlit command
st.set_page_config(
    page_title="HealthFlow AI",
    page_icon="🏥",
    layout="wide"
)

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="HealthFlow AI 🏥",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS — dark glass theme ────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Base */
  .stApp { background: linear-gradient(135deg, #f0f4ff 0%, #fdf4ff 50%, #f0fdfa 100%); color: #0f172a; }
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ede9fe 0%, #dbeafe 60%, #cffafe 100%);
    border-right: 2px solid rgba(124,58,237,0.2);
  }

  /* Hide default header */
  header[data-testid="stHeader"] { background: transparent; }

  /* Gradient title */
  .hero-title {
    font-size: 3rem; font-weight: 800; text-align: center; margin-bottom: .25rem;
    background: linear-gradient(135deg, #7c3aed, #2563eb, #06b6d4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .hero-sub {
    text-align: center; color: #475569; font-size: 1rem; margin-bottom: 1.5rem;
  }

  /* Badges */
  .badge-row { display: flex; gap: .5rem; justify-content: center; flex-wrap: wrap; margin-bottom: 2rem; }
  .badge {
    padding: .25rem .75rem; border-radius: 999px; font-size: .75rem;
    font-weight: 600; border: 1px solid; letter-spacing: .05em;
  }
  .badge-purple { color:#a78bfa; border-color:#7c3aed; background:rgba(124,58,237,.1); }
  .badge-blue   { color:#60a5fa; border-color:#2563eb; background:rgba(37,99,235,.1); }
  .badge-cyan   { color:#22d3ee; border-color:#06b6d4; background:rgba(6,182,212,.1); }
  .badge-green  { color:#4ade80; border-color:#16a34a; background:rgba(22,163,74,.1); }
  .badge-pink   { color:#f472b6; border-color:#db2777; background:rgba(219,39,119,.1); }

  /* Metric cards — each with its own colour wash */
  .metric-card {
    border-radius: 16px; padding: 1.25rem 1.5rem;
    transition: transform .15s, box-shadow .15s;
    border: none;
  }
  .metric-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,.10); }
  .metric-label { font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; margin-bottom: .25rem; font-weight: 700; opacity: .75; }
  .metric-value { font-size: 2rem; font-weight: 800; }

  /* Coloured card backgrounds */
  .mc-purple { background: linear-gradient(135deg,#ede9fe,#ddd6fe); color:#4c1d95; }
  .mc-blue   { background: linear-gradient(135deg,#dbeafe,#bfdbfe); color:#1e3a8a; }
  .mc-cyan   { background: linear-gradient(135deg,#cffafe,#a5f3fc); color:#164e63; }
  .mc-green  { background: linear-gradient(135deg,#dcfce7,#bbf7d0); color:#14532d; }
  .mc-pink   { background: linear-gradient(135deg,#fce7f3,#fbcfe8); color:#831843; }

  /* Value colours matching card */
  .metric-purple { color: #6d28d9; }
  .metric-blue   { color: #1d4ed8; }
  .metric-cyan   { color: #0e7490; }
  .metric-green  { color: #15803d; }
  .metric-pink   { color: #be185d; }

  /* Glass section card */
  .glass-card {
    background: rgba(255,255,255,.75);
    border: 1px solid rgba(124,58,237,.12);
    border-radius: 16px; padding: 1.5rem; margin-bottom: 1rem;
    backdrop-filter: blur(8px);
    box-shadow: 0 2px 12px rgba(124,58,237,.06);
  }
  .section-title {
    font-size: 1.1rem; font-weight: 700; color: #1e1b4b; margin-bottom: 1rem;
    border-left: 4px solid #7c3aed; padding-left: .75rem;
  }

  /* Sidebar status dots */
  .status-row { display:flex; align-items:center; gap:.5rem; margin:.35rem 0; font-size:.875rem; }
  .dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }
  .dot-green { background:#4ade80; box-shadow:0 0 6px #4ade80; }
  .dot-yellow{ background:#fbbf24; box-shadow:0 0 6px #fbbf24; }
  .dot-red   { background:#f87171; box-shadow:0 0 6px #f87171; }

  /* Medallion pipeline diagram */
  .medal-row { display:flex; align-items:center; gap:.25rem; flex-wrap:wrap; }
  .medal-box {
    padding:.5rem 1rem; border-radius:8px; font-weight:700; font-size:.85rem; text-align:center;
  }
  .medal-bronze { background:rgba(180,83,9,.2); border:1px solid #b45309; color:#fbbf24; }
  .medal-silver { background:rgba(100,116,139,.2); border:1px solid #64748b; color:#cbd5e1; }
  .medal-gold   { background:rgba(217,119,6,.2); border:1px solid #d97706; color:#fcd34d; }
  .medal-arrow  { color:#64748b; font-size:1.25rem; }

  /* Tab styling */
  [data-testid="stTab"] button { color:#94a3b8 !important; }
  [data-testid="stTab"] button[aria-selected="true"] { color:#a78bfa !important; border-bottom-color:#7c3aed !important; }

  /* Plotly chart background override */
  .js-plotly-plot .plotly .main-svg { background:transparent !important; }

  /* AI report card */
  .ai-card {
    background: linear-gradient(135deg, #ede9fe 0%, #dbeafe 50%, #cffafe 100%);
    border: 1px solid rgba(124,58,237,.25);
    border-radius: 16px; padding: 1.5rem;
    box-shadow: 0 4px 16px rgba(124,58,237,.08);
  }
  .ai-timestamp { font-size:.75rem; color:#64748b; margin-top:1rem; }
</style>
""", unsafe_allow_html=True)

# ── Plotly dark layout defaults ────────────────────────────────────────────────
CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#475569", family="Inter, sans-serif"),
    margin=dict(l=20, r=20, t=40, b=20),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)
PALETTE = ["#7c3aed", "#2563eb", "#06b6d4", "#4ade80", "#f472b6", "#fbbf24", "#f87171"]

# ── Databricks helpers ────────────────────────────────────────────────────────

def run_query(sql: str) -> pd.DataFrame:
    client = WorkspaceClient(
        host=os.getenv("DATABRICKS_HOST"),
        token=os.getenv("DATABRICKS_TOKEN"),
    )
    response = client.statement_execution.execute_statement(
        warehouse_id=os.getenv("DATABRICKS_WAREHOUSE_ID"),
        statement=sql,
        wait_timeout="30s",
    )
    cols = [col.name for col in response.manifest.schema.columns]
    rows = []
    if response.result and response.result.data_array:
        rows = response.result.data_array
    return pd.DataFrame(rows, columns=cols)


@st.cache_data(ttl=300, show_spinner=False)
def load_conditions() -> pd.DataFrame:
    df = run_query("SELECT * FROM healthflow_catalog.gold.conditions_analysis ORDER BY patient_count DESC")
    for col in ["patient_count", "avg_billing", "avg_stay_days"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_hospitals() -> pd.DataFrame:
    df = run_query("SELECT * FROM healthflow_catalog.gold.hospital_performance ORDER BY total_patients DESC LIMIT 10")
    for col in ["total_patients", "avg_billing", "urgent_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_demographics() -> pd.DataFrame:
    df = run_query("SELECT * FROM healthflow_catalog.gold.demographics")
    for col in ["patient_count", "avg_billing"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    age_order = ["0-18", "19-35", "36-50", "51-65", "65+"]
    if "age_group" in df.columns:
        df["age_group"] = pd.Categorical(df["age_group"], categories=age_order, ordered=True)
        df = df.sort_values("age_group")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_silver_summary() -> pd.DataFrame:
    df = run_query("""
        SELECT
            COUNT(*) AS total_patients,
            AVG(billing_amount) AS avg_billing,
            AVG(length_of_stay) AS avg_stay,
            SUM(CASE WHEN admission_type='Urgent' THEN 1 ELSE 0 END)
                * 100.0 / COUNT(*) AS urgent_pct,
            COUNT(DISTINCT medical_condition) AS condition_count
        FROM healthflow_catalog.silver.patients_clean
    """)
    for col in ["total_patients", "avg_billing", "avg_stay", "urgent_pct", "condition_count"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_admission_types() -> pd.DataFrame:
    df = run_query("""
        SELECT admission_type, COUNT(*) AS count
        FROM healthflow_catalog.silver.patients_clean
        GROUP BY admission_type
        ORDER BY count DESC
    """)
    if "count" in df.columns:
        df["count"] = pd.to_numeric(df["count"], errors="coerce")
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_ai_insights() -> pd.DataFrame:
    return run_query("""
        SELECT * FROM healthflow_catalog.gold.ai_insights
        ORDER BY generated_at DESC LIMIT 1
    """)


@st.cache_data(ttl=300, show_spinner=False)
def load_record_counts() -> dict:
    tables = {
        "bronze":       "healthflow_catalog.bronze.patients_raw",
        "silver":       "healthflow_catalog.silver.patients_clean",
        "conditions":   "healthflow_catalog.gold.conditions_analysis",
        "hospitals":    "healthflow_catalog.gold.hospital_performance",
        "demographics": "healthflow_catalog.gold.demographics",
    }
    counts = {}
    for key, tbl in tables.items():
        try:
            df = run_query(f"SELECT COUNT(*) AS n FROM {tbl}")
            counts[key] = int(float(df["n"].iloc[0]))
        except Exception:
            counts[key] = "—"
    return counts


# ── Load all data (with error capture) ────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    errors = {}
    data   = {}
    for name, fn in [
        ("conditions",   load_conditions),
        ("hospitals",    load_hospitals),
        ("demographics", load_demographics),
        ("summary",      load_silver_summary),
        ("admissions",   load_admission_types),
        ("ai_insights",  load_ai_insights),
        ("counts",       load_record_counts),
    ]:
        try:
            data[name] = fn()
        except Exception as exc:
            errors[name] = str(exc)
            data[name]   = pd.DataFrame() if name != "counts" else {}
    return data, errors


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">🏥 HealthFlow AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Enterprise Healthcare Pipeline powered by '
    '<strong>ADF</strong> + <strong>Databricks</strong> + <strong>Claude AI</strong></div>',
    unsafe_allow_html=True,
)
st.markdown("""
<div class="badge-row">
  <span class="badge badge-purple">⚡ ADF</span>
  <span class="badge badge-blue">🔷 DATABRICKS</span>
  <span class="badge badge-cyan">🥇 MEDALLION</span>
  <span class="badge badge-green">🤖 CLAUDE AI</span>
  <span class="badge badge-pink">📊 55K RECORDS</span>
</div>
""", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Connecting to Databricks…"):
    data, errors = load_all()

if errors:
    with st.expander("⚠️ Connection warnings", expanded=False):
        for k, v in errors.items():
            st.error(f"**{k}**: {v}")

# ── Metrics row ───────────────────────────────────────────────────────────────
summary = data.get("summary", pd.DataFrame())

def _val(df, col, default="—"):
    try:
        return df[col].iloc[0] if not df.empty and col in df.columns else default
    except Exception:
        return default

total_patients  = _val(summary, "total_patients", 54_966)
condition_count = _val(summary, "condition_count", 6)
avg_billing     = _val(summary, "avg_billing",    "—")
avg_stay        = _val(summary, "avg_stay",        "—")
urgent_pct      = _val(summary, "urgent_pct",      "—")

try:    total_patients  = f"{int(float(total_patients)):,}"
except: total_patients  = str(total_patients)
try:    avg_billing     = f"${float(avg_billing):,.0f}"
except: avg_billing     = str(avg_billing)
try:    avg_stay        = f"{float(avg_stay):.1f} days"
except: avg_stay        = str(avg_stay)
try:    urgent_pct      = f"{float(urgent_pct):.1f}%"
except: urgent_pct      = str(urgent_pct)

cols = st.columns(5)
metrics = [
    ("Total Patients",        total_patients,      "mc-purple", "metric-purple"),
    ("Medical Conditions",    str(condition_count), "mc-blue",   "metric-blue"),
    ("Avg Billing Amount",    avg_billing,          "mc-cyan",   "metric-cyan"),
    ("Avg Length of Stay",    avg_stay,             "mc-green",  "metric-green"),
    ("Urgent Admission Rate", urgent_pct,           "mc-pink",   "metric-pink"),
]
for col, (label, value, bg_cls, val_cls) in zip(cols, metrics):
    col.markdown(f"""
    <div class="metric-card {bg_cls}">
      <div class="metric-label">{label}</div>
      <div class="metric-value {val_cls}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🏥 HealthFlow AI")
    st.markdown("---")

    st.markdown("**Pipeline Status**")
    counts = data.get("counts", {})
    layers = [
        ("ADF Ingestion",    True),
        ("Bronze Layer",     bool(counts.get("bronze"))),
        ("Silver Layer",     bool(counts.get("silver"))),
        ("Gold Layer",       bool(counts.get("conditions"))),
        ("AI Insights",      not data.get("ai_insights", pd.DataFrame()).empty),
    ]
    for label, ok in layers:
        dot   = "dot-green" if ok else "dot-yellow"
        badge = "✅" if ok else "⏳"
        st.markdown(
            f'<div class="status-row"><span class="dot {dot}"></span>{label} {badge}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("**Dataset Stats**")
    stat_rows = [
        ("Bronze records",  counts.get("bronze",       "—")),
        ("Silver records",  counts.get("silver",       "—")),
        ("Conditions",      counts.get("conditions",   "—")),
        ("Hospitals",       counts.get("hospitals",    "—")),
        ("Demographics",    counts.get("demographics", "—")),
    ]
    for label, val in stat_rows:
        try:   display = f"{int(val):,}"
        except: display = str(val)
        st.metric(label, display)

    st.markdown("---")
    st.markdown("**Architecture**")
    st.markdown("""
    <div class="medal-row">
      <div class="medal-box medal-bronze">🥉 Bronze</div>
      <span class="medal-arrow">→</span>
      <div class="medal-box medal-silver">🥈 Silver</div>
      <span class="medal-arrow">→</span>
      <div class="medal-box medal-gold">🥇 Gold</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Powered by Azure ADF + Databricks + Claude AI")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "💰 Billing Analysis",
    "🤖 AI Insights",
    "🔍 Pipeline Status",
])

# ════════════════════════════════════════════════════════
# TAB 1 — Overview
# ════════════════════════════════════════════════════════
with tab1:
    conditions  = data.get("conditions",  pd.DataFrame())
    admissions  = data.get("admissions",  pd.DataFrame())
    demographics= data.get("demographics",pd.DataFrame())

    col_a, col_b = st.columns(2)

    # Bar: patients by condition
    with col_a:
        st.markdown('<div class="section-title">Patient Volume by Condition</div>', unsafe_allow_html=True)
        if not conditions.empty:
            fig = px.bar(
                conditions,
                x="patient_count", y="medical_condition",
                orientation="h",
                color="patient_count",
                color_continuous_scale=["#2563eb", "#7c3aed", "#06b6d4"],
                labels={"patient_count": "Patients", "medical_condition": ""},
            )
            fig.update_layout(**CHART_LAYOUT, coloraxis_showscale=False, height=340)
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Conditions data unavailable")

    # Donut: admission types
    with col_b:
        st.markdown('<div class="section-title">Admission Type Breakdown</div>', unsafe_allow_html=True)
        if not admissions.empty:
            admissions["count"] = pd.to_numeric(admissions["count"], errors="coerce")
            fig = go.Figure(go.Pie(
                labels=admissions["admission_type"],
                values=admissions["count"],
                hole=.55,
                marker=dict(colors=PALETTE),
                textinfo="label+percent",
                textfont=dict(color="#e2e8f0"),
            ))
            fig.update_layout(**CHART_LAYOUT, height=340, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Admission data unavailable")

    # Bar: age demographics
    st.markdown('<div class="section-title">Patient Demographics by Age Group</div>', unsafe_allow_html=True)
    if not demographics.empty:
        fig = px.bar(
            demographics,
            x="age_group", y="patient_count",
            color="age_group",
            color_discrete_sequence=PALETTE,
            labels={"patient_count": "Patients", "age_group": "Age Group"},
            text="patient_count",
        )
        fig.update_traces(texttemplate="%{text:,}", textposition="outside", marker_line_width=0)
        fig.update_layout(**CHART_LAYOUT, height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Demographics data unavailable")


# ════════════════════════════════════════════════════════
# TAB 2 — Billing Analysis
# ════════════════════════════════════════════════════════
with tab2:
    conditions = data.get("conditions", pd.DataFrame())
    hospitals  = data.get("hospitals",  pd.DataFrame())

    st.markdown('<div class="section-title">Average Billing Amount by Medical Condition</div>', unsafe_allow_html=True)
    if not conditions.empty:
        cond_sorted = conditions.sort_values("avg_billing", ascending=False)
        fig = px.bar(
            cond_sorted,
            x="medical_condition", y="avg_billing",
            color="avg_billing",
            color_continuous_scale=["#2563eb", "#7c3aed", "#f472b6"],
            labels={"avg_billing": "Avg Billing ($)", "medical_condition": "Condition"},
            text="avg_billing",
        )
        fig.update_traces(
            texttemplate="$%{text:,.0f}", textposition="outside",
            marker_line_width=0,
        )
        fig.update_layout(**CHART_LAYOUT, height=360, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Conditions data unavailable")

    # Hospital table
    st.markdown('<div class="section-title">Top 10 Hospitals by Patient Volume</div>', unsafe_allow_html=True)
    if not hospitals.empty:
        top10 = hospitals.head(10).copy()
        top10["avg_billing"]   = top10["avg_billing"].apply(lambda x: f"${float(x):,.2f}" if pd.notna(x) else "—")
        top10["total_patients"]= top10["total_patients"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        top10["urgent_count"]  = top10["urgent_count"].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "—")
        top10 = top10.rename(columns={
            "hospital": "Hospital",
            "total_patients": "Total Patients",
            "avg_billing": "Avg Billing",
            "urgent_count": "Urgent Cases",
        })
        st.dataframe(
            top10[["Hospital", "Total Patients", "Avg Billing", "Urgent Cases"]],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("Hospital data unavailable")

    # Avg stay by condition
    if not conditions.empty:
        st.markdown('<div class="section-title">Average Length of Stay by Condition</div>', unsafe_allow_html=True)
        stay_sorted = conditions.sort_values("avg_stay_days", ascending=False)
        fig = px.bar(
            stay_sorted,
            x="avg_stay_days", y="medical_condition",
            orientation="h",
            color="avg_stay_days",
            color_continuous_scale=["#06b6d4", "#2563eb", "#7c3aed"],
            labels={"avg_stay_days": "Avg Stay (days)", "medical_condition": ""},
            text="avg_stay_days",
        )
        fig.update_traces(texttemplate="%{text:.1f}d", textposition="outside", marker_line_width=0)
        fig.update_layout(**CHART_LAYOUT, height=300, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
# TAB 3 — AI Insights
# ════════════════════════════════════════════════════════
with tab3:
    ai_df = data.get("ai_insights", pd.DataFrame())

    st.markdown('<div class="section-title">🤖 Claude AI Healthcare Analysis</div>', unsafe_allow_html=True)

    if not ai_df.empty and "report_text" in ai_df.columns:
        report_text  = ai_df["report_text"].iloc[0]
        generated_at = ai_df["generated_at"].iloc[0] if "generated_at" in ai_df.columns else "—"

        st.markdown(f"""
        <div class="ai-card">
          <div style="font-size:.75rem;color:#a78bfa;font-weight:600;margin-bottom:1rem;letter-spacing:.05em;">
            ✨ GENERATED BY CLAUDE AI
          </div>
          <div style="color:#1e1b4b;line-height:1.75;white-space:pre-wrap;">{report_text}</div>
          <div class="ai-timestamp">Generated at: {generated_at}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="ai-card">
          <div style="color:#475569;text-align:center;padding:2rem;">
            No AI insights found. Run the <strong>04_ai_insights</strong> notebook in Databricks to generate a report.
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Billing vs stay scatter per condition
    conditions = data.get("conditions", pd.DataFrame())
    if not conditions.empty:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Billing vs Length of Stay by Condition</div>', unsafe_allow_html=True)
        fig = px.scatter(
            conditions,
            x="avg_stay_days", y="avg_billing",
            size="patient_count", color="medical_condition",
            color_discrete_sequence=PALETTE,
            labels={
                "avg_stay_days": "Avg Stay (days)",
                "avg_billing":   "Avg Billing ($)",
                "medical_condition": "Condition",
            },
            hover_data=["patient_count"],
        )
        fig.update_layout(**CHART_LAYOUT, height=360)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
# TAB 4 — Pipeline Status
# ════════════════════════════════════════════════════════
with tab4:
    counts = data.get("counts", {})

    # Medallion architecture diagram
    st.markdown("### 🏗️ Data Flow")

    cols = st.columns(9)

    items = [
        ("🌐", "GitHub\nCSV"),
        ("→", ""),
        ("⚡", "Azure\nADF"),
        ("→", ""),
        ("🗄️", "ADLS\nGen2"),
        ("→", ""),
        ("🥉", "Bronze\nRaw"),
        ("→", ""),
        ("🥈", "Silver\nClean"),
    ]

    for i, (icon, label) in enumerate(items):
        with cols[i]:
            if icon == "→":
                st.markdown(
                    "<div style='text-align:center;"
                    "font-size:1.5rem;padding-top:1rem'>"
                    "→</div>",
                    unsafe_allow_html=True
                )
            else:
                st.metric(label=label, value=icon)

    st.markdown("")

    cols2 = st.columns(5)
    items2 = [
        ("→", ""),
        ("🥇", "Gold\nAggregated"),
        ("→", ""),
        ("🤖", "Claude\nAI"),
        ("📊", "Dashboard"),
    ]

    for i, (icon, label) in enumerate(items2):
        with cols2[i]:
            if icon == "→":
                st.markdown(
                    "<div style='text-align:center;"
                    "font-size:1.5rem;padding-top:1rem'>"
                    "→</div>",
                    unsafe_allow_html=True
                )
            else:
                st.metric(label=label, value=icon)

    # Record counts per layer
    st.markdown('<div class="section-title">Record Counts by Layer</div>', unsafe_allow_html=True)
    layer_data = [
        ("🥉 Bronze",     counts.get("bronze",       "—"), "#b45309"),
        ("🥈 Silver",     counts.get("silver",       "—"), "#64748b"),
        ("🥇 Conditions", counts.get("conditions",   "—"), "#d97706"),
        ("🥇 Hospitals",  counts.get("hospitals",    "—"), "#d97706"),
        ("🥇 Demographics",counts.get("demographics","—"), "#d97706"),
    ]
    rcols = st.columns(5)
    for rcol, (label, count, color) in zip(rcols, layer_data):
        try:   display = f"{int(count):,}"
        except: display = str(count)
        rcol.markdown(f"""
        <div class="metric-card" style="border-color:rgba(255,255,255,.08)">
          <div class="metric-label">{label}</div>
          <div style="font-size:1.5rem;font-weight:700;color:{color};">{display}</div>
        </div>
        """, unsafe_allow_html=True)

    # ADF + Databricks info
    st.markdown("<br>", unsafe_allow_html=True)
    info_l, info_r = st.columns(2)
    with info_l:
        st.markdown('<div class="section-title">Azure Data Factory</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="glass-card">
          <div style="display:grid;gap:.5rem;font-size:.875rem;color:#475569;">
            <div>📌 <strong>ADF Name:</strong> {os.getenv('ADF_NAME','healthflow-adf')}</div>
            <div>📍 <strong>Location:</strong> {os.getenv('ADF_LOCATION','eastus')}</div>
            <div>🗄️ <strong>Storage:</strong> {os.getenv('STORAGE_ACCOUNT_NAME','healthflowstorage')}</div>
            <div>🔁 <strong>Schedule:</strong> Daily at midnight UTC</div>
            <div>📋 <strong>Pipelines:</strong> HealthcareIngestionPipeline, IncrementalIngestionPipeline</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    with info_r:
        st.markdown('<div class="section-title">Databricks Workspace</div>', unsafe_allow_html=True)
        host = os.getenv("DATABRICKS_HOST", "—")
        cluster = os.getenv("DATABRICKS_CLUSTER_ID", "—")
        st.markdown(f"""
        <div class="glass-card">
          <div style="display:grid;gap:.5rem;font-size:.875rem;color:#475569;">
            <div>🌐 <strong>Host:</strong> {host}</div>
            <div>⚙️  <strong>Cluster:</strong> {cluster}</div>
            <div>📁 <strong>Workspace:</strong> /HealthFlow/</div>
            <div>🗂️ <strong>Catalog:</strong> healthflow_catalog</div>
            <div>📓 <strong>Notebooks:</strong> Bronze → Silver → Gold → AI</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Gold tables breakdown chart
    conditions = data.get("conditions", pd.DataFrame())
    if not conditions.empty:
        st.markdown('<div class="section-title">Gold Layer — Conditions Overview</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Patient Count",
            x=conditions["medical_condition"],
            y=conditions["patient_count"],
            marker_color="#7c3aed",
            yaxis="y",
        ))
        fig.add_trace(go.Scatter(
            name="Avg Billing ($)",
            x=conditions["medical_condition"],
            y=conditions["avg_billing"],
            mode="lines+markers",
            line=dict(color="#06b6d4", width=2),
            marker=dict(size=8),
            yaxis="y2",
        ))
        fig.update_layout(
            **{k: v for k, v in CHART_LAYOUT.items() if k != "legend"},
            height=360,
            yaxis=dict(title="Patient Count",   showgrid=False, color="#94a3b8"),
            yaxis2=dict(title="Avg Billing ($)", overlaying="y", side="right", showgrid=False, color="#06b6d4"),
            legend=dict(orientation="h", y=1.1, bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig, use_container_width=True)
