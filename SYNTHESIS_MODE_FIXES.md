# Synthesis Mode Fixes - Implementation Summary

## Overview

Fixed four critical issues in synthesis mode and added comprehensive guardrails to keep synthesis useful, cost-effective, and reliable.

## Issues Fixed

### 1. ✅ Sampling Logic Bug
**Problem**: Code tried to include first+last chunks but truncated back to `chunks_per_doc`, so last chunk was never included when `total_chunks > chunks_per_doc`.

**Fix**: Explicit sampling logic:
- For `chunks_per_doc=2`: Always get chunks at indices `[0, total_chunks-1]` (first and last)
- For `chunks_per_doc=3`: Get chunks at indices `[0, total_chunks//2, total_chunks-1]` (first, middle, last)
- For `chunks_per_doc > 3`: Evenly distributed sampling without truncation bug

**File**: `src/utils/documents/database.py` (lines 171-187)

### 2. ✅ Prompt Size Risk
**Problem**: No caps on documents or total chunks; could create very large prompts.

**Fix**: Added comprehensive caps:
- **Document cap**: 5 documents max (most recent)
- **Chunk cap**: 10 total chunks max
- **Chunk length**: 400 chars per chunk (truncated)
- **Token budget**: 1000 tokens max (fallback to summaries if exceeded)

**Files**: 
- `src/utils/documents/database.py` (constants: lines 12-16, function: lines 103-220)
- `src/utils/openai_utils.py` (token estimation: lines 851-860)

### 3. ✅ Feature Flag Bypass
**Problem**: Synthesis mode queried ORM directly, ignoring `USE_RAILWAY_DOCUMENTS` flag.

**Fix**: Added feature flag check at start of `get_representative_chunks_from_all_documents()`:
- Checks `USE_RAILWAY_DOCUMENTS` before processing
- Returns empty list with warning log if disabled
- Matches behavior of `search_indexed_chunks()` function

**File**: `src/utils/documents/database.py` (lines 125-136)

### 4. ✅ Detection Scope
**Problem**: Only checked latest user message; could trigger on unintended queries.

**Fix**: Tighter detection with:
- **Explicit keywords**: "summarize all", "synthesize all", "comprehensive synthesis", etc.
- **Broad keywords**: "all sources", "all documents" (requires longer query ≥20 chars)
- **Minimum length**: 10 characters minimum to avoid triggering on single words like "all"

**File**: `src/utils/openai_utils.py` (lines 805-828)

## Additional Enhancements

### User-Facing Messages
When synthesis is requested but feature flag is disabled, AI receives a note to inform the user:
- Added to `extra_system` context
- AI will explain that Library Tool needs to be enabled

**File**: `src/utils/openai_utils.py` (lines 870-883)

### Token Budget Fallback
If estimated tokens exceed budget (1000), automatically falls back to document summaries:
- Estimates tokens: ~4 chars per token
- Falls back to `get_document_summaries_only()` if exceeded
- Logs warning for monitoring

**File**: `src/utils/openai_utils.py` (lines 851-860)

### Configuration Constants
All limits are configurable via constants in `database.py`:
```python
SYNTHESIS_MAX_DOCUMENTS = 5
SYNTHESIS_MAX_TOTAL_CHUNKS = 10
SYNTHESIS_CHUNK_TEXT_LIMIT = 400
SYNTHESIS_TOKEN_BUDGET = 1000
```

**File**: `src/utils/documents/database.py` (lines 12-16)

## Files Modified

1. **`src/utils/documents/database.py`**
   - Added configuration constants
   - Fixed sampling logic in `get_representative_chunks_from_all_documents()`
   - Added feature flag check
   - Added document/chunk caps
   - Added chunk text truncation
   - Added `get_document_summaries_only()` fallback function

2. **`src/utils/openai_utils.py`**
   - Tightened synthesis detection (explicit keywords + minimum length)
   - Added token estimation and budget check
   - Added fallback to summaries when budget exceeded
   - Added user-facing message when feature flag disabled
   - Updated `build_document_context_block()` truncation limit (500 → 400 chars)

## Testing Checklist

- [x] Sampling logic: First and last chunks included for 2-chunk mode
- [x] Document cap: Max 5 documents processed (most recent)
- [x] Chunk cap: Max 10 total chunks returned
- [x] Chunk truncation: Chunks truncated to 400 chars
- [x] Feature flag: Respects `USE_RAILWAY_DOCUMENTS` flag
- [x] Token budget: Falls back to summaries when exceeded
- [x] Detection: Tighter matching (explicit keywords + minimum length)
- [x] User messages: AI informed when feature disabled

## Guardrails Summary

| Guardrail | Value | Purpose |
|-----------|-------|---------|
| Max Documents | 5 | Limit processing to most recent documents |
| Max Total Chunks | 10 | Hard limit on chunks returned |
| Chunk Length | 400 chars | Keep individual chunks manageable |
| Token Budget | 1000 tokens | Prevent excessive API costs |
| Min Query Length | 10 chars | Avoid false positives on short queries |
| Explicit Keywords | Required | Tighter matching for synthesis requests |

## Backward Compatibility

- ✅ Normal search mode unchanged (still uses relevance-based search)
- ✅ Existing document queries unaffected
- ✅ Feature flag defaults to `true` (Railway-only)
- ✅ Graceful degradation when feature disabled

## Next Steps

1. Test with various document counts (1, 5, 10, 20 documents)
2. Test with various chunk sizes (small, medium, large documents)
3. Monitor token usage in production
4. Consider making constants configurable via environment variables if needed
5. Monitor false positive rate for synthesis detection

