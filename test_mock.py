"""
Mock test suite — tests the FULL API (routing, validation, error handling)
WITHOUT making any real HTTP calls to HF Inference API.
Runs in < 5 seconds.

Usage:  python test_mock.py
"""

import sys
import json
from unittest.mock import MagicMock, patch, Mock

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── 1. Import app (no heavy deps needed now — just requests, fastapi) ──────────
import app as translation_app

# ── 2. TestClient ─────────────────────────────────────────────────────────────
import warnings
warnings.filterwarnings("ignore")
from fastapi.testclient import TestClient

# ── 3. Build a mock requests.post that returns realistic HF API responses ──────
def make_mock_response(translation_text: str, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.ok = (status_code == 200)
    mock_resp.json.return_value = [{"translation_text": translation_text}]
    mock_resp.text = json.dumps([{"translation_text": translation_text}])
    return mock_resp

MOCK_TRANSLATIONS = {
    ("eng_Latn", "hin_Deva"): "शुभ प्रभात!",
    ("eng_Latn", "pan_Guru"): "ਸਤ ਸ੍ਰੀ ਅਕਾਲ!",
    ("eng_Latn", "guj_Gujr"): "સુપ્રભાત!",
    ("eng_Latn", "mar_Deva"): "सुप्रभात!",
    ("hin_Deva", "eng_Latn"): "Good morning!",
    ("pan_Guru", "eng_Latn"): "Welcome!",
    ("guj_Gujr", "mar_Deva"): "आज हवामान चांगले आहे.",
    ("pan_Guru", "hin_Deva"): "आपका स्वागत है।",
}

def mock_requests_post(url, headers=None, json=None, timeout=None):
    src = json.get("parameters", {}).get("src_lang", "")
    tgt = json.get("parameters", {}).get("tgt_lang", "")
    translation = MOCK_TRANSLATIONS.get((src, tgt), f"[MOCK: {src}->{tgt}]")
    return make_mock_response(translation)

# Mock GoogleTranslator so mock tests run purely through mocked backend
class MockGoogleTranslator:
    def __init__(self, source="auto", target="en"):
        self.source = source
        self.target = target

    def translate(self, text):
        raise Exception("Mock fallback to HF")

# Apply patch to deep_translator in app
import deep_translator
deep_translator.GoogleTranslator = MockGoogleTranslator
deep_translator.MyMemoryTranslator = MockGoogleTranslator

# ── 4. Simple test runner ─────────────────────────────────────────────────────
PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    icon = "PASS" if condition else "FAIL"
    extra = f" => {detail}" if detail else ""
    print(f"  [{icon}] {label}{extra}")
    if condition:
        PASS += 1
    else:
        FAIL += 1

SEP = "-" * 56

print("")
print(SEP)
print("  TRANSLATION API v2 -- MOCK TEST SUITE (HF Inference)")
print(SEP)

# Patch requests.post for all tests
with patch("app.requests.post", side_effect=mock_requests_post):
    with TestClient(translation_app.app) as client:

        # ── Test 1: Health check ───────────────────────────────────────────────
        print("\n[1] GET /health")
        r = client.get("/health")
        check("Status 200",       r.status_code == 200)
        check("status == ok",     r.json().get("status") == "ok")
        check("model field",      "model" in r.json())
        check("backend field",    r.json().get("backend") == "HF Inference API")

        # ── Test 2: Languages ──────────────────────────────────────────────────
        print("\n[2] GET /languages")
        r = client.get("/languages")
        check("Status 200", r.status_code == 200)
        langs = r.json().get("supported_languages", [])
        check("5 languages returned", len(langs) == 5, str(langs))
        for lang in ["english", "hindi", "punjabi", "gujarati", "marathi"]:
            check(f"  '{lang}' present", lang in langs)

        # ── Test 3: English -> Hindi ───────────────────────────────────────────
        print("\n[3] POST /translate -- English -> Hindi")
        r = client.post("/translate", json={
            "text": "Good morning!",
            "source_language": "english",
            "target_language": "hindi",
        })
        check("Status 200",               r.status_code == 200, str(r.status_code))
        check("original_text preserved",  r.json().get("original_text") == "Good morning!")
        check("translated_text present",  bool(r.json().get("translated_text")))
        check("source_language echoed",   r.json().get("source_language") == "english")
        check("target_language echoed",   r.json().get("target_language") == "hindi")

        # ── Test 4: Hindi -> English ───────────────────────────────────────────
        print("\n[4] POST /translate -- Hindi -> English")
        r = client.post("/translate", json={
            "text": "Namaste",
            "source_language": "hindi",
            "target_language": "english",
        })
        check("Status 200", r.status_code == 200, str(r.status_code))

        # ── Test 5: Same language (no-op) ──────────────────────────────────────
        print("\n[5] POST /translate -- same language (no-op)")
        r = client.post("/translate", json={
            "text": "Hello",
            "source_language": "english",
            "target_language": "english",
        })
        check("Status 200",              r.status_code == 200)
        check("text returned unchanged", r.json().get("translated_text") == "Hello")

        # ── Test 6: Indic -> Indic (direct, no pivot needed) ──────────────────
        print("\n[6] POST /translate -- Punjabi -> Hindi (direct via NLLB)")
        r = client.post("/translate", json={
            "text": "Welcome",
            "source_language": "punjabi",
            "target_language": "hindi",
        })
        check("Status 200", r.status_code == 200, str(r.status_code))
        check("has translated_text", bool(r.json().get("translated_text")))

        # ── Test 7: Gujarati -> Marathi (direct) ──────────────────────────────
        print("\n[7] POST /translate -- Gujarati -> Marathi (direct via NLLB)")
        r = client.post("/translate", json={
            "text": "Today the weather is nice.",
            "source_language": "gujarati",
            "target_language": "marathi",
        })
        check("Status 200", r.status_code == 200, str(r.status_code))

        # ── Test 8: Bad source language -> 400 ────────────────────────────────
        print("\n[8] POST /translate -- bad source -> 400")
        r = client.post("/translate", json={
            "text": "test",
            "source_language": "klingon",
            "target_language": "english",
        })
        check("Status 400",         r.status_code == 400)
        check("detail in response", "detail" in r.json())

        # ── Test 9: Bad target language -> 400 ────────────────────────────────
        print("\n[9] POST /translate -- bad target -> 400")
        r = client.post("/translate", json={
            "text": "test",
            "source_language": "english",
            "target_language": "swahili",
        })
        check("Status 400", r.status_code == 400)

        # ── Test 10: Missing field -> 422 ──────────────────────────────────────
        print("\n[10] POST /translate -- missing field -> 422")
        r = client.post("/translate", json={"text": "hello"})
        check("Status 422", r.status_code == 422)

        # ── Test 11: All 4 EN -> Indic pairs ──────────────────────────────────
        print("\n[11] POST /translate -- all 4 EN -> Indic pairs")
        for lang in ["hindi", "punjabi", "gujarati", "marathi"]:
            r = client.post("/translate", json={
                "text": "Hello world",
                "source_language": "english",
                "target_language": lang,
            })
            check(f"  english -> {lang}: 200", r.status_code == 200)

        # ── Test 12: All 4 Indic -> EN pairs ──────────────────────────────────
        print("\n[12] POST /translate -- all 4 Indic -> EN pairs")
        for lang in ["hindi", "punjabi", "gujarati", "marathi"]:
            r = client.post("/translate", json={
                "text": "Hello world",
                "source_language": lang,
                "target_language": "english",
            })
            check(f"  {lang} -> english: 200", r.status_code == 200)

        # ── Test 13: HF 503 response handled properly ──────────────────────────
        print("\n[13] HF 503 (model loading) -> 503 with helpful message")
        loading_resp = MagicMock()
        loading_resp.status_code = 503
        loading_resp.ok = False
        loading_resp.headers = {"content-type": "application/json"}
        loading_resp.json.return_value = {"error": "loading", "estimated_time": 20.0}
        loading_resp.text = '{"error": "loading", "estimated_time": 20.0}'
        # MyMemory uses requests.get — make it fail so HF fallback triggers
        mm_fail = MagicMock()
        mm_fail.ok = False
        mm_fail.json.return_value = {"responseData": {"translatedText": ""}}
        with patch("app.requests.post", return_value=loading_resp), \
             patch("app.requests.get", return_value=mm_fail):
            r = client.post("/translate", json={
                "text": "Hello",
                "source_language": "english",
                "target_language": "hindi",
            })
            check("Status 503",           r.status_code == 503)
            check("detail has retry hint", "retry" in r.json().get("detail", "").lower())

# ── Summary ────────────────────────────────────────────────────────────────────
print("")
print(SEP)
total = PASS + FAIL
print(f"  Result: {PASS}/{total} passed  |  {FAIL} failed")
print(SEP)
if FAIL == 0:
    print("  ALL TESTS PASSED -- Ready to deploy!\n")
    sys.exit(0)
else:
    print("  SOME TESTS FAILED -- fix before pushing.\n")
    sys.exit(1)
