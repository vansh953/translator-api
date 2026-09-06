"""
Interactive Demonstration & Judge Presentation CLI
Designed for live pitching and technical demonstrations to evaluators and judges.
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import time
import requests
import json

BASE_URL = "https://translator-api-4sky.onrender.com"

# Verified high-accuracy showcase examples
SHOWCASE_CASES = [
    {
        "title": "English -> Hindi (Welcome & Introduction)",
        "src": "english",
        "tgt": "hindi",
        "text": "Hello, welcome to our AI translation platform.",
    },
    {
        "title": "Hindi -> English (National / Cultural Context)",
        "src": "hindi",
        "tgt": "english",
        "text": "भारत एक सुंदर और महान देश है।",
    },
    {
        "title": "English -> Punjabi (Daily Greeting)",
        "src": "english",
        "tgt": "punjabi",
        "text": "Good morning, have a nice day!",
    },
    {
        "title": "English -> Gujarati (Business & General)",
        "src": "english",
        "tgt": "gujarati",
        "text": "Good morning, have a nice day!",
    },
    {
        "title": "Marathi -> English (Conversational)",
        "src": "marathi",
        "tgt": "english",
        "text": "नमस्कार, तुमचे येथे स्वागत आहे.",
    },
    {
        "title": "Indic-to-Indic Direct: Punjabi -> Hindi",
        "src": "punjabi",
        "tgt": "hindi",
        "text": "ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ।",
    },
    {
        "title": "Indic-to-Indic Direct: Hindi -> Gujarati",
        "src": "hindi",
        "tgt": "gujarati",
        "text": "आज का मौसम बहुत अच्छा है।",
    },
]

def print_banner(text):
    print("\n" + "=" * 65)
    print(f"  {text}")
    print("=" * 65)

def run_automated_showcase():
    print_banner("INDIAN LANGUAGE TRANSLATION API -- LIVE JUDGE DEMONSTRATION")
    print(f"Target Server: {BASE_URL}")

    # Step 1: Health
    print("\n[STEP 1] Checking API Health & Cloud Microservice Status...")
    t0 = time.perf_counter()
    r = requests.get(f"{BASE_URL}/health", timeout=15)
    dt = (time.perf_counter() - t0) * 1000
    print(f"-> Status: HTTP {r.status_code} (Response time: {dt:.1f} ms)")
    print(f"-> Backend Engine: {r.json().get('backend')} | Model: {r.json().get('model')}")

    # Step 2: Languages
    print("\n[STEP 2] Querying Supported Languages...")
    r = requests.get(f"{BASE_URL}/languages", timeout=15)
    langs = r.json().get("supported_languages", [])
    print(f"-> Active Languages ({len(langs)}): {', '.join([l.title() for l in langs])}")
    print(f"-> Total Direct Translation Directions: {len(langs) * (len(langs) - 1)} pairs")

    # Step 3: Real-time Translations
    print("\n[STEP 3] Executing Live Translation Pipeline...")
    for idx, case in enumerate(SHOWCASE_CASES, 1):
        print("-" * 65)
        print(f"Test #{idx}: {case['title']}")
        print(f"  Source [{case['src'].title()}] : {case['text']}")
        
        t0 = time.perf_counter()
        res = requests.post(
            f"{BASE_URL}/translate",
            json={"text": case["text"], "source_language": case["src"], "target_language": case["tgt"]},
            timeout=25
        )
        dt = (time.perf_counter() - t0) * 1000
        
        if res.status_code == 200:
            out = res.json().get("translated_text", "")
            print(f"  Target [{case['tgt'].title()}] : {out}")
            print(f"  Latency        : {dt:.1f} ms | Status: SUCCESS")
        else:
            print(f"  Status Error   : HTTP {res.status_code} - {res.text}")

    # Step 4: Edge case demonstration
    print("\n[STEP 4] Testing API Validation & Error Resilience...")
    print("Testing unsupported language request ('french' -> 'hindi')...")
    res = requests.post(
        f"{BASE_URL}/translate",
        json={"text": "Bonjour", "source_language": "french", "target_language": "hindi"},
        timeout=15
    )
    print(f"-> Expected HTTP 400 | Received: HTTP {res.status_code}")
    print(f"-> Error Message returned to client: {res.json().get('detail')}")

    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY")

def interactive_mode():
    print_banner("CUSTOM TRANSLATION TEST FOR JUDGE")
    print("Supported: english, hindi, punjabi, gujarati, marathi\n")
    while True:
        src = input("Enter Source Language (or 'q' to exit): ").strip().lower()
        if src == 'q':
            break
        tgt = input("Enter Target Language: ").strip().lower()
        text = input("Enter Text to Translate: ").strip()
        if not text:
            continue

        print("\nTranslating...")
        t0 = time.perf_counter()
        try:
            r = requests.post(
                f"{BASE_URL}/translate",
                json={"text": text, "source_language": src, "target_language": tgt},
                timeout=25
            )
            dt = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                print(f"\n[SUCCESS in {dt:.1f}ms]")
                print(f"Translated Text: {r.json().get('translated_text')}\n")
            else:
                print(f"\n[HTTP {r.status_code}] {r.text}\n")
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_mode()
    else:
        run_automated_showcase()
