"""
backend/app/agent/config.py
===========================
Configuration for the Gemini LLM agent.

Reads GEMINI_API_KEY and GEMINI_MODEL from environment variables.
Provides a client factory using official google-genai SDK.
"""

import os
from typing import Optional
from google import genai

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"


def get_gemini_api_key() -> str:
    """Return GEMINI_API_KEY from environment without logging or exposing it."""
    return os.getenv("GEMINI_API_KEY", "").strip()


def get_gemini_model_name() -> str:
    """Return configured GEMINI_MODEL or default flash model name."""
    model_name = os.getenv("GEMINI_MODEL", "").strip()
    return model_name if model_name else DEFAULT_GEMINI_MODEL


def get_gemini_client() -> genai.Client:
    """
    Instantiate and return a google-genai Client.
    Uses GEMINI_API_KEY if configured in environment.
    """
    api_key = get_gemini_api_key()
    if api_key:
        return genai.Client(api_key=api_key)
    return genai.Client()
