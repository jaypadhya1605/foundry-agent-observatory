"""
Part 1: WITHOUT APIM — Direct Azure OpenAI Calls
==================================================
Shows the "current state" where apps call Azure OpenAI directly.
No governance, no caching, no rate limiting, no token tracking.
"""

import json
import os
import time
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# ─── Direct Configuration (no gateway) ────────────────────
AOAI_ENDPOINT = os.getenv("AOAI_ENDPOINT", "https://ai-apim-demo-jp-001.cognitiveservices.azure.com/")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
TENANT_ID = os.getenv("AZURE_TENANT_ID", "651b2ef7-550d-4f5f-971f-166a3f599e7c")

def get_direct_client():
    """Create Azure OpenAI client — calls model DIRECTLY (no APIM)."""
    credential = DefaultAzureCredential(
        additionally_allowed_tenants=["*"],
        exclude_shared_token_cache_credential=True,
    )
    token = credential.get_token(
        "https://cognitiveservices.azure.com/.default",
        tenant_id=TENANT_ID,
    )
    return AzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=token.token,
        api_version="2025-01-01-preview",
    )


def demo_no_governance():
    """Show what happens without any API governance layer."""
    client = get_direct_client()

    print("=" * 70)
    print("  PART 1: CURRENT STATE — Direct Azure OpenAI (No APIM)")
    print("=" * 70)

    # ── Demo 1: No rate limiting ──────────────────────────
    print("\n📌 Demo 1: No Rate Limiting")
    print("   Sending 10 rapid requests — nothing stops us from burning tokens...")
    total_tokens = 0
    total_cost_est = 0.0

    questions = [
        "What are the symptoms of pneumonia?",
        "How does insulin resistance develop?",
        "What is the treatment for hypertension?",
        "Explain the stages of wound healing.",
        "What are common side effects of chemotherapy?",
        "How is Type 2 diabetes diagnosed?",
        "What is the difference between MRI and CT scan?",
        "Explain the mechanism of action of statins.",
        "What are the warning signs of a stroke?",
        "How does the immune system fight infection?",
    ]

    results = []
    for i, q in enumerate(questions):
        start = time.time()
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a healthcare assistant. Be concise."},
                {"role": "user", "content": q},
            ],
            max_completion_tokens=200,
            temperature=0.7,
        )
        elapsed = time.time() - start
        tokens_used = resp.usage.total_tokens
        total_tokens += tokens_used
        # Rough cost estimate: $5/1M input, $15/1M output for gpt-4o
        cost_est = (resp.usage.prompt_tokens * 5 + resp.usage.completion_tokens * 15) / 1_000_000
        total_cost_est += cost_est

        results.append({
            "question": q[:50],
            "tokens": tokens_used,
            "latency_ms": round(elapsed * 1000),
            "cost_est": round(cost_est, 6),
        })
        print(f"   [{i+1:2d}/10] {tokens_used:4d} tokens | {elapsed*1000:.0f}ms | ${cost_est:.6f} | {q[:45]}...")

    print(f"\n   ⚠️  TOTAL: {total_tokens} tokens | ~${total_cost_est:.4f}")
    print("   ⚠️  No rate limit hit. No cost control. No visibility.")

    # ── Demo 2: No caching ────────────────────────────────
    print("\n📌 Demo 2: No Caching — Same Question = Same Cost")
    print("   Asking the same question 5 times (paying full price each time)...")
    repeat_q = "What are the symptoms of pneumonia?"
    repeat_tokens = 0

    for i in range(5):
        start = time.time()
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a healthcare assistant. Be concise."},
                {"role": "user", "content": repeat_q},
            ],
            max_completion_tokens=200,
        )
        elapsed = time.time() - start
        repeat_tokens += resp.usage.total_tokens
        print(f"   Call {i+1}: {resp.usage.total_tokens} tokens | {elapsed*1000:.0f}ms — FULL PRICE (no cache)")

    print(f"   ⚠️  Wasted {repeat_tokens} tokens on identical questions. With caching: ~0 after first call.")

    # ── Demo 3: No content safety ─────────────────────────
    print("\n📌 Demo 3: No Content Safety Layer")
    print("   Without APIM, content filtering relies solely on the model's built-in filters.")
    print("   APIM adds an ADDITIONAL layer with customizable thresholds.")
    print("   → Jailbreak detection, PII filtering, custom blocklists — all configurable.")

    # ── Demo 4: No observability ──────────────────────────
    print("\n📌 Demo 4: No Token Observability")
    print("   Without APIM, you only see tokens in the response object.")
    print("   No centralized dashboard. No per-user/per-app analytics.")
    print("   No alerting when costs spike. No usage trending.")

    # ── Summary ───────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SUMMARY: Without APIM")
    print("=" * 70)
    print("  ❌ No rate limiting     → Costs can spiral uncontrolled")
    print("  ❌ No caching           → Paying repeatedly for same answers")
    print("  ❌ No content safety    → Single layer of protection only")
    print("  ❌ No token metrics     → Blind to usage patterns")
    print("  ❌ No load balancing    → Single point of failure")
    print("  ❌ No multi-tenant      → Can't isolate app/team usage")
    print("=" * 70)

    return results


if __name__ == "__main__":
    demo_no_governance()
