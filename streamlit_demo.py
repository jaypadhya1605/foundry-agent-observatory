"""
Providence APIM & AI Gateway — Interactive Demo
=================================================
Streamlit app covering Parts 1-5 with visual diagrams and live execution.
Run:  streamlit run streamlit_demo.py
"""

import streamlit as st
import time
import os
import json
import subprocess
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

# ─── Page Config ──────────────────────────────────────────
st.set_page_config(
    page_title="Providence APIM AI Gateway Demo",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem; border-radius: 12px; color: white; text-align: center;
        margin: 0.3rem 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .metric-card h3 { margin: 0; font-size: 2rem; }
    .metric-card p { margin: 0; opacity: 0.85; font-size: 0.9rem; }
    .good-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem; border-radius: 10px; color: white; margin: 0.3rem 0;
    }
    .bad-card {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
        padding: 1rem; border-radius: 10px; color: white; margin: 0.3rem 0;
    }
    .info-card {
        background: linear-gradient(135deg, #0078d4 0%, #00bcf2 100%);
        padding: 1rem; border-radius: 10px; color: white; margin: 0.3rem 0;
    }
    .arch-box {
        border: 2px solid #0078d4; border-radius: 10px; padding: 1rem;
        text-align: center; font-weight: bold; margin: 0.3rem;
    }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px; border-radius: 8px 8px 0 0;
        font-weight: 600;
    }
    div[data-testid="stExpander"] details summary p { font-size: 1.1rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ─── Configuration ────────────────────────────────────────
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT", "https://ai-apim-demo-jp-001.cognitiveservices.azure.com/")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "651b2ef7-550d-4f5f-971f-166a3f599e7c")
GATEWAY_URL = os.getenv("APIM_GATEWAY_URL", "https://apim-providence-demo-jp-001.azure-api.net")
SUBSCRIPTION_KEY = os.getenv("APIM_SUBSCRIPTION_KEY", "")
API_VERSION = "2024-02-01"

QUESTIONS = [
    "What are the symptoms of pneumonia?",
    "How does insulin resistance develop?",
    "What is the treatment for hypertension?",
    "Explain the stages of wound healing.",
    "What are common side effects of chemotherapy?",
    "How is Type 2 diabetes diagnosed?",
    "What is the difference between MRI and CT scan?",
    "Explain the mechanism of action of statins.",
    "What are the warning signs of a stroke?",
    "How does the immune system fight infection?",
]


# ─── Helper: Architecture Diagrams (Plotly) ──────────────
def draw_architecture_before():
    """Draw the 'before' architecture — direct calls with no gateway."""
    fig = go.Figure()
    # Apps
    apps = ["App 1<br>(Patient Portal)", "App 2<br>(Clinical Tool)", "App 3<br>(Admin)"]
    for i, app in enumerate(apps):
        y = 3 - i * 1.2
        fig.add_shape(type="rect", x0=0.2, y0=y-0.4, x1=2.2, y1=y+0.4,
                      fillcolor="#ef4444", opacity=0.9, line_color="#dc2626", line_width=2)
        fig.add_annotation(x=1.2, y=y, text=app, showarrow=False,
                           font=dict(color="white", size=13, family="Arial Black"))
        # Arrow to Azure OpenAI
        fig.add_annotation(x=5.5, y=y, ax=2.3, ay=y, showarrow=True,
                           arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor="#ef4444")
        fig.add_annotation(x=3.9, y=y+0.15, text="🔑 API Key", showarrow=False,
                           font=dict(size=10, color="#ef4444"))

    # Azure OpenAI box
    fig.add_shape(type="rect", x0=5.5, y0=0, x1=8.5, y1=3.4,
                  fillcolor="#3b82f6", opacity=0.9, line_color="#2563eb", line_width=2)
    fig.add_annotation(x=7, y=2.4, text="<b>Azure OpenAI</b>", showarrow=False,
                       font=dict(color="white", size=15))
    fig.add_annotation(x=7, y=1.7, text="gpt-4o", showarrow=False,
                       font=dict(color="white", size=12))
    fig.add_annotation(x=7, y=1.0, text="❌ No rate limits<br>❌ No caching<br>❌ No metrics",
                       showarrow=False, font=dict(color="#fca5a5", size=11))

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.5, 9.5]),
        yaxis=dict(visible=False, range=[-0.8, 4.2]),
        height=320, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_architecture_after():
    """Draw the 'after' architecture — with APIM AI Gateway."""
    fig = go.Figure()
    # Apps
    apps = ["App 1<br>(Patient Portal)", "App 2<br>(Clinical Tool)", "App 3<br>(Admin)"]
    for i, app in enumerate(apps):
        y = 3 - i * 1.2
        fig.add_shape(type="rect", x0=0.1, y0=y-0.4, x1=2.0, y1=y+0.4,
                      fillcolor="#6366f1", opacity=0.9, line_color="#4f46e5", line_width=2)
        fig.add_annotation(x=1.05, y=y, text=app, showarrow=False,
                           font=dict(color="white", size=11, family="Arial Black"))
        # Arrow to APIM
        fig.add_annotation(x=3.0, y=y, ax=2.1, ay=y, showarrow=True,
                           arrowhead=2, arrowsize=1.3, arrowwidth=2, arrowcolor="#6366f1")

    # Sub key label
    fig.add_annotation(x=2.55, y=3.6, text="🔐 Subscription Keys", showarrow=False,
                       font=dict(size=11, color="#6366f1"))

    # APIM Gateway box
    fig.add_shape(type="rect", x0=3.0, y0=-0.3, x1=7.0, y1=3.7,
                  fillcolor="#0078d4", opacity=0.95, line_color="#005a9e", line_width=3)
    fig.add_annotation(x=5.0, y=3.3, text="<b>APIM AI Gateway</b>", showarrow=False,
                       font=dict(color="white", size=15, family="Arial Black"))
    policies = [
        "🔐 Managed Identity Auth",
        "💾 Semantic Cache Check",
        "⏱️ Token Rate Limiting",
        "📊 Token Metrics Emission",
        "🛡️ Content Safety Filter",
        "🔄 Load Balancing (429-aware)",
    ]
    for i, p in enumerate(policies):
        fig.add_annotation(x=5.0, y=2.6 - i * 0.45, text=p, showarrow=False,
                           font=dict(color="white", size=11))

    # Arrow to backends
    fig.add_annotation(x=8.2, y=2.5, ax=7.1, ay=2.5, showarrow=True,
                       arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor="#10b981")
    fig.add_annotation(x=8.2, y=0.8, ax=7.1, ay=0.8, showarrow=True,
                       arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor="#f59e0b")
    fig.add_annotation(x=7.55, y=3.0, text="Managed<br>Identity", showarrow=False,
                       font=dict(size=9, color="#10b981"))

    # Azure OpenAI
    fig.add_shape(type="rect", x0=8.2, y0=1.9, x1=10.8, y1=3.1,
                  fillcolor="#10b981", opacity=0.9, line_color="#059669", line_width=2)
    fig.add_annotation(x=9.5, y=2.5, text="<b>Azure OpenAI</b><br>gpt-4o", showarrow=False,
                       font=dict(color="white", size=12))

    # Content Understanding
    fig.add_shape(type="rect", x0=8.2, y0=0.2, x1=10.8, y1=1.4,
                  fillcolor="#f59e0b", opacity=0.9, line_color="#d97706", line_width=2)
    fig.add_annotation(x=9.5, y=0.8, text="<b>Content<br>Understanding</b>", showarrow=False,
                       font=dict(color="white", size=12))

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.5, 11.5]),
        yaxis=dict(visible=False, range=[-0.8, 4.2]),
        height=350, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_semantic_cache_flow():
    """Draw semantic caching flow diagram."""
    fig = go.Figure()

    steps = [
        (0.5, 2, "📝 Incoming<br>Prompt", "#6366f1"),
        (2.8, 2, "🔢 Generate<br>Embedding", "#0078d4"),
        (5.1, 2, "🔍 Search<br>Redis Cache", "#f59e0b"),
    ]
    for x, y, text, color in steps:
        fig.add_shape(type="rect", x0=x, y0=y-0.6, x1=x+1.8, y1=y+0.6,
                      fillcolor=color, opacity=0.9, line_color=color, line_width=2)
        fig.add_annotation(x=x+0.9, y=y, text=text, showarrow=False,
                           font=dict(color="white", size=12, family="Arial Black"))

    # Arrows between steps
    for x1, x2 in [(2.3, 2.8), (4.6, 5.1)]:
        fig.add_annotation(x=x2, y=2, ax=x1, ay=2, showarrow=True,
                           arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor="#666")

    # Cache HIT branch
    fig.add_shape(type="rect", x0=7.8, y0=2.8, x1=10.0, y1=3.7,
                  fillcolor="#10b981", opacity=0.9, line_color="#059669", line_width=2)
    fig.add_annotation(x=8.9, y=3.25, text="✅ Cache HIT<br>Return cached response",
                       showarrow=False, font=dict(color="white", size=11))
    fig.add_annotation(x=7.8, y=3.25, ax=6.9, ay=2.4, showarrow=True,
                       arrowhead=2, arrowsize=1.3, arrowwidth=2, arrowcolor="#10b981")
    fig.add_annotation(x=7.3, y=2.9, text="≥ 80%<br>similar", showarrow=False,
                       font=dict(size=10, color="#10b981"))

    # Cache MISS branch
    fig.add_shape(type="rect", x0=7.8, y0=0.3, x1=10.0, y1=1.2,
                  fillcolor="#ef4444", opacity=0.9, line_color="#dc2626", line_width=2)
    fig.add_annotation(x=8.9, y=0.75, text="❌ Cache MISS<br>Forward to Azure OpenAI",
                       showarrow=False, font=dict(color="white", size=11))
    fig.add_annotation(x=7.8, y=0.75, ax=6.9, ay=1.6, showarrow=True,
                       arrowhead=2, arrowsize=1.3, arrowwidth=2, arrowcolor="#ef4444")
    fig.add_annotation(x=7.3, y=1.1, text="< 80%<br>similar", showarrow=False,
                       font=dict(size=10, color="#ef4444"))

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.2, 10.8]),
        yaxis=dict(visible=False, range=[-0.2, 4.2]),
        height=280, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def draw_gateway_policy_pipeline():
    """Draw the request flow through APIM policies."""
    fig = go.Figure()
    stages = [
        ("🔐 Auth\n(Managed ID)", "#6366f1"),
        ("💾 Cache\nLookup", "#f59e0b"),
        ("⏱️ Token\nRate Limit", "#ef4444"),
        ("📊 Emit\nMetrics", "#0078d4"),
        ("🛡️ Content\nSafety", "#10b981"),
        ("➡️ Forward\nto Backend", "#8b5cf6"),
    ]
    for i, (text, color) in enumerate(stages):
        x = i * 1.7 + 0.3
        fig.add_shape(type="rect", x0=x, y0=0.5, x1=x+1.4, y1=1.9,
                      fillcolor=color, opacity=0.9, line_color=color, line_width=2)
        fig.add_annotation(x=x+0.7, y=1.2, text=text, showarrow=False,
                           font=dict(color="white", size=11, family="Arial Black"))
        if i < len(stages) - 1:
            fig.add_annotation(x=x+1.55, y=1.2, ax=x+1.45, ay=1.2, showarrow=True,
                               arrowhead=2, arrowsize=1.5, arrowwidth=2, arrowcolor="#666")

    fig.add_annotation(x=0.3, y=2.2, text="<b>INBOUND POLICY PIPELINE</b>", showarrow=False,
                       font=dict(size=13, color="#333"), xanchor="left")

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.2, 10.8]),
        yaxis=dict(visible=False, range=[0, 2.6]),
        height=180, margin=dict(l=0, r=0, t=10, b=10),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


# ─── Azure OpenAI Client (lazy init) ─────────────────────
@st.cache_resource
def get_openai_client():
    from azure.identity import DefaultAzureCredential
    from openai import AzureOpenAI
    credential = DefaultAzureCredential(
        additionally_allowed_tenants=["*"],
        exclude_shared_token_cache_credential=True,
    )
    token = credential.get_token(
        "https://cognitiveservices.azure.com/.default",
        tenant_id=TENANT_ID,
    )
    return AzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=token.token,
        api_version="2025-01-01-preview",
    )


def call_direct(question, client):
    """Call Azure OpenAI directly (no APIM)."""
    start = time.time()
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a healthcare assistant. Be concise."},
            {"role": "user", "content": question},
        ],
        max_completion_tokens=200,
        temperature=0.7,
    )
    elapsed = time.time() - start
    return {
        "question": question,
        "tokens": resp.usage.total_tokens,
        "prompt_tokens": resp.usage.prompt_tokens,
        "completion_tokens": resp.usage.completion_tokens,
        "latency_ms": round(elapsed * 1000),
        "cost_est": round((resp.usage.prompt_tokens * 5 + resp.usage.completion_tokens * 15) / 1_000_000, 6),
        "answer": resp.choices[0].message.content[:200],
    }


def call_via_apim(question):
    """Call Azure OpenAI through APIM gateway."""
    import requests
    url = f"{GATEWAY_URL}/openai/deployments/{MODEL_NAME}/chat/completions?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    }
    body = {
        "messages": [
            {"role": "system", "content": "You are a healthcare assistant. Be concise."},
            {"role": "user", "content": question},
        ],
        "max_tokens": 200,
        "temperature": 0.7,
    }
    start = time.time()
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    elapsed = time.time() - start
    result = {
        "question": question,
        "status": resp.status_code,
        "latency_ms": round(elapsed * 1000),
        "request_id": resp.headers.get("x-apim-request-id", "N/A"),
        "model": resp.headers.get("x-apim-model", "N/A"),
        "region": resp.headers.get("x-apim-region", "N/A"),
        "cache_status": resp.headers.get("x-cache-status", "N/A"),
    }
    if resp.status_code == 200:
        data = resp.json()
        usage = data.get("usage", {})
        result["tokens"] = usage.get("total_tokens", 0)
        result["prompt_tokens"] = usage.get("prompt_tokens", 0)
        result["completion_tokens"] = usage.get("completion_tokens", 0)
        result["cost_est"] = round((result["prompt_tokens"] * 5 + result["completion_tokens"] * 15) / 1_000_000, 6)
        result["answer"] = data["choices"][0]["message"]["content"][:200]
    elif resp.status_code == 429:
        result["tokens"] = 0
        result["cost_est"] = 0
        result["answer"] = "🛑 RATE LIMITED (429)"
    else:
        result["tokens"] = 0
        result["cost_est"] = 0
        result["answer"] = f"Error {resp.status_code}: {resp.text[:150]}"
    return result


# ═══════════════════════════════════════════════════════════
#                      SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/microsoft.png", width=48)
    st.title("🛡️ APIM AI Gateway")
    st.caption("Providence Deep Dive Demo")
    st.divider()

    part = st.radio(
        "**Select Demo Part**",
        [
            "🏠 Overview",
            "1️⃣ Without APIM",
            "2️⃣ Setup AI Gateway",
            "3️⃣ With APIM",
            "4️⃣ Semantic Caching",
            "5️⃣ Budget & Alerts",
        ],
        index=0,
    )

    st.divider()
    st.markdown("**Resources**")
    st.code(f"Subscription:\n06c76c82-...-2e90af4bdd04", language=None)
    st.code(f"RG:\nrg-apim-providence-demo-jp-001", language=None)
    st.caption("April 2026 | Microsoft Azure")


# ═══════════════════════════════════════════════════════════
#              PART 0: OVERVIEW
# ═══════════════════════════════════════════════════════════
if part == "🏠 Overview":
    st.title("Azure API Management as an AI Gateway")
    st.markdown("**Govern, Observe & Optimize Your AI Workloads — Providence Health & Services**")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><h3>5</h3><p>Demo Parts</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><h3>60-80%</h3><p>Cost Savings (Cache)</p></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><h3>$0</h3><p>APIM Base Cost</p></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><h3>$2,500</h3><p>Monthly Budget</p></div>', unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("Architecture: Before vs. After")
    tab1, tab2 = st.tabs(["❌ Without APIM", "✅ With APIM AI Gateway"])
    with tab1:
        st.plotly_chart(draw_architecture_before(), use_container_width=True)
        st.error("**Problems:** API key sprawl • No rate limiting • No caching • No metrics • Costs spiral")
    with tab2:
        st.plotly_chart(draw_architecture_after(), use_container_width=True)
        st.success("**Benefits:** Managed identity • Token budgets • Semantic cache • Central metrics • Content safety")

    st.markdown("---")
    st.subheader("Gateway Policy Pipeline")
    st.plotly_chart(draw_gateway_policy_pipeline(), use_container_width=True)
    st.info("Every request passes through this pipeline. Policies execute in order: Auth → Cache → Limit → Metrics → Safety → Forward.")


# ═══════════════════════════════════════════════════════════
#              PART 1: WITHOUT APIM
# ═══════════════════════════════════════════════════════════
elif part == "1️⃣ Without APIM":
    st.title("Part 1: Without APIM — Direct Azure OpenAI Calls")
    st.markdown("No governance, no caching, no rate limiting, no token tracking.")

    st.plotly_chart(draw_architecture_before(), use_container_width=True)

    st.markdown("---")

    # ── Demo 1: Rapid requests ─────────────────────────────
    st.subheader("📌 Demo 1: No Rate Limiting — 10 Rapid Requests")
    st.markdown("Fire 10 healthcare questions directly at Azure OpenAI. Nothing stops the token burn.")

    if st.button("🔴 Run 10 Direct Calls (No Governance)", type="primary", key="d1_run"):
        client = get_openai_client()
        results = []
        progress = st.progress(0, text="Sending requests...")
        cols_header = st.columns([4, 1, 1, 1])
        cols_header[0].markdown("**Question**")
        cols_header[1].markdown("**Tokens**")
        cols_header[2].markdown("**Latency**")
        cols_header[3].markdown("**Cost**")

        result_container = st.container()

        for i, q in enumerate(QUESTIONS):
            r = call_direct(q, client)
            results.append(r)
            progress.progress((i + 1) / 10, text=f"Request {i+1}/10...")
            with result_container:
                cols = st.columns([4, 1, 1, 1])
                cols[0].text(f"{q[:50]}")
                cols[1].code(f"{r['tokens']}")
                cols[2].code(f"{r['latency_ms']}ms")
                cols[3].code(f"${r['cost_est']:.6f}")

        progress.empty()
        st.session_state["part1_results"] = results

        # Summary metrics
        total_tokens = sum(r["tokens"] for r in results)
        total_cost = sum(r["cost_est"] for r in results)
        avg_latency = sum(r["latency_ms"] for r in results) / len(results)

        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Tokens", f"{total_tokens:,}", delta="No limit!", delta_color="inverse")
        c2.metric("Total Cost", f"${total_cost:.4f}", delta="Uncontrolled")
        c3.metric("Avg Latency", f"{avg_latency:.0f}ms")

        st.error("⚠️ No rate limit hit. No cost control. No visibility. Tokens burn freely.")

    # ── Demo 2: No caching ──────────────────────────────────
    st.markdown("---")
    st.subheader("📌 Demo 2: No Caching — Same Question, Same Cost")
    st.markdown("Ask the **exact same question** 5 times. Full price every time.")

    if st.button("🔴 Ask Same Question 5x (No Cache)", type="primary", key="d2_run"):
        client = get_openai_client()
        repeat_results = []
        for i in range(5):
            r = call_direct("What are the symptoms of pneumonia?", client)
            repeat_results.append(r)

        df = pd.DataFrame(repeat_results)
        df.index = [f"Call {i+1}" for i in range(5)]
        df_display = df[["tokens", "latency_ms", "cost_est"]].copy()
        df_display.columns = ["Tokens", "Latency (ms)", "Cost ($)"]
        st.dataframe(df_display, use_container_width=True)

        wasted = sum(r["tokens"] for r in repeat_results[1:])
        st.error(f"⚠️ Wasted **{wasted} tokens** on duplicate questions. With caching → ~0 after first call.")

        # Bar chart
        fig = px.bar(
            x=[f"Call {i+1}" for i in range(5)],
            y=[r["tokens"] for r in repeat_results],
            labels={"x": "Call", "y": "Tokens Used"},
            title="Tokens Per Identical Call (No Caching)",
            color_discrete_sequence=["#ef4444"],
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)

    # ── Summary ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("Summary: What's Missing")
    cols = st.columns(3)
    for i, (icon, text) in enumerate([
        ("❌", "No Rate Limiting → Costs spiral"),
        ("❌", "No Caching → Duplicate cost"),
        ("❌", "No Content Safety → Single layer"),
    ]):
        with cols[i]:
            st.markdown(f'<div class="bad-card">{icon} {text}</div>', unsafe_allow_html=True)
    cols2 = st.columns(3)
    for i, (icon, text) in enumerate([
        ("❌", "No Token Metrics → Blind"),
        ("❌", "No Load Balancing → SPOF"),
        ("❌", "No Multi-tenant → No isolation"),
    ]):
        with cols2[i]:
            st.markdown(f'<div class="bad-card">{icon} {text}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#              PART 2: SETUP APIM GATEWAY
# ═══════════════════════════════════════════════════════════
elif part == "2️⃣ Setup AI Gateway":
    st.title("Part 2: Setting Up APIM as AI Gateway")
    st.markdown("Automated 5-step setup — from zero to governed AI in minutes.")

    # Policy pipeline diagram
    st.plotly_chart(draw_gateway_policy_pipeline(), use_container_width=True)

    st.markdown("---")

    # Steps visual
    steps = [
        ("Step 1", "Create APIM", "Consumption tier ($0 base). Enable managed identity.", "🏗️"),
        ("Step 2", "Grant RBAC", "APIM → 'Cognitive Services User' on Azure OpenAI. No API keys.", "🔐"),
        ("Step 3", "Create Backend", "Point APIM to Azure OpenAI endpoint.", "🔗"),
        ("Step 4", "Import API Spec", "Import OpenAI inference API at path /openai.", "📋"),
        ("Step 5", "Apply AI Policies", "Token limits, metrics, caching — the AI Gateway transformation.", "🛡️"),
    ]

    for step_name, title, desc, icon in steps:
        with st.expander(f"{icon}  {step_name}: {title}", expanded=False):
            st.markdown(desc)

    st.markdown("---")
    st.subheader("Run Setup Script")
    st.warning("⚠️ This creates Azure resources. Only run if resources don't exist yet.")

    if st.button("🟢 Run 02-setup-apim-gateway.py", type="primary", key="setup_run"):
        with st.spinner("Setting up APIM AI Gateway... (this may take a few minutes)"):
            script_path = os.path.join(os.path.dirname(__file__), "02-setup-apim-gateway.py")
            result = subprocess.run(
                ["python", script_path],
                capture_output=True, text=True, timeout=600,
                cwd=os.path.dirname(__file__),
            )
            if result.returncode == 0:
                st.success("✅ APIM AI Gateway setup complete!")
            else:
                st.error("Setup encountered issues.")
            with st.expander("📄 Full Output", expanded=True):
                st.code(result.stdout + result.stderr, language="text")

    # Gateway policy XML
    st.markdown("---")
    st.subheader("Gateway Policy (XML)")
    policy_xml = """<policies>
  <inbound>
    <base />
    <set-backend-service backend-id="openai-backend" />
    <authentication-managed-identity
        resource="https://cognitiveservices.azure.com" />
    <azure-openai-token-limit
        tokens-per-minute="10000"
        counter-key="@(context.Subscription.Id)"
        estimate-prompt-tokens="true" />
    <azure-openai-emit-token-metric namespace="AzureOpenAI">
        <dimension name="Subscription" />
        <dimension name="Model" />
    </azure-openai-emit-token-metric>
  </inbound>
  <outbound>
    <base />
    <set-header name="x-apim-request-id" exists-action="override">
        <value>@(context.RequestId.ToString())</value>
    </set-header>
  </outbound>
</policies>"""
    st.code(policy_xml, language="xml")

    # Resources table
    st.markdown("---")
    st.subheader("Resources Created")
    st.dataframe(pd.DataFrame([
        {"Resource": "apim-providence-demo-jp-001", "Type": "API Management", "SKU": "Consumption", "Est. Cost": "~$3.50/M calls"},
        {"Resource": "ai-apim-demo-jp-001", "Type": "AI Services", "SKU": "S0", "Est. Cost": "Pay-per-token"},
        {"Resource": "cu-providence-demo-jp-001", "Type": "Content Understanding", "SKU": "S0", "Est. Cost": "Pay-per-page"},
        {"Resource": "appinsights-apim-demo-jp-001", "Type": "Application Insights", "SKU": "Free", "Est. Cost": "$0"},
    ]), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#              PART 3: WITH APIM
# ═══════════════════════════════════════════════════════════
elif part == "3️⃣ With APIM":
    st.title("Part 3: With APIM — Governed AI Calls")
    st.markdown("Same 10 questions, now routed through the AI Gateway.")

    st.plotly_chart(draw_architecture_after(), use_container_width=True)

    if not SUBSCRIPTION_KEY:
        st.warning("⚠️ Set `APIM_SUBSCRIPTION_KEY` in your `.env` file to enable live calls through the gateway.")

    st.markdown("---")

    # ── Demo 1: Governed calls ─────────────────────────────
    st.subheader("📌 Demo 1: Centralized Gateway with Request Tracking")

    if st.button("🟢 Run 10 Governed Calls via APIM", type="primary", key="d3_run"):
        results = []
        progress = st.progress(0, text="Sending governed requests through APIM...")

        for i, q in enumerate(QUESTIONS):
            r = call_via_apim(q)
            results.append(r)
            progress.progress((i + 1) / 10, text=f"Request {i+1}/10...")

        progress.empty()
        st.session_state["part3_results"] = results

        # Results table
        df = pd.DataFrame(results)
        display_cols = ["question", "tokens", "latency_ms", "request_id", "model", "region"]
        available = [c for c in display_cols if c in df.columns]
        st.dataframe(df[available], use_container_width=True, hide_index=True)

        # Metrics
        total_tokens = sum(r.get("tokens", 0) for r in results)
        total_cost = sum(r.get("cost_est", 0) for r in results)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tokens", f"{total_tokens:,}")
        c2.metric("Total Cost", f"${total_cost:.4f}")
        c3.metric("Tracked Requests", f"{len(results)}/10", delta="All tracked ✅")
        c4.metric("Auth Method", "Managed Identity 🔐")

        st.success("✅ Every call tracked with unique request ID, model info, and region metadata.")

    # ── Demo 2: Subscription key governance ────────────────
    st.markdown("---")
    st.subheader("📌 Demo 2: Subscription Key Governance")
    st.markdown("Without a valid key, APIM blocks the request. No key = no access.")

    if st.button("🟢 Test Key Governance", key="d3_keys"):
        import requests
        url = f"{GATEWAY_URL}/openai/deployments/{MODEL_NAME}/chat/completions?api-version={API_VERSION}"
        body = {"messages": [{"role": "user", "content": "test"}], "max_tokens": 5}

        c1, c2, c3 = st.columns(3)
        # No key
        resp = requests.post(url, headers={"Content-Type": "application/json"}, json=body, timeout=10)
        with c1:
            st.markdown(f'<div class="bad-card">🔒 No Key<br>Status: <b>{resp.status_code}</b> — BLOCKED</div>',
                        unsafe_allow_html=True)
        # Wrong key
        resp = requests.post(url, headers={"Content-Type": "application/json",
                                           "Ocp-Apim-Subscription-Key": "invalid-key"},
                             json=body, timeout=10)
        with c2:
            st.markdown(f'<div class="bad-card">🔑 Wrong Key<br>Status: <b>{resp.status_code}</b> — BLOCKED</div>',
                        unsafe_allow_html=True)
        # Valid key
        if SUBSCRIPTION_KEY:
            resp = requests.post(url, headers={"Content-Type": "application/json",
                                               "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY},
                                 json=body, timeout=10)
            with c3:
                st.markdown(f'<div class="good-card">✅ Valid Key<br>Status: <b>{resp.status_code}</b> — ALLOWED</div>',
                            unsafe_allow_html=True)
        else:
            with c3:
                st.markdown('<div class="info-card">ℹ️ Valid Key<br>Set APIM_SUBSCRIPTION_KEY to test</div>',
                            unsafe_allow_html=True)

    # ── Comparison table ───────────────────────────────────
    st.markdown("---")
    st.subheader("📊 Before vs. After Comparison")
    comparison = pd.DataFrame([
        {"Feature": "Gateway Routing", "Without APIM": "❌ Direct calls", "With APIM": "✅ Centralized"},
        {"Feature": "Auth to OpenAI", "Without APIM": "🔑 API Key", "With APIM": "🔐 Managed Identity"},
        {"Feature": "Access Control", "Without APIM": "❌ Shared keys", "With APIM": "✅ Per-app sub keys"},
        {"Feature": "Request Tracking", "Without APIM": "❌ None", "With APIM": "✅ Unique request IDs"},
        {"Feature": "Token Rate Limiting", "Without APIM": "❌ None", "With APIM": "✅ BasicV2+ policy"},
        {"Feature": "Semantic Caching", "Without APIM": "❌ None", "With APIM": "✅ BasicV2+ + Redis"},
        {"Feature": "Centralized Metrics", "Without APIM": "❌ None", "With APIM": "✅ App Insights"},
        {"Feature": "Content Safety", "Without APIM": "Model only", "With APIM": "✅ APIM + Model"},
    ])
    st.dataframe(comparison, use_container_width=True, hide_index=True)

    # Side-by-side chart if both part1 and part3 results exist
    if "part1_results" in st.session_state and "part3_results" in st.session_state:
        st.markdown("---")
        st.subheader("📊 Latency Comparison: Direct vs. APIM")
        p1 = st.session_state["part1_results"]
        p3 = st.session_state["part3_results"]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name="Direct (No APIM)", x=[f"Q{i+1}" for i in range(10)],
            y=[r["latency_ms"] for r in p1], marker_color="#ef4444",
        ))
        fig.add_trace(go.Bar(
            name="Via APIM", x=[f"Q{i+1}" for i in range(10)],
            y=[r.get("latency_ms", 0) for r in p3], marker_color="#10b981",
        ))
        fig.update_layout(barmode="group", height=350, title="Latency Per Question (ms)")
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════
#              PART 4: SEMANTIC CACHING
# ═══════════════════════════════════════════════════════════
elif part == "4️⃣ Semantic Caching":
    st.title("Part 4: Semantic Caching — Save 60-80%")
    st.markdown("APIM uses embeddings to match **semantically similar** prompts to cached responses.")

    # Cache flow diagram
    st.plotly_chart(draw_semantic_cache_flow(), use_container_width=True)

    st.markdown("---")

    # ── Demo 1: Exact match ───────────────────────────────
    st.subheader("📌 Demo 1: Identical Questions (Exact Cache Hit)")
    st.markdown("Ask the **exact same question** 5 times. After first call, responses come from cache.")

    if st.button("🟢 Run 5x Identical Queries via APIM", type="primary", key="d4_exact"):
        results = []
        q = "What are the symptoms of pneumonia?"
        for i in range(5):
            r = call_via_apim(q)
            r["call_num"] = i + 1
            results.append(r)

        df = pd.DataFrame(results)
        df_display = df[["call_num", "tokens", "latency_ms", "cache_status"]].copy()
        df_display.columns = ["Call #", "Tokens", "Latency (ms)", "Cache Status"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # Chart
        colors = ["#ef4444" if r["cache_status"] in ("MISS", "N/A") else "#10b981" for r in results]
        fig = go.Figure(go.Bar(
            x=[f"Call {i+1}" for i in range(5)],
            y=[r["latency_ms"] for r in results],
            marker_color=colors,
            text=[r.get("cache_status", "N/A") for r in results],
            textposition="outside",
        ))
        fig.update_layout(height=300, title="Latency Per Call (Cached vs. Uncached)",
                          yaxis_title="Latency (ms)")
        st.plotly_chart(fig, use_container_width=True)

    # ── Demo 2: Semantic similarity ───────────────────────
    st.markdown("---")
    st.subheader("📌 Demo 2: Similar Questions (Semantic Cache Hit)")
    st.markdown("Different wording, **same intent** — semantic caching recognizes the similarity.")

    similar_qs = [
        "What are the symptoms of pneumonia?",
        "What symptoms does pneumonia cause?",
        "How do I know if I have pneumonia?",
        "Signs and symptoms of pneumonia",
        "Pneumonia symptoms list",
    ]

    if st.button("🟢 Run 5 Semantically Similar Queries", type="primary", key="d4_semantic"):
        results = []
        for i, q in enumerate(similar_qs):
            r = call_via_apim(q)
            r["label"] = "ORIGINAL" if i == 0 else "SIMILAR"
            results.append(r)

        for r in results:
            label_color = "good-card" if r.get("cache_status") == "HIT" else ("bad-card" if r["label"] == "ORIGINAL" else "info-card")
            st.markdown(
                f'<div class="{label_color}">'
                f'<b>[{r["label"]}]</b> {r["question"]}<br>'
                f'Latency: {r["latency_ms"]}ms | Tokens: {r.get("tokens", 0)} | Cache: {r.get("cache_status", "N/A")}'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Demo 3: Cost savings projection ───────────────────
    st.markdown("---")
    st.subheader("📌 Demo 3: Cost Savings Projection")

    scenarios = [
        {"Workload": "Patient FAQ (high repetition)", "Calls/Day": 5000, "Cache Hit Rate": 0.80},
        {"Workload": "Clinical Decision Support", "Calls/Day": 2000, "Cache Hit Rate": 0.60},
        {"Workload": "Mixed Workload", "Calls/Day": 3000, "Cache Hit Rate": 0.70},
    ]
    avg_tokens = 300
    cost_rate = 0.01  # per 1K tokens

    savings_data = []
    for s in scenarios:
        cost_without = s["Calls/Day"] * avg_tokens * cost_rate / 1000
        cost_with = s["Calls/Day"] * (1 - s["Cache Hit Rate"]) * avg_tokens * cost_rate / 1000
        savings = cost_without - cost_with
        savings_data.append({
            "Workload": s["Workload"],
            "Calls/Day": s["Calls/Day"],
            "Cache Hit Rate": f"{s['Cache Hit Rate']:.0%}",
            "Daily Cost (No Cache)": f"${cost_without:.2f}",
            "Daily Cost (With Cache)": f"${cost_with:.2f}",
            "Daily Savings": f"${savings:.2f}",
            "Monthly Savings": f"${savings * 30:.0f}",
        })

    st.dataframe(pd.DataFrame(savings_data), use_container_width=True, hide_index=True)

    # Chart
    fig = go.Figure()
    for s, sd in zip(scenarios, savings_data):
        cost_no = s["Calls/Day"] * avg_tokens * cost_rate / 1000
        cost_yes = s["Calls/Day"] * (1 - s["Cache Hit Rate"]) * avg_tokens * cost_rate / 1000
        fig.add_trace(go.Bar(name=f"{s['Workload']}", x=["Without Cache", "With Cache"], y=[cost_no * 30, cost_yes * 30]))
    fig.update_layout(barmode="group", title="Monthly Cost: With vs. Without Semantic Cache",
                      yaxis_title="Cost ($)", height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 Redis Enterprise costs ~$200/mo but saves $1,000+/mo in tokens at scale.")


# ═══════════════════════════════════════════════════════════
#              PART 5: BUDGET & ALERTS
# ═══════════════════════════════════════════════════════════
elif part == "5️⃣ Budget & Alerts":
    st.title("Part 5: Budget & Cost Alerts")
    st.markdown("Automated budget alerts — know before you overspend.")

    # Budget visual
    st.subheader("Budget Configuration: $25/month")

    budget = 25
    thresholds = [
        {"Threshold": "25%", "Amount": f"${budget * 0.25:.2f}", "Action": "Informational", "Color": "#10b981"},
        {"Threshold": "50%", "Amount": f"${budget * 0.50:.2f}", "Action": "Review usage", "Color": "#f59e0b"},
        {"Threshold": "75%", "Amount": f"${budget * 0.75:.2f}", "Action": "Investigate!", "Color": "#f97316"},
        {"Threshold": "90%", "Amount": f"${budget * 0.90:.2f}", "Action": "Take action!", "Color": "#ef4444"},
    ]

    cols = st.columns(4)
    for i, t in enumerate(thresholds):
        with cols[i]:
            st.markdown(
                f'<div style="background:{t["Color"]};padding:1rem;border-radius:10px;color:white;text-align:center;">'
                f'<h3 style="margin:0;">{t["Threshold"]}</h3>'
                f'<p style="margin:0;font-size:1.5rem;font-weight:bold;">{t["Amount"]}</p>'
                f'<p style="margin:0;opacity:0.9;">{t["Action"]}</p></div>',
                unsafe_allow_html=True,
            )

    # Budget gauge
    st.markdown("---")
    st.subheader("Budget Usage Gauge")

    current_spend = st.slider("Simulated Current Spend ($)", 0.0, 30.0, 8.0, 0.5)
    pct = min(current_spend / budget * 100, 120)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_spend,
        delta={"reference": budget, "increasing": {"color": "red"}, "decreasing": {"color": "green"}},
        title={"text": "Current Spend vs. $25 Budget"},
        number={"prefix": "$", "font": {"size": 48}},
        gauge={
            "axis": {"range": [0, 30], "tickprefix": "$"},
            "bar": {"color": "#0078d4"},
            "steps": [
                {"range": [0, 6.25], "color": "#d1fae5"},
                {"range": [6.25, 12.50], "color": "#fef3c7"},
                {"range": [12.50, 18.75], "color": "#fed7aa"},
                {"range": [18.75, 25], "color": "#fecaca"},
                {"range": [25, 30], "color": "#ef4444"},
            ],
            "threshold": {"line": {"color": "red", "width": 4}, "thickness": 0.75, "value": budget},
        },
    ))
    fig.update_layout(height=350)
    st.plotly_chart(fig, use_container_width=True)

    if current_spend > budget:
        st.error(f"🔴 OVER BUDGET by ${current_spend - budget:.2f}!")
    elif current_spend > budget * 0.9:
        st.warning(f"🟠 90% threshold breached! ${budget - current_spend:.2f} remaining.")
    elif current_spend > budget * 0.75:
        st.warning(f"🟡 75% threshold breached. Review usage.")
    else:
        st.success(f"🟢 Within budget. ${budget - current_spend:.2f} remaining.")

    # Run budget setup
    st.markdown("---")
    st.subheader("Setup Budget Alerts on Azure")

    if st.button("🟢 Run 05-setup-budget-alerts.py", type="primary", key="budget_run"):
        with st.spinner("Creating budget alerts..."):
            script_path = os.path.join(os.path.dirname(__file__), "05-setup-budget-alerts.py")
            result = subprocess.run(
                ["python", script_path],
                capture_output=True, text=True, timeout=120,
                cwd=os.path.dirname(__file__),
            )
            if result.returncode == 0:
                st.success("✅ Budget alerts created!")
            else:
                st.error("Budget setup encountered issues.")
            with st.expander("📄 Full Output"):
                st.code(result.stdout + result.stderr, language="text")

    # Resource costs
    st.markdown("---")
    st.subheader("Cost Breakdown")
    cost_data = pd.DataFrame([
        {"Resource": "APIM (Consumption)", "Monthly Cost": "$0 + $3.50/M calls", "Notes": "Near-zero for demo"},
        {"Resource": "Azure OpenAI (gpt-4o)", "Monthly Cost": "Pay-per-token", "Notes": "$5/1M in · $15/1M out"},
        {"Resource": "Content Understanding", "Monthly Cost": "Pay-per-page", "Notes": "westus region"},
        {"Resource": "App Insights", "Monthly Cost": "$0", "Notes": "Free tier"},
        {"Resource": "Redis Enterprise (if caching)", "Monthly Cost": "~$200/mo", "Notes": "For semantic cache"},
    ])
    st.dataframe(cost_data, use_container_width=True, hide_index=True)
