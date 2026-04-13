"""
Provision Azure Content Understanding Service (westus)
======================================================
Creates the Content Understanding resource and configures it
to work with APIM for patient discharge document processing.

Content Understanding = AI service for analyzing documents, images, audio, video.
Use case: Parse patient discharge summaries into structured data.
"""

import subprocess
import json
import sys

SUBSCRIPTION_ID = "06c76c82-8db9-4106-b3c0-2e90af4bdd04"
RESOURCE_GROUP = "rg-apim-providence-demo-jp-001"
LOCATION = "westus"
CU_ACCOUNT_NAME = "cu-providence-demo-jp-001"
APIM_NAME = "apim-providence-demo-jp-001"


def run(cmd, desc=""):
    """Run az CLI command."""
    if desc:
        print(f"  → {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0 and "already exists" not in result.stderr:
        print(f"    ⚠️  {result.stderr.strip()[:300]}")
    return result.stdout.strip()


def step1_register_provider():
    """Register the Content Understanding resource provider."""
    print("=" * 70)
    print("  STEP 1: Register Content Understanding Provider")
    print("=" * 70)

    run(f'az provider register --namespace Microsoft.CognitiveServices --wait',
        "Registering Microsoft.CognitiveServices provider...")
    print("  ✅ Provider registered.")


def step2_create_content_understanding():
    """Create Content Understanding (AI Services) in westus."""
    print("\n" + "=" * 70)
    print("  STEP 2: Create Content Understanding Service (westus)")
    print("=" * 70)
    print("  Region: westus (Content Understanding availability)")
    print("  SKU: S0 (pay-per-use)\n")

    run(f'az cognitiveservices account create '
        f'--name {CU_ACCOUNT_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--kind CognitiveServices '
        f'--sku S0 '
        f'--location {LOCATION} '
        f'--yes',
        f"Creating Content Understanding account '{CU_ACCOUNT_NAME}' in {LOCATION}...")

    # Get endpoint
    endpoint = run(
        f'az cognitiveservices account show '
        f'--name {CU_ACCOUNT_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query "properties.endpoint" -o tsv')
    print(f"  ✅ Content Understanding created: {endpoint}")
    return endpoint


def step3_grant_apim_access():
    """Grant APIM managed identity access to Content Understanding."""
    print("\n" + "=" * 70)
    print("  STEP 3: Grant APIM → Content Understanding RBAC")
    print("=" * 70)

    # Get APIM principal ID
    principal_id = run(
        f'az apim show --name {APIM_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query "identity.principalId" -o tsv')

    # Get CU resource ID
    cu_id = run(
        f'az cognitiveservices account show '
        f'--name {CU_ACCOUNT_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query id -o tsv')

    run(f'az role assignment create '
        f'--assignee {principal_id} '
        f'--role "Cognitive Services User" '
        f'--scope {cu_id}',
        "Granting 'Cognitive Services User' role to APIM...")
    print(f"  ✅ APIM ({APIM_NAME}) can now access Content Understanding via managed identity.")


def step4_add_apim_backend():
    """Add Content Understanding as a backend in APIM."""
    print("\n" + "=" * 70)
    print("  STEP 4: Add Content Understanding as APIM Backend")
    print("=" * 70)

    endpoint = run(
        f'az cognitiveservices account show '
        f'--name {CU_ACCOUNT_NAME} --resource-group {RESOURCE_GROUP} '
        f'--query "properties.endpoint" -o tsv')

    run(f'az apim backend create '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--backend-id content-understanding-backend '
        f'--protocol http '
        f'--url "{endpoint}contentunderstanding"',
        "Creating APIM backend for Content Understanding...")
    print(f"  ✅ Backend 'content-understanding-backend' → {CU_ACCOUNT_NAME}")


def step5_create_apim_api():
    """Create a Content Understanding API in APIM."""
    print("\n" + "=" * 70)
    print("  STEP 5: Create Content Understanding API in APIM")
    print("=" * 70)

    run(f'az apim api create '
        f'--service-name {APIM_NAME} '
        f'--resource-group {RESOURCE_GROUP} '
        f'--api-id content-understanding-api '
        f'--path "content-understanding" '
        f'--display-name "Content Understanding API" '
        f'--service-url "https://{CU_ACCOUNT_NAME}.cognitiveservices.azure.com/contentunderstanding" '
        f'--protocols https '
        f'--subscription-required true',
        "Creating Content Understanding API in APIM...")
    print("  ✅ API created at path /content-understanding")


def main():
    print("\n" + "=" * 70)
    print("  PROVISION CONTENT UNDERSTANDING + APIM INTEGRATION")
    print("  Use Case: Patient Discharge Document Processing")
    print("=" * 70)
    print(f"  Subscription: {SUBSCRIPTION_ID}")
    print(f"  Resource Group: {RESOURCE_GROUP}")
    print(f"  Location: {LOCATION}")
    print(f"  APIM: {APIM_NAME}\n")

    step1_register_provider()
    step2_create_content_understanding()
    step3_grant_apim_access()
    step4_add_apim_backend()
    step5_create_apim_api()

    print("\n" + "=" * 70)
    print("  SETUP COMPLETE")
    print("=" * 70)
    print(f"  Content Understanding: {CU_ACCOUNT_NAME} ({LOCATION})")
    print(f"  APIM endpoint:         https://{APIM_NAME}.azure-api.net/content-understanding")
    print(f"  Auth:                  Managed Identity (no API keys)")
    print("  Next: Run 02-patient-discharge-analyzer.py to test the pipeline")
    print("=" * 70)


if __name__ == "__main__":
    main()
