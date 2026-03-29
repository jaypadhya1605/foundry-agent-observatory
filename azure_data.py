"""Azure data service — queries App Insights and Azure Monitor for live telemetry."""

import os
import datetime
import logging
import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_credential = None


def _get_credential():
    global _credential
    if _credential is None:
        _credential = DefaultAzureCredential()
    return _credential


def _appi_query(query: str) -> list[dict]:
    """Run a KQL query against Application Insights REST API."""
    cred = _get_credential()
    token = cred.get_token("https://api.applicationinsights.io/.default").token
    app_id = os.environ["APPINSIGHTS_APP_ID"]
    resp = requests.post(
        f"https://api.applicationinsights.io/v1/apps/{app_id}/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": query},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    tables = data.get("tables", [{}])
    if not tables:
        return []
    cols = [c["name"] for c in tables[0].get("columns", [])]
    return [dict(zip(cols, row)) for row in tables[0].get("rows", [])]


def _arm_get(path: str, params: dict | None = None) -> dict:
    """GET against Azure Resource Manager."""
    cred = _get_credential()
    token = cred.get_token("https://management.azure.com/.default").token
    url = f"https://management.azure.com{path}"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _project_resource_id() -> str:
    sub = os.environ["AZURE_SUBSCRIPTION_ID"]
    rg = os.environ["RESOURCE_GROUP"]
    acct = os.environ["FOUNDRY_ACCOUNT_NAME"]
    proj = os.environ["FOUNDRY_PROJECT_NAME"]
    return (
        f"/subscriptions/{sub}/resourceGroups/{rg}"
        f"/providers/Microsoft.CognitiveServices/accounts/{acct}/projects/{proj}"
    )


# ── Overview KPIs ────────────────────────────────────────────────────────────


def get_overview_kpis(days: int = 7) -> dict:
    """Return high-level KPIs for the overview dashboard."""
    rows = _appi_query(f"""
        dependencies
        | where timestamp > ago({days}d)
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | where op == 'invoke_agent'
        | summarize TotalRuns=count(),
                    Failed=countif(success == false),
                    AvgLatency=round(avg(duration), 0),
                    P95Latency=round(percentile(duration, 95), 0)
    """)
    kpi = rows[0] if rows else {}
    total = kpi.get("TotalRuns", 0)
    failed = kpi.get("Failed", 0)
    success_rate = round(100 * (total - failed) / total, 1) if total else 0

    # Token usage
    tok = _appi_query(f"""
        dependencies
        | where timestamp > ago({days}d)
        | extend inp = toint(customDimensions['gen_ai.usage.input_tokens'])
        | extend out = toint(customDimensions['gen_ai.usage.output_tokens'])
        | where inp > 0 or out > 0
        | summarize TotalInput=sum(inp), TotalOutput=sum(out)
    """)
    tok_row = tok[0] if tok else {}

    # Estimated cost (rough: $2.50/1M input, $10/1M output for gpt-4o)
    inp_tokens = tok_row.get("TotalInput", 0) or 0
    out_tokens = tok_row.get("TotalOutput", 0) or 0
    est_cost = round(inp_tokens * 2.50 / 1_000_000 + out_tokens * 10.0 / 1_000_000, 2)

    return {
        "total_runs": total,
        "success_rate": success_rate,
        "avg_latency_ms": kpi.get("AvgLatency", 0),
        "p95_latency_ms": kpi.get("P95Latency", 0),
        "total_input_tokens": inp_tokens,
        "total_output_tokens": out_tokens,
        "estimated_cost": est_cost,
        "days": days,
    }


# ── Agent Inventory ──────────────────────────────────────────────────────────


def get_agents() -> list[dict]:
    """Return agent inventory with run counts and error rates."""
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | where op == 'invoke_agent' and isnotempty(agent_id)
        | extend agent_name = extract(@'^([^:]+)', 1, agent_id)
        | extend version = extract(@':(\d+)$', 1, agent_id)
        | summarize Runs=count(),
                    Failed=countif(success == false),
                    AvgLatency=round(avg(duration), 0),
                    P95Latency=round(percentile(duration, 95), 0),
                    LastSeen=max(timestamp),
                    Versions=dcount(version)
            by agent_name
        | extend ErrorRate=round(100.0 * Failed / Runs, 2)
        | extend Status=iff(ErrorRate < 10, 'Running', 'Degraded')
        | order by Runs desc
    """)


# ── Token Usage by Agent ─────────────────────────────────────────────────────


def get_token_usage() -> list[dict]:
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend inp = toint(customDimensions['gen_ai.usage.input_tokens'])
        | extend out = toint(customDimensions['gen_ai.usage.output_tokens'])
        | where isnotempty(agent_id) and (inp > 0 or out > 0)
        | extend agent_name = extract(@'^([^:]+)', 1, agent_id)
        | summarize InputTokens=sum(inp), OutputTokens=sum(out), Calls=count() by agent_name
        | extend TotalTokens = InputTokens + OutputTokens
        | order by TotalTokens desc
    """)


# ── Agent Run Timeline ───────────────────────────────────────────────────────


def get_run_timeline(hours: int = 168) -> list[dict]:
    return _appi_query(f"""
        dependencies
        | where timestamp > ago({hours}h)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | where op == 'invoke_agent' and isnotempty(agent_id)
        | extend agent_name = extract(@'^([^:]+)', 1, agent_id)
        | summarize Runs=count() by agent_name, bin(timestamp, 1h)
        | order by timestamp asc
    """)


# ── Workflow Performance ─────────────────────────────────────────────────────


def get_workflow_performance() -> list[dict]:
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | where name startswith 'discharge_workflow' or name startswith 'agent.'
        | summarize AvgDuration=round(avg(duration), 0),
                    P50=round(percentile(duration, 50), 0),
                    P95=round(percentile(duration, 95), 0),
                    Calls=count()
            by name
        | order by AvgDuration desc
    """)


# ── Model Usage ──────────────────────────────────────────────────────────────


def get_model_usage() -> list[dict]:
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | extend model = tostring(customDimensions['gen_ai.response.model'])
        | extend inp = toint(customDimensions['gen_ai.usage.input_tokens'])
        | extend out = toint(customDimensions['gen_ai.usage.output_tokens'])
        | where isnotempty(model) and (inp > 0 or out > 0)
        | summarize Calls=count(), TotalInput=sum(inp), TotalOutput=sum(out) by model
        | extend TotalTokens = TotalInput + TotalOutput
        | order by TotalTokens desc
    """)


# ── Error Rate by Agent ─────────────────────────────────────────────────────


def get_error_rates() -> list[dict]:
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | where op == 'invoke_agent' and isnotempty(agent_id)
        | extend agent_name = extract(@'^([^:]+)', 1, agent_id)
        | summarize Total=count(), Failed=countif(success == false) by agent_name
        | extend ErrorRate = round(100.0 * Failed / Total, 2)
        | order by ErrorRate desc
    """)


# ── Latency Distribution ────────────────────────────────────────────────────


def get_latency_distribution() -> list[dict]:
    return _appi_query("""
        dependencies
        | where timestamp > ago(7d)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | where op == 'invoke_agent' and isnotempty(agent_id)
        | extend agent_name = extract(@'^([^:]+)', 1, agent_id)
        | extend bucket = case(
            duration < 1000, "<1s",
            duration < 3000, "1-3s",
            duration < 5000, "3-5s",
            duration < 10000, "5-10s",
            ">10s")
        | summarize count() by agent_name, bucket
    """)


# ── Recent Traces ────────────────────────────────────────────────────────────


def get_recent_traces(limit: int = 30) -> list[dict]:
    return _appi_query(f"""
        dependencies
        | where timestamp > ago(1d)
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | extend op = tostring(customDimensions['gen_ai.operation.name'])
        | extend patient_id = tostring(customDimensions['patient.id'])
        | where name startswith 'discharge_workflow' or name startswith 'agent.' or op == 'invoke_agent'
        | project timestamp, name, operation_Id, duration, agent_id, op, patient_id, success
        | order by timestamp desc
        | take {limit}
    """)


# ── Evaluation Results ───────────────────────────────────────────────────────


def get_evaluation_summary() -> list[dict]:
    return _appi_query("""
        customEvents
        | where timestamp > ago(7d)
        | where name == 'gen_ai.evaluation.result'
        | extend run_id = tostring(customDimensions['gen_ai.evaluation.run_id'])
        | extend evaluator = tostring(customDimensions['gen_ai.evaluation.evaluator_id'])
        | extend score = todouble(customDimensions['gen_ai.evaluation.score'])
        | summarize AvgScore=round(avg(score), 2), Count=count() by evaluator
        | order by Count desc
    """)


# ── Azure Monitor Platform Metrics ──────────────────────────────────────────


def get_platform_metrics(days: int = 7) -> dict:
    """Fetch Azure Monitor platform metrics for the Foundry project."""
    proj_id = _project_resource_id()
    end = datetime.datetime.utcnow()
    start = end - datetime.timedelta(days=days)
    timespan = f"{start.isoformat()}Z/{end.isoformat()}Z"

    metrics_out = {}
    for metric_name in ["AgentRuns", "AgentResponses", "AgentInputTokens", "AgentOutputTokens", "AgentToolCalls"]:
        try:
            data = _arm_get(
                f"{proj_id}/providers/Microsoft.Insights/metrics",
                params={
                    "api-version": "2023-10-01",
                    "metricnames": metric_name,
                    "timespan": timespan,
                    "aggregation": "Total",
                    "interval": "P1D",
                },
            )
            total = 0
            for m in data.get("value", []):
                for ts in m.get("timeseries", []):
                    for dp in ts.get("data", []):
                        total += dp.get("total", 0) or 0
            metrics_out[metric_name] = int(total)
        except Exception as e:
            logger.warning("Metric %s failed: %s", metric_name, e)
            metrics_out[metric_name] = 0
    return metrics_out


# ── Conversation Traces ──────────────────────────────────────────────────────


def get_conversation_traces(limit: int = 15) -> list[dict]:
    return _appi_query(f"""
        dependencies
        | where timestamp > ago(7d)
        | extend conv_id = tostring(customDimensions['gen_ai.conversation.id'])
        | extend agent_id = tostring(customDimensions['gen_ai.agent.id'])
        | where isnotempty(conv_id)
        | summarize AgentCalls=count(), Agents=dcount(agent_id), Duration=max(timestamp)-min(timestamp) by conv_id
        | order by AgentCalls desc
        | take {limit}
    """)
