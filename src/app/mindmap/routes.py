"""
Mind Map Tool API Routes
Handles mind map generation with hierarchical tree structure
"""

from flask import request, jsonify, current_app, session
from functools import wraps
from src.app import db, limiter
from src.app.mindmap import mindmap
from src.models.mindmap import MindMap
from src.models.chat import Chat, Message
from src.models.document import Document
from src.models.room import Room
from src.app.access_control import get_current_user, can_access_room
from src.models.user import User
from src.utils.openai_utils import call_anthropic_api
from typing import Dict, List, Optional
from datetime import datetime, timezone
import json


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


def assemble_mindmap_context(context_mode: str, chat_id: Optional[int] = None, library_doc_ids: Optional[List[int]] = None) -> Dict[str, Optional[str]]:
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


def get_node_count_for_size(size: str) -> int:
    """Get target node count based on size."""
    if size == 'small':
        return 6  # 1 root + 5 branches (target 5-8 total)
    elif size == 'medium':
        return 12  # 1 root + 11 branches (target 10-15 total)
    elif size == 'large':
        return 25  # 1 root + 24 branches (target 20-30 total)
    else:
        return 12  # default to medium


def generate_mindmap_prompt(context_parts: Dict[str, Optional[str]], context_mode: str, node_count: int, instructions: Optional[str] = None) -> str:
    """Generate the prompt for mind map generation."""
    
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
    
    base_prompt = f"""You are creating a hierarchical mind map visualization.

STRICT CONTEXT BOUNDARY:
{context_instruction}

{context_section}

TASK:
Generate a hierarchical mind map with approximately {node_count} total nodes based on the context material above.

MIND MAP STRUCTURE:
- The mind map should have a ROOT node (central topic) that represents the main subject
- Primary branches should radiate from the root, representing major themes/concepts
- Secondary branches should connect to primary branches, representing sub-concepts
- The structure should be hierarchical (tree-like), not a flat list
- Aim for 2-3 levels of depth (root → primary branches → secondary branches)

NODE REQUIREMENTS:
- Each node must have:
  1. A short LABEL (1-4 words) - this will be displayed on the node
  2. A brief EXPLANATION (1 paragraph maximum) - this will appear when users hover over the node
- Labels should be concise and clear
- Explanations should be informative, drawing from the provided context
- Do not invent information not present in the context

ADDITIONAL INSTRUCTIONS:
{instructions if instructions else "Focus on key concepts and important relationships from the context. Organize hierarchically with the most important concept as the root."}

OUTPUT FORMAT (JSON):
{{
  "root": {{
    "id": "root",
    "label": "Main Topic Name",
    "explanation": "Brief explanation of the main topic (1 paragraph max)..."
  }},
  "nodes": [
    {{
      "id": "node1",
      "label": "Primary Branch 1",
      "explanation": "Brief explanation of this branch (1 paragraph max)...",
      "parent": "root",
      "children": [
        {{
          "id": "node1-1",
          "label": "Sub-branch 1",
          "explanation": "Brief explanation (1 paragraph max)...",
          "parent": "node1"
        }},
        {{
          "id": "node1-2",
          "label": "Sub-branch 2",
          "explanation": "Brief explanation (1 paragraph max)...",
          "parent": "node1"
        }}
      ]
    }},
    {{
      "id": "node2",
      "label": "Primary Branch 2",
      "explanation": "Brief explanation (1 paragraph max)...",
      "parent": "root",
      "children": []
    }}
  ]
}}

IMPORTANT:
- The root node has no parent
- All other nodes must have a parent ID
- Children arrays can be empty for leaf nodes
- Ensure the total node count (1 root + all nodes) is approximately {node_count}
- Each explanation must be 1 paragraph maximum

Return ONLY valid JSON, no additional text before or after."""

    return base_prompt


@mindmap.route('/generate', methods=['POST'])
@login_required
@limiter.limit("10 per minute; 50 per hour")
def generate_mindmap():
    """Generate a mind map based on chat and/or library context."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Validate required fields
        chat_id = data.get('chat_id')
        context_mode = data.get('context_mode', 'chat')
        size = data.get('size', 'medium')
        library_doc_ids = data.get('library_doc_ids', [])
        instructions = data.get('instructions', '').strip()
        
        if not chat_id:
            return jsonify({'error': 'chat_id is required'}), 400
        
        if context_mode not in ('chat', 'library', 'both'):
            return jsonify({'error': 'context_mode must be "chat", "library", or "both"'}), 400
        
        if size not in ('small', 'medium', 'large'):
            return jsonify({'error': 'size must be "small", "medium", or "large"'}), 400
        
        # Check chat access
        chat_obj = Chat.query.get(chat_id)
        if not chat_obj:
            return jsonify({'error': 'Chat not found'}), 404
        
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
                docs = Document.query.filter(
                    Document.id.in_(library_doc_ids),
                    Document.room_id == chat_obj.room_id
                ).all()
                if len(docs) != len(library_doc_ids):
                    return jsonify({'error': 'One or more documents not found or access denied'}), 403
        
        # Assemble context with strict boundaries
        context_parts = assemble_mindmap_context(context_mode, chat_id, library_doc_ids)
        
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
                'error': 'No context available. Please ensure chat has messages or library documents are selected.'
            }), 400
        
        # Get target node count
        node_count = get_node_count_for_size(size)
        
        # Generate mind map
        current_app.logger.info(f"Generating mind map for chat {chat_id}, size: {size}, nodes: {node_count}")
        
        try:
            # Generate prompt
            prompt = generate_mindmap_prompt(context_parts, context_mode, node_count, instructions)
            
            # Call AI
            text_content, is_truncated = call_anthropic_api(
                messages=[{"role": "user", "content": prompt}],
                system_prompt="You are an expert at creating hierarchical mind maps. Follow all instructions strictly and return only valid JSON.",
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
            mindmap_data = json.loads(json_text)
            
            # Validate structure
            if 'root' not in mindmap_data:
                raise ValueError("Missing 'root' in response")
            
            if 'nodes' not in mindmap_data:
                mindmap_data['nodes'] = []
            
            root = mindmap_data['root']
            if 'id' not in root or 'label' not in root or 'explanation' not in root:
                raise ValueError("Root node missing required fields (id, label, explanation)")
            
            # Validate nodes
            for node in mindmap_data['nodes']:
                if 'id' not in node or 'label' not in node or 'explanation' not in node or 'parent' not in node:
                    raise ValueError(f"Node missing required fields: {node.get('id', 'unknown')}")
                if 'children' not in node:
                    node['children'] = []
            
            # Store mind map
            mindmap_obj = MindMap(
                chat_id=chat_id,
                room_id=chat_obj.room_id,
                created_by=user.id,
                context_mode=context_mode,
                library_doc_ids=library_doc_ids if library_doc_ids else None,
                instructions=instructions if instructions else None,
                size=size,
                mind_map_data=mindmap_data
            )
            db.session.add(mindmap_obj)
            db.session.commit()
            
            # Return mind map data
            return jsonify({
                'success': True,
                'mind_map': mindmap_obj.to_dict()
            }), 200
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON decode error: {e}")
            return jsonify({'error': 'Failed to parse mind map response from AI'}), 500
        except Exception as e:
            current_app.logger.error(f"AI generation error: {e}")
            return jsonify({'error': f'Failed to generate mind map: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Mind map generation error: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to generate mind map: {str(e)}'}), 500
