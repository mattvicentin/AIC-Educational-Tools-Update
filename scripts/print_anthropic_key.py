import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("ANTHROPIC_API_KEY")
if key:
    print("Anthropic key loaded, starts with:", key[:12], "...", "length:", len(key))
else:
    print("No Anthropic key found") 