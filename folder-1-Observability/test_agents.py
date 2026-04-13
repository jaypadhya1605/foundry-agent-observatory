import os
from openai import AzureOpenAI
try:
    c = AzureOpenAI(
        azure_endpoint="https://mf-foundrydemo-healthcare-jp-001.services.ai.azure.com",
        api_key=os.getenv("FOUNDRY_API_KEY", ""),
        api_version="2025-01-01-preview",
    )
    agents = c.beta.assistants.list()
    for a in agents.data:
        print(f"Agent: {a.name} ({a.id}) model={a.model}")
    if not agents.data:
        print("No agents found")
except Exception as e:
    print(f"ERROR: {e}")
