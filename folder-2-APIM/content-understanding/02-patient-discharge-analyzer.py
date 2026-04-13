"""
Patient Discharge Analyzer — Content Understanding via APIM
============================================================
Demonstrates using Azure Content Understanding (routed through APIM)
to parse patient discharge documents into structured data.

This shows that APIM AI Gateway governs ALL AI services — not just LLMs.
Content Understanding, Document Intelligence, Speech, Vision — all can
be monitored, rate-limited, and cached through the same gateway.
"""

import base64
import json
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GATEWAY_URL = os.getenv("APIM_GATEWAY_URL", "https://apim-providence-demo-jp-001.azure-api.net")
SUBSCRIPTION_KEY = os.getenv("CU_SUBSCRIPTION_KEY", os.getenv("APIM_SUBSCRIPTION_KEY", ""))
CU_API_VERSION = "2024-12-01-preview"


# ─── Sample Documents for CU Analysis ─────────────────────
# Using public MS sample docs — CU requires accessible URLs
# In production, these would be patient discharge PDFs in blob storage
SAMPLE_DOCUMENTS = [
    {
        "patient_id": "Sample Invoice Document",
        "url": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/sample-invoice.pdf",
    },
    {
        "patient_id": "Sample Receipt Document",
        "url": "https://raw.githubusercontent.com/Azure-Samples/cognitive-services-REST-api-samples/master/curl/form-recognizer/contoso-allinone.jpg",
    },
]


def create_analyzer():
    """Create a Content Understanding analyzer for discharge documents."""
    print("=" * 70)
    print("  Creating Patient Discharge Analyzer")
    print("=" * 70)

    url = f"{GATEWAY_URL}/content-understanding/analyzers/discharge-doc-analyzer?api-version={CU_API_VERSION}"
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    }

    # Field schema uses only CU-supported types (string, object)
    analyzer_config = {
        "description": "Patient discharge document analyzer for structured data extraction",
        "scenario": "document",
        "fieldSchema": {
            "fields": {
                "PatientName": {
                    "type": "string",
                    "description": "Full name of the patient"
                },
                "MRN": {
                    "type": "string",
                    "description": "Medical Record Number"
                },
                "AdmissionDate": {
                    "type": "string",
                    "description": "Date patient was admitted"
                },
                "DischargeDate": {
                    "type": "string",
                    "description": "Date patient was discharged"
                },
                "PrimaryDiagnosis": {
                    "type": "string",
                    "description": "Primary diagnosis or reason for admission"
                },
                "DischargeMedications": {
                    "type": "string",
                    "description": "All medications prescribed at discharge"
                },
                "FollowUpInstructions": {
                    "type": "string",
                    "description": "Follow-up care instructions"
                },
                "DischargeCondition": {
                    "type": "string",
                    "description": "Patient condition at discharge"
                }
            }
        }
    }

    resp = requests.put(url, headers=headers, json=analyzer_config)
    if resp.status_code in (200, 201):
        print("  ✅ Analyzer 'discharge-doc-analyzer' created successfully")
        return True
    elif resp.status_code == 409:
        print("  ✅ Analyzer 'discharge-doc-analyzer' already exists — reusing")
        return True
    else:
        print(f"  ⚠️  Status {resp.status_code}: {resp.text[:300]}")
        return False


def analyze_discharge_document(patient_data):
    """Submit a discharge document for analysis through APIM."""
    patient_id = patient_data["patient_id"]

    # Use prebuilt-read analyzer (works with any document URL)
    # Our custom analyzer would need docs in blob storage; prebuilt-read
    # demonstrates APIM governance just as effectively
    url = (f"{GATEWAY_URL}/content-understanding/analyzers/"
           f"prebuilt-read:analyze?api-version={CU_API_VERSION}")
    headers = {
        "Content-Type": "application/json",
        "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
    }

    # Public sample document from Microsoft Learn docs
    body = {
        "url": patient_data["url"],
    }

    start = time.time()
    resp = requests.post(url, headers=headers, json=body)
    elapsed = time.time() - start

    # Check APIM headers for governance evidence
    request_id = resp.headers.get("x-apim-request-id", "N/A")
    apim_service = resp.headers.get("x-apim-service", "N/A")

    print(f"\n  Document: {patient_id}")
    print(f"  APIM Request ID: {request_id}")
    print(f"  APIM Service:    {apim_service}")
    print(f"  Latency: {elapsed*1000:.0f}ms")
    print(f"  Status: {resp.status_code}")

    if resp.status_code == 200:
        result = resp.json()
        print(f"  Extracted Fields:")
        fields = result.get("result", {}).get("contents", [{}])
        if fields:
            for field_name, field_val in fields[0].get("fields", {}).items():
                val = field_val.get("valueString", "N/A")
                print(f"    • {field_name}: {val}")
    elif resp.status_code == 202:
        # Async operation — poll for result
        operation_url = resp.headers.get("Operation-Location", "")
        print(f"  ⏳ Async operation started. Polling...")
        if operation_url:
            poll_result(operation_url, headers)
    else:
        print(f"  Response: {resp.text[:300]}")

    return resp, elapsed


def poll_result(operation_url, headers, max_wait=90):
    """Poll an async Content Understanding operation via APIM."""
    # Rewrite CU backend URL to route polling through APIM gateway
    # CU returns: https://cu-xxx.services.ai.azure.com/contentunderstanding/...
    # We need:    https://apim-xxx.azure-api.net/content-understanding/...
    if "contentunderstanding/" in operation_url and GATEWAY_URL not in operation_url:
        path = operation_url.split("contentunderstanding/", 1)[1]
        operation_url = f"{GATEWAY_URL}/content-understanding/{path}"
        print(f"    (Routing poll through APIM gateway)")

    waited = 0
    while waited < max_wait:
        time.sleep(3)
        waited += 3
        resp = requests.get(operation_url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("status", "unknown")
            print(f"    Status: {status} ({waited}s elapsed)")
            if status.lower() == "succeeded":
                result = data.get("result", {})
                contents = result.get("contents", [])
                if contents:
                    for field_name, field_val in contents[0].get("fields", {}).items():
                        val = field_val.get("valueString", "N/A")
                        print(f"    • {field_name}: {val}")
                return data
            elif status.lower() == "failed":
                print(f"    ❌ Analysis failed: {data.get('error', {})}")
                return data
    print(f"    ⚠️  Timed out after {max_wait}s")
    return None


def demo_discharge_analysis():
    """Full demo: analyze patient discharge documents through APIM."""
    print("=" * 70)
    print("  PATIENT DISCHARGE ANALYSIS via APIM + Content Understanding")
    print("=" * 70)
    print("  This demonstrates APIM governing a non-LLM AI service.")
    print("  Same gateway, same subscription keys, same observability.\n")

    if not SUBSCRIPTION_KEY:
        print("  ⚠️  Set CU_SUBSCRIPTION_KEY in .env first!")
        return

    # Step 1: Create the analyzer
    create_analyzer()

    # Step 2: Analyze each discharge document
    print("\n📌 Analyzing Patient Discharge Documents")
    print("   Each call goes through APIM → Content Understanding (westus)")
    print("   APIM provides: tracking, auth, rate limiting, metrics\n")

    for patient in SAMPLE_DOCUMENTS:
        analyze_discharge_document(patient)

    # Summary
    print("\n" + "=" * 70)
    print("  KEY TAKEAWAY")
    print("=" * 70)
    print("  APIM AI Gateway isn't just for LLMs / chat completions.")
    print("  It governs ALL AI services through a single pane of glass:")
    print("    • Azure OpenAI (GPT-4o)     — chat, completions")
    print("    • Content Understanding     — document analysis")
    print("    • Document Intelligence     — form/receipt OCR")
    print("    • Speech Services           — transcription")
    print("    • Custom Vision             — image classification")
    print()
    print("  One gateway. One set of policies. One dashboard.")
    print("=" * 70)


if __name__ == "__main__":
    demo_discharge_analysis()
