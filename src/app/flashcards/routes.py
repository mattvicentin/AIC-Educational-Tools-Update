"""
Flashcards Tool API Routes
Handles flashcard generation with strict context boundaries and no-repeat logic
"""

from flask import request, jsonify, current_app, session
from functools import wraps
from src.app import db, limiter
from src.app.flashcards import flashcards
from src.models.flashcards import FlashcardSet, FlashcardSession
from src.models.chat import Chat, Message
from src.models.document import Document, DocumentChunk
from src.models.room import Room
from src.app.access_control import get_current_user, require_login, require_chat_access, can_access_room
from src.models.user import User
from src.utils.openai_utils import call_anthropic_api
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import hashlib
import re
import uuid


def login_required(f):
    """Session-based login required decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def assemble_chat_context(chat_id: int, limit: int = 20) -> str:
    """Assemble chat messages into context string."""
    messages = (
        Message.query
        .filter_by(chat_id=chat_id)
        .order_by(Message.timestamp.desc())
        .limit(limit)
        .all()
    )
    
    # Reverse to chronological order
    messages = list(reversed(messages))
    
    context_parts = []
    for msg in messages:
        role_label = "User" if msg.role == "user" else "Assistant"
        context_parts.append(f"{role_label}: {msg.content}")
    
    return "\n\n".join(context_parts)


def assemble_library_context(doc_ids: List[int], max_chars: int = 10000) -> str:
    """Assemble library documents into context string."""
    if not doc_ids:
        return ""
    
    documents = Document.query.filter(Document.id.in_(doc_ids)).all()
    
    context_parts = []
    total_chars = 0
    
    for doc in documents:
        # Get document text (from full_text or chunks)
        doc_text = doc.full_text or ""
        
        if not doc_text and doc.chunks:
            # Reconstruct from chunks
            chunks = sorted(doc.chunks, key=lambda c: c.chunk_index)
            doc_text = "\n\n".join([c.chunk_text for c in chunks])
        
        # Truncate if needed
        remaining_chars = max_chars - total_chars
        if remaining_chars <= 0:
            break
        
        if len(doc_text) > remaining_chars:
            doc_text = doc_text[:remaining_chars] + "... [truncated]"
        
        context_parts.append(f"Document: {doc.name}\n{doc_text}")
        total_chars += len(doc_text)
        
        if total_chars >= max_chars:
            break
    
    return "\n\n---\n\n".join(context_parts)


def assemble_flashcard_context(context_mode: str, chat_id: Optional[int] = None, library_doc_ids: Optional[List[int]] = None) -> Dict[str, Optional[str]]:
    """Assemble context with strict boundaries - only pass allowed context."""
    context_parts = {}
    
    if context_mode == 'chat':
        if chat_id:
            context_parts['chat'] = assemble_chat_context(chat_id)
        else:
            context_parts['chat'] = None
        context_parts['library'] = None
    elif context_mode == 'library':
        context_parts['chat'] = None
        if library_doc_ids:
            context_parts['library'] = assemble_library_context(library_doc_ids)
        else:
            context_parts['library'] = None
    elif context_mode == 'both':
        if chat_id:
            context_parts['chat'] = assemble_chat_context(chat_id)
        else:
            context_parts['chat'] = None
        if library_doc_ids:
            context_parts['library'] = assemble_library_context(library_doc_ids)
        else:
            context_parts['library'] = None
    
    return context_parts


def calculate_card_count_from_grid(grid_size: str) -> int:
    """Convert '2x3' to 6 cards."""
    parts = grid_size.split('x')
    return int(parts[0]) * int(parts[1])


def normalize_and_hash_front(front_text: str) -> str:
    """Normalize front text and return hash."""
    # Normalize: lowercase, trim, remove punctuation
    normalized = re.sub(r'[^\w\s]', '', front_text.lower().strip())
    # Hash
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]  # 16-char hash


def generate_flashcard_prompt(context_parts: Dict[str, Optional[str]], context_mode: str, card_count: int, seen_fronts: List[str], instructions: Optional[str] = None) -> str:
    """Generate the prompt for flashcard generation with strict context boundaries."""
    
    # Build context section based on mode
    context_section = ""
    context_instruction = ""
    
    if context_mode == 'chat':
        context_instruction = "You MUST use ONLY the chat conversation context provided below. Do NOT use library documents or outside knowledge."
        if context_parts.get('chat'):
            context_section = f"=== CHAT CONVERSATION ===\n{context_parts['chat']}"
        else:
            context_section = "No chat context available."
    elif context_mode == 'library':
        context_instruction = "You MUST use ONLY the library documents context provided below. Do NOT use chat conversation or outside knowledge."
        if context_parts.get('library'):
            context_section = f"=== LIBRARY DOCUMENTS ===\n{context_parts['library']}"
        else:
            context_section = "No library context available."
    elif context_mode == 'both':
        context_instruction = "You MUST use ONLY the chat conversation and library documents provided below. If there is a conflict, prefer chat for user intent and library for factual detail. Do NOT use outside knowledge."
        context_sections = []
        if context_parts.get('chat'):
            context_sections.append(f"=== CHAT CONVERSATION ===\n{context_parts['chat']}")
        if context_parts.get('library'):
            context_sections.append(f"=== LIBRARY DOCUMENTS ===\n{context_parts['library']}")
        context_section = "\n\n".join(context_sections) if context_sections else "No context available."
    
    # Build seen fronts list for prompt
    seen_fronts_text = ""
    if seen_fronts:
        seen_fronts_text = f"\n\nAVOID DUPLICATES: Do not generate cards with fronts similar to these already generated:\n" + "\n".join([f"- {front}" for front in seen_fronts[:20]])  # Limit to 20 for prompt size
    
    base_prompt = f"""You are generating study flashcards.

STRICT CONTEXT BOUNDARY:
{context_instruction}

{context_section}

TASK:
Generate exactly {card_count} high-quality flashcards based on the context material above.

FLASHCARD RULES:
- Each flashcard has a FRONT and BACK.
- FRONT must be a short clue only (term/name/date/place/concept). No full explanation.
- BACK must fully explain the FRONT in 1–4 short bullet points or 1 tight paragraph.
- BACK must be supported by the provided context. If the context doesn't support it, do not invent.
- Keep cards independent (no "as mentioned above").
- Avoid duplicates and near-duplicates.{seen_fronts_text}

ADDITIONAL INSTRUCTIONS:
{instructions if instructions else "Focus on key concepts and important details from the context."}

OUTPUT FORMAT (JSON):
{{
  "status": "ok" | "insufficient_context",
  "cards": [
    {{
      "id": 1,
      "front": "Short clue here",
      "back": "Full explanation here"
    }}
  ],
  "hasMore": true/false
}}

If context is insufficient to generate the requested number of cards, return:
{{
  "status": "insufficient_context",
  "cards": [...], // whatever you could generate
  "hasMore": false,
  "message": "Context insufficient for requested count"
}}

Return ONLY valid JSON, no additional text before or after."""

    return base_prompt


@flashcards.route('/generate', methods=['POST'])
@login_required
@limiter.limit("10 per minute; 50 per hour")
def generate_flashcards():
    """Unified endpoint for generating flashcards (initial or generate-more)."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Check if generate-more mode
        session_id = data.get('session_id')
        if session_id:
            return handle_generate_more(session_id, user, data)
        else:
            return handle_initial_generation(data, user)
        
    except Exception as e:
        current_app.logger.error(f"Flashcard generation error: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'Failed to generate flashcards: {str(e)}'
        }), 500


def handle_initial_generation(data: Dict, user: User) -> jsonify:
    """Handle initial flashcard generation."""
    # Validate required fields
    chat_id = data.get('chat_id')
    context_mode = data.get('context_mode', 'chat')
    display_mode = data.get('display_mode')
    library_doc_ids = data.get('library_doc_ids', [])
    instructions = data.get('instructions', '').strip()
    
    if not chat_id:
        return jsonify({'status': 'error', 'message': 'chat_id is required'}), 400
    
    if not display_mode or display_mode not in ('grid', 'single'):
        return jsonify({'status': 'error', 'message': 'display_mode must be "grid" or "single"'}), 400
    
    if context_mode not in ('chat', 'library', 'both'):
        return jsonify({'status': 'error', 'message': 'context_mode must be "chat", "library", or "both"'}), 400
    
    # Calculate card count
    if display_mode == 'grid':
        grid_size = data.get('grid_size')
        if not grid_size or grid_size not in ('1x2', '2x2', '2x3', '3x3'):
            return jsonify({'status': 'error', 'message': 'grid_size must be "1x2", "2x2", "2x3", or "3x3"'}), 400
        card_count = calculate_card_count_from_grid(grid_size)
        is_infinite = data.get('infinite_grid', False)
    else:
        grid_size = None
        card_count = data.get('card_count')
        if card_count is None:
            is_infinite = True
        else:
            if not isinstance(card_count, int) or card_count < 1 or card_count > 100:
                return jsonify({'status': 'error', 'message': 'card_count must be between 1 and 100'}), 400
            is_infinite = False
    
    # Check chat access
    chat_obj = Chat.query.get(chat_id)
    if not chat_obj:
        return jsonify({'status': 'error', 'message': 'Chat not found'}), 404
    
    room_obj = Room.query.get(chat_obj.room_id)
    if not room_obj:
        return jsonify({'status': 'error', 'message': 'Room not found'}), 404
    
    if not can_access_room(user, room_obj):
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    # Validate library access if needed
    if context_mode in ('library', 'both'):
        if not library_doc_ids:
            if context_mode == 'library':
                return jsonify({'status': 'error', 'message': 'At least one library document is required when context_mode is "library"'}), 400
        else:
            docs = Document.query.filter(
                Document.id.in_(library_doc_ids),
                Document.room_id == chat_obj.room_id
            ).all()
            if len(docs) != len(library_doc_ids):
                return jsonify({'status': 'error', 'message': 'One or more documents not found or access denied'}), 403
    
    # Assemble context with strict boundaries
    context_parts = assemble_flashcard_context(context_mode, chat_id, library_doc_ids)
    
    # Check if context is available
    has_context = False
    if context_mode == 'chat' and context_parts.get('chat'):
        has_context = True
    elif context_mode == 'library' and context_parts.get('library'):
        has_context = True
    elif context_mode == 'both' and (context_parts.get('chat') or context_parts.get('library')):
        has_context = True
    
    if not has_context:
        return jsonify({
            'status': 'insufficient_context',
            'message': 'No context available. Please ensure chat has messages or library documents are selected.',
            'cards': [],
            'hasMore': False
        }), 400
    
    # Generate flashcards
    current_app.logger.info(f"Generating flashcards for chat {chat_id}, {card_count} cards, mode: {display_mode}")
    
    try:
        # Generate prompt
        prompt = generate_flashcard_prompt(context_parts, context_mode, card_count, [], instructions)
        
        # Call AI
        text_content, is_truncated = call_anthropic_api(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert educator creating study flashcards. Follow all instructions strictly.",
            max_tokens=4000
        )
        
        if not text_content or not text_content.strip():
            raise ValueError("Empty response from AI")
        
        # Extract JSON from response
        json_start = text_content.find('{')
        json_end = text_content.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_text = text_content[json_start:json_end]
        flashcard_data = json.loads(json_text)
        
        # Handle response status
        response_status = flashcard_data.get('status', 'ok')
        cards = flashcard_data.get('cards', [])
        
        if response_status == 'insufficient_context':
            # Return what we got
            return jsonify({
                'status': 'insufficient_context',
                'cards': cards,
                'hasMore': False,
                'message': flashcard_data.get('message', 'Context insufficient for requested count')
            }), 200
        
        # Validate and process cards
        if len(cards) != card_count:
            current_app.logger.warning(f"Expected {card_count} cards, got {len(cards)}")
        
        # Add hashes to cards
        processed_cards = []
        seen_hashes = set()
        for i, card in enumerate(cards):
            if 'front' not in card or 'back' not in card:
                continue
            
            card_hash = normalize_and_hash_front(card['front'])
            if card_hash in seen_hashes:
                # Skip duplicate
                continue
            
            seen_hashes.add(card_hash)
            card['id'] = i + 1
            card['hash'] = card_hash
            processed_cards.append(card)
        
        if not processed_cards:
            return jsonify({
                'status': 'error',
                'message': 'No valid flashcards generated'
            }), 500
        
        # Store flashcard set
        flashcard_set = FlashcardSet(
            chat_id=chat_id,
            room_id=chat_obj.room_id,
            created_by=user.id,
            context_mode=context_mode,
            library_doc_ids=library_doc_ids if library_doc_ids else None,
            instructions=instructions if instructions else None,
            display_mode=display_mode,
            grid_size=grid_size,
            is_infinite=is_infinite,
            cards=processed_cards
        )
        db.session.add(flashcard_set)
        
        # Create session if infinite
        session_obj = None
        cursor_state = None
        if is_infinite:
            session_id = str(uuid.uuid4())
            cursor_state = {
                'normalizedFrontHashes': list(seen_hashes),
                'totalGenerated': len(processed_cards),
                'lastContextHash': hashlib.sha256(str(context_parts).encode()).hexdigest()[:16]
            }
            session_obj = FlashcardSession(
                flashcard_set_id=flashcard_set.id,
                user_id=user.id,
                session_id=session_id,
                cursor_state=cursor_state
            )
            db.session.add(session_obj)
        
        db.session.commit()
        
        # Return response
        response = {
            'status': 'ok',
            'cards': processed_cards,
            'hasMore': is_infinite
        }
        
        if is_infinite and session_obj:
            response['session_id'] = session_obj.session_id
            response['cursor'] = cursor_state
        
        return jsonify(response), 200
        
    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSON decode error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to parse flashcard response from AI'
        }), 500
    except Exception as e:
        current_app.logger.error(f"AI generation error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to generate flashcards: {str(e)}'
        }), 500


def handle_generate_more(session_id: str, user: User, data: Dict) -> jsonify:
    """Handle generate-more request for infinite mode."""
    # Load session
    session_obj = FlashcardSession.query.filter_by(session_id=session_id).first()
    if not session_obj:
        return jsonify({'status': 'error', 'message': 'Session not found'}), 404
    
    # Check access
    if session_obj.user_id != user.id:
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    # Get flashcard set
    flashcard_set = session_obj.flashcard_set
    if not flashcard_set:
        return jsonify({'status': 'error', 'message': 'Flashcard set not found'}), 404
    
    # Update last accessed
    session_obj.last_accessed_at = datetime.now(timezone.utc)
    
    # Get cursor state
    cursor_state = session_obj.cursor_state or {}
    seen_hashes = set(cursor_state.get('normalizedFrontHashes', []))
    
    # Determine card count
    if flashcard_set.display_mode == 'grid':
        card_count = calculate_card_count_from_grid(flashcard_set.grid_size)
    else:
        card_count = data.get('card_count', 10)  # Default 10 for single mode generate-more
    
    # Assemble context (reuse from original set)
    context_parts = assemble_flashcard_context(
        flashcard_set.context_mode,
        flashcard_set.chat_id,
        flashcard_set.library_doc_ids
    )
    
    # Get seen fronts for prompt (limit to reasonable number)
    seen_fronts = []
    if flashcard_set.cards:
        seen_fronts = [card.get('front', '') for card in flashcard_set.cards[:50]]
    
    try:
        # Generate prompt
        prompt = generate_flashcard_prompt(
            context_parts,
            flashcard_set.context_mode,
            card_count,
            seen_fronts,
            flashcard_set.instructions
        )
        
        # Call AI
        text_content, is_truncated = call_anthropic_api(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are an expert educator creating study flashcards. Follow all instructions strictly.",
            max_tokens=4000
        )
        
        if not text_content or not text_content.strip():
            raise ValueError("Empty response from AI")
        
        # Extract JSON
        json_start = text_content.find('{')
        json_end = text_content.rfind('}') + 1
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_text = text_content[json_start:json_end]
        flashcard_data = json.loads(json_text)
        
        response_status = flashcard_data.get('status', 'ok')
        new_cards = flashcard_data.get('cards', [])
        
        if response_status == 'insufficient_context':
            return jsonify({
                'status': 'insufficient_context',
                'cards': [],
                'hasMore': False,
                'message': flashcard_data.get('message', 'No more cards can be generated from available context')
            }), 200
        
        # Process and filter duplicates
        processed_cards = []
        new_hashes = set()
        start_id = len(flashcard_set.cards) + 1
        
        for i, card in enumerate(new_cards):
            if 'front' not in card or 'back' not in card:
                continue
            
            card_hash = normalize_and_hash_front(card['front'])
            if card_hash in seen_hashes or card_hash in new_hashes:
                # Skip duplicate
                continue
            
            new_hashes.add(card_hash)
            card['id'] = start_id + len(processed_cards)
            card['hash'] = card_hash
            processed_cards.append(card)
        
        if not processed_cards:
            return jsonify({
                'status': 'insufficient_context',
                'cards': [],
                'hasMore': False,
                'message': 'No new unique cards could be generated'
            }), 200
        
        # Update flashcard set
        flashcard_set.cards.extend(processed_cards)
        
        # Update cursor state
        cursor_state['normalizedFrontHashes'] = list(seen_hashes | new_hashes)
        cursor_state['totalGenerated'] = cursor_state.get('totalGenerated', 0) + len(processed_cards)
        session_obj.cursor_state = cursor_state
        
        db.session.commit()
        
        return jsonify({
            'status': 'ok',
            'cards': processed_cards,
            'cursor': cursor_state,
            'hasMore': True
        }), 200
        
    except json.JSONDecodeError as e:
        current_app.logger.error(f"JSON decode error: {e}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to parse flashcard response from AI'
        }), 500
    except Exception as e:
        current_app.logger.error(f"AI generation error: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Failed to generate more flashcards: {str(e)}'
        }), 500
