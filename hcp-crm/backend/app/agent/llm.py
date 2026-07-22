"""Thin wrapper around Groq-hosted LLMs used across the agent.

Primary model: gemma2-9b-it (fast, cheap - used for the main agent loop and
entity extraction/summarization tools).
Fallback / heavier-context model: llama-3.3-70b-versatile (used when the
primary model errors out, e.g. rate limits, or when a task needs more
context/reasoning, such as generating richer follow-up suggestions).
"""
from langchain_groq import ChatGroq

from app.config import settings


def get_primary_llm(temperature: float = 0.2):
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_PRIMARY_MODEL,
        temperature=temperature,
    )


def get_fallback_llm(temperature: float = 0.3):
    return ChatGroq(
        api_key=settings.GROQ_API_KEY,
        model=settings.GROQ_FALLBACK_MODEL,
        temperature=temperature,
    )


def invoke_with_fallback(messages, temperature: float = 0.2):
    """Try the primary (small/cheap) model first; fall back to the larger
    model if the primary call fails for any reason (rate limit, timeout...)."""
    try:
        return get_primary_llm(temperature).invoke(messages)
    except Exception:
        return get_fallback_llm(temperature).invoke(messages)
