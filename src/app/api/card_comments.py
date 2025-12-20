"""
Card Comments API

CRUD endpoints for comments on individual cards (segments) in Card View.
Cards are ephemeral but card_key provides a stable reference for comments.

Endpoints:
    GET  /chat/<chat_id>/cards/<card_key>/comments - List comments (paginated)
    POST /chat/<chat_id>/cards/<card_key>/comments - Create comment
    POST /chat/<chat_id>/cards/<card_key>/comments/ai - Generate AI reply
    DELETE /chat/<chat_id>/cards/<card_key>/comments/<comment_id> - Soft delete

All endpoints require chat access and CSRF protection.
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from sqlalchemy import and_

from src.app import db, limiter
from src.app.access_control import require_login, require_chat_access, get_current_user
from src.models import CardComment, Chat, Message, Room, RoomMember

card_comments_api = Blueprint("card_comments_api", __name__)

# Rate limits
RATE_LIMIT_POST = "10 per minute"  # Prevent spam
RATE_LIMIT_GET = "60 per minute"   # Generous for reading
RATE_LIMIT_AI = "5 per minute"     # More restrictive for AI calls

# Pagination
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50

# Content limits
MAX_COMMENT_LENGTH = 8000  # ~8KB per comment

# AI reply settings
MAX_CONSECUTIVE_AI_REPLIES = 2  # Per user per card
AI_REPLY_MAX_TOKENS = 250       # Keep responses brief
AI_REPLY_MAX_CHARS = 1500       # Hard cap on AI response length (chars, not tokens)
AI_CONTEXT_MAX_COMMENTS = 5     # Recent comments to include
AI_CONTEXT_MAX_CHARS = 2000     # Truncate long card bodies


def _get_chat_context(chat_id: int) -> tuple:
    """
    Get chat and room context, validating existence.
    
    Returns:
        Tuple of (chat, room) or raises 404
    """
    chat = Chat.query.get_or_404(chat_id)
    room = Room.query.get_or_404(chat.room_id)
    return chat, room


def _can_delete_comment(user, comment, room) -> bool:
    """
    Check if user can delete this comment.
    
    Allowed for:
    - Comment author
    - Room owner
    """
    if not user:
        return False
    
    # Author can delete their own
    if comment.user_id == user.id:
        return True
    
    # Room owner can delete any
    if room.owner_id == user.id:
        return True
    
    return False


@card_comments_api.route("/chat/<int:chat_id>/cards/<card_key>/comments", methods=["GET"])
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_GET)
def list_comments(chat_id: int, card_key: str):
    """
    List comments for a card, paginated.
    
    Query params:
        after: Cursor (comment ID) to fetch after (for pagination)
        limit: Number of comments to return (default 20, max 50)
    
    Returns:
        {
            "success": true,
            "comments": [...],
            "has_more": true/false,
            "next_cursor": "123" or null
        }
    """
    chat, room = _get_chat_context(chat_id)
    
    # Parse pagination params
    after_id = request.args.get("after", type=int)
    limit = min(request.args.get("limit", DEFAULT_PAGE_SIZE, type=int), MAX_PAGE_SIZE)
    
    # Build query - exclude soft-deleted, order by id for consistent pagination
    query = CardComment.query.filter(
        and_(
            CardComment.chat_id == chat_id,
            CardComment.card_key == card_key,
            CardComment.deleted_at.is_(None)
        )
    ).order_by(CardComment.id.asc())  # Use id for cursor consistency
    
    # Apply cursor pagination
    if after_id:
        query = query.filter(CardComment.id > after_id)
    
    # Fetch one extra to check if there's more
    comments = query.limit(limit + 1).all()
    
    has_more = len(comments) > limit
    if has_more:
        comments = comments[:limit]
    
    # Serialize
    comment_dicts = [c.to_dict(include_user=True) for c in comments]
    
    return jsonify({
        "success": True,
        "comments": comment_dicts,
        "has_more": has_more,
        "next_cursor": str(comments[-1].id) if comments and has_more else None,
        "total_in_page": len(comment_dicts),
    })


@card_comments_api.route("/chat/<int:chat_id>/cards/<card_key>/comments", methods=["POST"])
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_POST)
def create_comment(chat_id: int, card_key: str):
    """
    Create a new comment on a card.
    
    Request JSON:
        {
            "content": "Comment text...",
            "message_id": 123,           // Required - source message
            "segment_index": 0,          // Required - which segment
            "segment_body": "..."        // Optional - for mismatch detection hash
        }
    
    Returns:
        {
            "success": true,
            "comment": {...}
        }
    """
    chat, room = _get_chat_context(chat_id)
    user = get_current_user()
    
    # Parse request
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    
    content = data.get("content", "").strip()
    message_id = data.get("message_id")
    segment_index = data.get("segment_index")
    segment_body = data.get("segment_body")
    
    # Validate required fields
    if not content:
        return jsonify({"success": False, "error": "content is required"}), 400
    
    if len(content) > MAX_COMMENT_LENGTH:
        return jsonify({
            "success": False, 
            "error": f"Comment too long (max {MAX_COMMENT_LENGTH} chars)"
        }), 400
    
    if message_id is None:
        return jsonify({"success": False, "error": "message_id is required"}), 400
    
    if segment_index is None:
        return jsonify({"success": False, "error": "segment_index is required"}), 400
    
    # Validate message exists and belongs to this chat
    message = Message.query.get(message_id)
    if not message or message.chat_id != chat_id:
        return jsonify({"success": False, "error": "Invalid message_id"}), 400
    
    # Validate card_key matches message/segment if segment_body provided
    # This prevents attaching comments to arbitrary card_keys
    if segment_body:
        from src.models import generate_card_key
        expected_key = generate_card_key(message_id, segment_index, segment_body)
        if card_key != expected_key:
            return jsonify({
                "success": False, 
                "error": "card_key mismatch - does not match message/segment"
            }), 400
    
    # Create comment
    try:
        comment = CardComment.create(
            chat_id=chat_id,
            room_id=room.id,
            message_id=message_id,
            user_id=user.id,
            card_key=card_key,
            segment_index=segment_index,
            content=content,
            segment_body=segment_body,
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "comment": comment.to_dict(include_user=True),
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@card_comments_api.route("/chat/<int:chat_id>/cards/<card_key>/comments/ai", methods=["POST"])
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_AI)
def create_ai_comment(chat_id: int, card_key: str):
    """
    Generate an AI reply comment on a card.
    
    Guarded: Max 2 consecutive AI replies per user per card.
    After 2 AI replies, user must add their own comment to continue.
    
    Request JSON:
        {
            "message_id": 123,           // Required - source message
            "segment_index": 0,          // Required - which segment
            "card_header": "...",        // Optional - card header text (used in prompt)
            "card_body": "...",          // Required - card body text
            "segment_body": "...",       // Optional - for card_key validation & hash
            "guiding_question": "..."    // Optional - from Card View context
        }
    
    Returns:
        {
            "success": true,
            "comment": {...}
        }
        
    Or if blocked:
        {
            "success": false,
            "error": "what_do_you_think",
            "message": "You've used 2 AI replies. What do you think?"
        }
    """
    import logging
    logger = logging.getLogger(__name__)
    
    chat, room = _get_chat_context(chat_id)
    user = get_current_user()
    
    # Check consecutive AI replies guard (include chat_id for extra isolation)
    consecutive_ai = CardComment.count_consecutive_ai_for_user(card_key, user.id, chat_id=chat_id)
    if consecutive_ai >= MAX_CONSECUTIVE_AI_REPLIES:
        return jsonify({
            "success": False,
            "error": "what_do_you_think",
            "message": "You've used 2 AI replies in a row. What do you think?",
            "consecutive_ai_count": consecutive_ai,
        }), 429  # Too Many Requests
    
    # Parse request
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "JSON body required"}), 400
    
    message_id = data.get("message_id")
    segment_index = data.get("segment_index")
    card_header = data.get("card_header", "").strip()
    card_body = data.get("card_body", "").strip()
    segment_body = data.get("segment_body")
    guiding_question = data.get("guiding_question", "").strip()
    
    # Validate required fields
    if message_id is None:
        return jsonify({"success": False, "error": "message_id is required"}), 400
    
    if segment_index is None:
        return jsonify({"success": False, "error": "segment_index is required"}), 400
    
    if not card_body:
        return jsonify({"success": False, "error": "card_body is required"}), 400
    
    # Validate message exists and belongs to this chat
    message = Message.query.get(message_id)
    if not message or message.chat_id != chat_id:
        return jsonify({"success": False, "error": "Invalid message_id"}), 400
    
    # Validate card_key matches message/segment if segment_body provided
    # (same check as human POST endpoint to prevent arbitrary card_key attachment)
    if segment_body:
        from src.models import generate_card_key
        expected_key = generate_card_key(message_id, segment_index, segment_body)
        if card_key != expected_key:
            return jsonify({
                "success": False,
                "error": "card_key mismatch - does not match message/segment"
            }), 400
    
    # Build AI prompt context
    prompt_context = _build_ai_reply_context(
        chat=chat,
        room=room,
        card_key=card_key,
        card_header=card_header,
        card_body=card_body,
        guiding_question=guiding_question,
    )
    
    # Generate AI reply
    try:
        ai_content = _generate_ai_reply(prompt_context)
        if not ai_content:
            return jsonify({
                "success": False,
                "error": "AI generation failed",
                "message": "Could not generate a reply. Please try again.",
            }), 500
        
        # Hard cap on AI response length (belt-and-suspenders after max_tokens)
        if len(ai_content) > AI_REPLY_MAX_CHARS:
            logger.warning(f"AI reply exceeded max chars ({len(ai_content)} > {AI_REPLY_MAX_CHARS}), trimming")
            ai_content = ai_content[:AI_REPLY_MAX_CHARS].rstrip() + "..."
            
    except Exception as e:
        logger.error(f"AI reply generation failed: {e}")
        return jsonify({
            "success": False,
            "error": "ai_error",
            "message": "AI service unavailable. Please try again later.",
        }), 503
    
    # Create comment with content_type='ai'
    try:
        comment = CardComment.create(
            chat_id=chat_id,
            room_id=room.id,
            message_id=message_id,
            user_id=user.id,
            card_key=card_key,
            segment_index=segment_index,
            content=ai_content,
            segment_body=segment_body,
            content_type='ai',
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "comment": comment.to_dict(include_user=True),
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to save AI comment: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def _build_ai_reply_context(
    chat: Chat,
    room: Room,
    card_key: str,
    card_header: str,
    card_body: str,
    guiding_question: str = "",
) -> dict:
    """
    Build context dict for AI reply generation.
    
    Includes room goals, chat purpose, card content, recent comments.
    Truncates long content to stay within token budget.
    """
    # Truncate card body if too long
    truncated_body = card_body[:AI_CONTEXT_MAX_CHARS]
    if len(card_body) > AI_CONTEXT_MAX_CHARS:
        truncated_body += "... [truncated]"
    
    # Get recent comments on this card for context (include chat_id for isolation)
    recent_comments = CardComment.query.filter(
        and_(
            CardComment.card_key == card_key,
            CardComment.chat_id == chat.id,  # Extra isolation
            CardComment.deleted_at.is_(None)
        )
    ).order_by(CardComment.created_at.desc()).limit(AI_CONTEXT_MAX_COMMENTS).all()
    
    # Reverse to chronological order
    recent_comments = list(reversed(recent_comments))
    
    # Format comment thread
    comment_thread = []
    for c in recent_comments:
        author = "AI" if c.content_type == 'ai' else (
            c.user.display_name if c.user else "User"
        )
        # Truncate individual comments
        content = c.content[:500] + "..." if len(c.content) > 500 else c.content
        comment_thread.append(f"- {author}: {content}")
    
    return {
        "room_name": room.name,
        "room_goals": getattr(room, 'goals', None) or getattr(room, 'description', '') or "",
        "chat_purpose": chat.purpose if hasattr(chat, 'purpose') and chat.purpose else "",
        "guiding_question": guiding_question,
        "card_header": card_header,
        "card_body": truncated_body,
        "recent_comments": comment_thread,
    }


def _generate_ai_reply(context: dict) -> str:
    """
    Generate AI reply using Anthropic API.
    
    Returns brief, thoughtful comment (1 paragraph or ≤5 bullets).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Build system prompt - more specific with format examples
    system_prompt = """You are a learning assistant adding brief, insightful comments to a discussion.

FORMAT (choose ONE):
A) One paragraph (2-3 sentences max)
B) 2-5 bullet points starting with •

RULES:
• Reference specific content from the card
• Either ask ONE follow-up question OR share ONE new insight (not both)
• Never summarize or repeat what was said
• Skip pleasantries ("Great point!", "Interesting!")
• Be direct and substantive

EXAMPLE GOOD RESPONSES:
"The distinction between X and Y raises an important question: how might this apply when Z?"
"• This connects to the broader concept of A\n• Consider the implication for B\n• What happens when C is true?"

EXAMPLE BAD RESPONSES:
"Great observation! This is really interesting. Let me share some thoughts..." (too fluffy)
"In summary, the card discusses..." (summarizing)"""

    # Build user prompt with trimmed context
    parts = []
    total_chars = 0
    max_context_chars = 2500  # Keep prompt under ~700 tokens
    
    # Add room/chat context (low priority, trim first)
    if context.get("room_goals") and total_chars < max_context_chars:
        room_goals = context['room_goals'][:200]
        parts.append(f"Room: {room_goals}")
        total_chars += len(room_goals)
    
    if context.get("chat_purpose") and total_chars < max_context_chars:
        chat_purpose = context['chat_purpose'][:150]
        parts.append(f"Discussion: {chat_purpose}")
        total_chars += len(chat_purpose)
    
    # Add guiding question (medium priority)
    if context.get("guiding_question"):
        parts.append(f"Guiding question: {context['guiding_question'][:200]}")
        total_chars += 200
    
    # Add card content (high priority - always include)
    parts.append("\n--- Card ---")
    if context.get("card_header"):
        parts.append(f"Topic: {context['card_header'][:100]}")
    
    # Trim card body to fit budget
    remaining_chars = max(500, max_context_chars - total_chars - 300)
    card_body = context.get('card_body', '')[:remaining_chars]
    if len(context.get('card_body', '')) > remaining_chars:
        card_body += "..."
    parts.append(card_body)
    
    # Add recent comments (medium-high priority)
    if context.get("recent_comments"):
        parts.append("\n--- Recent comments ---")
        # Only include last 3 comments, trimmed
        for comment in context["recent_comments"][-3:]:
            parts.append(comment[:250])
    
    parts.append("\n--- Reply with ONE brief comment (paragraph or bullets): ---")
    
    user_prompt = "\n".join(parts)
    
    # Call AI
    try:
        from src.utils.openai_utils import call_anthropic_api, call_openai_api
        
        raw_text = None
        
        # Try Anthropic first
        try:
            text, _ = call_anthropic_api(
                messages=[{"role": "user", "content": user_prompt}],
                system_prompt=system_prompt,
                max_tokens=AI_REPLY_MAX_TOKENS,
            )
            if text:
                raw_text = text.strip()
        except Exception as e:
            logger.warning(f"Anthropic call failed for AI reply: {e}")
        
        # Fallback to OpenAI if Anthropic failed
        if not raw_text:
            try:
                text, _ = call_openai_api(
                    messages=[{"role": "user", "content": user_prompt}],
                    system_prompt=system_prompt,
                    max_tokens=AI_REPLY_MAX_TOKENS,
                )
                if text:
                    raw_text = text.strip()
            except Exception as e:
                logger.warning(f"OpenAI fallback failed for AI reply: {e}")
        
        if not raw_text:
            return None
        
        # Post-process: clean up and enforce format
        return _clean_ai_reply(raw_text)
        
    except Exception as e:
        logger.error(f"AI reply generation error: {e}")
        return None


def _clean_ai_reply(text: str) -> str:
    """
    Clean and normalize AI reply format.
    
    - Removes preamble phrases
    - Normalizes bullet markers
    - Trims excessive length
    """
    if not text:
        return text
    
    # Remove common preamble patterns
    preambles = [
        "Here's my comment:",
        "Here is my response:",
        "My response:",
        "Comment:",
        "Here's a brief comment:",
        "I'd like to add:",
    ]
    for preamble in preambles:
        if text.lower().startswith(preamble.lower()):
            text = text[len(preamble):].strip()
    
    # Normalize bullet markers to •
    lines = text.split('\n')
    normalized_lines = []
    for line in lines:
        stripped = line.strip()
        # Convert various bullet markers to •
        if stripped.startswith(('- ', '* ', '– ', '— ')):
            normalized_lines.append('• ' + stripped[2:])
        elif stripped.startswith(('-', '*')) and len(stripped) > 1:
            normalized_lines.append('• ' + stripped[1:].strip())
        else:
            normalized_lines.append(line)
    
    text = '\n'.join(normalized_lines)
    
    # Remove trailing incomplete sentences if response was cut off
    if text and text[-1] not in '.!?•':
        # Find last complete sentence
        last_punct = max(text.rfind('.'), text.rfind('!'), text.rfind('?'))
        if last_punct > len(text) * 0.5:  # Only trim if we keep >50%
            text = text[:last_punct + 1]
    
    return text.strip()


@card_comments_api.route(
    "/chat/<int:chat_id>/cards/<card_key>/comments/<int:comment_id>", 
    methods=["DELETE"]
)
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_POST)  # Same limit as POST to prevent abuse
def delete_comment(chat_id: int, card_key: str, comment_id: int):
    """
    Soft delete a comment.
    
    Allowed for:
    - Comment author
    - Room owner
    
    Returns:
        {
            "success": true,
            "message": "Comment deleted"
        }
    """
    chat, room = _get_chat_context(chat_id)
    user = get_current_user()
    
    # Find comment
    comment = CardComment.query.filter(
        and_(
            CardComment.id == comment_id,
            CardComment.chat_id == chat_id,
            CardComment.card_key == card_key,
            CardComment.deleted_at.is_(None)
        )
    ).first()
    
    if not comment:
        return jsonify({"success": False, "error": "Comment not found"}), 404
    
    # Check permission
    if not _can_delete_comment(user, comment, room):
        return jsonify({"success": False, "error": "Permission denied"}), 403
    
    # Soft delete
    try:
        comment.soft_delete()
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Comment deleted",
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@card_comments_api.route("/chat/<int:chat_id>/cards/<card_key>/comments/count", methods=["GET"])
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_GET)
def comment_count(chat_id: int, card_key: str):
    """
    Get comment count for a card (for displaying badges).
    
    Returns:
        {
            "success": true,
            "count": 5
        }
    """
    count = CardComment.query.filter(
        and_(
            CardComment.chat_id == chat_id,
            CardComment.card_key == card_key,
            CardComment.deleted_at.is_(None)
        )
    ).count()
    
    return jsonify({
        "success": True,
        "count": count,
    })


@card_comments_api.route("/chat/<int:chat_id>/cards/comments/counts", methods=["POST"])
@require_login
@require_chat_access
@limiter.limit(RATE_LIMIT_GET)
def bulk_comment_counts(chat_id: int):
    """
    Get comment counts for multiple cards in one request.
    
    Request JSON:
        {
            "card_keys": ["abc123", "def456", ...]
        }
    
    Returns:
        {
            "success": true,
            "counts": {
                "abc123": 5,
                "def456": 0,
                ...
            }
        }
    """
    data = request.get_json()
    if not data or "card_keys" not in data:
        return jsonify({"success": False, "error": "card_keys required"}), 400
    
    card_keys = data.get("card_keys", [])
    if not isinstance(card_keys, list) or len(card_keys) > 50:
        return jsonify({"success": False, "error": "card_keys must be array (max 50)"}), 400
    
    # Query counts grouped by card_key
    from sqlalchemy import func
    
    results = db.session.query(
        CardComment.card_key,
        func.count(CardComment.id)
    ).filter(
        and_(
            CardComment.chat_id == chat_id,
            CardComment.card_key.in_(card_keys),
            CardComment.deleted_at.is_(None)
        )
    ).group_by(CardComment.card_key).all()
    
    # Build counts dict, defaulting missing keys to 0
    counts = {key: 0 for key in card_keys}
    for card_key, count in results:
        counts[card_key] = count
    
    return jsonify({
        "success": True,
        "counts": counts,
    })

