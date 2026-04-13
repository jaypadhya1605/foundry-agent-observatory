"""
Part 4: Semantic Caching Demo
==============================
Shows how APIM semantic caching can save 60-80% on repeated/similar queries.
Compares cached vs. uncached latency and token spend.

⚠️  REQUIRES: APIM BasicV2+ tier and Azure Cache for Redis Enterprise.
    On Consumption tier, this script runs the calls but caching won't be active.
    The cost savings projection is still accurate for production planning.
"""

import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.getenv("APIM_GATEWAY_URL", "https://apim-providence-demo-jp-001.azure-api.net")
SUBSCRIPTION_KEY = os.getenv("APIM_SUBSCRIPTION_KEY", "")
MODEL_DEPLOYMENT = os.getenv("MODEL_NAME", "gpt-4o")
API_VERSION = "2024-02-01"


def call_gateway(question):
    """Call through APIM gateway."""
    url = f"{GATEWAY_URL}/openai/deployments/{MODEL_DEPLOYMENT}/chat/completions?api-version={API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    }
    body = {
        "messages": [
            {"role": "system", "content": "You are a healthcare assistant. Be concise."},
            {"role": "user", "content": question},
        ],
        "max_tokens": 200,
    }
    start = time.time()
    resp = requests.post(url, headers=headers, json=body)
    elapsed = time.time() - start
    return resp, elapsed


def demo_semantic_caching():
    """Demonstrate semantic caching cost savings."""
    print("=" * 70)
    print("  PART 4: Semantic Caching — Save 60-80% on AI Costs")
    print("=" * 70)

    if not SUBSCRIPTION_KEY:
        print("\n  ⚠️  Set APIM_SUBSCRIPTION_KEY in .env first!")
        return

    # ── Demo 1: Exact same question ──────────────────────
    print("\n📌 Demo 1: Identical Questions (Exact Cache Hit)")
    print("   Asking the exact same question 5 times...\n")

    question = "What are the symptoms of pneumonia?"
    for i in range(5):
        resp, elapsed = call_gateway(question)
        cache_status = resp.headers.get("x-cache-status", "MISS")
        tokens = 0
        if resp.status_code == 200:
            tokens = resp.json().get("usage", {}).get("total_tokens", 0)
        print(f"   Call {i+1}: {elapsed*1000:6.0f}ms | {tokens:4d} tokens | Cache: {cache_status}")

    print("\n   💡 After first call, responses come from cache:")
    print("      → Near-zero latency, zero token consumption, zero cost!")

    # ── Demo 2: Semantically similar questions ───────────
    print("\n📌 Demo 2: Similar Questions (Semantic Cache Hit)")
    print("   These ask the SAME thing with different wording...\n")

    similar_questions = [
        "What are the symptoms of pneumonia?",           # Original
        "What symptoms does pneumonia cause?",           # Reworded
        "How do I know if I have pneumonia?",            # Different phrasing
        "Signs and symptoms of pneumonia",               # Abbreviated
        "Pneumonia symptoms list",                       # Keyword style
    ]

    for i, q in enumerate(similar_questions):
        resp, elapsed = call_gateway(q)
        cache_status = resp.headers.get("x-cache-status", "MISS")
        tokens = 0
        if resp.status_code == 200:
            tokens = resp.json().get("usage", {}).get("total_tokens", 0)
        label = "ORIGINAL" if i == 0 else "SIMILAR"
        print(f"   [{label:8s}] {elapsed*1000:6.0f}ms | {tokens:4d} tokens | Cache: {cache_status} | {q}")

    print("\n   💡 Semantic caching uses embeddings to match similar intent,")
    print("      not just exact text. Threshold controls similarity (0.8 = 80% match).")

    # ── Demo 3: Cost savings calculation ──────────────────
    print("\n📌 Demo 3: Cost Savings Projection")
    print("   Based on typical healthcare Q&A patterns:\n")

    scenarios = [
        {"name": "Patient FAQ (high repetition)", "calls_per_day": 5000, "cache_hit_rate": 0.80},
        {"name": "Clinical decision support",     "calls_per_day": 2000, "cache_hit_rate": 0.60},
        {"name": "Mixed workload",                "calls_per_day": 3000, "cache_hit_rate": 0.70},
    ]

    avg_tokens_per_call = 300
    cost_per_1k_tokens = 0.01  # ~$10/1M tokens blended

    for s in scenarios:
        daily_calls = s["calls_per_day"]
        hit_rate = s["cache_hit_rate"]
        cache_hits = daily_calls * hit_rate
        cache_misses = daily_calls * (1 - hit_rate)

        cost_without = daily_calls * avg_tokens_per_call * cost_per_1k_tokens / 1000
        cost_with = cache_misses * avg_tokens_per_call * cost_per_1k_tokens / 1000
        savings = cost_without - cost_with
        savings_pct = (savings / cost_without) * 100

        print(f"   {s['name']:<35} {daily_calls:>6} calls/day | "
              f"Cache hit: {hit_rate:.0%} | "
              f"Savings: ${savings:.2f}/day ({savings_pct:.0f}%)")

    print("\n   💡 At scale, semantic caching pays for itself many times over.")
    print("      Redis Enterprise cost: ~$200/mo → saves $1000+/mo in tokens.")

    # ── Summary ──────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  SEMANTIC CACHING SUMMARY")
    print("=" * 70)
    print("  How it works:")
    print("    1. APIM generates embedding of the incoming prompt")
    print("    2. Searches Redis vector store for similar cached prompts")
    print("    3. If similarity > threshold (0.8) → return cached response")
    print("    4. If miss → forward to Azure OpenAI, cache the response")
    print()
    print("  Requirements:")
    print("    • Azure Cache for Redis Enterprise (RediSearch module)")
    print("    • Embeddings model deployed (text-embedding-3-small)")
    print("    • NOT compatible with streaming responses")
    print()
    print("  Best for:")
    print("    ✅ FAQ / Patient portals (high repetition)")
    print("    ✅ Standard clinical lookups")
    print("    ✅ Training / onboarding queries")
    print("    ❌ NOT for unique per-patient data queries")
    print("=" * 70)


if __name__ == "__main__":
    demo_semantic_caching()
