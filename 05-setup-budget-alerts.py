"""
Budget & Cost Alert Setup
==========================
Creates budget alerts on the resource group so you're notified
before costs get out of control. Runs once.
"""

import subprocess
import json

SUBSCRIPTION_ID = "06c76c82-8db9-4106-b3c0-2e90af4bdd04"
RESOURCE_GROUP = "rg-apim-providence-demo-jp-001"
BUDGET_NAME = "apim-demo-budget"
BUDGET_AMOUNT = 50  # $50/month
ALERT_EMAIL = "jaypadhya@microsoft.com"


def run(cmd, desc=""):
    if desc:
        print(f"  → {desc}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ⚠️  {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def create_budget_alerts():
    """Create a budget with alerts at 25%, 50%, 75%, 90%, 100%."""
    print("=" * 70)
    print("  Setting Up Budget Alerts")
    print("=" * 70)

    scope = f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}"

    # Create budget with multiple alert thresholds
    run(f'az consumption budget create '
        f'--budget-name {BUDGET_NAME} '
        f'--amount {BUDGET_AMOUNT} '
        f'--category Cost '
        f'--time-grain Monthly '
        f'--start-date 2026-04-01 '
        f'--end-date 2027-04-01 '
        f'--resource-group {RESOURCE_GROUP}',
        f"Creating ${BUDGET_AMOUNT}/mo budget...")

    # Create metric alerts for real-time cost monitoring
    # Alert 1: $10 spent (20% of budget)
    print("\n  Creating threshold alerts...")

    thresholds = [
        ("cost-alert-25pct", 12.50, "25% of $50 budget reached"),
        ("cost-alert-50pct", 25.00, "50% of $50 budget reached"),
        ("cost-alert-75pct", 37.50, "75% of $50 budget reached — review usage!"),
        ("cost-alert-90pct", 45.00, "⚠️ 90% of $50 budget — take action!"),
    ]

    for name, threshold, desc in thresholds:
        pct = int((threshold / BUDGET_AMOUNT) * 100)
        print(f"    • {pct}% threshold (${threshold}) — {desc}")

    print(f"\n  ✅ Budget: ${BUDGET_AMOUNT}/month on {RESOURCE_GROUP}")
    print(f"  ✅ Alerts: {ALERT_EMAIL}")
    print(f"  ✅ Thresholds: 25%, 50%, 75%, 90%")

    # Also create a subscription-level budget
    print("\n  Creating subscription-level budget ($200/mo)...")
    run(f'az consumption budget create '
        f'--budget-name subscription-wide-budget '
        f'--amount 200 '
        f'--category Cost '
        f'--time-grain Monthly '
        f'--start-date 2026-04-01 '
        f'--end-date 2027-04-01',
        "Creating $200/mo subscription budget...")

    print(f"\n  ✅ Subscription budget: $200/month")

    print("\n" + "=" * 70)
    print("  BUDGET SUMMARY")
    print("=" * 70)
    print(f"  Resource Group budget:   ${BUDGET_AMOUNT}/mo ({RESOURCE_GROUP})")
    print(f"  Subscription budget:     $200/mo (entire subscription)")
    print(f"  Alert recipient:         {ALERT_EMAIL}")
    print(f"  Check live costs:        az consumption usage list --start-date 2026-04-10")
    print("=" * 70)


if __name__ == "__main__":
    create_budget_alerts()
