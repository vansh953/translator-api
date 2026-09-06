"""
Indian Language Translation API — powered by NLLB-200 (Meta AI) via HF Inference API
Languages: English, Hindi, Punjabi, Gujarati, Marathi
All pairs are direct — no two-hop pivot needed (NLLB-200 supports 200 languages natively).
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import requests
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ── Configuration ─────────────────────────────────────────────────────────────

LANG_CODES: dict[str, str] = {
    "english":  "eng_Latn",
    "hindi":    "hin_Deva",
    "punjabi":  "pan_Guru",
    "gujarati": "guj_Gujr",
    "marathi":  "mar_Deva",
}

NLLB_MODEL         = "facebook/nllb-200-distilled-600M"
HF_API_URL         = f"https://router.huggingface.co/hf-inference/models/{NLLB_MODEL}"
HF_ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
HF_TOKEN           = os.getenv("HF_TOKEN")          # optional — raises rate limits

# Candidate models for router chat fallback
CANDIDATE_MODELS = [
    "meta-llama/Llama-3.1-8B-Instruct",
    "Qwen/Qwen2.5-7B-Instruct",
    "mistralai/Mistral-7B-Instruct-v0.3",
]


# ── Startup / shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Translation API starting — using HF Inference API ({NLLB_MODEL})")
    print("HF_TOKEN:", "set" if HF_TOKEN else "not set (anonymous, 300 req/hr limit)")
    yield
    print("Shutting down.")


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Indian Language Translation API",
    description=(
        "Free translation API powered by NLLB-200 (Meta AI) via HF Inference API. "
        "Supports English, Hindi, Punjabi, Gujarati, Marathi — all pairs direct."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str
    source_language: str
    target_language: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "Hello, how are you?",
                "source_language": "english",
                "target_language": "punjabi",
            }
        }
    }


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str


# ── Core translation logic ────────────────────────────────────────────────────

def _call_hf_chat_fallback(text: str, source_lang: str, target_lang: str) -> str:
    """Fallback to HF Inference Providers chat completions if task endpoint is unavailable."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    for model_name in CANDIDATE_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"You are a professional translator. Translate the given text accurately from {source_lang} to {target_lang}. "
                        "Output ONLY the translated text in the target script. Do NOT add any preamble, explanation, notes, or quotes."
                    ),
                },
                {"role": "user", "content": text},
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
        }
        try:
            resp = requests.post(HF_ROUTER_CHAT_URL, headers=headers, json=payload, timeout=25)
            if resp.ok:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    if content:
                        return content
            else:
                print(f"Model {model_name} returned {resp.status_code}: {resp.text[:100]}")
        except Exception as exc:
            print(f"Model {model_name} failed: {exc}")
    return ""


def _call_hf_api(text: str, src_code: str, tgt_code: str, source_lang: str = "", target_lang: str = "") -> str:
    """Call HF Inference API directly via HTTP with fallback."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"

    payload = {
        "inputs": text,
        "parameters": {
            "src_lang": src_code,
            "tgt_lang": tgt_code,
        },
    }

    last_error = ""

    # 1. Try modern router endpoint
    try:
        resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 503:
            info = resp.json() if "application/json" in resp.headers.get("content-type", "") else {}
            wait = info.get("estimated_time", "unknown")
            raise HTTPException(
                status_code=503,
                detail=f"Model is loading on HF servers, retry in ~{wait}s",
            )

        if resp.ok:
            data = resp.json()
            if isinstance(data, list) and data:
                item = data[0]
                if isinstance(item, dict):
                    return item.get("translation_text", str(item))
                return str(item)
            return str(data)
        else:
            last_error = f"{HF_API_URL} returned {resp.status_code}: {resp.text[:200]}"
    except HTTPException:
        raise
    except Exception as exc:
        last_error = f"Request to {HF_API_URL} failed: {exc}"

    # 2. If direct task endpoint did not succeed, try HF Provider Chat fallback
    if source_lang and target_lang:
        fallback_translated = _call_hf_chat_fallback(text, source_lang, target_lang)
        if fallback_translated:
            return fallback_translated

    raise HTTPException(
        status_code=502,
        detail=f"HF Inference error: {last_error}",
    )


def translate(text: str, source_lang: str, target_lang: str) -> str:
    src = source_lang.strip().lower()
    tgt = target_lang.strip().lower()

    if src not in LANG_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported source language '{src}'. Supported: {list(LANG_CODES)}",
        )
    if tgt not in LANG_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target language '{tgt}'. Supported: {list(LANG_CODES)}",
        )
    if src == tgt:
        return text  # nothing to do

    return _call_hf_api(text, LANG_CODES[src], LANG_CODES[tgt], src, tgt)


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/translate", response_model=TranslateResponse, summary="Translate text")
async def translate_endpoint(req: TranslateRequest):
    """
    Translate text between any supported language pair.
    All pairs are direct — NLLB-200 supports 200 languages natively.
    """
    translated = translate(req.text, req.source_language, req.target_language)
    return TranslateResponse(
        original_text=req.text,
        translated_text=translated,
        source_language=req.source_language,
        target_language=req.target_language,
    )


@app.get("/languages", summary="List supported languages")
async def list_languages():
    """Returns all supported language names for use in API requests."""
    return {"supported_languages": list(LANG_CODES.keys())}


@app.get("/health", summary="Health check")
async def health():
    """Returns server status and backend info."""
    return {
        "status": "ok",
        "model": NLLB_MODEL,
        "backend": "HF Inference API",
        "hf_token_set": HF_TOKEN is not None,
    }


@app.get("/debug-hf", summary="Diagnose Hugging Face API connectivity")
async def debug_hf():
    """Diagnostic tool to inspect HF router connectivity from this server."""
    headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    report = {}

    # Test candidate chat models
    for m in CANDIDATE_MODELS:
        try:
            payload = {
                "model": m,
                "messages": [{"role": "user", "content": "Translate 'Hello' to Hindi in one word."}],
                "max_tokens": 30,
            }
            resp = requests.post(HF_ROUTER_CHAT_URL, headers=headers, json=payload, timeout=12)
            if resp.ok:
                choice = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                report[m] = f"SUCCESS: {choice}"
            else:
                report[m] = f"HTTP {resp.status_code}: {resp.text[:120]}"
        except Exception as exc:
            report[m] = f"EXCEPTION: {exc}"

    # Test direct task endpoint
    try:
        task_payload = {
            "inputs": "Hello",
            "parameters": {"src_lang": "eng_Latn", "tgt_lang": "hin_Deva"},
        }
        r = requests.post(HF_API_URL, headers=headers, json=task_payload, timeout=12)
        report["nllb_task_api"] = f"HTTP {r.status_code}: {r.text[:150]}"
    except Exception as exc:
        report["nllb_task_api"] = f"EXCEPTION: {exc}"

    return report

