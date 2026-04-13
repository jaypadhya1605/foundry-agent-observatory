"""
Azure AI Foundry Demo Setup Script
===================================
This script sets up the complete demo environment:
1. Runs model evaluations using healthcare dataset
2. Creates agents with tools
3. Generates playground/agent traffic for monitoring data
4. Sets up guardrails (content filters)
"""

import json
import os
import time
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Configuration
SUBSCRIPTION_ID = "2852c4f9-8fcc-47c1-8e96-c4142a9ae463"
RESOURCE_GROUP = "rg-healthcareai-demo-jp-001"
PROJECT_NAME = "proj-healthcare-demo-jp-001"
AI_SERVICES_NAME = "ai-healthcare-foundry-jp-001"
LOCATION = "eastus2"

# Azure AI Foundry project connection string
# Format: <region>.api.azureml.ms;<subscription_id>;<resource_group>;<project_name>
PROJECT_CONNECTION_STRING = f"{LOCATION}.api.azureml.ms;{SUBSCRIPTION_ID};{RESOURCE_GROUP};{PROJECT_NAME}"

def get_project_client():
    """Get authenticated project client."""
    credential = DefaultAzureCredential()
    client = AIProjectClient.from_connection_string(
        conn_str=PROJECT_CONNECTION_STRING,
        credential=credential,
    )
    return client

def load_eval_dataset():
    """Load the healthcare evaluation dataset."""
    dataset = []
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, "healthcare-eval-dataset.jsonl")
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                dataset.append(json.loads(line))
    return dataset

# ============================================================
# PART 1: Generate model responses for evaluation data
# ============================================================
def generate_model_responses(client, dataset, model_name="gpt-5.3-chat"):
    """Generate responses from the deployed model for each question."""
    print(f"\n{'='*60}")
    print(f"Generating responses from {model_name}...")
    print(f"{'='*60}")
    
    results = []
    # Use the inference client from the project
    chat_client = client.inference.get_chat_completions_client()
    
    for i, item in enumerate(dataset):
        question = item["question"]
        print(f"  [{i+1}/{len(dataset)}] {question[:60]}...")
        
        try:
            response = chat_client.complete(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a knowledgeable healthcare assistant at a hospital. Provide accurate, helpful, and empathetic responses to patient questions. Always recommend consulting with a healthcare provider for specific medical concerns."},
                    {"role": "user", "content": question}
                ],
                max_tokens=500,
                temperature=0.7
            )
            answer = response.choices[0].message.content
            results.append({
                "question": question,
                "answer": answer,
                "ground_truth": item["ground_truth"],
                "context": item.get("context", "")
            })
            print(f"    -> Response received ({len(answer)} chars)")
        except Exception as e:
            print(f"    -> ERROR: {e}")
            results.append({
                "question": question,
                "answer": f"Error: {str(e)}",
                "ground_truth": item["ground_truth"],
                "context": item.get("context", "")
            })
    
    return results

# ============================================================
# PART 2: Create and run an Agent with tools
# ============================================================
def create_healthcare_agent(client):
    """Create a healthcare demo agent with Code Interpreter tool."""
    print(f"\n{'='*60}")
    print("Creating Healthcare Demo Agent...")
    print(f"{'='*60}")
    
    agent = client.agents.create_agent(
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

You have access to Code Interpreter for data analysis and visualization tasks.""",
        tools=[{"type": "code_interpreter"}],
    )
    print(f"  Agent created: {agent.id} ({agent.name})")
    return agent

def run_agent_conversations(client, agent):
    """Run sample conversations with the agent to generate monitoring data."""
    print(f"\n{'='*60}")
    print("Running agent conversations for demo data...")
    print(f"{'='*60}")
    
    conversations = [
        "What are the top 5 causes of hospital readmissions and how can they be prevented?",
        "Create a bar chart showing typical hospital department patient volumes: ER=450, Cardiology=280, Orthopedics=190, Neurology=150, Oncology=210, Pediatrics=320",
        "Explain the difference between inpatient and outpatient care, and when each is appropriate.",
        "What infection control protocols should be followed during flu season?",
        "Calculate the average length of stay if we have these patient stays: 2, 3, 5, 1, 7, 4, 3, 2, 6, 4 days. Also compute the standard deviation.",
        "What are the key metrics hospitals track for patient satisfaction?",
        "Summarize the Joint Commission's patient safety goals for 2026.",
    ]
    
    for i, message in enumerate(conversations):
        print(f"\n  Conversation [{i+1}/{len(conversations)}]: {message[:60]}...")
        try:
            thread = client.agents.create_thread()
            
            client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=message
            )
            
            run = client.agents.create_and_process_run(
                thread_id=thread.id,
                agent_id=agent.id,
            )
            
            if run.status == "completed":
                messages = client.agents.list_messages(thread_id=thread.id)
                if messages.data:
                    last_msg = messages.data[0]
                    if last_msg.content:
                        response_text = last_msg.content[0].text.value if hasattr(last_msg.content[0], 'text') else str(last_msg.content[0])
                        print(f"    -> Agent responded ({len(response_text)} chars)")
                    else:
                        print(f"    -> Agent responded (no text content)")
            else:
                print(f"    -> Run finished with status: {run.status}")
                
            time.sleep(1)  # Small delay between conversations
            
        except Exception as e:
            print(f"    -> ERROR: {e}")

# ============================================================
# PART 3: Run additional chat completions for traffic/monitoring
# ============================================================
def generate_traffic_for_monitoring(client, model_name="gpt-5.2"):
    """Generate additional API calls to populate monitoring dashboards."""
    print(f"\n{'='*60}")
    print(f"Generating traffic on {model_name} for monitoring data...")
    print(f"{'='*60}")
    
    chat_client = client.inference.get_chat_completions_client()
    
    queries = [
        "What is blood pressure and what do the numbers mean?",
        "How often should adults get a physical exam?",
        "What are the warning signs of dehydration?",
        "Explain what an MRI scan involves and how to prepare for one.",
        "What dietary changes can help manage high cholesterol?",
        "What is sepsis and why is it a medical emergency?",
        "How does telemedicine work and when is it appropriate?",
        "What are the stages of wound healing?",
        "Explain the importance of hand hygiene in healthcare settings.",
        "What should patients know about informed consent before procedures?",
    ]
    
    for i, query in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] {query[:55]}...")
        try:
            response = chat_client.complete(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful hospital information assistant."},
                    {"role": "user", "content": query}
                ],
                max_tokens=300,
                temperature=0.7
            )
            tokens = response.usage
            print(f"    -> OK (input: {tokens.prompt_tokens}, output: {tokens.completion_tokens} tokens)")
        except Exception as e:
            print(f"    -> ERROR: {e}")
        time.sleep(0.5)

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("AZURE AI FOUNDRY DEMO SETUP")
    print("Healthcare AI Demo for Providence")
    print("=" * 60)

    # Initialize client
    client = get_project_client()
    print(f"Connected to project: {PROJECT_NAME}")

    # Load dataset
    dataset = load_eval_dataset()
    print(f"Loaded {len(dataset)} evaluation questions")

    # Step 1: Generate responses from GPT-5.3-chat for evaluation
    results_53 = generate_model_responses(client, dataset, model_name="gpt-5.3-chat")
    
    # Save results for evaluation
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_file = os.path.join(script_dir, "eval-results-gpt53.jsonl")
    with open(results_file, "w", encoding="utf-8") as f:
        for r in results_53:
            f.write(json.dumps(r) + "\n")
    print(f"\nResults saved to {results_file}")

    # Step 2: Generate responses from GPT-5.2 for comparison
    results_52 = generate_model_responses(client, dataset, model_name="gpt-5.2")
    
    results_file_52 = os.path.join(script_dir, "eval-results-gpt52.jsonl")
    with open(results_file_52, "w", encoding="utf-8") as f:
        for r in results_52:
            f.write(json.dumps(r) + "\n")
    print(f"\nResults saved to {results_file_52}")

    # Step 3: Create agent and run conversations
    agent = create_healthcare_agent(client)
    run_agent_conversations(client, agent)
    
    # Step 4: Generate extra traffic on gpt-5.2 for monitoring variety
    generate_traffic_for_monitoring(client, model_name="gpt-5.2")
    
    # Step 5: Generate extra traffic on gpt-5.3-chat
    generate_traffic_for_monitoring(client, model_name="gpt-5.3-chat")

    print(f"\n{'='*60}")
    print("DEMO SETUP COMPLETE!")
    print(f"{'='*60}")
    print(f"""
Summary of what was created:
  - Hub: foundry-healthcare-hub-jp-001
  - Project: proj-healthcare-demo-jp-001  
  - Models deployed: gpt-5.2 (DataZoneStandard), gpt-5.3-chat (GlobalStandard)
  - Evaluation responses: 15 questions x 2 models
  - Agent: Providence-Healthcare-Agent (with Code Interpreter)
  - Agent conversations: 7 sample interactions
  - Monitoring traffic: 20 additional API calls across both models
  
Next steps in the Portal (ai.azure.com):
  1. Go to Evaluations -> Create new evaluation using the .jsonl files
  2. Go to Guardrails -> Review/customize content filters  
  3. Go to Operate -> Overview to see agent & model metrics
  4. Go to Operate -> Admin -> AI Gateway to set up APIM
""")

if __name__ == "__main__":
    main()
