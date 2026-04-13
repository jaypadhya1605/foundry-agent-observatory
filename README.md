# Providence APIM & AI Gateway Deep Dive

End-to-end demo: Azure API Management as an AI Gateway for healthcare workloads.

## Repository Structure

```
folder-1-Observability/     # Foundry agent observability & tracing demos
folder-2-APIM/              # APIM AI Gateway + Content Understanding
  ├── 01-without-apim.py          # Direct Azure OpenAI calls (no governance)
  ├── 02-setup-apim-gateway.py    # Provision APIM + AI policies
  ├── 03-with-apim.py             # Governed calls through APIM
  ├── 04-semantic-caching-demo.py # Semantic caching cost savings
  ├── 05-setup-budget-alerts.py   # Budget alerts ($25/mo)
  ├── content-understanding/      # Content Understanding + APIM integration
  │   ├── 01-provision-content-understanding.py
  │   ├── 02-patient-discharge-analyzer.py
  │   └── cu-gateway-policy.xml
  ├── gateway-policy.xml
  └── education-apim-vs-aigateway.md
.github/workflows/deploy.yml     # CI/CD pipeline
```

## Quick Start

```bash
# 1. Set environment
export AZURE_SUBSCRIPTION_ID=06c76c82-8db9-4106-b3c0-2e90af4bdd04

# 2. Run APIM setup
python folder-2-APIM/02-setup-apim-gateway.py

# 3. Provision Content Understanding (westus)
python folder-2-APIM/content-understanding/01-provision-content-understanding.py

# 4. Test patient discharge analysis
python folder-2-APIM/content-understanding/02-patient-discharge-analyzer.py
```

## Key Resources
| Resource | Region | SKU |
|---|---|---|
| apim-providence-demo-jp-001 | eastus2 | Consumption |
| ai-apim-demo-jp-001 (OpenAI) | eastus2 | S0 |
| cu-providence-demo-jp-001 (Content Understanding) | westus | S0 |

## Budget: $25/month on resource group
