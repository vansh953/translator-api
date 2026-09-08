import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import requests

BASE = "https://translator-api-4sky.onrender.com"

# English -> All Indic
en_to_indic = [
    ("english", "hindi",    "Hello, how are you? Welcome to our platform."),
    ("english", "punjabi",  "Hello, how are you? Welcome to our platform."),
    ("english", "gujarati", "Hello, how are you? Welcome to our platform."),
    ("english", "marathi",  "Hello, how are you? Welcome to our platform."),
]

# All Indic -> English
indic_to_en = [
    ("hindi",    "english", "नमस्ते, आप कैसे हैं?"),
    ("punjabi",  "english", "ਹੈਲੋ ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?"),
    ("gujarati", "english", "નમસ્તે, તમે કેમ છો?"),
    ("marathi",  "english", "नमस्कार, तुम्ही कसे आहात?"),
]

passed = 0
failed = 0

def run_group(label, pairs):
    global passed, failed
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")
    for src, tgt, text in pairs:
        try:
            r = requests.post(
                f"{BASE}/translate",
                json={"text": text, "source_language": src, "target_language": tgt},
                timeout=20,
            )
            if r.status_code == 200:
                out = r.json().get("translated_text", "")
                # Check it's not an error page
                if "error" in out.lower() and "500" in out:
                    print(f"  FAIL [{src} -> {tgt}] Got error page: {out[:60]}")
                    failed += 1
                else:
                    print(f"  OK   [{src} -> {tgt}]")
                    print(f"       In : {text}")
                    print(f"       Out: {out}")
                    passed += 1
            else:
                print(f"  FAIL [{src} -> {tgt}] HTTP {r.status_code}: {r.text[:80]}")
                failed += 1
        except Exception as e:
            print(f"  ERR  [{src} -> {tgt}] {e}")
            failed += 1

run_group("ENGLISH  ->  HINDI / PUNJABI / GUJARATI / MARATHI", en_to_indic)
run_group("HINDI / PUNJABI / GUJARATI / MARATHI  ->  ENGLISH", indic_to_en)

print(f"\n{'='*55}")
print(f"  RESULT: {passed} passed  |  {failed} failed")
print(f"{'='*55}")
