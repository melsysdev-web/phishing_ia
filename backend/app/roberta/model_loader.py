from functools import lru_cache

from transformers import AutoModelForSequenceClassification, AutoTokenizer

from backend.app.core.paths import get_models_dir

MODEL_PATH = str(get_models_dir() / "roberta_phishing_new")


@lru_cache(maxsize=1)
def get_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH)
    model.eval()
    return tokenizer, model

# No cuantizar. Aquí había un quantize_dynamic a int8 puesto para acelerar la
# CPU, pero medido hace lo contrario de lo que su comentario afirmaba: para
# convertir los pesos los materializa todos, y dispara un pico de +735 MB
# (757 MB de pico total, 407 MB residentes) frente a los 238 MB que cuesta
# el modelo en fp32, que safetensors mapea de forma perezosa.
#
# Ese pico es lo que hacía que /predict devolviera 502 en Render: el worker
# moría por OOM contra el límite de 512 MB y se llevaba el servicio entero.
#
# Lo que compraba a cambio: 1.96 ms por URL (16.5%) en un pipeline de 3-8 s
# dominado por I/O de red a VirusTotal, Safe Browsing y WHOIS. No compensa.
#
# (torch.ao.quantization además está deprecado y desaparece en torch 2.10.)
