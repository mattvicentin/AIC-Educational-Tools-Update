"""
Narrative Tool API Routes
Handles narrative generation with Linear and Interactive modes
"""

from flask import request, jsonify, current_app, session
from functools import wraps
from src.app import db, limiter
from src.app.narrative import narrative
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


def assemble_narrative_context(context_mode: str, chat_id: Optional[int] = None, library_doc_ids: Optional[List[int]] = None) -> Dict[str, Optional[str]]:
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


def get_reflection_prompts() -> Dict[str, str]:
    """Get hard-coded reflection prompts for different narrative types."""
    return {
        'linear': (
            "Reflect on the narrative you just read. What concepts from the course materials did you recognize? "
            "How did the story help you understand these concepts? Can you think of real-world situations where these concepts apply?"
        ),
        'interactive': (
            "Reflect on your experience with this interactive narrative. What decisions did you make and why? "
            "How did your choices connect to the concepts from the course materials? What would have happened differently "
            "if you had made other choices? How does this relate to real-world decision-making?"
        )
    }


def generate_linear_narrative_prompt(context_parts: Dict[str, Optional[str]], context_mode: str, instructions: Optional[str] = None) -> str:
    """Generate the prompt for linear narrative generation."""
    
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
    
    base_prompt = f"""You are an expert at creating educational narratives that help students build conceptual understanding and transfer knowledge.

STRICT CONTEXT BOUNDARY:
{context_instruction}

{context_section}

TASK:
Create a fictional narrative that is grounded in the course materials provided above. The narrative should:
- Help students understand key concepts from the materials through storytelling
- Present concepts in a relatable, engaging way
- Allow students to see how concepts apply in narrative contexts
- Be appropriate length for reading (let the content determine the optimal length, but aim for a complete, meaningful story)

NARRATIVE REQUIREMENTS:
- The story should be a complete, self-contained narrative
- Ground all concepts, examples, and situations in the provided context materials
- Do not introduce concepts or information not present in the context
- Write in a clear, engaging style appropriate for educational purposes
- Focus on conceptual understanding rather than just facts
- No reflection prompts or questions should appear within the narrative itself

ADDITIONAL INSTRUCTIONS:
{instructions if instructions else "Create a narrative that effectively illustrates the key concepts from the course materials."}

Return ONLY the narrative text, no additional commentary, no reflection questions, no meta-text. Just the story itself."""

    return base_prompt


def generate_interactive_narrative_prompt(context_parts: Dict[str, Optional[str]], context_mode: str, complexity: str, instructions: Optional[str] = None) -> str:
    """Generate the prompt for interactive narrative generation."""
    
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
    
    # Complexity constraints
    complexity_constraints = {
        'explanation': {
            'choices_per_node': 2,
            'min_chars': 2000,
            'min_nodes': 5,
            'min_chars_per_node': 200,
            'description': 'Few choices, explicit explanations'
        },
        'simulation': {
            'choices_per_node': 3,
            'min_chars': 4000,
            'min_nodes': 8,
            'min_chars_per_node': 300,
            'description': 'Multiple trade-offs, delayed consequences'
        },
        'challenge': {
            'choices_per_node': 4,
            'min_chars': 6000,
            'min_nodes': 12,
            'min_chars_per_node': 400,
            'description': 'Conflicting goals, minimal guidance'
        }
    }
    
    constraints = complexity_constraints.get(complexity, complexity_constraints['explanation'])
    
    base_prompt = f"""You are an expert at creating interactive educational narratives that help students build conceptual understanding through decision-making.

STRICT CONTEXT BOUNDARY:
{context_instruction}

{context_section}

TASK:
Create an interactive narrative where the learner makes choices that affect the story. The narrative should:
- Help students understand key concepts from the materials through interactive storytelling
- Present decision points that connect to course concepts
- Show consequences of different choices
- Have multiple possible endings based on different choice paths
- Be grounded entirely in the provided context materials

COMPLEXITY LEVEL: {complexity.upper()}
- Choices per decision point: {constraints['choices_per_node']}
- Minimum total length: {constraints['min_chars']} characters across ALL nodes
- Minimum number of nodes: {constraints['min_nodes']} nodes (including start and endings)
- Minimum content per node: {constraints['min_chars_per_node']} characters
- Style: {constraints['description']}
- Story depth: More complex = deeper story with more interconnected decision points and longer content

INTERACTIVE NARRATIVE STRUCTURE:
- Start with an initial node that sets up the story (at least {constraints['min_chars_per_node']} characters)
- CRITICAL: Create AT LEAST {constraints['min_nodes']} total nodes to ensure sufficient depth and complexity
- IMPORTANT: Count your nodes carefully - you need {constraints['min_nodes']} nodes minimum (including start node and all endings)
- Each node (except endings) must have exactly {constraints['choices_per_node']} choices
- Choices should connect to concepts from the course materials and present meaningful dilemmas
- Create multiple interconnected paths that lead to different endings (at least 3-4 different endings for Challenge, 2-3 for others)
- Each ending should reflect different outcomes based on choices made and be substantial (at least {constraints['min_chars_per_node']} characters)
- The total narrative should be at least {constraints['min_chars']} characters across all nodes
- For Challenge level: Create deeper branching with 3-4 decision points before reaching endings, showing how early choices affect later outcomes
- TIP: To reach {constraints['min_nodes']} nodes, plan your structure: 1 start + multiple decision nodes + multiple endings = {constraints['min_nodes']}+ total

NODE REQUIREMENTS:
- Each node must have: id, content (story text), choices array, isEnding flag
- Each choice must have: id, text (choice description), nextNode (id of next node)
- Ending nodes have empty choices array and isEnding: true
- Content should be substantial (minimum {constraints['min_chars_per_node']} characters per node) to advance the story meaningfully
- Choices should be meaningful, present real dilemmas, and connect to course concepts
- For Challenge level: Choices should present conflicting goals where no option is clearly "best"
- Each node's content should be rich enough to immerse the learner in the scenario

ADDITIONAL INSTRUCTIONS:
{instructions if instructions else "Create an interactive narrative that effectively illustrates key concepts through decision-making scenarios."}

OUTPUT FORMAT (JSON):
{{
  "nodes": [
    {{
      "id": "start",
      "content": "Story text that sets up the scenario...",
      "choices": [
        {{"id": "choice1", "text": "Choice 1 description", "nextNode": "node1"}},
        {{"id": "choice2", "text": "Choice 2 description", "nextNode": "node2"}}
      ],
      "isEnding": false
    }},
    {{
      "id": "node1",
      "content": "Story continues based on choice 1...",
      "choices": [
        {{"id": "choice3", "text": "Next choice 1", "nextNode": "ending1"}},
        {{"id": "choice4", "text": "Next choice 2", "nextNode": "ending2"}}
      ],
      "isEnding": false
    }},
    {{
      "id": "ending1",
      "content": "Ending text based on path taken...",
      "choices": [],
      "isEnding": true
    }}
  ],
  "startNodeId": "start"
}}

CRITICAL REQUIREMENTS:
- Generate the COMPLETE narrative tree upfront (all nodes, all paths, all endings)
- NODE COUNT: Create AT LEAST {constraints['min_nodes']} total nodes (this is mandatory - count them before responding!)
- To reach {constraints['min_nodes']} nodes: Plan 1 start node + multiple decision nodes (each with {constraints['choices_per_node']} choices) + multiple endings
- Example structure for {constraints['min_nodes']} nodes: Start (1) → Decision nodes (6-8) → Endings (3-4) = {constraints['min_nodes']}+ total
- Ensure minimum character count of {constraints['min_chars']} characters total across ALL nodes
- Each non-ending node must have exactly {constraints['choices_per_node']} choices
- Each node's content must be at least {constraints['min_chars_per_node']} characters (longer is better, especially for Challenge level)
- Create multiple endings: at least 3-4 different endings for Challenge level, 2-3 for Simulation, 2 for Explanation
- For Challenge level: Ensure there are multiple decision points (at least 3-4 choices before reaching any ending) to show how decisions compound
- All content must be grounded in the provided context materials
- For Challenge level: Make choices more nuanced - avoid obvious "good vs bad" options; instead present trade-offs where each choice has meaningful consequences

NODE REFERENCE VALIDATION:
- EVERY choice's "nextNode" field MUST reference a node ID that exists in your "nodes" array
- Before finalizing your response, verify that every "nextNode" value matches an actual node "id"
- Do NOT create choices that reference nodes that don't exist
- All node IDs must be unique strings (use descriptive names like "node1", "ending1", "path_a", etc.)
- The "startNodeId" must match one of the node IDs in your "nodes" array

OUTPUT FORMAT (JSON):
{{
  "nodes": [
    {{
      "id": "start",
      "content": "Story text that sets up the scenario...",
      "choices": [
        {{"id": "choice1", "text": "Choice 1 description", "nextNode": "node1"}},
        {{"id": "choice2", "text": "Choice 2 description", "nextNode": "node2"}}
      ],
      "isEnding": false
    }},
    {{
      "id": "node1",
      "content": "Story continues based on choice 1...",
      "choices": [
        {{"id": "choice3", "text": "Next choice 1", "nextNode": "ending1"}},
        {{"id": "choice4", "text": "Next choice 2", "nextNode": "ending2"}}
      ],
      "isEnding": false
    }},
    {{
      "id": "ending1",
      "content": "Ending text based on path taken...",
      "choices": [],
      "isEnding": true
    }}
  ],
  "startNodeId": "start"
}}

VALIDATION CHECKLIST (verify before responding):
1. All node IDs are unique
2. Every "nextNode" in choices references an existing node ID
3. "startNodeId" exists in the nodes array
4. Total number of nodes is at least {constraints['min_nodes']}
5. All non-ending nodes have exactly {constraints['choices_per_node']} choices
6. All ending nodes have empty choices arrays and isEnding: true
7. Each node's content is at least {constraints['min_chars_per_node']} characters
8. Total content length meets minimum of {constraints['min_chars']} characters across all nodes
9. For Challenge level: There are at least 3-4 decision points (non-ending nodes) before reaching any ending
10. Multiple endings exist (3-4 for Challenge, 2-3 for Simulation, 2 for Explanation)

Return ONLY valid JSON, no additional text before or after"""

    return base_prompt


@narrative.route('/generate', methods=['POST'])
@login_required
@limiter.limit("10 per minute; 50 per hour")
def generate_narrative():
    """Generate a narrative (Linear or Interactive) based on chat and/or library context."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Validate required fields
        chat_id = data.get('chat_id')
        narrative_type = data.get('narrative_type')
        context_mode = data.get('context_mode', 'chat')
        library_doc_ids = data.get('library_doc_ids', [])
        instructions = data.get('instructions', '').strip()
        complexity = data.get('complexity')
        
        if not chat_id:
            return jsonify({'error': 'chat_id is required'}), 400
        
        if not narrative_type or narrative_type not in ('linear', 'interactive'):
            return jsonify({'error': 'narrative_type must be "linear" or "interactive"'}), 400
        
        if context_mode not in ('chat', 'library', 'both'):
            return jsonify({'error': 'context_mode must be "chat", "library", or "both"'}), 400
        
        # Validate complexity for interactive narratives
        if narrative_type == 'interactive':
            if not complexity or complexity not in ('explanation', 'simulation', 'challenge'):
                return jsonify({'error': 'complexity is required for interactive narratives and must be "explanation", "simulation", or "challenge"'}), 400
            
            # Define complexity constraints for validation (needed in this scope)
            complexity_constraints = {
                'explanation': {
                    'choices_per_node': 2,
                    'min_chars': 2000,
                    'min_nodes': 5,
                    'min_chars_per_node': 200,
                    'description': 'Few choices, explicit explanations'
                },
                'simulation': {
                    'choices_per_node': 3,
                    'min_chars': 4000,
                    'min_nodes': 8,
                    'min_chars_per_node': 300,
                    'description': 'Multiple trade-offs, delayed consequences'
                },
                'challenge': {
                    'choices_per_node': 4,
                    'min_chars': 6000,
                    'min_nodes': 12,
                    'min_chars_per_node': 400,
                    'description': 'Conflicting goals, minimal guidance'
                }
            }
        
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
        context_parts = assemble_narrative_context(context_mode, chat_id, library_doc_ids)
        
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
        
        # Generate narrative
        current_app.logger.info(f"Generating {narrative_type} narrative for chat {chat_id}, complexity: {complexity}")
        
        try:
            if narrative_type == 'linear':
                # Generate linear narrative prompt
                prompt = generate_linear_narrative_prompt(context_parts, context_mode, instructions)
                
                # Call AI
                text_content, is_truncated = call_anthropic_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_prompt="You are an expert at creating educational narratives. Follow all instructions strictly and return only the narrative text.",
                    max_tokens=4000
                )
                
                if not text_content or not text_content.strip():
                    raise ValueError("Empty response from AI")
                
                # Return linear narrative
                return jsonify({
                    'success': True,
                    'narrative_type': 'linear',
                    'narrative': text_content.strip()
                }), 200
                
            else:  # interactive
                # Define complexity constraints for validation (needed in this scope)
                complexity_constraints = {
                    'explanation': {
                        'choices_per_node': 2,
                        'min_chars': 2000,
                        'min_nodes': 5,
                        'min_chars_per_node': 200,
                        'description': 'Few choices, explicit explanations'
                    },
                    'simulation': {
                        'choices_per_node': 3,
                        'min_chars': 4000,
                        'min_nodes': 8,
                        'min_chars_per_node': 300,
                        'description': 'Multiple trade-offs, delayed consequences'
                    },
                    'challenge': {
                        'choices_per_node': 4,
                        'min_chars': 6000,
                        'min_nodes': 12,
                        'min_chars_per_node': 400,
                        'description': 'Conflicting goals, minimal guidance'
                    }
                }
                # Get constraints for validation
                constraints = complexity_constraints.get(complexity, complexity_constraints['explanation'])
                
                # Generate interactive narrative prompt
                prompt = generate_interactive_narrative_prompt(context_parts, context_mode, complexity, instructions)
                
                # Retry logic for interactive narratives (they're more complex and prone to validation errors)
                max_retries = 2
                narrative_data = None
                last_error = None
                
                for attempt in range(max_retries + 1):
                    try:
                        # Call AI
                        text_content, is_truncated = call_anthropic_api(
                            messages=[{"role": "user", "content": prompt}],
                            system_prompt="""You are an expert at creating interactive educational narratives. 

CRITICAL VALIDATION REQUIREMENTS:
1. FIRST: Create ALL nodes with unique IDs before writing any choices
2. THEN: Write choices, ensuring every "nextNode" references an EXISTING node ID from your nodes list
3. VERIFY: Before responding, check that every "nextNode" in every choice matches an actual node "id" exactly
4. The "startNodeId" must match one of your node IDs exactly

STEP-BY-STEP PROCESS:
Step 1: List all nodes you will create (with their IDs)
Step 2: Create the nodes array with all nodes
Step 3: Add choices to each node, referencing ONLY the node IDs from Step 1
Step 4: Verify all references match before returning

Return ONLY valid JSON that passes these validation checks. Double-check all node references before responding.""",
                            max_tokens=8192  # Maximum supported by current Claude models (claude-3-5-sonnet/haiku)
                        )
                        
                        if not text_content or not text_content.strip():
                            raise ValueError("Empty response from AI")
                        
                        # Extract JSON from response (handle text before/after JSON)
                        import re
                        # Try to find JSON object using regex (more robust)
                        json_match = re.search(r'\{[\s\S]*\}', text_content)
                        if json_match:
                            json_text = json_match.group(0)
                        else:
                            # Fallback to simple find (in case regex fails)
                            json_start = text_content.find('{')
                            json_end = text_content.rfind('}') + 1
                            if json_start == -1 or json_end == 0:
                                # Log the response for debugging
                                current_app.logger.error(f"Failed to extract JSON from response. Response length: {len(text_content)}, First 500 chars: {text_content[:500]}")
                                raise ValueError(
                                    f"No JSON found in response. Response may be truncated or malformed. "
                                    f"Response preview: {text_content[:200]}..."
                                )
                            json_text = text_content[json_start:json_end]
                        
                        # Try to parse JSON
                        try:
                            narrative_data = json.loads(json_text)
                        except json.JSONDecodeError as e:
                            current_app.logger.error(f"JSON parse error: {e}. JSON text length: {len(json_text)}, First 500 chars: {json_text[:500]}")
                            raise ValueError(
                                f"Failed to parse JSON from response. The response may be incomplete or malformed. "
                                f"JSON decode error: {str(e)}"
                            )
                        
                        # Validate structure
                        if 'nodes' not in narrative_data:
                            raise ValueError("Missing 'nodes' in response")
                        
                        if 'startNodeId' not in narrative_data:
                            raise ValueError("Missing 'startNodeId' in response")
                        
                        # Validate nodes - first pass: collect all node IDs
                        node_ids = set()
                        for node in narrative_data['nodes']:
                            if 'id' not in node:
                                raise ValueError("Node missing 'id' field")
                            if 'content' not in node:
                                raise ValueError(f"Node {node.get('id')} missing 'content' field")
                            if 'choices' not in node:
                                raise ValueError(f"Node {node.get('id')} missing 'choices' field")
                            if 'isEnding' not in node:
                                raise ValueError(f"Node {node.get('id')} missing 'isEnding' field")
                            
                            node_ids.add(node['id'])
                        
                        # Verify start node exists
                        start_node_exists = narrative_data['startNodeId'] in node_ids
                        if not start_node_exists:
                            raise ValueError(f"Start node '{narrative_data['startNodeId']}' not found in nodes")
                        
                        # Validate minimum node count (allow 70% of minimum as acceptable, or at least 3 nodes)
                        min_nodes_threshold = max(3, int(constraints['min_nodes'] * 0.7))
                        if len(narrative_data['nodes']) < min_nodes_threshold:
                            raise ValueError(
                                f"Narrative has {len(narrative_data['nodes'])} nodes, but minimum required is {constraints['min_nodes']} nodes "
                                f"(acceptable minimum: {min_nodes_threshold}). Please create more nodes to meet the complexity requirements."
                            )
                        elif len(narrative_data['nodes']) < constraints['min_nodes']:
                            # Warn but don't fail if close to minimum (70-100% of required)
                            current_app.logger.warning(
                                f"Narrative has {len(narrative_data['nodes'])} nodes, below recommended {constraints['min_nodes']} nodes. "
                                f"Accepting but consider adding more nodes for better complexity."
                            )
                        
                        # Validate minimum content per node and calculate total
                        total_chars = 0
                        for node in narrative_data['nodes']:
                            node_content = str(node.get('content', ''))
                            node_chars = len(node_content)
                            total_chars += node_chars
                            
                            # Allow 70% of minimum per node (some nodes can be shorter if others are longer)
                            min_chars_per_node_threshold = int(constraints['min_chars_per_node'] * 0.7)
                            if node_chars < min_chars_per_node_threshold:
                                raise ValueError(
                                    f"Node '{node.get('id')}' has only {node_chars} characters, but minimum required is {constraints['min_chars_per_node']} characters per node "
                                    f"(acceptable minimum: {min_chars_per_node_threshold}). Please expand the content for this node."
                                )
                        
                        # Validate total character count (allow 80% of minimum as acceptable)
                        min_chars_threshold = int(constraints['min_chars'] * 0.8)
                        if total_chars < min_chars_threshold:
                            raise ValueError(
                                f"Total narrative length is {total_chars} characters, but minimum required is {constraints['min_chars']} characters "
                                f"(acceptable minimum: {min_chars_threshold}). Please expand content across all nodes to meet the complexity requirements."
                            )
                        elif total_chars < constraints['min_chars']:
                            # Warn but don't fail if close to minimum
                            current_app.logger.warning(
                                f"Narrative has {total_chars} characters, slightly below recommended {constraints['min_chars']} characters. "
                                f"Accepting but consider expanding content for better depth."
                            )
                        
                        # For Challenge level: Validate minimum decision points before endings
                        if complexity == 'challenge':
                            # Count non-ending nodes (decision points)
                            decision_points = [n for n in narrative_data['nodes'] if not n.get('isEnding', False)]
                            if len(decision_points) < 3:
                                raise ValueError(
                                    f"Challenge level requires at least 3-4 decision points before reaching endings, but only {len(decision_points)} non-ending nodes found. "
                                    f"Please create more decision points to show how choices compound."
                                )
                            
                            # Validate that paths have multiple decision points (check that endings aren't reached too quickly)
                            # This is a heuristic: ensure at least some paths go through 3+ nodes
                            ending_nodes = [n for n in narrative_data['nodes'] if n.get('isEnding', False)]
                            if len(ending_nodes) < 3:
                                raise ValueError(
                                    f"Challenge level requires at least 3-4 different endings, but only {len(ending_nodes)} endings found. "
                                    f"Please create more diverse endings based on different choice paths."
                                )
                        
                        # Second pass: validate choices and their references
                        for node in narrative_data['nodes']:
                            # Validate choices for non-ending nodes
                            if not node.get('isEnding'):
                                choices = node.get('choices', [])
                                expected_choices = 2 if complexity == 'explanation' else (3 if complexity == 'simulation' else 4)
                                if len(choices) != expected_choices:
                                    raise ValueError(f"Node {node['id']} has {len(choices)} choices, expected {expected_choices}")
                                
                                for choice in choices:
                                    if 'id' not in choice or 'text' not in choice or 'nextNode' not in choice:
                                        raise ValueError(f"Invalid choice structure in node {node['id']}")
                                    # Now validate that nextNode exists (all node IDs are collected)
                                    if choice['nextNode'] not in node_ids:
                                        available_nodes_str = ', '.join([f"'{n}'" for n in sorted(node_ids)])
                                        raise ValueError(
                                            f"Choice in node '{node['id']}' references non-existent node '{choice['nextNode']}'. "
                                            f"Available nodes: [{available_nodes_str}]. "
                                            f"Please ensure all choice 'nextNode' values match existing node IDs."
                                        )
                        
                        # If we got here, validation passed - break out of retry loop
                        break
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        last_error = e
                        if attempt < max_retries:
                            current_app.logger.warning(f"Interactive narrative generation attempt {attempt + 1} failed: {e}. Retrying...")
                            # Add a retry instruction to the prompt
                            error_msg = str(e)
                            prompt += f"\n\nIMPORTANT: Your previous attempt had validation errors: {error_msg}\n"
                            prompt += "Please ensure ALL requirements are met. Follow these steps:\n"
                            prompt += f"1. Create AT LEAST {constraints['min_nodes']} total nodes\n"
                            prompt += f"2. Each node must have at least {constraints['min_chars_per_node']} characters of content\n"
                            prompt += f"3. Total content must be at least {constraints['min_chars']} characters across all nodes\n"
                            prompt += "4. First, list ALL node IDs you will create\n"
                            prompt += "5. Then create the nodes array with those exact IDs\n"
                            prompt += "6. When writing choices, reference ONLY the node IDs from step 4\n"
                            prompt += "7. Double-check every 'nextNode' value matches an existing node 'id' exactly\n"
                            if complexity == 'challenge':
                                prompt += "8. For Challenge level: Ensure at least 3-4 decision points (non-ending nodes) before reaching any ending\n"
                                prompt += "9. For Challenge level: Create at least 3-4 different endings\n"
                                prompt += "10. For Challenge level: Make choices present conflicting goals with meaningful trade-offs"
                        else:
                            # Last attempt failed, re-raise the error
                            raise
                
                if narrative_data is None:
                    raise ValueError(f"Failed to generate valid narrative after {max_retries + 1} attempts: {last_error}")
                
                # At this point, narrative_data has passed all validation
                
                # Return interactive narrative
                return jsonify({
                    'success': True,
                    'narrative_type': 'interactive',
                    'complexity': complexity,
                    'narrative': narrative_data
                }), 200
                
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON decode error: {e}")
            return jsonify({'error': 'Failed to parse narrative response from AI'}), 500
        except Exception as e:
            current_app.logger.error(f"AI generation error: {e}")
            return jsonify({'error': f'Failed to generate narrative: {str(e)}'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Narrative generation error: {e}")
        db.session.rollback()
        return jsonify({'error': f'Failed to generate narrative: {str(e)}'}), 500


@narrative.route('/feedback', methods=['POST'])
@login_required
@limiter.limit("10 per minute; 50 per hour")
def generate_feedback():
    """Generate AI feedback on user reflection."""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json() or {}
        
        # Validate required fields
        narrative_type = data.get('narrative_type')
        narrative_content = data.get('narrative_content')
        reflection_text = data.get('reflection_text')
        context_parts = data.get('context_parts', {})
        complexity = data.get('complexity')  # Optional, only for interactive
        
        if not narrative_type or narrative_type not in ('linear', 'interactive'):
            return jsonify({'error': 'narrative_type must be "linear" or "interactive"'}), 400
        
        if not narrative_content:
            return jsonify({'error': 'narrative_content is required'}), 400
        
        if not reflection_text or not reflection_text.strip():
            return jsonify({'error': 'reflection_text is required'}), 400
        
        # Build feedback prompt
        context_section = ""
        if context_parts.get('chat'):
            context_section += f"=== CHAT CONVERSATION ===\n{context_parts['chat']}\n\n"
        if context_parts.get('library'):
            context_section += f"=== LIBRARY DOCUMENTS ===\n{context_parts['library']}\n\n"
        
        if narrative_type == 'linear':
            narrative_section = f"=== NARRATIVE ===\n{narrative_content}\n\n"
            feedback_prompt = f"""You are providing formative feedback on a student's reflection about a narrative they read.

{context_section}

{narrative_section}

=== STUDENT REFLECTION ===
{reflection_text}

TASK:
Compare the student's reflection to:
1. The source material concepts (from the context above)
2. The narrative content

Provide structured feedback in the following format:

CONCEPTUAL UNDERSTANDING:
[Assess how well the student recognized and understood concepts from the course materials. Point out specific concepts they identified correctly and any they may have missed or misunderstood.]

TRANSFER APPLICATION:
[Evaluate how well the student connected the narrative to real-world situations or other contexts. Provide guidance on strengthening these connections.]

Provide formative feedback only - no grades, no authoritative judgment. Be encouraging and constructive. Keep feedback concise but meaningful."""
        else:  # interactive
            narrative_section = f"=== INTERACTIVE NARRATIVE ===\n{json.dumps(narrative_content, indent=2)}\n\n"
            feedback_prompt = f"""You are providing formative feedback on a student's reflection about an interactive narrative they experienced.

{context_section}

{narrative_section}

=== STUDENT REFLECTION ===
{reflection_text}

TASK:
Compare the student's reflection to:
1. The source material concepts (from the context above)
2. The narrative decision logic (the choices they made and the consequences)
3. Alternative decision paths they might have taken

Provide structured feedback in the following format:

CONCEPTUAL UNDERSTANDING:
[Assess how well the student recognized and understood concepts from the course materials. Point out specific concepts they identified correctly and any they may have missed or misunderstood.]

DECISION REASONING:
[Evaluate the student's understanding of their decision-making process. Discuss how their choices connected to course concepts and what alternative choices might have led to different outcomes.]

TRANSFER APPLICATION:
[Evaluate how well the student connected the narrative experience to real-world decision-making. Provide guidance on strengthening these connections.]

Provide formative feedback only - no grades, no authoritative judgment. Be encouraging and constructive. Keep feedback concise but meaningful."""
        
        # Call AI
        text_content, is_truncated = call_anthropic_api(
            messages=[{"role": "user", "content": feedback_prompt}],
            system_prompt="You are an expert at providing formative feedback on student reflections. Provide structured, constructive feedback.",
            max_tokens=2000
        )
        
        if not text_content or not text_content.strip():
            raise ValueError("Empty response from AI")
        
        # Parse structured feedback
        feedback_text = text_content.strip()
        
        # Extract structured sections
        feedback_dict = {
            'conceptual_understanding': '',
            'transfer_application': ''
        }
        
        if narrative_type == 'interactive':
            feedback_dict['decision_reasoning'] = ''
        
        # Try to parse structured format
        lines = feedback_text.split('\n')
        current_section = None
        current_text = []
        
        for line in lines:
            line_upper = line.upper().strip()
            if 'CONCEPTUAL UNDERSTANDING' in line_upper:
                if current_section:
                    feedback_dict[current_section] = '\n'.join(current_text).strip()
                current_section = 'conceptual_understanding'
                current_text = []
            elif 'DECISION REASONING' in line_upper and narrative_type == 'interactive':
                if current_section:
                    feedback_dict[current_section] = '\n'.join(current_text).strip()
                current_section = 'decision_reasoning'
                current_text = []
            elif 'TRANSFER APPLICATION' in line_upper or 'TRANSFER' in line_upper:
                if current_section:
                    feedback_dict[current_section] = '\n'.join(current_text).strip()
                current_section = 'transfer_application'
                current_text = []
            elif current_section:
                if line.strip():
                    current_text.append(line)
        
        # Save last section
        if current_section:
            feedback_dict[current_section] = '\n'.join(current_text).strip()
        
        # If parsing failed, put everything in conceptual_understanding
        if not any(feedback_dict.values()):
            feedback_dict['conceptual_understanding'] = feedback_text
        
        return jsonify({
            'success': True,
            'feedback': feedback_dict
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Feedback generation error: {e}")
        return jsonify({'error': f'Failed to generate feedback: {str(e)}'}), 500
