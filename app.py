"""
Indian Language Translation API — powered by IndicTrans2 (AI4Bharat)
Models : indictrans2-en-indic-dist-200M  /  indictrans2-indic-en-dist-200M
Languages: English, Hindi, Punjabi, Gujarati, Marathi
Indic → Indic: two-hop pivot through English
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from IndicTransToolkit import IndicProcessor


# ── Language configuration ────────────────────────────────────────────────────

LANG_CODES: dict[str, str] = {
    "english":  "eng_Latn",
    "hindi":    "hin_Deva",
    "punjabi":  "pan_Guru",
    "gujarati": "guj_Gujr",
    "marathi":  "mar_Deva",
}

DEVICE = "cpu"

# Global model store — populated once at startup via lifespan
MODELS: dict = {}


# ── Startup / shutdown ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load both IndicTrans2 models once when the server starts."""
    print("🔄  Loading IndicTrans2 models … (this takes ~30 s on first run)")

    ip = IndicProcessor(inference=True)

    print("   ↳ en → indic …")
    en_indic_tok = AutoTokenizer.from_pretrained(
        "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True
    )
    en_indic_mdl = AutoModelForSeq2SeqLM.from_pretrained(
        "ai4bharat/indictrans2-en-indic-dist-200M", trust_remote_code=True
    ).to(DEVICE).eval()

    print("   ↳ indic → en …")
    indic_en_tok = AutoTokenizer.from_pretrained(
        "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True
    )
    indic_en_mdl = AutoModelForSeq2SeqLM.from_pretrained(
        "ai4bharat/indictrans2-indic-en-dist-200M", trust_remote_code=True
    ).to(DEVICE).eval()

    MODELS.update({
        "ip":       ip,
        "en_indic": (en_indic_tok, en_indic_mdl),
        "indic_en": (indic_en_tok, indic_en_mdl),
    })
    print("✅  Models ready — server accepting requests")
    yield
    MODELS.clear()


# ── FastAPI app ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Indian Language Translation API",
    description=(
        "Free translation API powered by IndicTrans2 (AI4Bharat). "
        "Supports English ↔ Hindi, Punjabi, Gujarati, Marathi. "
        "Indic→Indic pairs pivot through English automatically."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten this to your backend URL in production
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


# ── Internal translation logic ────────────────────────────────────────────────

def _run_model(
    sentences: list[str],
    src_code: str,
    tgt_code: str,
    model_key: str,
) -> list[str]:
    """
    Run one translation hop through the specified model.
    Uses IndicProcessor for mandatory pre- and post-processing.
    """
    ip: IndicProcessor = MODELS["ip"]
    tokenizer, model = MODELS[model_key]

    # IndicProcessor MUST preprocess before tokenisation
    batch = ip.preprocess_batch(sentences, src_lang=src_code, tgt_lang=tgt_code)

    inputs = tokenizer(
        batch,
        padding="longest",
        truncation=True,
        max_length=256,
        return_tensors="pt",
    ).to(DEVICE)

    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            num_beams=5,
            max_length=256,
            num_return_sequences=1,
        )

    decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)

    # IndicProcessor MUST postprocess the decoded strings
    return ip.postprocess_batch(decoded, lang=tgt_code)


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

    src_code = LANG_CODES[src]
    tgt_code = LANG_CODES[tgt]

    # English → Indic  (single hop)
    if src == "english":
        return _run_model([text], src_code, tgt_code, "en_indic")[0]

    # Indic → English  (single hop)
    if tgt == "english":
        return _run_model([text], src_code, tgt_code, "indic_en")[0]

    # Indic → Indic  (two-hop pivot through English)
    english_pivot = _run_model([text], src_code, "eng_Latn", "indic_en")[0]
    return _run_model([english_pivot], "eng_Latn", tgt_code, "en_indic")[0]


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.post("/translate", response_model=TranslateResponse, summary="Translate text")
async def translate_endpoint(req: TranslateRequest):
    """
    Translate text between any supported language pair.

    - **English ↔ Hindi / Punjabi / Gujarati / Marathi** — direct model hop
    - **Indic ↔ Indic** — automatic two-hop pivot through English
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
    """Returns server status and whether models are loaded."""
    return {
        "status": "ok",
        "models_loaded": bool(MODELS),
    }
