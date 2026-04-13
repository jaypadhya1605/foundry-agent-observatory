import json
files = [
    r"c:\Users\jaypadhya\OneDrive - Microsoft\Desktop\Providence\Azure Foundry Deep Dive Session\eval-results-gpt-52.jsonl",
    r"c:\Users\jaypadhya\OneDrive - Microsoft\Desktop\Providence\Azure Foundry Deep Dive Session\eval-results-gpt53chat.jsonl",
]
for fp in files:
    print(f"\n=== {fp.split(chr(92))[-1]} ===")
    with open(fp, "r") as f:
        for i, line in enumerate(f):
            d = json.loads(line)
            ans = d.get("answer", "")
            print(f"  Q{i+1}: {len(ans)} chars - {repr(ans[:60])}")
