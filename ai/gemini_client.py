"""Gemini API client with Fast and Deep modes using google-genai SDK."""

import json
import logging
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from ai.deep_prompt import build_filing_prompt, build_ipo_prompt
from ai.fast_prompt import FAST_SYSTEM_PROMPT, build_fast_prompt
from config.settings import GEMINI_API_KEY

logger = logging.getLogger(__name__)

FAST_MODEL = "gemini-2.0-flash-exp"
DEEP_MODEL = "gemini-2.0-flash-exp"


def _client() -> Optional[genai.Client]:
    if not GEMINI_API_KEY:
        logger.warning("Gemini API key not configured")
        return None
    return genai.Client(api_key=GEMINI_API_KEY)


def _parse_json(text: str) -> Optional[Any]:
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Gemini JSON response: %s", text[:200])
        return None


def fast_classify(headlines: List[str]) -> List[Dict[str, Any]]:
    """Classify a batch of headlines. Returns list of classifications."""
    if not headlines:
        return []
    client = _client()
    if not client:
        return []

    try:
        response = client.models.generate_content(
            model=FAST_MODEL,
            contents=build_fast_prompt(headlines),
            config=types.GenerateContentConfig(
                system_instruction=FAST_SYSTEM_PROMPT,
                response_mime_type="application/json",
            ),
        )
        parsed = _parse_json(response.text)
        if isinstance(parsed, dict) and "results" in parsed:
            return parsed["results"]
        if isinstance(parsed, list):
            return parsed
        logger.warning("Unexpected Gemini Fast response structure")
        return []
    except Exception as exc:
        logger.warning("Gemini Fast mode failed: %s", exc)
        return []


def deep_analyze_ipo(context: str) -> Optional[Dict[str, Any]]:
    client = _client()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model=DEEP_MODEL,
            contents=build_ipo_prompt(context),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _parse_json(response.text)
    except Exception as exc:
        logger.warning("Gemini Deep IPO mode failed: %s", exc)
        return None


def deep_analyze_filing(context: str) -> Optional[Dict[str, Any]]:
    client = _client()
    if not client:
        return None
    try:
        response = client.models.generate_content(
            model=DEEP_MODEL,
            contents=build_filing_prompt(context),
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _parse_json(response.text)
    except Exception as exc:
        logger.warning("Gemini Deep filing mode failed: %s", exc)
        return None
