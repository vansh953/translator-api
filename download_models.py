"""
Pre-download IndicTrans2 models during Docker build.
Bakes model weights into the image → fast container startup on Render.
"""
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

MODELS = [
    "ai4bharat/indictrans2-en-indic-dist-200M",
    "ai4bharat/indictrans2-indic-en-dist-200M",
]

for name in MODELS:
    print(f"⬇  Downloading {name} …")
    AutoTokenizer.from_pretrained(name, trust_remote_code=True)
    AutoModelForSeq2SeqLM.from_pretrained(name, trust_remote_code=True)
    print(f"✅  {name} cached")

print("🎉  All models downloaded — image is ready!")
