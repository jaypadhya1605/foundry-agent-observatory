"""
Part 3: WITH APIM — AI Gateway Governed Calls
================================================
Same questions as Part 1, but now routed through APIM AI Gateway.
Shows: managed identity auth, request tracking, custom headers, subscription key governance.

Note: We're running Consumption tier ($0 base cost) which provides:
  ✅ Backend routing + managed identity (no API keys to Azure OpenAI)
  ✅ Subscription key governance (per-app access control)
  ✅ Custom header injection (request tracking, model/latency metadata)
  ✅ Built-in subscription-level throttling
  ❌ Token-level rate limiting (requires BasicV2+)
  ❌ Semantic caching (requires BasicV2+ and Redis Enterprise)
  ❌ Token metrics emission (requires BasicV2+)
"""

import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── APIM Gateway Configuration ──────────────────────────
GATEWAY_URL = os.getenv("APIM_GATEWAY_URL", "https://apim-providence-demo-jp-001.azure-api.net")
SUBSCRIPTION_KEY = os.getenv("APIM_SUBSCRIPTION_KEY", "")
MODEL_DEPLOYMENT = os.getenv("MODEL_NAME", "gpt-4o")
API_VERSION = "2024-02-01"


def call_through_gateway(question, system_prompt="You are a healthcare assistant. Be concise."):
    """Call Azure OpenAI through APIM gateway — shows governance in action."""
    url = f"{GATEWAY_URL}/openai/deployments/{MODEL_DEPLOYMENT}/chat/completions?api-version={API_VERSION}"

    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    }

    body = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        "max_tokens": 200,
        "temperature": 0.7,
    }

    start = time.time()
    resp = requests.post(url, headers=headers, json=body)
    elapsed = time.time() - start

    return resp, elapsed


def demo_with_governance():
    """Show the same calls but WITH APIM governance."""
    print("=" * 70)
    print("  PART 3: WITH APIM — AI Gateway Governed Calls")
    print("=" * 70)

    if not SUBSCRIPTION_KEY:
        print("\n  ⚠️  Set APIM_SUBSCRIPTION_KEY in .env first!")
        print("  Get it from: az apim subscription keys list --service-name apim-providence-demo-jp-001 \\")
        print("               --resource-group rg-apim-providence-demo-jp-001 --subscription-id demo-sub")
        return

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

    # ── Demo 1: Calls routed through APIM with tracking headers ─────
    print("\n📌 Demo 1: Centralized Gateway with Request Tracking")
    print("   Every request now gets a unique tracking ID, model info, and latency metadata.\n")

    total_tokens = 0
    results = []

    for i, q in enumerate(questions):
        resp, elapsed = call_through_gateway(q)

        if resp.status_code == 200:
            data = resp.json()
            usage = data.get("usage", {})
            total = usage.get("total_tokens", 0)
            total_tokens += total

            # Custom headers injected by our APIM policy
            request_id = resp.headers.get("x-apim-request-id", "N/A")
            model = resp.headers.get("x-apim-model", "N/A")
            region = resp.headers.get("x-apim-region", "N/A")

            results.append({
                "question": q[:45],
                "tokens": total,
                "latency_ms": round(elapsed * 1000),
                "request_id": request_id[:12],
                "model": model,
            })

            print(f"   [{i+1:2d}/10] {total:4d} tokens | {elapsed*1000:.0f}ms | "
                  f"model={model} | region={region} | id={request_id[:12]}... | {q[:40]}...")
        elif resp.status_code == 429:
            print(f"   [{i+1:2d}/10] 🛑 RATE LIMITED! (429) — Subscription throttle hit!")
            results.append({"question": q[:45], "status": "RATE_LIMITED"})
        else:
            print(f"   [{i+1:2d}/10] ⚠️  Status {resp.status_code}: {resp.text[:100]}")

    print(f"\n   ✅ TOTAL: {total_tokens} tokens consumed through gateway")
    print("   ✅ Every call tracked with unique request ID (x-apim-request-id)")
    print("   ✅ Model and processing time exposed via custom headers")
    print("   ✅ All calls authenticated via managed identity (no API keys in code!)")

    # ── Demo 2: Subscription key as access control ────────
    print("\n📌 Demo 2: Subscription Key Governance")
    print("   Without valid subscription key → 401 Unauthorized.\n")

    bad_url = f"{GATEWAY_URL}/openai/deployments/{MODEL_DEPLOYMENT}/chat/completions?api-version={API_VERSION}"
    bad_resp = requests.post(bad_url, headers={"Content-Type": "application/json"},
                             json={"messages": [{"role": "user", "content": "test"}]})
    print(f"   No key:      Status {bad_resp.status_code} — {'🛑 BLOCKED' if bad_resp.status_code == 401 else '⚠️ Unexpected'}")

    wrong_resp = requests.post(bad_url,
                               headers={"Content-Type": "application/json",
                                        "Ocp-Apim-Subscription-Key": "invalid-key-12345"},
                               json={"messages": [{"role": "user", "content": "test"}]})
    print(f"   Wrong key:   Status {wrong_resp.status_code} — {'🛑 BLOCKED' if wrong_resp.status_code == 401 else '⚠️ Unexpected'}")

    good_resp, _ = call_through_gateway("What is HIPAA?")
    print(f"   Valid key:   Status {good_resp.status_code} — {'✅ ALLOWED' if good_resp.status_code == 200 else '⚠️ Check config'}")

    print("\n   💡 Each team/app gets their own subscription key.")
    print("   → Revoke access instantly without changing backend keys.")
    print("   → Different keys can have different rate limits (on BasicV2+).")

    # ── Demo 3: Managed identity (no API keys) ────────────
    print("\n📌 Demo 3: No API Keys to Azure OpenAI")
    print("   APIM uses managed identity to authenticate to Azure OpenAI.")
    print("   → No secrets in code or config")
    print("   → No key rotation needed")
    print("   → RBAC-controlled access")
    print("   → The ONLY key is the APIM subscription key (which you control)")

    # ── Demo 4: What you unlock by upgrading to BasicV2+ ─
    print("\n📌 Demo 4: What BasicV2+ Unlocks (Production Tier)")
    print("   Consumption tier ($0 base) gives you the gateway pattern.")
    print("   BasicV2+ (~$170/mo) adds AI-SPECIFIC governance:\n")
    print("   ┌─────────────────────────────────────────────────────────┐")
    print("   │  azure-openai-token-limit    → Token-per-minute budgets │")
    print("   │  azure-openai-semantic-cache  → Vector similarity cache  │")
    print("   │  azure-openai-emit-token-metric → Per-model token metrics│")
    print("   │  llm-content-safety          → Pre-model content filter  │")
    print("   └─────────────────────────────────────────────────────────┘")
    print("   💡 Recommendation: Start Consumption to validate the pattern,")
    print("      then upgrade when workload justifies the base cost.")

    # ── Comparison ────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  COMPARISON: Without APIM vs. With APIM")
    print("=" * 70)
    print(f"  {'Feature':<30} {'Without APIM':<20} {'With APIM'}")
    print(f"  {'-'*30} {'-'*20} {'-'*20}")
    print(f"  {'Gateway Routing':<30} {'❌ Direct calls':<20} {'✅ Centralized'}")
    print(f"  {'Auth to OpenAI':<30} {'🔑 API Key':<20} {'🔐 Managed Identity'}")
    print(f"  {'Access Control':<30} {'❌ Shared keys':<20} {'✅ Per-app sub keys'}")
    print(f"  {'Request Tracking':<30} {'❌ None':<20} {'✅ Unique request IDs'}")
    print(f"  {'Token Rate Limiting':<30} {'❌ None':<20} {'✅ BasicV2+ policy'}")
    print(f"  {'Semantic Caching':<30} {'❌ None':<20} {'✅ BasicV2+ + Redis'}")
    print(f"  {'Cost (base)':<30} {'$0':<20} {'$0 (Consumption)'}")
    print(f"  {'Centralized Metrics':<30} {'❌ None':<20} {'✅ App Insights'}")
    print(f"  {'Multi-tenant Isolation':<30} {'❌ None':<20} {'✅ Per-subscription'}")
    print(f"  {'Content Safety':<30} {'Model only':<20} {'✅ APIM + Model'}")
    print("=" * 70)

    return results


if __name__ == "__main__":
    demo_with_governance()
