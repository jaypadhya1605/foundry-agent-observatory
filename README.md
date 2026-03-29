# Foundry Agent Observatory — Web Dashboard

A web-based monitoring dashboard for Microsoft Foundry AI agents, built with the
same look and feel as the Foundry v2 / next-gen portal. Displays live agent metrics,
traces, evaluations, governance, and architecture — all powered by Application
Insights and Azure Monitor APIs.

## Features

- **Overview Dashboard** — Running agents, estimated cost, success rate, token usage
- **Agents** — Agent inventory with status, versions, error rates, runs
- **Traces** — End-to-end workflow waterfall and distributed trace explorer
- **Evaluations** — Quality scores, continuous evaluation, red-teaming results
- **Monitoring** — KQL-powered charts: latency heatmap, token trends, model usage
- **Governance & Compliance** — Guardrails status, blocklists, content safety
- **Architecture** — Interactive workflow diagram of the hospital discharge system
- **Test Console** — Run tracing, guardrail, and blocklist tests live from the UI

## Quick Start

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Set environment variables (copy .env.template → .env)
cp .env.template .env
# Fill in your Foundry project endpoint and App Insights details

# 3. Run locally
python app.py
# Open http://localhost:8000
```

## Azure Deployment

```bash
# Deploy via GitHub Actions (see .github/workflows/deploy.yml)
git push origin main
```

## Architecture

```
┌─────────────────────────────────────────────┐
│        Foundry Agent Observatory (Flask)      │
├──────────┬──────────┬───────────┬────────────┤
│ Overview │  Agents  │  Traces   │ Evaluations│
│Dashboard │ Inventory│ Explorer  │  Scores    │
├──────────┴──────────┴───────────┴────────────┤
│              API Layer (Flask)                │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐ │
│  │App Insights│  │Azure Mon │  │Foundry SDK │ │
│  │ REST API  │  │Metrics API│  │AIProjectCli│ │
│  └──────────┘  └──────────┘  └────────────┘ │
└─────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Flask + Gunicorn
- **Frontend**: HTML/CSS/JS with Foundry v2 dark theme
- **Data Sources**: Application Insights REST API, Azure Monitor Metrics, Foundry SDK
- **Deployment**: Azure App Service via GitHub Actions
