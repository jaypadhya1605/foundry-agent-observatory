# Providence APIM & AI Gateway Deep Dive — Monday Demo Plan

## Session Goal
Show Providence team the **value of APIM as an AI Gateway** — from current unmanaged state to a governed, observable, cost-controlled AI layer.

---

## Agenda (~90 min)

### Part 1: The Problem — Current State Without APIM (15 min)
- **Script**: `01-without-apim.py`
- Direct calls to Azure OpenAI — no governance, no observability, no cost controls
- Show: no rate limiting, no caching, no content safety filtering
- Demonstrate: token consumption with zero visibility
- **Key message**: "This is how most teams start — and why costs spiral"

### Part 2: Education — What is APIM & AI Gateway? (20 min)
- **Reference**: `education-apim-vs-aigateway.md`
- What is Azure API Management?
- What is an AI Gateway? How does it differ from standard APIM?
- AI-specific policies: token limits, semantic caching, content safety
- Architecture diagrams: before vs. after

### Part 3: Hands-On — Setting Up APIM as AI Gateway (20 min)
- **Script**: `02-setup-apim-gateway.py`
- Create APIM → connect Azure OpenAI backend
- Enable managed identity authentication
- Import OpenAI API spec
- Apply AI governance policies (token limit, metrics, content safety)

### Part 4: The Transformation — With APIM (20 min)
- **Script**: `03-with-apim.py`
- Same calls routed through APIM gateway
- Show: token metrics headers, rate limiting in action, cached responses
- Compare: latency, cost, observability vs. Part 1
- **Script**: `04-semantic-caching-demo.py`
- Demonstrate 60-80% cost savings with semantic cache

### Part 5: Pros, Cons & Recommendations (15 min)
- **Reference**: `pros-cons-analysis.md`
- When to use APIM, when not to
- Cost of APIM itself vs. savings
- Recommendations for Providence's architecture

---

## Resources Created
| Resource | Type | SKU | Est. Cost |
|---|---|---|---|
| rg-apim-providence-demo-jp-001 | Resource Group | — | $0 |
| ai-apim-demo-jp-001 | AI Services | S0 | Pay-per-use |
| apim-providence-demo-jp-001 | API Management | Consumption | ~$3.50/million calls |
| appinsights-apim-demo-jp-001 | Application Insights | — | Free tier |
| gpt-4o (deployment) | Model | GlobalStandard 30 TPM | Pay-per-token |

## Budget Alert
- $50/month alert set on the resource group
