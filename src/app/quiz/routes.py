"""
Quiz Tool API Routes
Handles quiz generation, grading, and context assembly
"""

from flask import request, jsonify, current_app, session
from functools import wraps
from src.app import db, limiter
from src.app.quiz import quiz
from src.models.quiz import Quiz, QuizAnswer
from src.models.chat import Chat, Message
from src.models.document import Document, DocumentChunk
from src.models.room import Room
from src.app.access_control import get_current_user, require_login, require_chat_access, can_access_room
from src.models.user import User
from src.utils.openai_utils import call_anthropic_api
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import json
import os


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


def assemble_quiz_context(chat_id: int, context_mode: str, library_doc_ids: Optional[List[int]] = None) -> str:
    """Assemble context based on mode (chat, library, or both)."""
    context_parts = []
    
    if context_mode in ('chat', 'both'):
        chat_context = assemble_chat_context(chat_id, limit=20)
        if chat_context:
            context_parts.append("=== CHAT CONVERSATION ===\n" + chat_context)
    
    if context_mode in ('library', 'both'):
        if library_doc_ids:
            library_context = assemble_library_context(library_doc_ids, max_chars=10000)
            if library_context:
                context_parts.append("=== LIBRARY DOCUMENTS ===\n" + library_context)
    
    return "\n\n".join(context_parts)


def generate_quiz_prompt(context: str, question_count: int, instructions: Optional[str] = None) -> str:
    """Generate the prompt for quiz generation."""
    base_prompt = f"""You are an expert educator creating multiple-choice questions for assessment.

CONTEXT MATERIAL:
{context}

TASK:
Generate exactly {question_count} high-quality multiple-choice questions based on the context material above.

REQUIREMENTS:
1. Each question must have exactly ONE correct answer
2. Each question must have 3-5 answer choices (preferably 4-5)
3. Questions should test understanding, not just recall
4. Distractors (wrong answers) should be plausible but clearly incorrect
5. Questions should be unambiguous and clearly worded
6. Include a brief explanation (1-2 sentences) for why the correct answer is correct

INSTRUCTIONS:
{instructions if instructions else "Focus on key concepts and important details from the context."}

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "id": 1,
      "text": "Question text here?",
      "choices": [
        "Choice A",
        "Choice B",
        "Choice C",
        "Choice D"
      ],
      "correct_answer": 0,
      "explanation": "Brief explanation of why this answer is correct"
    }}
  ]
}}

Return ONLY valid JSON, no additional text before or after."""

    return base_prompt


@quiz.route('/generate', methods=['POST'])
@login_required
@limiter.limit("10 per minute; 50 per hour")
def generate_quiz():
    """Generate a quiz based on chat and/or library context."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Validate required fields
        chat_id = data.get('chat_id')
        question_count = data.get('question_count', 5)
        context_mode = data.get('context_mode', 'chat')  # 'chat', 'library', 'both'
        library_doc_ids = data.get('library_doc_ids', [])
        instructions = data.get('instructions', '').strip()
        
        if not chat_id:
            return jsonify({'error': 'chat_id is required'}), 400
        
        # Validate question_count
        if not isinstance(question_count, int) or question_count < 1 or question_count > 20:
            return jsonify({'error': 'question_count must be between 1 and 20'}), 400
        
        # Validate context_mode
        if context_mode not in ('chat', 'library', 'both'):
            return jsonify({'error': 'context_mode must be "chat", "library", or "both"'}), 400
        
        # Check chat access
        chat_obj = Chat.query.get(chat_id)
        if not chat_obj:
            return jsonify({'error': 'Chat not found'}), 404
        
        # Get room object for access check
        room_obj = Room.query.get(chat_obj.room_id)
        if not room_obj:
            return jsonify({'error': 'Room not found'}), 404
        
        if not can_access_room(user, room_obj):
            return jsonify({'error': 'Access denied'}), 403
        
        # Validate library access if needed
        if context_mode in ('library', 'both'):
            if not library_doc_ids:
                if context_mode == 'library':
                    return jsonify({'error': 'At least one library document is required when context_mode is "library"'}), 400
            else:
                # Verify user has access to all documents
                docs = Document.query.filter(
                    Document.id.in_(library_doc_ids),
                    Document.room_id == chat_obj.room_id
                ).all()
                if len(docs) != len(library_doc_ids):
                    return jsonify({'error': 'One or more documents not found or access denied'}), 403
        
        # Assemble context
        context = assemble_quiz_context(chat_id, context_mode, library_doc_ids)
        
        if not context.strip():
            return jsonify({'error': 'No context available. Please ensure chat has messages or library documents are selected.'}), 400
        
        # Generate quiz prompt
        prompt = generate_quiz_prompt(context, question_count, instructions)
        
        # Call AI to generate quiz
        current_app.logger.info(f"Generating quiz for chat {chat_id}, {question_count} questions")
        
        try:
            # call_anthropic_api returns (text, is_truncated) tuple
            text_content, is_truncated = call_anthropic_api(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert educator creating multiple-choice questions for assessment.",
                max_tokens=4000
            )
            
            if not text_content or not text_content.strip():
                raise ValueError("Empty response from AI")
            
            # Extract JSON from response (handle markdown code blocks)
            json_start = text_content.find('{')
            json_end = text_content.rfind('}') + 1
            if json_start == -1 or json_end == 0:
                raise ValueError("No JSON found in response")
            
            json_text = text_content[json_start:json_end]
            quiz_data = json.loads(json_text)
            
            if is_truncated:
                current_app.logger.warning(f"Quiz generation response was truncated")
            
            questions = quiz_data.get('questions', [])
            if len(questions) != question_count:
                current_app.logger.warning(
                    f"Expected {question_count} questions, got {len(questions)}"
                )
            
            # Validate questions structure
            for i, q in enumerate(questions):
                if 'text' not in q or 'choices' not in q or 'correct_answer' not in q:
                    raise ValueError(f"Invalid question structure at index {i}")
                if not isinstance(q['correct_answer'], int):
                    raise ValueError(f"correct_answer must be integer at index {i}")
                if q['correct_answer'] < 0 or q['correct_answer'] >= len(q['choices']):
                    raise ValueError(f"correct_answer out of range at index {i}")
            
            # Store quiz in database
            quiz_obj = Quiz(
                chat_id=chat_id,
                room_id=chat_obj.room_id,
                created_by=user.id,
                question_count=len(questions),
                context_mode=context_mode,
                library_doc_ids=library_doc_ids if library_doc_ids else None,
                instructions=instructions if instructions else None,
                questions=questions
            )
            db.session.add(quiz_obj)
            db.session.commit()
            
            # Return quiz without correct answers
            return jsonify({
                'success': True,
                'quiz': quiz_obj.to_dict(include_answers=False),
                'quiz_id': quiz_obj.id
            }), 200
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON decode error: {e}")
            return jsonify({'error': 'Failed to parse quiz response from AI'}), 500
        except Exception as e:
            current_app.logger.error(f"AI generation error: {e}")
            return jsonify({'error': f'Failed to generate quiz: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Quiz generation error: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to generate quiz: {str(e)}'}), 500


@quiz.route('/<int:quiz_id>/grade', methods=['POST'])
@login_required
@limiter.limit("20 per minute; 200 per hour")
def grade_quiz(quiz_id: int):
    """Grade a quiz submission."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        quiz_obj = Quiz.query.get(quiz_id)
        if not quiz_obj:
            return jsonify({'error': 'Quiz not found'}), 404
        
        # Check access - get room object
        room_obj = Room.query.get(quiz_obj.room_id)
        if not room_obj:
            return jsonify({'error': 'Room not found'}), 404
        
        if not can_access_room(user, room_obj):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json() or {}
        answers = data.get('answers', {})  # {question_id: choice_index}
        
        if not answers:
            return jsonify({'error': 'Answers are required'}), 400
        
        # Grade answers
        questions = quiz_obj.questions
        results = []
        score = 0
        total = len(questions)
        
        for q in questions:
            q_id = q.get('id')
            user_answer = answers.get(str(q_id)) or answers.get(q_id)
            correct_answer = q.get('correct_answer')
            
            is_correct = user_answer == correct_answer
            
            if is_correct:
                score += 1
            
            results.append({
                'question_id': q_id,
                'question_text': q.get('text'),
                'user_answer': user_answer,
                'correct_answer': correct_answer,
                'is_correct': is_correct,
                'explanation': q.get('explanation', '')
            })
        
        # Store answer record
        answer_obj = QuizAnswer(
            quiz_id=quiz_id,
            user_id=user.id,
            answers=answers,
            score=score,
            total=total,
            results=results,
            graded_at=datetime.now(timezone.utc)
        )
        db.session.add(answer_obj)
        
        # Mark quiz as completed if not already
        if not quiz_obj.completed_at:
            quiz_obj.completed_at = datetime.now(timezone.utc)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'total': total,
            'results': results,
            'answer_id': answer_obj.id
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Quiz grading error: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to grade quiz: {str(e)}'}), 500


@quiz.route('/<int:quiz_id>', methods=['GET'])
@login_required
def get_quiz(quiz_id: int):
    """Get quiz details (without correct answers)."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        quiz_obj = Quiz.query.get(quiz_id)
        if not quiz_obj:
            return jsonify({'error': 'Quiz not found'}), 404
        
        # Check access - get room object
        room_obj = Room.query.get(quiz_obj.room_id)
        if not room_obj:
            return jsonify({'error': 'Room not found'}), 404
        
        if not can_access_room(user, room_obj):
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'success': True,
            'quiz': quiz_obj.to_dict(include_answers=False)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get quiz error: {e}")
        return jsonify({'error': f'Failed to get quiz: {str(e)}'}), 500

