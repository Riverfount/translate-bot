import httpx
from app.config import settings


async def translate_text(text: str, target: str | None = None) -> dict:
    """Traduz texto usando Google Cloud Translation API v2."""
    target = target or settings.target_language

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://translation.googleapis.com/language/translate/v2",
            params={"key": settings.google_translate_api_key},
            json={"q": text, "target": target, "format": "text"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    t = data["data"]["translations"][0]
    return {
        "translated": t["translatedText"],
        "detected_source": t.get("detectedSourceLanguage", "?"),
    }
