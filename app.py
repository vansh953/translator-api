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

NLLB_MODEL  = "facebook/nllb-200-distilled-600M"
HF_API_URL  = f"https://api-inference.huggingface.co/models/{NLLB_MODEL}"
HF_TOKEN    = os.getenv("HF_TOKEN")          # optional — raises rate limits


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


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str
    source_language: str   # "english" | "hindi" | "punjabi" | "gujarati" | "marathi"
    target_language: str

    class Config:
        json_schema_extra = {
            "example": {
                "text": "Hello, how are you?",
                "source_language": "english",
                "target_language": "punjabi",
            }
        }


class TranslateResponse(BaseModel):
    original_text: str
    translated_text: str
    source_language: str
    target_language: str


# ── Core translation logic ────────────────────────────────────────────────────

def _call_hf_api(text: str, src_code: str, tgt_code: str) -> str:
    """Call HF Inference API directly via HTTP — no SDK provider issues."""
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

    resp = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)

    if resp.status_code == 503:
        # Model is loading — HF returns 503 with estimated_time
        info = resp.json()
        wait = info.get("estimated_time", "unknown")
        raise HTTPException(
            status_code=503,
            detail=f"Model is loading on HF servers, retry in ~{wait}s",
        )

    if not resp.ok:
        raise HTTPException(
            status_code=502,
            detail=f"HF Inference API error {resp.status_code}: {resp.text[:300]}",
        )

    data = resp.json()
    # Normal response: [{"translation_text": "..."}]
    if isinstance(data, list) and data:
        return data[0].get("translation_text", str(data[0]))
    # Fallback for unexpected shapes
    return str(data)


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

    return _call_hf_api(text, LANG_CODES[src], LANG_CODES[tgt])


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
