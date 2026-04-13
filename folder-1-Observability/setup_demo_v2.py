"""
Azure AI Foundry Demo Setup Script (v2 SDK)
=============================================
Generates evaluation data, creates agents, and produces traffic
so the Foundry portal has rich data to show during the demo.
"""

import json
import os
import time
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import ListSortOrder

# ─── Configuration ───────────────────────────────────────────
SUBSCRIPTION_ID = "2852c4f9-8fcc-47c1-8e96-c4142a9ae463"
RESOURCE_GROUP  = "rg-healthcareai-demo-jp-001"
PROJECT_NAME    = "proj-healthcare-demo-jp-001"
LOCATION        = "eastus2"

# Foundry v2 endpoint
PROJECT_ENDPOINT = f"https://{LOCATION}.api.azureml.ms"

MODELS = ["gpt-5.3-chat", "gpt-5.2"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Helpers ─────────────────────────────────────────────────
def get_credential():
    return DefaultAzureCredential()

def load_eval_dataset():
    path = os.path.join(SCRIPT_DIR, "healthcare-eval-dataset.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

# ═════════════════════════════════════════════════════════════
# PART 1 — Generate model responses via OpenAI client
# ═════════════════════════════════════════════════════════════
def generate_responses(dataset, model_name):
    """Call deployed model for each question in the eval set."""
    print(f"\n{'='*60}")
    print(f"  Generating responses from: {model_name}")
    print(f"{'='*60}")

    cred = get_credential()
    project_client = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=cred,
    )
    openai_client = project_client.get_openai_client()

    results = []
    for i, item in enumerate(dataset):
        q = item["question"]
        print(f"  [{i+1}/{len(dataset)}] {q[:65]}...")
        try:
            resp = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system",
                     "content": ("You are a knowledgeable healthcare assistant at a hospital. "
                                 "Provide accurate, helpful, and empathetic responses. "
                                 "Always recommend consulting a healthcare provider for specific concerns.")},
                    {"role": "user", "content": q},
                ],
                max_tokens=500,
                temperature=0.7,
            )
            answer = resp.choices[0].message.content
            print(f"       ✓ {len(answer)} chars  (tokens in:{resp.usage.prompt_tokens} out:{resp.usage.completion_tokens})")
        except Exception as e:
            answer = f"[Error] {e}"
            print(f"       ✗ {e}")

        results.append({
            "question": q,
            "answer": answer,
            "ground_truth": item["ground_truth"],
            "context": item.get("context", ""),
        })

    # Save
    out = os.path.join(SCRIPT_DIR, f"eval-results-{model_name.replace('.','')}.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"  Saved ➜ {out}")
    return results

# ═════════════════════════════════════════════════════════════
# PART 2 — Create Agent & run conversations
# ═════════════════════════════════════════════════════════════
def setup_agent():
    """Create a healthcare agent with Code Interpreter and have conversations."""
    print(f"\n{'='*60}")
    print("  Creating Healthcare Agent …")
    print(f"{'='*60}")

    cred = get_credential()
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=cred)

    # The agents endpoint uses the project scope
    # We need to get the proper agents endpoint from the project
    agents_client = AgentsClient(
        endpoint=PROJECT_ENDPOINT,
        credential=cred,
    )

    agent = agents_client.create_agent(
        model="gpt-5.3-chat",
        name="Providence-Healthcare-Agent",
        instructions="""You are a Providence Health AI Assistant. You help hospital staff and patients with:

1. Finding information about hospital policies and procedures
2. Understanding medical terminology and conditions
3. Analyzing healthcare data and creating visualizations
4. Answering general health and wellness questions

RULES:
- NEVER provide specific medical diagnoses or treatment plans
- NEVER share or acknowledge individual patient data (PHI/PII)
- Always recommend consulting a licensed healthcare provider for medical advice
- Cite reliable medical sources when possible (CDC, WHO, NIH)
- Be empathetic, clear, and professional
- If unsure, say "I don't have enough information to answer accurately"

You have access to Code Interpreter for data analysis tasks.""",
        tools=[{"type": "code_interpreter"}],
    )
    print(f"  ✓ Agent created: {agent.id}  ({agent.name})")

    # Run conversations
    conversations = [
        "What are the top 5 causes of hospital readmissions and how can they be prevented?",
        "Create a Python visualization showing hospital department patient volumes: ER=450, Cardiology=280, Orthopedics=190, Neurology=150, Oncology=210, Pediatrics=320",
        "Explain the difference between inpatient and outpatient care and when each is appropriate.",
        "What infection control protocols should be followed during flu season?",
        "Calculate the average length of stay if we have these patient stays in days: 2, 3, 5, 1, 7, 4, 3, 2, 6, 4. Also compute the standard deviation.",
        "What are the key metrics hospitals track for patient satisfaction scores?",
        "Summarize HIPAA requirements for electronic health records security.",
    ]

    for i, msg in enumerate(conversations):
        print(f"\n  Agent convo [{i+1}/{len(conversations)}]: {msg[:60]}…")
        try:
            result = agents_client.create_thread_and_process_run(
                agent_id=agent.id,
                body={
                    "thread": {
                        "messages": [{"role": "user", "content": msg}]
                    }
                },
            )
            print(f"       ✓ Run status: {result.status}")
            time.sleep(1)
        except Exception as e:
            print(f"       ✗ {e}")

    return agent.id

# ═════════════════════════════════════════════════════════════
# PART 3 — Extra traffic for monitoring dashboards
# ═════════════════════════════════════════════════════════════
def generate_monitoring_traffic():
    """Send additional calls to both models so Operate dashboards have data."""
    print(f"\n{'='*60}")
    print("  Generating monitoring traffic …")
    print(f"{'='*60}")

    cred = get_credential()
    project_client = AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=cred)
    openai_client = project_client.get_openai_client()

    extra_queries = [
        ("gpt-5.2", "What is blood pressure and what do the numbers mean?"),
        ("gpt-5.2", "How often should adults get a physical exam?"),
        ("gpt-5.2", "What are the warning signs of dehydration?"),
        ("gpt-5.2", "Explain what an MRI scan involves and how to prepare for one."),
        ("gpt-5.2", "What dietary changes can help manage high cholesterol?"),
        ("gpt-5.3-chat", "What is sepsis and why is it a medical emergency?"),
        ("gpt-5.3-chat", "How does telemedicine work and when is it appropriate?"),
        ("gpt-5.3-chat", "What are the stages of wound healing?"),
        ("gpt-5.3-chat", "Explain the importance of hand hygiene in healthcare settings."),
        ("gpt-5.3-chat", "What should patients know about informed consent?"),
        ("gpt-5.2", "How do hospitals handle organ donation and transplant prioritization?"),
        ("gpt-5.3-chat", "What role does nutrition play in post-surgical recovery?"),
    ]

    for i, (model, query) in enumerate(extra_queries):
        print(f"  [{i+1}/{len(extra_queries)}] {model}: {query[:50]}…")
        try:
            resp = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful hospital information assistant."},
                    {"role": "user", "content": query},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            u = resp.usage
            print(f"       ✓ in:{u.prompt_tokens}  out:{u.completion_tokens}")
        except Exception as e:
            print(f"       ✗ {e}")
        time.sleep(0.5)

# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════
def main():
    banner = """
    ╔═══════════════════════════════════════════════════════╗
    ║   AZURE AI FOUNDRY  —  HEALTHCARE DEMO SETUP         ║
    ║   Providence Deep-Dive Session                        ║
    ╚═══════════════════════════════════════════════════════╝
    """
    print(banner)

    dataset = load_eval_dataset()
    print(f"  Loaded {len(dataset)} evaluation questions\n")

    # 1. Evaluation responses
    for model in MODELS:
        generate_responses(dataset, model)

    # 2. Agent creation + conversations
    agent_id = setup_agent()

    # 3. Monitoring traffic
    generate_monitoring_traffic()

    # Summary
    print(f"""
    {'='*55}
     DEMO SETUP COMPLETE  ✓
    {'='*55}

     Resources created / populated:
       Hub        : foundry-healthcare-hub-jp-001
       Project    : proj-healthcare-demo-jp-001
       Models     : gpt-5.2 (DataZoneStandard)
                    gpt-5.3-chat (GlobalStandard)
       Agent      : Providence-Healthcare-Agent ({agent_id})
       Eval data  : 15 questions × 2 models = 30 responses
       Traffic    : 12 extra API calls for monitoring

     Portal next-steps (ai.azure.com):
       Build  → Evaluations → Create using .jsonl files
       Build  → Guardrails  → Create custom content filter
       Operate → Overview   → View agent & model metrics
       Operate → Admin → AI Gateway → Add APIM gateway
    """)

if __name__ == "__main__":
    main()
