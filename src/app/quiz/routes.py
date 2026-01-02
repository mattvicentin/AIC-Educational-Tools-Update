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


def calculate_mixed_distribution(question_count: int) -> Dict[str, int]:
    """Calculate Easy/Average/Hard distribution for Mixed difficulty."""
    if question_count == 1:
        return {'easy': 0, 'average': 1, 'hard': 0}
    elif question_count == 2:
        return {'easy': 1, 'average': 1, 'hard': 0}
    
    # Calculate percentages
    easy_count = max(1 if question_count >= 5 else 0, round(question_count * 0.2))
    hard_count = max(1 if question_count >= 5 else 0, round(question_count * 0.2))
    average_count = question_count - easy_count - hard_count
    
    # Ensure at least 1 average if >= 3 questions
    if question_count >= 3 and average_count < 1:
        if easy_count > 0:
            easy_count -= 1
        elif hard_count > 0:
            hard_count -= 1
        average_count = question_count - easy_count - hard_count
    
    return {'easy': easy_count, 'average': average_count, 'hard': hard_count}


def generate_quiz_prompt(context: str, question_count: int, difficulty: str = 'average', instructions: Optional[str] = None) -> str:
    """Generate the prompt for quiz generation."""
    
    # Build difficulty-specific instructions
    difficulty_instructions = ""
    
    if difficulty == 'easy':
        difficulty_instructions = """
DIFFICULTY LEVEL: EASY

Question Characteristics:
- Knowledge Depth: Focus on direct recall or basic recognition
- Question Type: Definitions, facts, straightforward multiple choice, true/false
- Distractors: Obviously incorrect options that are clearly wrong
- Wording: Use clear, simple, direct language
- Assumptions: None - questions should be self-contained
- Time to Solve: Very short - questions should be answerable quickly

Guidelines:
- Ask "what is" or "which of the following" questions
- Use simple vocabulary and sentence structure
- Make correct answer clearly distinguishable from distractors
- Avoid trick wording, abstraction, or hidden assumptions
- Focus on basic facts and definitions from the context
"""
    elif difficulty == 'average':
        difficulty_instructions = """
DIFFICULTY LEVEL: AVERAGE

Question Characteristics:
- Knowledge Depth: Require conceptual understanding or application
- Question Type: Application scenarios, comparisons, identifying consequences or implications
- Distractors: Plausible but incorrect options that require some thought to eliminate
- Wording: Moderately indirect - may require some interpretation
- Assumptions: One assumption may be required
- Time to Solve: Moderate - questions require 1-2 reasoning steps

Guidelines:
- Ask "how would you apply" or "what would happen if" questions
- Require connecting concepts to scenarios
- Use moderately complex vocabulary appropriate for the subject
- Distractors should seem reasonable but be incorrect upon closer examination
- Include light contextual framing
"""
    elif difficulty == 'hard':
        difficulty_instructions = """
DIFFICULTY LEVEL: HARD

Question Characteristics:
- Knowledge Depth: Require multi-step reasoning, synthesis, or evaluation
- Question Type: Edge cases, conceptual traps, questions where multiple answers seem correct initially
- Distractors: Very subtle, high-quality distractors that require deep understanding to eliminate
- Wording: Dense or abstract phrasing that requires careful reading
- Assumptions: Multiple assumptions may be required
- Time to Solve: Long - questions require careful, multi-step reasoning

Guidelines:
- Ask "evaluate", "synthesize", or "analyze" questions
- Combine multiple concepts in a single question
- Use sophisticated vocabulary and abstract concepts
- Distractors should be very subtle and require strong prior knowledge to eliminate
- Assume strong background knowledge
- May involve edge cases or nuanced distinctions
"""
    elif difficulty == 'mixed':
        distribution = calculate_mixed_distribution(question_count)
        difficulty_instructions = f"""
DIFFICULTY LEVEL: MIXED

Generate a balanced set of questions with the following distribution:
- {distribution['easy']} Easy question(s): Direct recall, simple language, obviously wrong distractors
- {distribution['average']} Average question(s): Conceptual understanding, plausible distractors, 1-2 reasoning steps
- {distribution['hard']} Hard question(s): Multi-step reasoning, subtle distractors, abstract phrasing

Mix the difficulty levels throughout the quiz. Label each question's difficulty in your thinking, but present them in a natural order.
"""
    
    base_prompt = f"""You are an expert educator creating multiple-choice questions for assessment.

CONTEXT MATERIAL:
{context}

TASK:
Generate exactly {question_count} high-quality multiple-choice questions based on the context material above.

{difficulty_instructions}

REQUIREMENTS:
1. Each question must have exactly ONE correct answer
2. Each question must have 3-5 answer choices (preferably 4-5)
3. Questions should test understanding appropriate to the difficulty level
4. Distractors (wrong answers) should match the difficulty level characteristics
5. Questions should be unambiguous and clearly worded for their difficulty level
6. Include a brief explanation (1-2 sentences) for why the correct answer is correct

ADDITIONAL INSTRUCTIONS:
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
        difficulty = data.get('difficulty', 'average')  # 'easy', 'average', 'hard', 'mixed'
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
        
        # Validate difficulty
        if difficulty not in ('easy', 'average', 'hard', 'mixed'):
            return jsonify({'error': 'difficulty must be "easy", "average", "hard", or "mixed"'}), 400
        
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
        prompt = generate_quiz_prompt(context, question_count, difficulty, instructions)
        
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
                difficulty=difficulty,
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

