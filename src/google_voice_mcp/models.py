"""Strict validation shared by public interfaces; no synthetic records."""

import re

from google_voice_mcp.browser import VoiceError


def integer(value: int, name: str, maximum: int) -> int:
    if type(value) is not int or not 1 <= value <= maximum:
        raise VoiceError(f"{name} must be an integer from 1 to {maximum}")
    return value


def boolean(value: bool, name: str) -> bool:
    if type(value) is not bool:
        raise VoiceError(f"{name} must be a boolean")
    return value


def message(recipient: str, text: str) -> None:
    if not isinstance(recipient, str) or re.fullmatch(r"\+[1-9][0-9]{7,14}", recipient) is None:
        raise VoiceError("recipient must be an international phone number, e.g. +12025550123")
    if not isinstance(text, str) or not text.strip() or len(text) > 1600:
        raise VoiceError("text must contain 1 to 1600 characters and not be blank")
