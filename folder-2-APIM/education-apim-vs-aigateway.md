# APIM vs. AI Gateway — Education Reference

## What is Azure API Management (APIM)?

Azure API Management is a **fully managed service** for publishing, securing, transforming, maintaining, and monitoring APIs. It sits as a **reverse proxy** between API consumers and backend services.

### Core Capabilities
- **API Gateway** — Route, transform, and secure API calls
- **Developer Portal** — Self-service API documentation and onboarding
- **Management Plane** — Policy configuration, analytics, lifecycle management

---

## What is an AI Gateway?

An **AI Gateway** is APIM **configured with AI-specific policies** that understand OpenAI/LLM semantics. It's not a separate product — it's APIM with AI intelligence.

### Key Insight
> **APIM = General API Gateway**
> **AI Gateway = APIM + AI-Aware Policies (token limits, semantic caching, content safety)**

---

## Side-by-Side Comparison

| Capability | Standard APIM | APIM as AI Gateway |
|---|---|---|
| **Request routing** | ✅ URL/header-based | ✅ + Model-aware routing |
| **Rate limiting** | ✅ Requests per minute | ✅ + **Tokens per minute** |
| **Caching** | ✅ Exact URL match | ✅ + **Semantic similarity** cache |
| **Metrics** | ✅ Requests, latency | ✅ + **Token consumption** per model |
| **Content filtering** | ❌ No built-in | ✅ **LLM content safety** policies |
| **Cost control** | ✅ Rate limits | ✅ + **Token budgets** per consumer |
| **Load balancing** | ✅ Round-robin/weighted | ✅ + **429-aware** circuit breaker |
| **Auth** | ✅ Keys, OAuth, certs | ✅ + **Managed identity** to AI backends |

---

## Architecture: Before vs. After

### ❌ Before (No APIM)
```
┌──────────┐     DIRECT      ┌────────────────┐
│  App 1   │────────────────→│                │
├──────────┤                 │  Azure OpenAI  │
│  App 2   │────────────────→│                │
├──────────┤                 │   (gpt-4o)     │
│  App 3   │────────────────→│                │
└──────────┘                 └────────────────┘

Problems:
• Each app has its own API key (security risk)
• No centralized rate limiting
• No token tracking across apps
• No caching — duplicate queries = duplicate cost
• No content safety beyond model defaults
```

### ✅ After (With APIM AI Gateway)
```
┌──────────┐                 ┌──────────────────────────────────┐     ┌────────────────┐
│  App 1   │──┐              │    APIM AI Gateway               │     │                │
├──────────┤  │   Sub Key    │                                  │ MI  │  Azure OpenAI  │
│  App 2   │──┼─────────────→│  Auth → Cache → Limit → Metrics │────→│                │
├──────────┤  │              │                                  │     │   (gpt-4o)     │
│  App 3   │──┘              │  Token tracking per app/model    │     │                │
└──────────┘                 └──────────────────────────────────┘     └────────────────┘

Benefits:
• Single entry point with subscription keys (not AI keys)
• Per-app token budgets (free tier: 5K, premium: 100K)
• Semantic cache → 60-80% cost savings on repeated queries
• Content safety → additional filtering layer
• Central dashboard for all AI usage
```

---

## AI-Specific APIM Policies

### 1. Token Rate Limiting (`azure-openai-token-limit`)
Unlike standard rate limiting (requests/min), this counts **tokens** — the actual cost driver.
```
10,000 tokens/min per subscription → predictable costs
```

### 2. Semantic Caching (`azure-openai-semantic-cache-lookup/store`)
Uses **embeddings + vector search** to match semantically similar prompts.
```
"What are pneumonia symptoms?" ≈ "Signs of pneumonia" → CACHE HIT
```

### 3. Token Metrics (`azure-openai-emit-token-metric`)
Emits **custom metrics** to Azure Monitor with dimensions:
- Per subscription (which app)
- Per model (which deployment)
- Per API (which endpoint)

### 4. Content Safety (`llm-content-safety`)
Server-side content filtering that works **before** the request reaches the model:
- Hate, violence, sexual, self-harm categories
- Jailbreak detection
- Custom blocklists

---

## Cost Comparison: APIM Tiers

| Tier | Base Cost | Per-Call Cost | Best For |
|---|---|---|---|
| **Consumption** | $0/mo | ~$3.50/million calls | Demos, low traffic |
| **Basic v2** | ~$170/mo | Included (250K calls) | Small production |
| **Standard v2** | ~$700/mo | Included | Medium production |
| **Premium** | ~$2,800/mo | Included | Enterprise, VNET |

**For Providence demo**: Consumption tier → near-zero cost.

---

## Pros and Cons

### ✅ Pros of APIM as AI Gateway
1. **Cost control** — Token budgets prevent runaway spending
2. **Caching** — 60-80% savings on repeated queries
3. **Security** — Managed identity eliminates API key sprawl
4. **Observability** — Centralized token metrics across all apps
5. **Multi-tenancy** — Isolate usage by team/app/department
6. **Content safety** — Additional filtering layer
7. **Load balancing** — Distribute across regions, handle 429s
8. **No code changes** — Apps just change the endpoint URL

### ❌ Cons / Considerations
1. **Added latency** — ~10-50ms per request (minor for most cases)
2. **Streaming complexity** — Some policies don't work with SSE streaming
3. **Semantic cache cost** — Requires Redis Enterprise (~$200/mo)
4. **Learning curve** — XML policies require APIM expertise
5. **Single region** — Consumption tier is single-region only
6. **Not for all workloads** — Fine-tuning, batch APIs don't benefit much

### 📋 Recommendation for Providence
- **Start with Consumption tier** for pilot/evaluation
- **Enable token metrics and rate limiting first** (immediate value)
- **Add semantic caching** for high-repetition workloads (patient FAQ, intake Q&A)
- **Graduate to Standard v2** when going to production
