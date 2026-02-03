#!/usr/bin/env python3
"""Test which Anthropic models are available."""

# TODO: verify usage; consider moving this script into scripts/ or removing if unused.

from anthropic import Anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Test various model names
models_to_test = [
    'claude-3-5-sonnet-20241022',
    'claude-3-5-sonnet-20240620',
    'claude-3-5-haiku-20241022',
    'claude-3-5-haiku-20240307',
    'claude-3-opus-20240229',
    'claude-3-sonnet-20240229',
    'claude-3-haiku-20240307',
]

print("Testing Anthropic models...\n")

working_models = []
for model in models_to_test:
    try:
        response = client.messages.create(
            model=model,
            max_tokens=5,
            messages=[{'role': 'user', 'content': 'hi'}]
        )
        print(f"✅ {model}: Working")
        working_models.append(model)
    except Exception as e:
        error_msg = str(e)
        if 'not_found' in error_msg.lower() or '404' in error_msg:
            print(f"❌ {model}: Not found")
        else:
            print(f"⚠️  {model}: {error_msg[:80]}")

print(f"\n✅ Found {len(working_models)} working model(s)")
if working_models:
    print(f"Recommended: {working_models[0]}")
