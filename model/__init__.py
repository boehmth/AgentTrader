# model/__init__.py — Dispatcher zwischen mehreren LLM-Providern.
#
# Wähle den Provider über die .env:
#   LLM_PROVIDER=gemini   (Default; nutzt model/gemini.py, braucht GOOGLE_API_KEY)
#   LLM_PROVIDER=sap      (nutzt model/sap.py, braucht SAP GenAI Hub Service Key)
#
# Das Modell (bei sap) kann per .env-Variable SAP_GENAI_MODEL gesetzt oder zur
# Laufzeit per set_model(...) überschrieben werden. set_model resettet die
# provider-internen Caches (Deployment-ID etc.).

import os
from dotenv import load_dotenv

load_dotenv()

_PROVIDER = (os.getenv("LLM_PROVIDER") or "gemini").strip().lower()


def set_provider(name: str) -> None:
    """Provider zur Laufzeit wechseln (z. B. 'gemini' -> 'sap')."""
    global _PROVIDER
    _PROVIDER = name.strip().lower()


def set_model(model_name: str) -> None:
    """Modell zur Laufzeit setzen. Provider-aware:

    - Wenn model_name mit 'gemini' oder 'models/' beginnt -> Gemini-Provider.
    - Sonst -> SAP-Provider (typische Namen: gpt-4o, anthropic--claude-...).

    Setzt entsprechend GEMINI_MODEL oder SAP_GENAI_MODEL, wechselt den Provider
    und leert relevante Caches.
    """
    m = model_name.strip()
    if m.startswith("gemini") or m.startswith("models/"):
        # Gemini erwartet 'models/gemini-flash-latest' als Kanon; wir akzeptieren
        # aber auch nur 'gemini-flash-latest' und ergänzen den Prefix.
        canonical = m if m.startswith("models/") else f"models/{m}"
        os.environ["GEMINI_MODEL"] = canonical
        set_provider("gemini")
        # gemini-Client cachet keine Deployment-IDs, aber Modul selbst hält
        # MODEL_NAME als konstante Variable — bei einem Neu-Import lesen wir sie
        # neu. Wir invalidieren daher hier: reload.
        try:
            import importlib
            from . import gemini as _gem
            importlib.reload(_gem)
        except Exception:
            pass
    else:
        os.environ["SAP_GENAI_MODEL"] = m
        set_provider("sap")
        try:
            from . import sap as _sap_mod
            _sap_mod._DEPLOYMENT_CACHE.clear()
            _sap_mod._INFERENCE_PATH_CACHE.clear()
        except Exception:
            pass


def call_llm(system_prompt: str, user_prompt: str) -> dict:
    if _PROVIDER == "sap":
        from .sap import call_llm as _call
    elif _PROVIDER == "gemini":
        from .gemini import call_llm as _call
    else:
        raise RuntimeError(
            f"Unbekannter LLM_PROVIDER '{_PROVIDER}'. Erlaubt: 'gemini' oder 'sap'."
        )
    return _call(system_prompt, user_prompt)


# Kompatibilitäts-Symbol
PROVIDER = _PROVIDER