"""
Run Azure AI Foundry Evaluations
=================================
Creates evaluation runs that show up in the portal Evaluations tab.
Uses the azure-ai-evaluation SDK.
"""

import json
import os
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import (
    evaluate,
    RelevanceEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
)


# Configuration
SUBSCRIPTION_ID = "2852c4f9-8fcc-47c1-8e96-c4142a9ae463"
RESOURCE_GROUP  = "rg-healthcareai-demo-jp-001"
PROJECT_NAME    = "proj-healthcare-demo-jp-001"
AI_SERVICES     = "ai-healthcare-foundry-jp-001"
LOCATION        = "eastus2"

AOAI_ENDPOINT = f"https://{AI_SERVICES}.cognitiveservices.azure.com/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Azure AI project scope for evaluation
azure_ai_project = {
    "subscription_id": SUBSCRIPTION_ID,
    "resource_group_name": RESOURCE_GROUP,
    "project_name": PROJECT_NAME,
}

def run_evaluation(eval_file, eval_name, model_name):
    """Run evaluation using azure-ai-evaluation SDK."""
    print(f"\n{'='*60}")
    print(f"  Running evaluation: {eval_name}")
    print(f"  Data file: {eval_file}")
    print(f"{'='*60}")

    credential = DefaultAzureCredential()

    # Model config for evaluators (they need a model to judge quality)
    # Using gpt-4o as the judge model (supports max_tokens parameter)
    model_config = {
        "azure_endpoint": AOAI_ENDPOINT,
        "azure_deployment": "gpt-4o",
        "api_version": "2025-01-01-preview",
    }

    # Load data
    data_path = os.path.join(SCRIPT_DIR, eval_file)
    
    # Initialize evaluators with model_config
    relevance_eval = RelevanceEvaluator(model_config=model_config, credential=credential)
    coherence_eval = CoherenceEvaluator(model_config=model_config, credential=credential)
    fluency_eval = FluencyEvaluator(model_config=model_config, credential=credential)

    try:
        result = evaluate(
            data=data_path,
            evaluators={
                "relevance": relevance_eval,
                "coherence": coherence_eval,
                "fluency": fluency_eval,
            },
            evaluator_config={
                "relevance": {
                    "column_mapping": {
                        "query": "${data.question}",
                        "response": "${data.answer}",
                        "context": "${data.context}",
                    }
                },
                "coherence": {
                    "column_mapping": {
                        "query": "${data.question}",
                        "response": "${data.answer}",
                    }
                },
                "fluency": {
                    "column_mapping": {
                        "query": "${data.question}",
                        "response": "${data.answer}",
                    }
                },
            },
            azure_ai_project=azure_ai_project,
            evaluation_name=eval_name,
        )
        
        print(f"\n  Evaluation Results for {eval_name}:")
        if hasattr(result, 'metrics') and result.metrics:
            for metric, value in result.metrics.items():
                print(f"    {metric}: {value}")
        else:
            print(f"    Result: {result}")
            
    except Exception as e:
        print(f"  ERROR running evaluation: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("""
    ============================================================
      RUNNING MODEL EVALUATIONS
      These will show up in Foundry Portal -> Evaluations tab
    ============================================================
    """)

    # Run evaluation on GPT-5.3-chat results
    run_evaluation(
        eval_file="eval-results-gpt53chat.jsonl",
        eval_name="Healthcare-QA-GPT53-Chat",
        model_name="gpt-5.3-chat"
    )

    # Run evaluation on GPT-5.2 results
    run_evaluation(
        eval_file="eval-results-gpt52.jsonl",
        eval_name="Healthcare-QA-GPT52",
        model_name="gpt-5.2"
    )

    print("""
    ============================================================
      EVALUATIONS COMPLETE
      Check portal -> Build -> Evaluations to see results
    ============================================================
    """)

if __name__ == "__main__":
    main()
