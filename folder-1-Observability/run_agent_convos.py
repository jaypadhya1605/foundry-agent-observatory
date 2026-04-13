"""
Run agent conversations on the new Foundry using the project endpoint.
The Assistants API requires the Foundry services endpoint, not cognitiveservices.
"""
import os
import time
from openai import AzureOpenAI

API_KEY = os.getenv("FOUNDRY_API_KEY", "")
FOUNDRY_ENDPOINT = "https://mf-foundrydemo-healthcare-jp-001.services.ai.azure.com"
AGENT_ID = "asst_Az0AhnnnWZ2XIrBurcilC18i"

client = AzureOpenAI(
    azure_endpoint=FOUNDRY_ENDPOINT,
    api_key=API_KEY,
    api_version="2025-01-01-preview",
)

conversations = [
    "What are the top 5 causes of hospital readmissions and how can they be prevented?",
    "Generate Python code to create a bar chart of hospital department volumes: ER=450, Cardiology=280, Orthopedics=190, Neurology=150, Oncology=210, Pediatrics=320",
    "Explain the difference between inpatient and outpatient care.",
    "What infection control protocols should be followed during flu season?",
    "Calculate average length of stay for these patient stays in days: 2, 3, 5, 1, 7, 4, 3, 2, 6, 4. Also compute std dev.",
    "What are key metrics hospitals track for patient satisfaction?",
    "Summarize HIPAA requirements for electronic health records security.",
    "What are the implications of AI in healthcare for patient privacy?",
    "How do hospitals measure and improve clinical outcomes?",
    "What are best practices for medication reconciliation during patient transitions?",
]

print(f"Running {len(conversations)} agent conversations for tracing...\n")

for i, msg in enumerate(conversations):
    print(f"  [{i+1}/{len(conversations)}] {msg[:60]}...")
    try:
        thread = client.beta.threads.create()
        client.beta.threads.messages.create(thread_id=thread.id, role="user", content=msg)
        run = client.beta.threads.runs.create_and_poll(thread_id=thread.id, assistant_id=AGENT_ID)
        print(f"       Status: {run.status}")
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

print("\nAgent conversations complete.")
