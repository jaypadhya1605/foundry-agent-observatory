"""
Part 2: Setup APIM as AI Gateway
==================================
Creates and configures APIM with Azure OpenAI backend,
managed identity auth, and AI governance policies.

Run this ONCE to set up the gateway infrastructure.
"""

import json
import os
import subprocess
import sys
import time

# ─── Configuration ────────────────────────────────────────
SUBSCRIPTION_ID = "06c76c82-8db9-4106-b3c0-2e90af4bdd04"
RESOURCE_GROUP = "rg-apim-providence-demo-jp-001"
LOCATION = "eastus2"
APIM_NAME = "apim-providence-demo-jp-001"
AI_SERVICES_NAME = "ai-apim-demo-jp-001"
APPINSIGHTS_NAME = "appinsights-apim-demo-jp-001"
LOG_ANALYTICS_NAME = "law-apim-demo-jp-001"
MODEL_DEPLOYMENT = "gpt-4o"

def run(cmd, desc=""):
    """Run az CLI command and return output."""
    if desc:
        print(f"\n  → {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"    ⚠️  {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def step1_create_apim():
    """Create APIM instance (Consumption tier — $0 base cost)."""
    print("=" * 70)
    print("  STEP 1: Create API Management (Consumption Tier)")
    print("=" * 70)
    print("  Consumption tier = pay-per-call (~$3.50/million calls)")
    print("  Perfect for demos and low-traffic scenarios.\n")

    run(f'az apim create '
        f'--name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--location {LOCATION} '
        f'--publisher-name "Providence-Demo" '
        f'--publisher-email "jaypadhya@microsoft.com" '
        f'--sku-name Consumption '
        f'--enable-managed-identity true',
        "Creating APIM instance (Consumption tier)...")

    # Get APIM principal ID for RBAC
    principal_id = run(
        f'az apim show --name {APIM_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query "identity.principalId" -o tsv')
    print(f"  ✅ APIM created. Managed Identity Principal: {principal_id}")
    return principal_id


def step2_grant_rbac(principal_id):
    """Grant APIM managed identity access to Azure OpenAI."""
    print("\n" + "=" * 70)
    print("  STEP 2: Grant APIM → Azure OpenAI RBAC Access")
    print("=" * 70)

    aoai_id = run(
        f'az cognitiveservices account show '
        f'--name {AI_SERVICES_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query id -o tsv')

    run(f'az role assignment create '
        f'--assignee {principal_id} '
        f'--role "Cognitive Services User" '
        f'--scope {aoai_id}',
        "Granting 'Cognitive Services User' role...")
    print("  ✅ RBAC assigned. APIM can now call Azure OpenAI via managed identity.")


def step3_create_backend():
    """Create Azure OpenAI backend in APIM."""
    print("\n" + "=" * 70)
    print("  STEP 3: Create Azure OpenAI Backend")
    print("=" * 70)

    run(f'az apim backend create '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--backend-id openai-backend '
        f'--protocol http '
        f'--url "https://{AI_SERVICES_NAME}.cognitiveservices.azure.com/openai"',
        "Creating backend pointing to Azure OpenAI...")
    print(f"  ✅ Backend 'openai-backend' → {AI_SERVICES_NAME}")


def step4_import_api():
    """Import Azure OpenAI API specification."""
    print("\n" + "=" * 70)
    print("  STEP 4: Import Azure OpenAI API Specification")
    print("=" * 70)

    run(f'az apim api import '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--api-id azure-openai-api '
        f'--path "openai" '
        f'--display-name "Azure OpenAI Service" '
        f'--specification-format OpenApi '
        f'--specification-url "https://raw.githubusercontent.com/Azure/azure-rest-api-specs/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable/2024-02-01/inference.json" '
        f'--service-url "https://{AI_SERVICES_NAME}.cognitiveservices.azure.com/openai" '
        f'--subscription-required true',
        "Importing OpenAI API spec...")
    print("  ✅ API imported at path /openai")


def step5_apply_policies():
    """Apply AI Gateway policies — the core value-add."""
    print("\n" + "=" * 70)
    print("  STEP 5: Apply AI Governance Policies")
    print("=" * 70)
    print("  This is where APIM becomes an AI GATEWAY.\n")

    policy_xml = f"""<policies>
    <inbound>
        <base />
        <!-- 1. Route to Azure OpenAI backend -->
        <set-backend-service backend-id="openai-backend" />

        <!-- 2. Authenticate with managed identity (no API keys!) -->
        <authentication-managed-identity resource="https://cognitiveservices.azure.com" />

        <!-- 3. Token rate limiting — cost control -->
        <azure-openai-token-limit
            tokens-per-minute="10000"
            counter-key="@(context.Subscription.Id)"
            estimate-prompt-tokens="true"
            tokens-consumed-header-name="x-tokens-consumed"
            remaining-tokens-header-name="x-tokens-remaining" />

        <!-- 4. Token metrics — observability -->
        <azure-openai-emit-token-metric namespace="AzureOpenAI">
            <dimension name="Subscription" value="@(context.Subscription.Id)" />
            <dimension name="Model" value="@(context.Request.MatchedParameters["deployment-id"])" />
            <dimension name="API" value="@(context.Api.Name)" />
        </azure-openai-emit-token-metric>
    </inbound>
    <backend>
        <base />
    </backend>
    <outbound>
        <base />
    </outbound>
    <on-error>
        <base />
    </on-error>
</policies>"""

    # Save policy to temp file
    policy_path = os.path.join(os.path.dirname(__file__), "gateway-policy.xml")
    with open(policy_path, "w") as f:
        f.write(policy_xml)

    run(f'az apim api policy create '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--api-id azure-openai-api '
        f'--xml-policy "{policy_path}"',
        "Applying AI governance policies...")

    print("  ✅ Policies applied:")
    print("     • Managed identity auth (no API keys)")
    print("     • Token rate limiting (10K TPM)")
    print("     • Token usage metrics (per subscription, model, API)")


def step6_create_subscription_key():
    """Create APIM subscription for the demo."""
    print("\n" + "=" * 70)
    print("  STEP 6: Create API Subscription Key")
    print("=" * 70)

    run(f'az apim subscription create '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--subscription-id demo-sub '
        f'--display-name "Providence Demo" '
        f'--scope "/apis/azure-openai-api" '
        f'--state active',
        "Creating subscription key...")

    keys = run(f'az apim subscription keys list '
               f'--service-name {APIM_NAME} '
               f'--resource-group {RESOURCE_GROUP} '
               f'--subscription-id demo-sub -o json')
    if keys:
        key_data = json.loads(keys)
        print(f"  ✅ Subscription key created.")
        print(f"  Primary Key: {key_data.get('primaryKey', 'N/A')[:8]}...")
    else:
        print("  ✅ Subscription created (retrieve keys from portal).")


def step7_setup_monitoring():
    """Create Application Insights + Log Analytics for observability."""
    print("\n" + "=" * 70)
    print("  STEP 7: Setup Monitoring (App Insights + Log Analytics)")
    print("=" * 70)

    run(f'az monitor log-analytics workspace create '
        f'--workspace-name {LOG_ANALYTICS_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--location {LOCATION}',
        "Creating Log Analytics workspace...")

    law_id = run(f'az monitor log-analytics workspace show '
                 f'--workspace-name {LOG_ANALYTICS_NAME} '
                 f'--resource-group {RESOURCE_GROUP} '
                 f'--query id -o tsv')

    run(f'az monitor app-insights component create '
        f'--app {APPINSIGHTS_NAME} '
        f'--location {LOCATION} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--workspace {law_id}',
        "Creating Application Insights...")

    print("  ✅ Monitoring stack deployed.")


def print_summary():
    """Print final configuration summary."""
    gateway_url = run(
        f'az apim show --name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--query "gatewayUrl" -o tsv')

    print("\n" + "=" * 70)
    print("  SETUP COMPLETE! — AI Gateway Ready")
    print("=" * 70)
    print(f"  Gateway URL:  {gateway_url}")
    print(f"  API Path:     {gateway_url}/openai/deployments/{MODEL_DEPLOYMENT}/chat/completions")
    print(f"  Auth:         Ocp-Apim-Subscription-Key header")
    print(f"  Policies:     Token limit (10K TPM), Token metrics, Managed identity")
    print(f"  Monitoring:   {APPINSIGHTS_NAME}")
    print("=" * 70)
    print("\n  Next: Run 03-with-apim.py to see the difference!\n")


if __name__ == "__main__":
    print("\n🚀 Setting up APIM as AI Gateway for Providence Demo\n")
    principal_id = step1_create_apim()
    step2_grant_rbac(principal_id)
    step3_create_backend()
    step4_import_api()
    step5_apply_policies()
    step6_create_subscription_key()
    step7_setup_monitoring()
    print_summary()
