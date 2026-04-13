"""
╔══════════════════════════════════════════════════════════════╗
║   Azure AI Foundry — SDK Demo for Providence Health         ║
║   Enterprise-grade Agent Management & Governance            ║
╚══════════════════════════════════════════════════════════════╝

Demonstrates:
  1. SDK-based agent discovery & introspection
  2. Model deployment inventory
  3. Connection & governance audit
  4. Agent versioning & lifecycle management
  5. Agent conversation via SDK
  6. Continuous evaluation rules
  7. Guardrails — RAI content-safety policies (via ARM REST)
  8. Observability — OpenTelemetry-traced agent conversation
  9. Knowledge assets — datasets, indexes, red-team taxonomy
"""

import json
import os
import subprocess
import time
from datetime import datetime, timezone

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


# ─── Configuration ───────────────────────────────────────────
PROJECT_ENDPOINT = (
    "https://ai-healthcare-foundry-jp-001.services.ai.azure.com"
    "/api/projects/ai-healthcare-foundry-j-project"
)
TARGET_AGENT = "myHealthcare-demo-agent02"

# ARM REST for guardrails / RAI policies
SUBSCRIPTION_ID = "2852c4f9-8fcc-47c1-8e96-c4142a9ae463"
RESOURCE_GROUP = "rg-healthcareai-demo-jp-001"
ACCOUNT_NAME = "ai-healthcare-foundry-jp-001"
RAI_API_VERSION = "2024-10-01"

# Healthcare demo questions for the agent conversation
DEMO_QUESTIONS = [
    "who are the Four Renowned Physicians Honored with Endowed Chairs at Providence Saint John Health Center?"
    "What are the clinical guidelines for managing Type 2 diabetes in elderly patients?",
    "Who is the first hospital to receive the American Heart Association's Get With The Guidelines Coronary Artery Disease STEMI Receiving Silver with Target ?Can you give me details on award?",
    "What are the key steps in a patient discharge plan for someone recovering from pneumonia?",
]


def banner(text, char="═"):
    width = 60
    print(f"\n{'':>{2}}{char * width}")
    print(f"  {text}")
    print(f"{'':>{2}}{char * width}\n")


def section(num, title):
    print(f"\n{'─' * 60}")
    print(f"  [{num}] {title}")
    print(f"{'─' * 60}")


def main():
    banner("Azure AI Foundry — SDK Demo for Providence Health")

    # Show SDK versions
    import azure.ai.projects
    import openai as openai_pkg
    print(f"  SDK Versions:")
    print(f"    azure-ai-projects : {azure.ai.projects.__version__}")
    print(f"    openai            : {openai_pkg.__version__}")
    print(f"    Project endpoint  : {PROJECT_ENDPOINT}")
    print(f"    Timestamp         : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    # ── Connect ──
    credential = DefaultAzureCredential()
    client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential)

    # ════════════════════════════════════════════════════════════
    # 1. AGENT DISCOVERY
    # ════════════════════════════════════════════════════════════
    section(1, "Agent Discovery — List all agents in project")

    agents = list(client.agents.list())
    print(f"\n  Found {len(agents)} agent(s):\n")

    for i, agent in enumerate(agents, 1):
        details = client.agents.get(agent_name=agent.id)
        d = details.as_dict()
        latest = d.get("versions", {}).get("latest", {})
        definition = latest.get("definition", {})

        model = definition.get("model", "N/A")
        kind = definition.get("kind", "N/A")
        instructions = definition.get("instructions", "N/A")
        tools = definition.get("tools", [])
        version = latest.get("version", "N/A")
        rai = definition.get("rai_config", {}).get("rai_policy_name", "N/A")
        if rai and "/" in rai:
            rai = rai.split("/")[-1]  # Just show policy name

        print(f"  Agent #{i}: {agent.id}")
        print(f"    Model:        {model}")
        print(f"    Kind:         {kind}")
        print(f"    Version:      {version}")
        print(f"    RAI Policy:   {rai}")
        tool_types = [t.get("type", "unknown") for t in tools] if tools else ["None"]
        print(f"    Tools:        {', '.join(tool_types)}")
        if len(instructions) > 150:
            instructions = instructions[:150] + "..."
        print(f"    Instructions: {instructions}")
        print()

    # ════════════════════════════════════════════════════════════
    # 2. MODEL DEPLOYMENTS
    # ════════════════════════════════════════════════════════════
    section(2, "Model Deployment Inventory")

    deployments = list(client.deployments.list())
    print(f"\n  {'Model':<25} {'Version':<15} {'SKU':<20} {'Capacity'}")
    print(f"  {'─'*25} {'─'*15} {'─'*20} {'─'*10}")

    for dep in deployments:
        d = dep.as_dict()
        print(f"  {d['modelName']:<25} {d['modelVersion']:<15} {d['sku']['name']:<20} {d['sku']['capacity']} TPM")

    print(f"\n  Total deployments: {len(deployments)}")

    # ════════════════════════════════════════════════════════════
    # 3. CONNECTIONS & GOVERNANCE AUDIT
    # ════════════════════════════════════════════════════════════
    section(3, "Connections & Governance Audit")

    connections = list(client.connections.list())
    print(f"\n  Connected services:")
    for conn in connections:
        d = conn.as_dict()
        name = d.get("name", "N/A")
        conn_type = d.get("type", "N/A")
        auth_type = d.get("credentials", {}).get("type", "N/A")
        print(f"    • {name}")
        print(f"      Type: {conn_type} | Auth: {auth_type}")

    # Telemetry connection string
    try:
        ai_conn = client.telemetry.get_application_insights_connection_string()
        print(f"\n  App Insights: Connected ✓")
        print(f"    Connection: {ai_conn[:60]}...")
    except Exception:
        print(f"\n  App Insights: Not configured")

    # ════════════════════════════════════════════════════════════
    # 4. AGENT VERSIONING
    # ════════════════════════════════════════════════════════════
    section(4, f"Agent Versioning — {TARGET_AGENT}")

    versions = list(client.agents.list_versions(agent_name=TARGET_AGENT))
    print(f"\n  Total versions: {len(versions)}")
    for v in versions:
        vd = v.as_dict()
        ver_num = vd.get("version", "?")
        created = vd.get("created_at", 0)
        created_str = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC") if created else "N/A"
        model = vd.get("definition", {}).get("model", "N/A")
        print(f"    v{ver_num} — Model: {model} | Created: {created_str}")

    # ════════════════════════════════════════════════════════════
    # 5. AGENT CONVERSATION
    # ════════════════════════════════════════════════════════════
    section(5, f"Agent Conversation — {TARGET_AGENT}")

    openai_client = client.get_openai_client()

    # Get agent details for model
    agent_details = client.agents.get(agent_name=TARGET_AGENT).as_dict()
    agent_def = agent_details["versions"]["latest"]["definition"]
    agent_model = agent_def["model"]
    agent_instructions = agent_def.get("instructions", "")

    print(f"\n  Using model: {agent_model}")
    print(f"  Agent instructions loaded from Foundry\n")

    for i, question in enumerate(DEMO_QUESTIONS, 1):
        print(f"  Q{i}: {question}")
        print(f"  {'─' * 56}")

        try:
            response = openai_client.responses.create(
                model=agent_model,
                instructions=agent_instructions,
                input=question,
            )
            answer = response.output_text
            # Show first 300 chars of response
            display = answer[:300] + "..." if len(answer) > 300 else answer
            print(f"  A{i}: {display}")
            print(f"  [{len(answer)} chars | model: {agent_model}]\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")

        time.sleep(1)

    # ════════════════════════════════════════════════════════════
    # 6. CONTINUOUS EVALUATION RULES
    # ════════════════════════════════════════════════════════════
    section(6, "Continuous Evaluation Rules")

    eval_rules = list(client.evaluation_rules.list())
    print(f"\n  Found {len(eval_rules)} evaluation rule(s):\n")

    for rule in eval_rules:
        rd = rule.as_dict()
        rule_name = rd.get("id", "N/A")
        display = rd.get("displayName", "")
        description = rd.get("description", "")
        agent_name = rd.get("filter", {}).get("agentName", "N/A")
        action = rd.get("action", {})
        eval_id = action.get("evalId", "N/A")
        action_type = action.get("type", "N/A")
        max_hourly = action.get("maxHourlyRuns", "N/A")
        sampling = action.get("samplingRate", "all")
        event_type = rd.get("eventType", "N/A")
        created = rd.get("systemData", {}).get("createdAt", "N/A")

        print(f"  Rule: {display or rule_name}")
        print(f"    ID:             {rule_name}")
        print(f"    Description:    {description[:100] if description else 'N/A'}")
        print(f"    Agent:          {agent_name}")
        print(f"    Evaluation ID:  {eval_id}")
        print(f"    Action:         {action_type} | Event: {event_type}")
        print(f"    Max hourly:     {max_hourly} | Sampling: {sampling or 'all'}")
        print(f"    Created:        {created}")
        print()

    # ════════════════════════════════════════════════════════════
    # 7. GUARDRAILS — RAI CONTENT-SAFETY POLICIES
    # ════════════════════════════════════════════════════════════
    section(7, "Guardrails — RAI Content-Safety Policies")

    rai_url = (
        f"https://management.azure.com/subscriptions/{SUBSCRIPTION_ID}"
        f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.CognitiveServices"
        f"/accounts/{ACCOUNT_NAME}/raiPolicies?api-version={RAI_API_VERSION}"
    )

    try:
        az_cmd = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
        result = subprocess.run(
            [az_cmd, "rest", "--method", "get", "--url", rai_url],
            capture_output=True, text=True, timeout=30,
        )
        policies = json.loads(result.stdout).get("value", [])
        print(f"\n  Found {len(policies)} RAI polic(y/ies):\n")

        for pol in policies:
            pname = pol.get("name", "N/A")
            props = pol.get("properties", {})
            base = props.get("basePolicyName", "—")
            filters = props.get("contentFilters", [])

            print(f"  Policy: {pname}")
            if base and base != "N/A":
                print(f"    Based on: {base}")
            print(f"    Content filters ({len(filters)}):")
            print(f"      {'Source':<12} {'Category':<28} {'Severity':<12} {'Blocking':<10} {'Enabled'}")
            print(f"      {'─'*12} {'─'*28} {'─'*12} {'─'*10} {'─'*8}")

            for f in filters:
                src = f.get("source", "?")
                name = f.get("name", "?")
                sev = f.get("severityThreshold", "—")
                blk = "Yes" if f.get("blocking") else "No"
                ena = "Yes" if f.get("enabled") else "No"
                print(f"      {src:<12} {name:<28} {str(sev):<12} {blk:<10} {ena}")

            blocklists = props.get("customBlocklistConfig", []) or []
            if blocklists:
                print(f"    Custom blocklists: {len(blocklists)}")
                for bl in blocklists:
                    print(f"      • {bl.get('blocklistName', 'N/A')}")
            print()

    except Exception as e:
        print(f"\n  Could not retrieve RAI policies: {e}\n")

    # ════════════════════════════════════════════════════════════
    # 8. OBSERVABILITY — TRACED AGENT CONVERSATION
    # ════════════════════════════════════════════════════════════
    section(8, "Observability — Traced Agent Conversation")

    # Get App Insights connection string for tracing
    ai_conn_str = client.telemetry.get_application_insights_connection_string()
    print(f"  App Insights connection: {ai_conn_str[:60]}...")

    # Configure OpenTelemetry → Azure Monitor
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

    exporter = AzureMonitorTraceExporter(connection_string=ai_conn_str)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    tracer = trace.get_tracer("foundry-sdk-demo")

    traced_question = "What are the clinical guidelines for managing Type 2 diabetes in elderly patients?"
    print(f"\n  Traced Q: {traced_question}")
    print(f"  {'─' * 56}")

    with tracer.start_as_current_span("healthcare-agent-traced-call") as span:
        span.set_attribute("agent.name", TARGET_AGENT)
        span.set_attribute("agent.model", agent_model)
        span.set_attribute("demo.section", "observability")

        try:
            traced_response = openai_client.responses.create(
                model=agent_model,
                instructions=agent_instructions,
                input=traced_question,
            )
            answer = traced_response.output_text
            span.set_attribute("response.length", len(answer))
            span.set_attribute("response.status", "success")

            display = answer[:300] + "..." if len(answer) > 300 else answer
            print(f"  A: {display}")
            print(f"  [{len(answer)} chars | traced ✓]\n")
        except Exception as e:
            span.set_attribute("response.status", "error")
            span.set_attribute("error.message", str(e))
            print(f"  ERROR: {e}\n")

    # Force flush to ensure spans are exported
    provider.force_flush()
    print("  Trace exported to App Insights ✓")
    print(f"  View traces at: https://portal.azure.com → App Insights → Transaction search")

    # ════════════════════════════════════════════════════════════
    # 9. KNOWLEDGE ASSETS — DATASETS, INDEXES, RED-TEAM TAXONOMY
    # ════════════════════════════════════════════════════════════
    section(9, "Knowledge Assets — Datasets, Indexes & Red-Team Taxonomy")

    # 9a. Datasets
    datasets = list(client.datasets.list())
    print(f"\n  Datasets ({len(datasets)}):")
    for ds in datasets:
        dd = ds.as_dict()
        display_name = dd.get("displayName", dd.get("name", "N/A"))
        version = dd.get("version", "?")
        ds_type = dd.get("type", "N/A")
        print(f"    • {display_name} (v{version})")

    # 9b. Indexes
    indexes = list(client.indexes.list())
    print(f"\n  Indexes ({len(indexes)}):")
    for ix in indexes:
        ixd = ix.as_dict()
        ix_name = ixd.get("name", "N/A")
        ix_type = ixd.get("type", "N/A")
        vector_store = ixd.get("vectorStoreId", "N/A")
        print(f"    • {ix_name}")
        print(f"      Type: {ix_type} | Vector Store: {vector_store}")

    # 9c. Red-Team Evaluation Taxonomies
    taxonomies = list(client.beta.evaluation_taxonomies.list())
    print(f"\n  Red-Team Taxonomies ({len(taxonomies)}):")
    for tax in taxonomies:
        td = tax.as_dict()
        tax_name = td.get("name", "N/A")
        tax_ver = td.get("version", "?")
        tax_input = td.get("taxonomyInput", {})
        target_type = tax_input.get("target", {}).get("type", "N/A")
        target_agent = tax_input.get("target", {}).get("name", "N/A")
        risk_cats = tax_input.get("riskCategories", [])
        categories = td.get("taxonomyCategories", [])

        print(f"    • {tax_name} (v{tax_ver})")
        print(f"      Target: {target_agent} ({target_type})")
        print(f"      Risk categories: {', '.join(risk_cats)}")
        print(f"      Sub-categories ({len(categories)}):")
        for cat in categories:
            cat_name = cat.get("name", "N/A")
            sub_cats = cat.get("subCategories", [])
            enabled_count = sum(1 for sc in sub_cats if sc.get("enabled"))
            print(f"        {cat_name}: {len(sub_cats)} checks ({enabled_count} enabled)")

    # ── Cleanup ──
    openai_client.close()
    provider.shutdown()
    client.close()
    credential.close()

    banner("Demo Complete — Azure AI Foundry SDK", "═")
    print("  Demonstrated:")
    print("    ✓ Agent discovery & introspection via SDK")
    print("    ✓ Model deployment inventory")
    print("    ✓ Connection & governance audit")
    print("    ✓ Agent version history")
    print("    ✓ Agent conversation using Foundry-managed config")
    print("    ✓ Continuous evaluation rules")
    print("    ✓ Guardrails — RAI content-safety policies")
    print("    ✓ Observability — OpenTelemetry traced conversation")
    print("    ✓ Knowledge assets — datasets, indexes, red-team taxonomy")
    print()


if __name__ == "__main__":
    main()
