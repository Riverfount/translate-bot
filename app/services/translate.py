import httpx
from app.config import settings


async def translate_text(text: str, target: str | None = None) -> dict[str, str]:
    """Traduz texto usando LibreTranslate."""
    target = target or settings.target_language

    # Normaliza a URL configurada: remove barra final e um /translate já
    # presente, pra sempre concatenar exatamente um /translate — evita
    # duplicar o path se libretranslate_url já vier com o sufixo.
    base_url = settings.libretranslate_url.rstrip("/")
    if base_url.endswith("/translate"):
        base_url = base_url[: -len("/translate")]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base_url}/translate",
            json={
                "q": text,
                "source": "auto",
                "target": target,
                "api_key": settings.get("libretranslate_api_key", ""),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "translated": data["translatedText"],
        "detected_source": data.get("detectedLanguage", {}).get("language", "?"),
    }
