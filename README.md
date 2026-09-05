---
title: Indian Language Translation API
emoji: 🌐
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 🌐 Indian Language Translation API

Free, self-hosted translation API powered by **IndicTrans2** (AI4Bharat).  
Supports **English ↔ Hindi, Punjabi, Gujarati, Marathi** — with automatic Indic→Indic pivot.

**Live URL:** `https://translation-api.onrender.com` *(replace after Render deploy)*

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
{ "status": "ok", "models_loaded": true }
```

---

## Language Pairs

| From → To     | English | Hindi | Punjabi | Gujarati | Marathi |
|---------------|:-------:|:-----:|:-------:|:--------:|:-------:|
| **English**   | —       | ✅    | ✅      | ✅       | ✅      |
| **Hindi**     | ✅      | —     | ✅*     | ✅*      | ✅*     |
| **Punjabi**   | ✅      | ✅*   | —       | ✅*      | ✅*     |
| **Gujarati**  | ✅      | ✅*   | ✅*     | —        | ✅*     |
| **Marathi**   | ✅      | ✅*   | ✅*     | ✅*      | —       |

*\* Indic → Indic pairs pivot through English automatically.*

---

## Backend Integration (Node.js)

```js
// services/translationService.js
const axios = require('axios');

const TRANSLATION_API = process.env.TRANSLATION_API_URL || 'https://translation-api.onrender.com';

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

- **Model**: [IndicTrans2 dist-200M](https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M) by AI4Bharat
- **Framework**: FastAPI + Uvicorn
- **Deployment**: Render (Docker, free tier)
- **Toolkit**: [IndicTransToolkit](https://github.com/VarunGumma/IndicTransToolkit) for preprocessing
