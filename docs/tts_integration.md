### Natural Text‑to‑Speech (TTS) Integration Plan

This document outlines options and an implementation path to add natural TTS for assistant replies in AI Collab Online.

---

#### Goals
- High‑quality, natural voices
- Low latency for recent messages
- Consistent cross‑browser behavior
- Easy to disable/limit (feature flag + quotas)

---

#### Options Overview

- **Client‑only (fast prototype)**
  - Web Speech API (Chrome/Edge best; Safari OK; Firefox partial)
  - Pros: zero cost, no server changes, instant
  - Cons: variable quality, inconsistent voices, no shared cache

- **Server TTS Providers (recommended for production)**
  - OpenAI TTS (natural voices, streaming)
  - ElevenLabs / PlayHT (wide voice catalogs, quality, SSML)
  - Azure Neural TTS / Google Cloud TTS / Amazon Polly (enterprise‑grade, SSML)
  - Self‑hosted (Coqui XTTS/Piper) for maximum control; higher ops cost

---

#### UX Patterns
- Per‑message controls: a small speaker icon → play/pause, progress, speed (0.8–1.25x)
- Prefetch last assistant reply after render; cache for instant replay
- Continuous playback toggle (read new assistant replies automatically) – requires a user gesture due to autoplay policies
- Accessibility: keyboard shortcuts, ARIA labels, captions toggle

---

#### Architecture (Server‑Backed MVP)

- Feature flag: `TTS_ENABLED`
- Config:
  - `TTS_PROVIDER` = `openai|azure|google|elevenlabs|playht|polly|coqui`
  - Provider keys: `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, etc.
  - Defaults: `TTS_DEFAULT_VOICE`, `TTS_MAX_SECONDS`, `TTS_CACHE_TTL_SECONDS`

- Endpoint: `POST /tts`
  - Request JSON: `{ "message_id": 123, "text": "...", "voice": "alloy", "provider": "openai", "format": "mp3" }`
  - Response: `audio/mpeg` (or JSON with a signed URL if using object storage)
  - Rate limit: tie to user/session and `TTS_MAX_SECONDS`

- Caching
  - Key = SHA256(`provider|voice|text`) → avoid duplicate costs
  - Storage options:
    - Memory/disk (simple) for dev
    - Object storage (S3/R2/GCS) for production; return signed URLs
  - DB table `tts_cache` (optional) to track keys, durations, counts, TTL

- Client
  - Add a speaker icon to assistant messages
  - On click: if cached URL present → play; else POST `/tts`, stream or fetch blob → play
  - Prefetch the latest assistant message after render (respect quotas)
  - Maintain a single `<audio>` element per chat; reuse source

- CSP additions
  - `media-src 'self' blob: data:`
  - If using provider streaming/CDN, add provider domains in `connect-src`/`media-src`

---

#### Provider Notes

- OpenAI TTS
  - Pros: simple API, natural voices, streaming support
  - Cons: pricing; requires key; regional availability considerations

- ElevenLabs / PlayHT
  - Pros: strong voice library, expressive styles, SSML prosody
  - Cons: vendor lock‑in; per‑char pricing

- Azure/Google/Polly
  - Pros: enterprise reliability, SSML, regional hosting
  - Cons: setup complexity, quotas

- Coqui/Piper (self‑hosted)
  - Pros: control, no per‑char vendor cost
  - Cons: model hosting & scaling, latency tuning

---

#### Streaming vs. Non‑Streaming

- Non‑Streaming (simpler MVP)
  - Synthesize full MP3/OGG → return file/URL → play
  - Latency <2s target; good with caching

- Streaming (lower latency)
  - Provider WebSocket/SSE → client buffer via MediaSource Extensions → play while receiving
  - Adds client complexity; implement after MVP

---

#### Data Model (optional cache)

`tts_cache` (SQL)
```
id (pk)
key_hash (unique)
provider
voice
bytes_url_or_path
duration_seconds
size_bytes
ttl_expires_at
created_at, last_accessed_at, access_count
```

---

#### Error Handling & Limits
- Timeouts per provider call (e.g., 10s)
- Fallback voice/provider order; return 503 if exhausted
- Enforce per‑user/room quotas (trial mode aware)
- Return structured JSON errors for the client to show helpful messages

---

#### Phased Rollout
1) Prototype (client‑only Web Speech API)
   - Add speaker icon; synthesize locally; no server changes

2) Server MVP (OpenAI or ElevenLabs)
   - Implement `/tts` + in‑memory cache
   - Prefetch latest assistant reply
   - Add feature flag & basic rate limit

3) Production
   - Object storage cache + DB index
   - Observability (latency, cache‑hit rate, cost)
   - Quotas per user/room; admin controls
   - Streaming enhancement if needed

---

#### Example `/tts` Flow (pseudocode)

```python
@app.route('/tts', methods=['POST'])
@require_login  # or trial-aware
def tts_generate():
    data = request.get_json()
    text = (data.get('text') or '').strip()
    voice = data.get('voice') or os.getenv('TTS_DEFAULT_VOICE', 'alloy')
    provider = data.get('provider') or os.getenv('TTS_PROVIDER', 'openai')
    fmt = (data.get('format') or 'mp3').lower()

    assert text, 'text required'
    enforce_rate_limits(user, text)

    key = sha256(f"{provider}|{voice}|{fmt}|{text}".encode()).hexdigest()
    audio = cache_get(key)
    if audio:
        return send_audio(audio)

    audio = call_provider_tts(provider, text, voice, fmt)
    cache_put(key, audio)
    return send_audio(audio)
```

---

#### Testing Checklist
- Cross‑browser playback (Chrome, Edge, Safari, Firefox)
- Autoplay policies (requires user gesture)
- Error paths (network error, quota exceeded, provider 429)
- Cache hit/miss and eviction
- Trial mode limits + analytics (usage per user/room)

---

#### Risks & Mitigations
- Latency spikes → add prefetch + streaming; timeout + fallback
- Cost spikes → cache, quotas, and only TTS the latest messages by default
- Browser inconsistencies → use server TTS for consistent output
- Storage growth → TTL and size caps, scheduled clean‑ups

---

#### Suggested Config (Railway)
```
TTS_ENABLED=true
TTS_PROVIDER=openai  # or elevenlabs/playht/azure/google/polly
TTS_DEFAULT_VOICE=alloy
TTS_CACHE_TTL_SECONDS=2592000  # 30 days
TTS_MAX_SECONDS=120
# Provider keys
OPENAI_API_KEY=...
ELEVENLABS_API_KEY=...
AZURE_SPEECH_KEY=...  AZURE_SPEECH_REGION=...
GOOGLE_APPLICATION_CREDENTIALS=...
AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_DEFAULT_REGION=...
```

---

#### Implementation Order (Recommended)
1) Add flag + UI speaker icon (disabled by default)
2) Client‑only prototype (Web Speech) for UX validation
3) `/tts` with provider + in‑memory cache
4) Prefetch latest assistant reply + simple quotas
5) Move to object storage cache + DB metadata; add analytics & alerts
6) Optional: streaming TTS


