"""
Foundry Tracing Demo — Healthcare Agent Conversations
======================================================
Uses AIProjectClient + AIProjectInstrumentor + Azure Monitor
to send traced agent conversations to Application Insights,
which then appear in the Foundry portal Tracing tab.
"""

import os, time

# ── Set env vars BEFORE any SDK imports ──
os.environ["AZURE_EXPERIMENTAL_ENABLE_GENAI_TRACING"] = "true"
os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"
os.environ["AZURE_TRACING_GEN_AI_ENABLE_TRACE_CONTEXT_PROPAGATION"] = "true"
os.environ["OTEL_SERVICE_NAME"] = "healthcare-agent-app"

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from azure.monitor.opentelemetry import configure_azure_monitor
from azure.ai.projects import AIProjectClient
from azure.ai.projects.telemetry import AIProjectInstrumentor
from azure.identity import DefaultAzureCredential

# ─── Configuration ───────────────────────────────────────────
PROJECT_ENDPOINT = "https://mf-foundrydemo-healthcare-jp-001.services.ai.azure.com/api/projects/prj-FoundryDemo-healthcare-jp-03102026"
MODEL = "gpt-5.4"

APP_INSIGHTS_CONN_STR = (
    "InstrumentationKey=fbf451fb-7819-4a2c-87f5-2fc5559a2edc;"
    "IngestionEndpoint=https://eastus2-3.in.applicationinsights.azure.com/;"
    "LiveEndpoint=https://eastus2.livediagnostics.monitor.azure.com/;"
    "ApplicationId=87605427-06fb-405a-966b-fb22c5573a6c"
)

# Healthcare scenarios for traced conversations (single-turn for reliability)
HEALTHCARE_SCENARIOS = [
    {"name": "Patient Triage Assessment", "model": "gpt-5.4",
     "message": "A 65-year-old patient presents with chest pain, shortness of breath, and diaphoresis. What is the appropriate triage protocol?"},
    {"name": "Medication Interaction Review", "model": "gpt-5.4",
     "message": "Review potential drug interactions for a patient currently on warfarin, amiodarone, and metformin. What are the key concerns?"},
    {"name": "Post-Surgical Care Planning", "model": "gpt-5.3-chat",
     "message": "Create a post-operative care plan for a patient who underwent a total knee replacement. Include pain management and physical therapy milestones."},
    {"name": "Chronic Disease Management", "model": "gpt-5.3-chat",
     "message": "Design a comprehensive management plan for a patient with Type 2 diabetes, hypertension, and stage 3 chronic kidney disease."},
    {"name": "Emergency Department Workflow", "model": "gpt-5.4",
     "message": "A patient arrives via ambulance with suspected stroke. Describe the optimal ED workflow following current AHA/ASA guidelines."},
    {"name": "Pediatric Care Consultation", "model": "gpt-5.3-chat",
     "message": "A 3-year-old presents with recurrent ear infections, 5 episodes in the past 12 months. What evaluation and treatment approach do you recommend?"},
    {"name": "Clinical Documentation Review", "model": "gpt-5.4",
     "message": "Review best practices for clinical documentation in an EHR system to ensure compliance with CMS requirements and support accurate coding."},
    {"name": "Population Health Analytics", "model": "gpt-5.3-chat",
     "message": "How can Providence Health use population health data analytics to identify high-risk patients for heart failure readmission?"},
    {"name": "Surgical Risk Assessment", "model": "gpt-5.4",
     "message": "What preoperative risk assessment tools should be used for a 72-year-old patient scheduled for elective hip replacement with a history of atrial fibrillation?"},
    {"name": "Mental Health Screening", "model": "gpt-5.3-chat",
     "message": "Describe an evidence-based approach for implementing universal depression screening in a primary care setting using the PHQ-9."},
    {"name": "Sepsis Early Detection", "model": "gpt-5.4",
     "message": "What are the current best practices for early sepsis detection and the recommended treatment bundle within the first hour?"},
    {"name": "Care Coordination", "model": "gpt-5.3-chat",
     "message": "How should a health system coordinate care transitions from acute care to home health for elderly patients with multiple chronic conditions?"},
]


def main():
    print("=" * 60)
    print("  Foundry Tracing — Healthcare Agent Conversations")
    print("=" * 60)

    # ── Step 1: Configure Azure Monitor (App Insights) ──
    print("\n[1/4] Configuring Azure Monitor tracing...")
    resource = Resource.create({
        "service.name": "healthcare-agent-app",
        "service.version": "1.0.0",
        "deployment.environment": "demo",
    })
    configure_azure_monitor(
        connection_string=APP_INSIGHTS_CONN_STR,
        resource=resource,
    )
    print("  ✓ Azure Monitor configured (service: healthcare-agent-app)")

    # ── Step 2: Enable AI Project instrumentation ──
    print("[2/4] Enabling AIProjectInstrumentor...")
    AIProjectInstrumentor().instrument()
    print("  ✓ Instrumentation enabled (content tracing ON)")

    # ── Step 3: Create AIProjectClient ──
    print("[3/4] Creating AIProjectClient...")
    credential = DefaultAzureCredential()
    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=credential,
    )

    # Verify App Insights connection
    try:
        ai_conn_str = project_client.telemetry.get_application_insights_connection_string()
        print(f"  ✓ App Insights connected: {ai_conn_str[:60]}...")
    except Exception as e:
        print(f"  ⚠ Could not get AI connection string from project: {e}")
        print("    (Using hardcoded connection string — traces will still work)")

    # ── Step 4: Run traced healthcare conversations ──
    print(f"\n[4/4] Running {len(HEALTHCARE_SCENARIOS)} traced healthcare scenarios...\n")

    tracer = trace.get_tracer(__name__)
    openai_client = project_client.get_openai_client()

    for i, scenario in enumerate(HEALTHCARE_SCENARIOS, 1):
        scenario_name = scenario["name"]
        model = scenario["model"]
        print(f"  [{i}/{len(HEALTHCARE_SCENARIOS)}] {scenario_name} ({model})")

        with tracer.start_as_current_span(f"healthcare-scenario-{scenario_name}") as span:
            span.set_attribute("scenario.name", scenario_name)
            span.set_attribute("scenario.index", i)
            span.set_attribute("scenario.model", model)
            span.set_attribute("healthcare.domain", "Providence Health")

            try:
                response = openai_client.responses.create(
                    model=model,
                    input=scenario["message"],
                )
                output_text = response.output_text
                span.set_attribute("response.length", len(output_text))
                print(f"       ✓ {len(output_text)} chars")
            except Exception as e:
                print(f"       ✗ ERROR — {e}")

            time.sleep(1)  # Brief pause between scenarios

    # ── Cleanup ──
    openai_client.close()
    project_client.close()
    credential.close()

    # ── Flush telemetry ──
    print("\n  Flushing telemetry to Application Insights...")
    from opentelemetry.sdk.trace import TracerProvider as SdkTracerProvider
    provider = trace.get_tracer_provider()
    if hasattr(provider, 'force_flush'):
        provider.force_flush(timeout_millis=30000)
    time.sleep(10)  # Extra wait for async export

    print("\n" + "=" * 60)
    print("  TRACING COMPLETE")
    print("  Traces should appear in Foundry portal within 2-5 minutes")
    print("  Navigate to: Observe and optimize → Tracing")
    print("=" * 60)


if __name__ == "__main__":
    main()
