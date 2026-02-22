"""
Testes para app/services/translate.py

Cobre:
- Tradução bem-sucedida com detecção de idioma
- Uso do idioma padrão das settings quando `target` não é passado
- Uso do idioma explícito quando passado como argumento
- API key enviada corretamente como query param
- Fallback "?" quando detectedSourceLanguage está ausente
- Erros HTTP da API (4xx, 5xx)
- Timeout da requisição
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.translate import translate_text


def _mock_response(translated: str, detected: str, status: int = 200) -> MagicMock:
    """Monta um httpx.Response fake com a estrutura da Google Translate API v2."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status
    mock.json.return_value = {
        "data": {
            "translations": [
                {
                    "translatedText": translated,
                    "detectedSourceLanguage": detected,
                }
            ]
        }
    }
    mock.raise_for_status = MagicMock()
    return mock


def _mock_error_response(status: int) -> MagicMock:
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status
    mock.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=f"HTTP {status}",
        request=MagicMock(),
        response=mock,
    )
    return mock


@pytest.mark.asyncio
async def test_translate_returns_translated_text():
    """Resultado deve conter o texto traduzido e o idioma detectado."""
    mock_resp = _mock_response(translated="Olá mundo", detected="en")

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        result = await translate_text("Hello world", target="pt")

    assert result["translated"] == "Olá mundo"
    assert result["detected_source"] == "en"


@pytest.mark.asyncio
async def test_translate_uses_default_target_language():
    """
    Quando `target` não é passado, deve usar settings.target_language ("pt").
    Verifica que o parâmetro `target` enviado à API é "pt".
    """
    mock_resp = _mock_response(translated="Bonjour", detected="pt")

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        await translate_text("Bonjour")

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["target"] == "pt"


@pytest.mark.asyncio
async def test_translate_uses_explicit_target_language():
    """Quando `target` é passado, ele deve sobrescrever o padrão das settings."""
    mock_resp = _mock_response(translated="Hello", detected="pt")

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        await translate_text("Olá", target="en")

        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["target"] == "en"


@pytest.mark.asyncio
async def test_translate_sends_api_key():
    """A API key das settings deve ser enviada como query param."""
    mock_resp = _mock_response(translated="X", detected="en")

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        await translate_text("test")

        _, kwargs = mock_client.post.call_args
        assert kwargs["params"]["key"] == "fake-api-key"


@pytest.mark.asyncio
async def test_translate_detected_source_fallback():
    """Se a API não retornar `detectedSourceLanguage`, deve usar '?' como fallback."""
    mock = MagicMock(spec=httpx.Response)
    mock.raise_for_status = MagicMock()
    mock.json.return_value = {"data": {"translations": [{"translatedText": "Texto"}]}}

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock)
        mock_client_cls.return_value = mock_client

        result = await translate_text("Texto")

    assert result["detected_source"] == "?"


@pytest.mark.asyncio
async def test_translate_raises_on_http_error():
    """Deve propagar HTTPStatusError em respostas 4xx/5xx."""
    mock_resp = _mock_error_response(status=403)

    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.HTTPStatusError):
            await translate_text("Hello")


@pytest.mark.asyncio
async def test_translate_raises_on_timeout():
    """Deve propagar TimeoutException quando a API não responder a tempo."""
    with patch("app.services.translate.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_client_cls.return_value = mock_client

        with pytest.raises(httpx.TimeoutException):
            await translate_text("Hello")
