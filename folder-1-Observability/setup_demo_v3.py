"""
Azure AI Foundry Demo Setup Script — Direct OpenAI + Agents
=============================================================
Uses Azure OpenAI endpoint directly for chat completions,
and the Azure AI Agents SDK for agent creation.
"""

import json
import os
import time
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

# ─── Configuration ───────────────────────────────────────────
SUBSCRIPTION_ID = "2852c4f9-8fcc-47c1-8e96-c4142a9ae463"
RESOURCE_GROUP  = "rg-healthcareai-demo-jp-001"
PROJECT_NAME    = "proj-healthcare-demo-jp-001"
AI_SERVICES     = "ai-healthcare-foundry-jp-001"
LOCATION        = "eastus2"

# Azure OpenAI endpoint (via AI Services)
AOAI_ENDPOINT = f"https://{AI_SERVICES}.cognitiveservices.azure.com/"

MODELS = ["gpt-5.3-chat", "gpt-5.2"]
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Helpers ─────────────────────────────────────────────────
def get_openai_client():
    """Create Azure OpenAI client using DefaultAzureCredential."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://cognitiveservices.azure.com/.default")
    client = AzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=token.token,
        api_version="2025-01-01-preview",
    )
    return client

def load_eval_dataset():
    path = os.path.join(SCRIPT_DIR, "healthcare-eval-dataset.jsonl")
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

# ═════════════════════════════════════════════════════════════
# PART 1 — Generate model responses
# ═════════════════════════════════════════════════════════════
def generate_responses(client, dataset, model_name):
    """Call deployed model for each question."""
    print(f"\n{'='*60}")
    print(f"  Generating responses from: {model_name}")
    print(f"{'='*60}")

    results = []
    for i, item in enumerate(dataset):
        q = item["question"]
        print(f"  [{i+1}/{len(dataset)}] {q[:65]}...")
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system",
                     "content": ("You are a knowledgeable healthcare assistant at a hospital. "
                                 "Provide accurate, helpful, and empathetic responses. "
                                 "Always recommend consulting a healthcare provider for specific concerns.")},
                    {"role": "user", "content": q},
                ],
                max_completion_tokens=500,
                temperature=0.7,
            )
            answer = resp.choices[0].message.content
            print(f"       OK ({len(answer)} chars, in:{resp.usage.prompt_tokens} out:{resp.usage.completion_tokens})")
        except Exception as e:
            answer = f"[Error] {e}"
            print(f"       ERROR: {e}")

        results.append({
            "question": q,
            "answer": answer,
            "ground_truth": item["ground_truth"],
            "context": item.get("context", ""),
        })

    out = os.path.join(SCRIPT_DIR, f"eval-results-{model_name.replace('.','')}.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r) + "\n")
    print(f"  Saved -> {out}")
    return results

# ═════════════════════════════════════════════════════════════
# PART 2 — Create Agent via Assistants API
# ═════════════════════════════════════════════════════════════
def setup_agent(client):
    """Create a healthcare agent using the OpenAI Assistants API."""
    print(f"\n{'='*60}")
    print("  Creating Healthcare Agent (Assistants API) ...")
    print(f"{'='*60}")

    agent = client.beta.assistants.create(
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
    print(f"  Agent created: {agent.id}  ({agent.name})")

    conversations = [
        "What are the top 5 causes of hospital readmissions and how can they be prevented?",
        "Generate Python code to create a bar chart of hospital department volumes: ER=450, Cardiology=280, Orthopedics=190, Neurology=150, Oncology=210, Pediatrics=320",
        "Explain the difference between inpatient and outpatient care.",
        "What infection control protocols should be followed during flu season?",
        "Calculate average length of stay for these patient stays in days: 2, 3, 5, 1, 7, 4, 3, 2, 6, 4. Also compute std dev.",
        "What are key metrics hospitals track for patient satisfaction?",
        "Summarize HIPAA requirements for electronic health records security.",
    ]

    for i, msg in enumerate(conversations):
        print(f"\n  Agent convo [{i+1}/{len(conversations)}]: {msg[:55]}...")
        try:
            thread = client.beta.threads.create()
            client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=msg,
            )
            run = client.beta.threads.runs.create_and_poll(
                thread_id=thread.id,
                assistant_id=agent.id,
            )
            print(f"       Run status: {run.status}")
            if run.status == "completed":
                msgs = client.beta.threads.messages.list(thread_id=thread.id)
                for m in msgs.data:
                    if m.role == "assistant" and m.content:
                        txt = m.content[0].text.value if hasattr(m.content[0], 'text') else str(m.content[0])
                        print(f"       Response: {txt[:80]}...")
                        break
            time.sleep(1)
        except Exception as e:
            print(f"       ERROR: {e}")

    return agent.id

# ═════════════════════════════════════════════════════════════
# PART 3 — Extra traffic for monitoring dashboards
# ═════════════════════════════════════════════════════════════
def generate_monitoring_traffic(client):
    """Send additional calls so Operate dashboards populate."""
    print(f"\n{'='*60}")
    print("  Generating monitoring traffic ...")
    print(f"{'='*60}")

    extra = [
        ("gpt-5.2",      "What is blood pressure and what do the numbers mean?"),
        ("gpt-5.2",      "How often should adults get a physical exam?"),
        ("gpt-5.2",      "What are the warning signs of dehydration?"),
        ("gpt-5.2",      "Explain what an MRI scan involves."),
        ("gpt-5.2",      "What dietary changes help manage high cholesterol?"),
        ("gpt-5.3-chat", "What is sepsis and why is it an emergency?"),
        ("gpt-5.3-chat", "How does telemedicine work?"),
        ("gpt-5.3-chat", "What are the stages of wound healing?"),
        ("gpt-5.3-chat", "Importance of hand hygiene in healthcare?"),
        ("gpt-5.3-chat", "What should patients know about informed consent?"),
        ("gpt-5.2",      "How do hospitals handle organ donation?"),
        ("gpt-5.3-chat", "Role of nutrition in post-surgical recovery?"),
    ]

    for i, (model, query) in enumerate(extra):
        print(f"  [{i+1}/{len(extra)}] {model}: {query[:45]}...")
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful hospital information assistant."},
                    {"role": "user", "content": query},
                ],
                max_completion_tokens=300,
                temperature=0.7,
            )
            u = resp.usage
            print(f"       OK (in:{u.prompt_tokens} out:{u.completion_tokens})")
        except Exception as e:
            print(f"       ERROR: {e}")
        time.sleep(0.5)

# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════
def main():
    print("""
    ============================================================
      AZURE AI FOUNDRY  -  HEALTHCARE DEMO SETUP
      Providence Deep-Dive Session
    ============================================================
    """)

    # Initialize
    client = get_openai_client()
    dataset = load_eval_dataset()
    print(f"  Loaded {len(dataset)} evaluation questions\n")

    # 1. Eval responses - both models
    for model in MODELS:
        generate_responses(client, dataset, model)

    # 2. Agent + conversations
    agent_id = setup_agent(client)

    # 3. Extra traffic
    generate_monitoring_traffic(client)

    print(f"""
    ============================================================
      DEMO SETUP COMPLETE
    ============================================================

     Resources created / populated:
       Hub        : foundry-healthcare-hub-jp-001
       Project    : proj-healthcare-demo-jp-001
       AI Services: ai-healthcare-foundry-jp-001
       Models     : gpt-5.2 (DataZoneStandard)
                    gpt-5.3-chat (GlobalStandard)
       Agent      : Providence-Healthcare-Agent ({agent_id})
       Eval data  : 15 questions x 2 models = 30 responses
       Traffic    : 12 extra API calls for monitoring

     Portal next-steps (ai.azure.com):
       Build  > Evaluations > Create using .jsonl files
       Build  > Guardrails  > Create custom content filter
       Operate > Overview   > View agent & model metrics
       Operate > Admin      > AI Gateway > Add APIM gateway
    """)

if __name__ == "__main__":
    main()
