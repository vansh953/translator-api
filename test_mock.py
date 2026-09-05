"""
Mock test -- tests the FULL API (routing, validation, error handling, pivot logic)
WITHOUT downloading any ML models. Runs in < 5 seconds.

Usage:  python test_mock.py
"""

import sys
from unittest.mock import MagicMock, patch

# ── 1. Mock all heavy packages before importing app ───────────────────────────
torch_mock        = MagicMock()
transformers_mock = MagicMock()
indic_mock        = MagicMock()

sys.modules["torch"]                       = torch_mock
sys.modules["transformers"]                = transformers_mock
sys.modules["IndicTransToolkit"]           = indic_mock
sys.modules["IndicTransToolkit.processor"] = indic_mock

# ── 2. Import app AFTER mocking ───────────────────────────────────────────────
import app as translation_app  # noqa: E402 (mocks must be above this line)

# ── 3. Inject fake models into MODELS dict ────────────────────────────────────
fake_ip = MagicMock()
fake_ip.preprocess_batch.side_effect = lambda sentences, **kw: sentences
fake_ip.postprocess_batch.side_effect = lambda decoded, **kw: decoded

fake_tokenizer = MagicMock()
fake_inputs = MagicMock()
fake_inputs.to.return_value = {"input_ids": MagicMock()}
fake_tokenizer.return_value = fake_inputs
fake_tokenizer.batch_decode.return_value = ["[MOCK TRANSLATION]"]

fake_model = MagicMock()
fake_model.generate.return_value = MagicMock()

translation_app.MODELS.update({
    "ip":       fake_ip,
    "en_indic": (fake_tokenizer, fake_model),
    "indic_en": (fake_tokenizer, fake_model),
})

# Patch torch.inference_mode context manager
torch_mock.inference_mode.return_value.__enter__ = lambda s: None
torch_mock.inference_mode.return_value.__exit__  = lambda s, *a: None

# ── 4. TestClient ─────────────────────────────────────────────────────────────
try:
    from httpx2 import Client  # newer FastAPI prefers httpx2
    from starlette.testclient import TestClient
except ImportError:
    from fastapi.testclient import TestClient  # fallback to httpx

import warnings
warnings.filterwarnings("ignore")  # suppress httpx deprecation warning

client = TestClient(translation_app.app)

# ── 5. Simple test runner ─────────────────────────────────────────────────────
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
print("  TRANSLATION API -- MOCK TEST SUITE")
print(SEP)

# ── Test 1: Health check ──────────────────────────────────────────────────────
print("\n[1] GET /health")
r = client.get("/health")
check("Status 200",          r.status_code == 200)
check("status == ok",        r.json().get("status") == "ok")
check("models_loaded field", "models_loaded" in r.json())

# ── Test 2: Languages ──────────────────────────────────────────────────────────
print("\n[2] GET /languages")
r = client.get("/languages")
check("Status 200",  r.status_code == 200)
langs = r.json().get("supported_languages", [])
check("5 languages returned",  len(langs) == 5, str(langs))
for lang in ["english", "hindi", "punjabi", "gujarati", "marathi"]:
    check(f"  '{lang}' present", lang in langs)

# ── Test 3: English -> Hindi ───────────────────────────────────────────────────
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

# ── Test 4: Hindi -> English ───────────────────────────────────────────────────
print("\n[4] POST /translate -- Hindi -> English")
r = client.post("/translate", json={
    "text": "Namaste",
    "source_language": "hindi",
    "target_language": "english",
})
check("Status 200",  r.status_code == 200, str(r.status_code))

# ── Test 5: Same language (no-op) ─────────────────────────────────────────────
print("\n[5] POST /translate -- same language (no-op)")
fake_model.generate.reset_mock()
r = client.post("/translate", json={
    "text": "Hello",
    "source_language": "english",
    "target_language": "english",
})
check("Status 200",               r.status_code == 200)
check("text returned unchanged",  r.json().get("translated_text") == "Hello")
check("model NOT called",         not fake_model.generate.called)

# ── Test 6: Indic -> Indic pivot ───────────────────────────────────────────────
print("\n[6] POST /translate -- Punjabi -> Hindi (two-hop pivot)")
fake_model.generate.reset_mock()
r = client.post("/translate", json={
    "text": "Welcome",
    "source_language": "punjabi",
    "target_language": "hindi",
})
check("Status 200",            r.status_code == 200, str(r.status_code))
# Pivot calls model twice (indic->en, en->indic)
check("model called twice",    fake_model.generate.call_count == 2,
      f"called {fake_model.generate.call_count}x")

# ── Test 7: Bad source language -> 400 ────────────────────────────────────────
print("\n[7] POST /translate -- bad source -> 400")
r = client.post("/translate", json={
    "text": "test",
    "source_language": "klingon",
    "target_language": "english",
})
check("Status 400",          r.status_code == 400)
check("detail in response",  "detail" in r.json())

# ── Test 8: Bad target language -> 400 ───────────────────────────────────────
print("\n[8] POST /translate -- bad target -> 400")
r = client.post("/translate", json={
    "text": "test",
    "source_language": "english",
    "target_language": "swahili",
})
check("Status 400",  r.status_code == 400)

# ── Test 9: Missing field -> 422 (Pydantic validation) ────────────────────────
print("\n[9] POST /translate -- missing field -> 422")
r = client.post("/translate", json={"text": "hello"})
check("Status 422",  r.status_code == 422)

# ── Test 10: All language pairs ───────────────────────────────────────────────
print("\n[10] POST /translate -- all 4 Indic languages")
for lang in ["hindi", "punjabi", "gujarati", "marathi"]:
    r = client.post("/translate", json={
        "text": "Hello world",
        "source_language": "english",
        "target_language": lang,
    })
    check(f"  english -> {lang}: 200", r.status_code == 200)

# ── Summary ────────────────────────────────────────────────────────────────────
print("")
print(SEP)
total = PASS + FAIL
print(f"  Result: {PASS}/{total} passed  |  {FAIL} failed")
print(SEP)
if FAIL == 0:
    print("  ALL TESTS PASSED -- API logic is correct! Ready for GitHub.\n")
    sys.exit(0)
else:
    print("  SOME TESTS FAILED -- fix before pushing.\n")
    sys.exit(1)
