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
HF_LEGACY_URL      = f"https://api-inference.huggingface.co/models/{NLLB_MODEL}"
HF_ROUTER_CHAT_URL = "https://router.huggingface.co/v1/chat/completions"
HF_FALLBACK_MODEL  = "Qwen/Qwen2.5-7B-Instruct"
HF_TOKEN           = os.getenv("HF_TOKEN")          # optional — raises rate limits


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

    payload = {
        "model": HF_FALLBACK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    f"You are a professional translator. Translate the given text accurately from {source_lang} to {target_lang}. "
                    "Return ONLY the direct translated text. Do not add quotes, explanations, or notes."
                ),
            },
            {"role": "user", "content": text},
        ],
        "temperature": 0.1,
        "max_tokens": 1000,
    }
    try:
        resp = requests.post(HF_ROUTER_CHAT_URL, headers=headers, json=payload, timeout=30)
        if resp.ok:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "").strip()
                if content:
                    return content
    except Exception as exc:
        print(f"Fallback chat completion failed: {exc}")
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

    endpoints = [HF_API_URL, HF_LEGACY_URL]
    last_error = ""

    for url in endpoints:
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
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
                last_error = f"{url} returned status {resp.status_code}: {resp.text[:200]}"
        except HTTPException:
            raise
        except Exception as exc:
            last_error = f"Request to {url} failed: {exc}"

    # If direct endpoints did not succeed, try HF Provider Chat fallback
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
