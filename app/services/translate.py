import httpx
from app.config import settings


async def translate_text(text: str, target: str | None = None) -> dict:
    """Traduz texto usando LibreTranslate."""
    target = target or settings.target_language

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{settings.libretranslate_url}/translate",
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
