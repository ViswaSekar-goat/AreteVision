import os

from dotenv import load_dotenv
from groq import (
    APIConnectionError,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
    InternalServerError,
)
from langchain_groq import ChatGroq

load_dotenv()


def get_groq_llm():

    api_keys = [
        os.getenv(f"GROQ_API_KEY_{i}")
        for i in range(0, 13)
        if os.getenv(f"GROQ_API_KEY_{i}")
    ]

    if not api_keys:
        raise ValueError("No Groq API keys found in .env")

    models = [
        ChatGroq(
            model="qwen/qwen3.8-27b",
            api_key=key,
            temperature=0,
            max_retries=0,
        )
        for key in api_keys
    ]

    primary = models[0]
    fallbacks = models[1:]

    if not fallbacks:
        return primary

    return primary.with_fallbacks(
        fallbacks,
        exceptions_to_handle=(
            APIConnectionError,
            AuthenticationError,
            PermissionDeniedError,
            RateLimitError,
            InternalServerError,
        ),
    )