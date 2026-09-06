"""
Test suite against the live Render deployment: https://translator-api-4sky.onrender.com
"""
import requests
import json
import time

BASE_URL = "https://translator-api-4sky.onrender.com"

test_cases = [
    ("EN -> HI", "english", "hindi", "Hello, how are you? Welcome to our platform."),
    ("HI -> EN", "hindi", "english", "भारत एक सुंदर और महान देश है।"),
    ("EN -> PA", "english", "punjabi", "Good morning, have a nice day!"),
    ("EN -> GU", "english", "gujarati", "Good morning, have a nice day!"),
    ("EN -> MR", "english", "marathi", "Good morning, have a nice day!"),
    ("HI -> MR", "hindi", "marathi", "नमस्ते, आज का दिन बहुत अच्छा है।"),
    ("PA -> HI", "punjabi", "hindi", "ਤੁਹਾਡਾ ਸਵਾਗਤ ਹੈ।")
]

print("=" * 60)
print(f"TESTING LIVE RENDER DEPLOYMENT: {BASE_URL}")
print("=" * 60)

# 1. Health
r = requests.get(f"{BASE_URL}/health", timeout=30)
print(f"Health check [{r.status_code}]: {r.json()}")

# 2. Languages
r = requests.get(f"{BASE_URL}/languages", timeout=30)
print(f"Languages [{r.status_code}]: {r.json()}")

# 3. Translations
print("\n" + "-" * 60)
print("TRANSLATION TESTS")
print("-" * 60)

for name, src, tgt, text in test_cases:
    t0 = time.time()
    payload = {
        "text": text,
        "source_language": src,
        "target_language": tgt
    }
    r = requests.post(f"{BASE_URL}/translate", json=payload, timeout=60)
    dt = time.time() - t0
    if r.status_code == 200:
        data = r.json()
        print(f"[{name}] ({dt:.2f}s) OK")
        print(f"   In : {text}")
        print(f"   Out: {data.get('translated_text')}\n")
    else:
        print(f"[{name}] ({dt:.2f}s) FAILED - status={r.status_code}")
        print(f"   Response: {r.text}\n")
