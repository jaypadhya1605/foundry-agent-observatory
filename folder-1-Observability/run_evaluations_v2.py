"""
Run Evaluations on New Foundry v2 — Local computation + manual portal logging
==============================================================================
The azure-ai-evaluation SDK v1.15.3 uses MachineLearningServices/workspaces
for portal logging which is incompatible with Foundry v2 (CognitiveServices).
So we compute evaluations locally and output results.
"""

import json, os
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import (
    evaluate,
    RelevanceEvaluator,
    CoherenceEvaluator,
    FluencyEvaluator,
)

AI_SERVICES = "mf-FoundryDemo-healthcare-jp-001"
AOAI_ENDPOINT = f"https://{AI_SERVICES}.cognitiveservices.azure.com/"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def run_evaluation(eval_file, eval_name):
    print(f"\n{'='*60}")
    print(f"  Running evaluation: {eval_name}")
    print(f"  Data: {eval_file}")
    print(f"{'='*60}")

    credential = DefaultAzureCredential()
    model_config = {
        "azure_endpoint": AOAI_ENDPOINT,
        "azure_deployment": "gpt-4o",
        "api_version": "2025-01-01-preview",
    }

    data_path = os.path.join(SCRIPT_DIR, eval_file)
    relevance_eval = RelevanceEvaluator(model_config=model_config, credential=credential)
    coherence_eval = CoherenceEvaluator(model_config=model_config, credential=credential)
    fluency_eval   = FluencyEvaluator(model_config=model_config, credential=credential)

    try:
        result = evaluate(
            data=data_path,
            evaluators={
                "relevance": relevance_eval,
                "coherence": coherence_eval,
                "fluency":   fluency_eval,
            },
            evaluator_config={
                "relevance": {"column_mapping": {"query": "${data.question}", "response": "${data.answer}", "context": "${data.context}"}},
                "coherence": {"column_mapping": {"query": "${data.question}", "response": "${data.answer}"}},
                "fluency":   {"column_mapping": {"query": "${data.question}", "response": "${data.answer}"}},
            },
            # Skip portal logging (incompatible with Foundry v2)
            # Results will be saved locally
            output_path=os.path.join(SCRIPT_DIR, f"eval-output-{eval_name}"),
            evaluation_name=eval_name,
        )

        print(f"\n  Results for {eval_name}:")
        if hasattr(result, 'metrics') and result.metrics:
            for metric, value in result.metrics.items():
                print(f"    {metric}: {value}")
        elif isinstance(result, dict) and 'metrics' in result:
            for metric, value in result['metrics'].items():
                print(f"    {metric}: {value}")
        else:
            print(f"    Result: {result}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()


def main():
    print("""
    ============================================================
      RUNNING EVALUATIONS — New Foundry v2
      mf-FoundryDemo-healthcare-jp-001
      Judge model: gpt-4o (150K TPM)
    ============================================================
    """)

    run_evaluation("eval-results-gpt53chat.jsonl", "Healthcare-QA-GPT53-Chat")
    run_evaluation("eval-results-gpt54.jsonl",     "Healthcare-QA-GPT54")

    print("""
    ============================================================
      EVALUATIONS COMPLETE
      Results saved locally in eval-output-* directories
    ============================================================
    """)


if __name__ == "__main__":
    main()
