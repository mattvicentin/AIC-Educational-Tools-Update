import os

import pytest


def _load_env():
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        pass


@pytest.mark.network
def test_anthropic_or_openai_call_smoke():
    """Smoke test that makes a real AI API call if keys are present.

    Skips gracefully if neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set.
    The call uses a tiny prompt and small max_tokens to limit cost.
    """
    _load_env()

    # Prefer Anthropic if available
    ant_key = os.getenv("ANTHROPIC_API_KEY")
    if ant_key:
        from src.utils.openai_utils import call_anthropic_api

        text, truncated = call_anthropic_api(
            [{"role": "user", "content": "Reply with a single short word: ok"}],
            system_prompt="You are concise.",
            max_tokens=10,
        )
        assert isinstance(text, str) and len(text) > 0
        assert isinstance(truncated, bool)
        return

    # Otherwise try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from src.utils.openai_utils import call_openai_api

        text, truncated = call_openai_api(
            [{"role": "user", "content": "Reply with a single short word: ok"}],
            system_prompt="You are concise.",
            max_tokens=10,
        )
        assert isinstance(text, str) and len(text) > 0
        assert isinstance(truncated, bool)
        return

    pytest.skip("No AI API key set; set ANTHROPIC_API_KEY or OPENAI_API_KEY to run this test.")


