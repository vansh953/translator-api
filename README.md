---
title: Indian Language Translation API
emoji: 🌐
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8080
pinned: false
---

# 🌐 Indian Language Translation API

Free translation API powered by **NLLB-200** (Meta AI) via HF Inference API.
Supports **English ↔ Hindi, Punjabi, Gujarati, Marathi** — all pairs direct, no pivot needed.

**Live URL:** `https://YOUR_APP_URL` *(replace after deploying)*

---

## API Reference

### `POST /translate`

Translate text between any supported language pair.

**Request**
```json
{
  "text": "Hello, how are you?",
  "source_language": "english",
  "target_language": "punjabi"
}
```

**Response**
```json
{
  "original_text": "Hello, how are you?",
  "translated_text": "ਹੈਲੋ, ਤੁਸੀਂ ਕਿਵੇਂ ਹੋ?",
  "source_language": "english",
  "target_language": "punjabi"
}
```

---

### `GET /languages`

Returns all supported language names.

```json
{
  "supported_languages": ["english", "hindi", "punjabi", "gujarati", "marathi"]
}
```

---

### `GET /health`

```json
{
  "status": "ok",
  "models_loaded": true,
  "model": "facebook/nllb-200-distilled-600M",
  "backend": "HF Inference API"
}
```

---

## Language Pairs

| From → To     | English | Hindi | Punjabi | Gujarati | Marathi |
|---------------|:-------:|:-----:|:-------:|:--------:|:-------:|
| **English**   | —       | ✅    | ✅      | ✅       | ✅      |
| **Hindi**     | ✅      | —     | ✅      | ✅       | ✅      |
| **Punjabi**   | ✅      | ✅    | —       | ✅       | ✅      |
| **Gujarati**  | ✅      | ✅    | ✅      | —        | ✅      |
| **Marathi**   | ✅      | ✅    | ✅      | ✅       | —       |

All Indic→Indic pairs are **direct** — no two-hop pivot needed.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `HF_TOKEN` | Optional | Free HF token — increases rate limits |

Get a free token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).

---

## Backend Integration (Node.js)

```js
// services/translationService.js
const axios = require('axios');

const TRANSLATION_API = process.env.TRANSLATION_API_URL || 'https://your-app-url';

async function translate(text, sourceLang, targetLang) {
  const { data } = await axios.post(`${TRANSLATION_API}/translate`, {
    text,
    source_language: sourceLang,
    target_language: targetLang,
  });
  return data.translated_text;
}

module.exports = { translate };
```

---

## Tech Stack

- **Model**: [NLLB-200 distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M) by Meta AI
- **Backend**: HF Inference API (free, serverless)
- **Framework**: FastAPI + Uvicorn
- **Deployment**: Docker (Cloud Run / Railway / any platform)
- **RAM**: ~80 MB (no local model loading)
