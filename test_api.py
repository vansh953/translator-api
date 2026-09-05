"""
Local test script — run this before pushing to GitHub.

Usage:
    1. Start the server:  uvicorn app:app --port 7860
    2. Run this script:   python test_api.py
"""

import httpx
import json

BASE = "http://localhost:7860"


def pretty(label: str, resp):
    print(f"\n{'─'*55}")
    print(f"  {label}")
    print(f"  Status : {resp.status_code}")
    try:
        print(f"  Body   : {json.dumps(resp.json(), ensure_ascii=False, indent=4)}")
    except Exception:
        print(f"  Body   : {resp.text}")


def run():
    client = httpx.Client(timeout=120)  # models can take time on first request

    # 1. Health check
    pretty("GET /health", client.get(f"{BASE}/health"))

    # 2. List languages
    pretty("GET /languages", client.get(f"{BASE}/languages"))

    # 3. English → Hindi
    pretty("EN → HI", client.post(f"{BASE}/translate", json={
        "text": "Good morning! How are you?",
        "source_language": "english",
        "target_language": "hindi",
    }))

    # 4. English → Punjabi
    pretty("EN → PA", client.post(f"{BASE}/translate", json={
        "text": "Hello, how are you?",
        "source_language": "english",
        "target_language": "punjabi",
    }))

    # 5. English → Gujarati
    pretty("EN → GU", client.post(f"{BASE}/translate", json={
        "text": "Please submit the form.",
        "source_language": "english",
        "target_language": "gujarati",
    }))

    # 6. English → Marathi
    pretty("EN → MR", client.post(f"{BASE}/translate", json={
        "text": "Welcome to the system.",
        "source_language": "english",
        "target_language": "marathi",
    }))

    # 7. Hindi → English
    pretty("HI → EN", client.post(f"{BASE}/translate", json={
        "text": "नमस्ते, आप कैसे हैं?",
        "source_language": "hindi",
        "target_language": "english",
    }))

    # 8. Punjabi → Hindi  (Indic→Indic pivot)
    pretty("PA → HI (pivot)", client.post(f"{BASE}/translate", json={
        "text": "ਤੁਹਾਡਾ ਸੁਆਗਤ ਹੈ",
        "source_language": "punjabi",
        "target_language": "hindi",
    }))

    # 9. Bad language — should return 400
    pretty("Bad language (expect 400)", client.post(f"{BASE}/translate", json={
        "text": "test",
        "source_language": "klingon",
        "target_language": "english",
    }))

    print(f"\n{'─'*55}")
    print("  ✅  All tests complete")


if __name__ == "__main__":
    run()
