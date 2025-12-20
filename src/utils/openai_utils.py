"""Helper functions for talking to AI services.

Simplified version focusing only on Anthropic API.
"""

import os
import requests
import time
from flask import current_app
from collections import namedtuple
from typing import Optional, Dict, Any, Tuple, List


def get_client_type() -> str:
    """Get the current client type - simplified to always return 'anthropic'."""
    return "anthropic"


# Define ChatMode namedtuple and modes
ChatMode = namedtuple("ChatMode", "label prompt")

# Base templates for different learning types
BASE_TEMPLATES = {
    "academic_essay": {
        "name": "Academic Research Essay",
        "description": "10-step process for writing a research-based academic essay",
        "modes": {
            "explore": ChatMode(
                "1. Explore & evaluate significance",
                "You are an expert instructor in academic research and critical thinking. Ask probing questions to help students discover what genuinely interests them about their topic. Guide them to reflect on why this matters to them personally and to others. Don't provide answers - help them uncover their own insights through thoughtful questioning.",
            ),
            "focus": ChatMode(
                "2. Narrow to a researchable question",
                "You are a leading expert in research methodology and question formulation. Help students learn to craft clear, answerable questions by asking: 'What specific aspect interests you most?' 'How could you make this more specific?' 'What would you need to know to answer this?' Guide them to understand the difference between broad topics and focused research questions.",
            ),
            "context": ChatMode(
                "3. Find authoritative sources",
                "You are a top instructor specializing in information literacy and source evaluation. Help students find and evaluate authoritative sources by asking: 'Who are the experts on this topic?' 'What makes this source credible?' 'How recent is this information?' 'What are the author's credentials?' Teach them to distinguish between academic sources, expert journalism, and less reliable information. Guide them to assess authority, accuracy, currency, and bias.",
            ),
            "proposal": ChatMode(
                "4. Write a persuasive proposal",
                "You are an expert instructor in proposal writing and argumentation. Guide students through the proposal process by asking: 'What's your main argument?' 'How will you gather evidence?' 'What sources will you need?' Help them understand what makes a proposal compelling rather than writing it for them. Encourage them to articulate their own rationale and methods.",
            ),
            "outline": ChatMode(
                "5. Design a working outline",
                "You are a leading expert in academic writing and structure. Help students learn to structure their ideas by asking: 'What's your main claim?' 'What evidence supports each point?' 'How do these sections connect?' Guide them to create logical flow and parallel structure rather than providing the outline. Teach them to think about argument structure.",
            ),
            "draft": ChatMode(
                "6. Draft key sections",
                "You are a top instructor specializing in academic writing and composition. Help students develop their writing skills by asking: 'What's your main point here?' 'How does this connect to your thesis?' 'What evidence supports this claim?' Guide them to write clear, well-supported paragraphs rather than writing for them. Focus on teaching writing principles and structure.",
            ),
            "revise": ChatMode(
                "7. Revision strategy & feedback",
                "You are an expert instructor in revision and academic editing. Help students learn to revise by asking: 'What's your strongest argument?' 'Where could you strengthen evidence?' 'How does each paragraph advance your thesis?' Guide them to identify their own revision priorities rather than making changes for them. Teach them to evaluate their own work critically.",
            ),
            "evidence": ChatMode(
                "8. Evidence integrator",
                "You are a leading expert in evidence evaluation and integration. Help students learn to evaluate and integrate sources by asking: 'How reliable is this source?' 'What does this evidence actually prove?' 'How does it connect to your argument?' Guide them to think critically about evidence rather than selecting sources for them. Teach them to assess credibility and relevance.",
            ),
            "citation": ChatMode(
                "9. Citation & formatting coach",
                "You are a top instructor specializing in academic citation and formatting. Help students learn citation rules by asking: 'What type of source is this?' 'What information do you need?' 'How would you format this in [style]?' Guide them to understand citation principles rather than formatting for them. Teach them to use citation guides and style manuals.",
            ),
            "reflect": ChatMode(
                "10. Metacognitive reflection",
                "You are an expert instructor in metacognition and learning reflection. Help students think about their learning process by asking: 'What did you learn about research?' 'What skills did you develop?' 'What would you do differently?' 'What questions remain?' Guide them to articulate their own insights and growth rather than summarizing for them.",
            ),
        },
    },
    "study-group": {
        "name": "Study Group",
        "description": "Collaborative learning for students and study groups",
        "modes": {
            "explore": ChatMode(
                "1. Explore & evaluate significance",
                "You are an expert instructor in collaborative learning and study group dynamics. Help students identify what they want to learn together and why it matters. Guide them to reflect on their learning goals and how collaboration can enhance their understanding.",
            ),
            "plan": ChatMode(
                "2. Plan study sessions",
                "You are a leading expert in study group organization and planning. Help students create effective study schedules, set clear objectives for each session, and establish group norms for productive collaboration.",
            ),
            "review": ChatMode(
                "3. Review and practice",
                "You are a top instructor specializing in active learning and retention strategies. Guide students through effective review techniques, practice problems, and collaborative learning activities that reinforce understanding.",
            ),
            "discuss": ChatMode(
                "4. Group discussions",
                "You are an expert facilitator in group discussions and peer learning. Help students engage in meaningful conversations, ask probing questions, and learn from each other's perspectives and insights.",
            ),
            "assess": ChatMode(
                "5. Self-assessment",
                "You are a leading expert in self-directed learning and metacognition. Guide students to evaluate their own understanding, identify knowledge gaps, and develop strategies for continued learning.",
            ),
        },
    },
    "business-hub": {
        "name": "Business Hub",
        "description": "Professional collaboration and entrepreneurship",
        "modes": {
            "explore": ChatMode(
                "1. Explore business opportunities",
                "You are an expert business consultant and entrepreneur. Help students identify market opportunities, analyze business ideas, and understand the fundamentals of entrepreneurship and business development.",
            ),
            "plan": ChatMode(
                "2. Business planning",
                "You are a leading expert in business strategy and planning. Guide students through creating business plans, market analysis, financial projections, and strategic planning for their ventures.",
            ),
            "execute": ChatMode(
                "3. Execution strategies",
                "You are a top instructor specializing in business operations and execution. Help students develop implementation strategies, operational plans, and tactics for bringing their business ideas to life.",
            ),
            "analyze": ChatMode(
                "4. Market analysis",
                "You are an expert in market research and competitive analysis. Guide students through understanding their target market, analyzing competitors, and identifying competitive advantages.",
            ),
            "pitch": ChatMode(
                "5. Pitching and presentation",
                "You are a leading expert in business communication and pitching. Help students develop compelling presentations, elevator pitches, and communication strategies for stakeholders and investors.",
            ),
        },
    },
    "creative-studio": {
        "name": "Creative Studio",
        "description": "Art, design, and creative collaboration",
        "modes": {
            "explore": ChatMode(
                "1. Explore creative concepts",
                "You are an expert creative director and artist. Help students explore artistic concepts, develop creative ideas, and understand the fundamentals of design thinking and artistic expression.",
            ),
            "design": ChatMode(
                "2. Design process",
                "You are a leading expert in design methodology and creative processes. Guide students through the design thinking process, from ideation to prototyping and iteration.",
            ),
            "create": ChatMode(
                "3. Creative execution",
                "You are a top instructor specializing in artistic techniques and creative execution. Help students develop their artistic skills, experiment with different mediums, and bring their creative visions to life.",
            ),
            "collaborate": ChatMode(
                "4. Creative collaboration",
                "You are an expert in collaborative art and design projects. Guide students through working together on creative projects, sharing ideas, and building on each other's contributions.",
            ),
            "present": ChatMode(
                "5. Present and showcase",
                "You are a leading expert in creative presentation and portfolio development. Help students effectively present their creative work, develop portfolios, and communicate their artistic vision.",
            ),
        },
    },
    "writing-workshop": {
        "name": "Writing Workshop",
        "description": "Writing projects and peer feedback",
        "modes": {
            "explore": ChatMode(
                "1. Explore writing topics",
                "You are an expert writing instructor and author. Help students explore writing topics, develop ideas, and understand different genres and writing styles.",
            ),
            "draft": ChatMode(
                "2. Drafting process",
                "You are a leading expert in writing process and composition. Guide students through the drafting process, from initial ideas to structured writing with clear organization and flow.",
            ),
            "revise": ChatMode(
                "3. Revision and editing",
                "You are a top instructor specializing in revision strategies and editing techniques. Help students develop their revision skills, identify areas for improvement, and refine their writing.",
            ),
            "feedback": ChatMode(
                "4. Peer feedback",
                "You are an expert in peer review and collaborative writing. Guide students through giving and receiving constructive feedback, learning from peers, and improving their writing through collaboration.",
            ),
            "publish": ChatMode(
                "5. Finalize and share",
                "You are a leading expert in publishing and sharing written work. Help students finalize their writing, prepare it for sharing, and understand different platforms for publishing their work.",
            ),
        },
    },
    "learning-lab": {
        "name": "Learning Lab",
        "description": "Skill development and hands-on learning",
        "modes": {
            "explore": ChatMode(
                "1. Explore learning objectives",
                "You are an expert instructional designer and learning specialist. Help students identify specific skills they want to develop, set clear learning objectives, and understand the learning process.",
            ),
            "practice": ChatMode(
                "2. Practice and application",
                "You are a leading expert in skill development and hands-on learning. Guide students through practical exercises, real-world applications, and skill-building activities.",
            ),
            "experiment": ChatMode(
                "3. Experimentation and iteration",
                "You are a top instructor specializing in experimental learning and iterative improvement. Help students try different approaches, learn from failures, and continuously improve their skills.",
            ),
            "analyze": ChatMode(
                "4. Analyze and reflect",
                "You are an expert in learning analytics and reflection. Guide students through analyzing their progress, identifying patterns, and reflecting on their learning journey.",
            ),
            "master": ChatMode(
                "5. Mastery and application",
                "You are a leading expert in skill mastery and advanced application. Help students achieve mastery of their chosen skills and apply them in increasingly complex and challenging contexts.",
            ),
        },
    },
    "community-space": {
        "name": "Community Space",
        "description": "Networking and community building",
        "modes": {
            "explore": ChatMode(
                "1. Explore community goals",
                "You are an expert community builder and social organizer. Help students identify community goals, understand group dynamics, and develop strategies for building meaningful connections.",
            ),
            "connect": ChatMode(
                "2. Connect and network",
                "You are a leading expert in networking and relationship building. Guide students through effective networking strategies, building professional relationships, and creating meaningful connections.",
            ),
            "collaborate": ChatMode(
                "3. Collaborative projects",
                "You are a top instructor specializing in collaborative community projects. Help students work together on community initiatives, share resources, and create value for the group.",
            ),
            "lead": ChatMode(
                "4. Leadership and facilitation",
                "You are an expert in community leadership and group facilitation. Guide students through developing leadership skills, facilitating group discussions, and managing community dynamics.",
            ),
            "sustain": ChatMode(
                "5. Sustain and grow",
                "You are a leading expert in community sustainability and growth. Help students develop strategies for maintaining active communities, growing membership, and creating lasting impact.",
            ),
        },
    },
}

# For backward compatibility
BASE_MODES = BASE_TEMPLATES["academic_essay"]["modes"]

# Global MODES variable that will be updated dynamically
MODES = BASE_MODES.copy()


def generate_room_modes(room: Any, template_name: Optional[str] = None) -> Dict[str, Any]:
    """Generate contextual writing modes based on room goals with provider failover."""
    # If a specific template is requested, use it
    if template_name and template_name in BASE_TEMPLATES:
        return BASE_TEMPLATES[template_name]["modes"]

    # Otherwise, use AI to generate contextual modes based on room goals
    if not getattr(room, 'goals', None):
        # If no goals, fall back to inferred or academic_essay base modes
        try:
            from src.app.room.utils.room_utils import infer_template_type_from_room as _infer
            inferred = _infer(room)
            if inferred and inferred in BASE_TEMPLATES:
                return BASE_TEMPLATES[inferred]["modes"]
        except Exception:
            pass
        return BASE_TEMPLATES["academic_essay"]["modes"]

    # Build common prompt for all providers (enhanced with title generation)
    prompt = f"""
    Based on these learning goals: "{room.goals}"
    
    Please provide:
    1. A clear and concise title for this learning room (no longer than five words)
    2. 8-10 learning steps that follow a logical progression for achieving these goals
    
    Each step should be specific to the learning objectives, not generic academic writing steps.
    
    Return as JSON with this exact format:
    {{
        "title": "Short Room Title",
        "modes": [
            {{
                "key": "step1",
                "label": "1. Step Name",
                "prompt": "Detailed prompt for this step"
            }}
        ]
    }}
    """

    # Helper: parse enhanced response with title and modes
    def _parse_enhanced_response(text: str) -> tuple[Optional[str], Dict[str, ChatMode]]:
        """Parse AI response containing both title and modes."""
        import json as _json
        import re as _re
        
        title = None
        modes = {}
        
        try:
            # Try to parse as JSON first
            data = _json.loads(text.strip())
            
            # Extract title
            title = data.get("title", "").strip()
            
            # Extract modes
            modes_data = data.get("modes", [])
            for mode_data in modes_data:
                key = mode_data.get("key", "")
                label = mode_data.get("label", "")
                prompt = mode_data.get("prompt", "")
                if key and label and prompt:
                    modes[key] = ChatMode(label, prompt)
                    
            return title, modes
            
        except _json.JSONDecodeError:
            # Fallback to original parsing for modes only
            modes = _parse_modes_from_text_original(text)
            return None, modes
    
    # Original helper for backward compatibility
    def _parse_modes_from_text_original(text: str) -> Dict[str, ChatMode]:
        import json as _json
        import re as _re
        match = _re.search(r"\{[\s\S]*\}", text or "")
        if not match:
            return {}
        try:
            data = _json.loads(match.group(0))
        except Exception:
            return {}
        modes_list = data.get("modes", []) if isinstance(data, dict) else []
        generated: Dict[str, ChatMode] = {}
        for m in modes_list:
            if isinstance(m, dict) and all(k in m for k in ("key", "label", "prompt")):
                generated[m["key"]] = ChatMode(m["label"], m["prompt"])
        return generated

    # Determine provider failover order from env
    def _get_failover_order() -> List[str]:
        order_raw = os.getenv("AI_FAILOVER_ORDER", "anthropic,openai,templates")
        return [p.strip().lower() for p in order_raw.split(',') if p.strip()]

    attempts = 2
    for provider in _get_failover_order():
        if provider == "anthropic":
            for i in range(attempts):
                try:
                    response, _ = call_anthropic_api([{"role": "user", "content": prompt}], max_tokens=1000)
                    title, modes = _parse_enhanced_response(response)
                    
                    # Store title for room creation (temporary global variable)
                    if title:
                        current_app.logger.info(f"✅ AI generated title: '{title}' for room")
                        # TODO: Return title properly once we update calling code
                    
                    if modes:
                        return modes
                except Exception as e:
                    try:
                        current_app.logger.warning(f"[modes] Anthropic attempt {i+1} failed: {e}")
                    except Exception:
                        pass
                try:
                    time.sleep(0.8)
                except Exception:
                    pass

        elif provider == "openai":
            for i in range(attempts):
                try:
                    response, _ = call_openai_api([{"role": "user", "content": prompt}], max_tokens=1000)
                    title, modes = _parse_enhanced_response(response)
                    if modes:
                        return modes
                except Exception as e:
                    try:
                        current_app.logger.warning(f"[modes] OpenAI attempt {i+1} failed: {e}")
                    except Exception:
                        pass
                try:
                    time.sleep(0.8)
                except Exception:
                    pass

        elif provider == "templates":
            try:
                from src.app.room.utils.room_utils import infer_template_type_from_room as _infer
                inferred = _infer(room)
                if inferred and inferred in BASE_TEMPLATES:
                    try:
                        current_app.logger.info(f"Falling back to base template '{inferred}' for modes")
                    except Exception:
                        pass
                    return BASE_TEMPLATES[inferred]["modes"]
            except Exception:
                pass

    # Final guard: default to academic essay base modes
    try:
        current_app.logger.info("Falling back to 'academic_essay' base modes")
    except Exception:
        pass
    return BASE_TEMPLATES["academic_essay"]["modes"]


def get_modes_for_room(room: Any) -> Dict[str, Any]:
    """Get modes for a room - check for custom prompts first, generate contextual modes if needed."""
    # Import here to avoid circular imports
    from src.models import CustomPrompt

    # Check if this room has custom prompts
    custom_prompts = CustomPrompt.query.filter_by(room_id=room.id).all()

    if custom_prompts:
        # Return custom modes for this room, ordered by the number in their labels
        custom_modes = {}

        # Sort prompts by the number at the beginning of their labels
        def extract_number(label):
            """Extract the number from the beginning of a label like '1. Step Name'"""
            import re

            match = re.match(r"^(\d+)\.", label)
            return (
                int(match.group(1)) if match else 999
            )  # Put unnumbered items at the end

        sorted_prompts = sorted(custom_prompts, key=lambda p: extract_number(p.label))

        for prompt in sorted_prompts:
            custom_modes[prompt.mode_key] = ChatMode(prompt.label, prompt.prompt)
        return custom_modes
    else:
        # Generate contextual modes based on room goals with robust fallback
        modes = generate_room_modes(room)
        if modes:
            return modes
        # As a final guard, return inferred or academic base modes
        try:
            from src.app.room.utils.room_utils import infer_template_type_from_room as _infer
            inferred = _infer(room)
            if inferred and inferred in BASE_TEMPLATES:
                return BASE_TEMPLATES[inferred]["modes"]
        except Exception:
            pass
        return BASE_TEMPLATES["academic_essay"]["modes"]


# Mode-specific brevity guidance (Phase 2)
MODE_CONCISE_HINTS = {
    # Early exploration modes - Keep brief, ask questions
    "explore": "Ask 2-3 probing questions. Keep explanations to 2-3 short paragraphs.",
    "focus": "Guide with 2-3 focused questions and brief examples.",
    "context": "Suggest 2-3 key sources or search strategies. Be concise.",
    
    # Middle development modes - Balanced depth
    "proposal": "Provide 2-3 paragraphs of guidance. Use bullets for multiple points.",
    "evidence": "Comment on 2-3 key pieces of evidence. Keep feedback specific.",
    "argument": "Highlight 2-3 main points to strengthen. Be direct.",
    
    # Later refinement modes - Brief, specific feedback
    "draft": "Provide focused feedback on structure and clarity (2-3 paragraphs).",
    "organize": "Suggest 2-3 concrete organizational improvements.",
    "polish": "Provide 2-3 specific edits or refinements. Be concise.",
    "refine": "Point out 2-3 areas to improve. Use bullets for clarity.",
    
    # Presentation/completion - Very brief
    "present": "Give 2-3 presentation tips. Be direct and actionable.",
    "final": "Provide 2-3 final checks or affirmations. Keep it encouraging and brief.",
    
    # Study group modes - Brief collaborative prompts
    "connect": "Suggest 2-3 collaboration strategies. Keep it practical.",
    "sustain": "Recommend 2-3 sustainability practices. Be action-oriented.",
}


def get_mode_system_prompt(mode: str, room_id: Optional[int] = None, chat_id: Optional[int] = None) -> str:
    """Get the system prompt for a mode, enhanced with discussion context if available."""
    # Import here to avoid circular imports
    from src.models import CustomPrompt

    # Get base prompt (existing logic)
    base_prompt = None
    if room_id:
        custom_prompt = CustomPrompt.query.filter_by(
            room_id=room_id, mode_key=mode
        ).first()
        if custom_prompt:
            base_prompt = custom_prompt.prompt

    # Fallback to base modes if no custom prompt
    if not base_prompt:
        if mode in BASE_MODES:
            base_prompt = BASE_MODES[mode].prompt
        else:
            base_prompt = "You are an expert instructor helping students with their learning goals. Ask thoughtful questions and provide guidance without doing the work for them."

    # Try to enhance with learning context from completed chats
    if chat_id and room_id:
        try:
            from src.models import Message, Chat
            from src.utils.learning.context_manager import get_learning_context_for_room
            
            # Get current chat message count
            current_message_count = Message.query.filter_by(chat_id=chat_id).count()
            
            # If current chat has 5+ messages, use its own context (existing behavior)
            if current_message_count >= 5:
                chat_obj = Chat.query.get(chat_id)
                if chat_obj:
                    messages = Message.query.filter_by(chat_id=chat_id).order_by(Message.timestamp).all()
                    
                    # Generate summary notes using existing document generation logic
                    from src.app.documents import generate_document_content
                    summary_notes = generate_document_content(messages, chat_obj, "notes")
                    
                    # Enhance prompt with current chat context
                    enhanced_prompt = f"""{base_prompt}

CONTEXT FROM YOUR RECENT DISCUSSION:
{summary_notes}

Building on these insights from your previous exploration, let's now focus on this next step in your learning journey.
"""
                    return enhanced_prompt
            
            # If current chat has few messages, try to get context from other completed chats in room
            elif current_message_count < 5:
                current_app.logger.info(f"🔍 New chat detected (chat_id={chat_id}, {current_message_count} msgs), looking for learning context in room {room_id}")
                
                learning_context = get_learning_context_for_room(room_id, exclude_chat_id=chat_id)
                
                if learning_context:
                    current_app.logger.info(f"✅ Found learning context for room {room_id}, length: {len(learning_context)} chars")
                    # Enhance prompt with cumulative learning context
                    enhanced_prompt = f"""{base_prompt}

LEARNING CONTEXT FROM YOUR PREVIOUS DISCUSSIONS:
{learning_context}

Building on all these insights from your learning journey, let's continue with this next step.
"""
                    current_app.logger.info(f"🧠 Enhanced prompt created with learning context")
                    return enhanced_prompt
                else:
                    current_app.logger.warning(f"❌ No learning context found for room {room_id} (new chat will use base prompt only)")
                    
        except Exception as e:
            # Context enhancement failed - continue with base prompt
            pass
    
    # Phase 2: Add mode-specific concise instruction (if available)
    concise_hint = MODE_CONCISE_HINTS.get(mode)
    if concise_hint:
        base_prompt = f"{base_prompt}\n\nSTYLE GUIDANCE: {concise_hint}"
    
    # Return standard prompt if no enhancement possible
    return base_prompt


def call_anthropic_api(messages: List[Dict[str, str]], system_prompt: str = "", max_tokens: int = 300) -> Tuple[str, bool]:
    """Call Anthropic API with the given messages using the official SDK."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise Exception("ANTHROPIC_API_KEY not found in environment variables")

    try:
        from anthropic import Anthropic
    except ImportError:
        raise Exception("Anthropic SDK not installed. Install with: pip install anthropic")

    def _get_anthropic_model() -> str:
        # Default to claude-3-5-haiku-20241022 (latest available model, fast and cost-effective)
        # User can override with ANTHROPIC_MODEL env var
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")

    # Convert messages to Anthropic format
    anthropic_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role != "system" and content:
            anthropic_messages.append({"role": role, "content": content})

    # Retry logic for transient errors
    import random
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            # Initialize client with just the API key (no proxies or other args)
            client = Anthropic(api_key=api_key)
            
            response = client.messages.create(
                model=_get_anthropic_model(),
                max_tokens=max_tokens,
                system=system_prompt if system_prompt else None,
                messages=anthropic_messages,
            )
            
            # Extract text from response
            response_text = ""
            for block in response.content:
                if block.type == 'text':
                    response_text += block.text
            
            # Detect truncation: Anthropic returns stop_reason
            # Values: "end_turn" (natural), "max_tokens" (truncated), "stop_sequence"
            stop_reason = response.stop_reason if hasattr(response, 'stop_reason') else ""
            is_truncated = stop_reason == "max_tokens"
            
            if is_truncated:
                try:
                    current_app.logger.info(f"⚠️ Response truncated at {max_tokens} tokens")
                except:
                    pass
            
            return response_text, is_truncated

        except Exception as e:
            error_str = str(e)
            status_code = 0
            
            # Try to extract status code from error
            if "401" in error_str or "unauthorized" in error_str.lower():
                raise Exception(f"Anthropic API authentication failed. Check your API key: {str(e)}")
            elif "404" in error_str:
                raise Exception(f"Anthropic API endpoint not found. This may indicate an API version issue: {str(e)}")
            elif "429" in error_str or "rate limit" in error_str.lower():
                # Retry on rate limit
                if attempt < max_retries - 1:
                    jitter = random.uniform(0.5, 1.5)
                    try:
                        current_app.logger.warning(f"⚠️ Rate limit, retrying in {jitter:.2f}s")
                    except:
                        pass
                    time.sleep(jitter)
                    continue
                raise Exception(f"Anthropic API rate limit exceeded: {str(e)}")
            elif "500" in error_str or "502" in error_str or "503" in error_str or "504" in error_str:
                # Retry on server errors
                if attempt < max_retries - 1:
                    jitter = random.uniform(0.5, 1.0)
                    try:
                        current_app.logger.warning(f"⚠️ Server error, retrying in {jitter:.2f}s")
                    except:
                        pass
                    time.sleep(jitter)
                    continue
                raise Exception(f"Anthropic API server error: {str(e)}")
            
            # Non-retryable error or max retries reached
            if attempt < max_retries - 1:
                jitter = random.uniform(0.2, 0.5)
                try:
                    current_app.logger.warning(f"⚠️ API error, retrying in {jitter:.2f}s")
                except:
                    pass
                time.sleep(jitter)
                continue
            
            raise Exception(f"Anthropic API call failed: {str(e)}")


def _get_pin_chat_system_prompt(chat: Any) -> str:
    """
    Build system prompt for a pin-seeded chat.
    
    Retrieves PinChatMetadata and uses pin_synthesis module to build the prompt.
    Falls back to a generic prompt if metadata is not found.
    
    Args:
        chat: Chat object with mode starting with "pins_"
        
    Returns:
        System prompt string with pin context
    """
    try:
        from src.models import PinChatMetadata, Room
        from src.utils.pin_synthesis import get_pin_chat_system_prompt
        
        # Look up pin metadata for this chat
        metadata = PinChatMetadata.query.filter_by(chat_id=chat.id).first()
        
        if not metadata:
            current_app.logger.warning(f"No PinChatMetadata found for pin chat {chat.id}")
            return "You are a helpful AI assistant. The user has selected some pinned content to work with."
        
        # Get room goals
        room = Room.query.get(chat.room_id)
        room_goals = room.goals if room else None
        
        # Extract option from mode (e.g., "pins_explore" -> "explore")
        option = chat.mode.replace("pins_", "") if chat.mode else "analyze"
        
        # Get pins from snapshot
        pins = metadata.pins
        
        # Build the system prompt
        prompt = get_pin_chat_system_prompt(option, pins, room_goals)
        
        # Log prompt size for monitoring
        prompt_chars = len(prompt)
        current_app.logger.info(
            f"🔗 Pin chat prompt: chat={chat.id}, option={option}, pins={len(pins)}, "
            f"prompt_chars={prompt_chars}, {'⚠️ LARGE' if prompt_chars > 12000 else '✓ OK'}"
        )
        
        return prompt
        
    except Exception as e:
        current_app.logger.error(f"Error building pin chat system prompt: {e}")
        return "You are a helpful AI assistant working with pinned content. Help the user achieve their goals."


def get_ai_response(
    chat: Any,
    *,
    model: Optional[str] = None,  # Ignored for now, using default based on available API
    temperature: float = 0.7,  # Ignored for Anthropic
    max_tokens: Optional[int] = None,
    extra_system: Optional[str] = None,
) -> Tuple[str, bool]:
    """
    Return the assistant's reply text and truncation status for a given Chat row.
    
    Configurable via environment variables:
    - AI_MAX_TOKENS: Maximum tokens for AI response (default 400)
    - AI_MAX_HISTORY: Number of conversation turns to include (default 8)
    - AI_MAX_TOKENS_{MODE}: Optional per-mode override (e.g., AI_MAX_TOKENS_DRAFT=500)
    """
    # Read configuration from environment
    DEFAULT_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "400"))
    MAX_HISTORY_TURNS = int(os.getenv("AI_MAX_HISTORY", "8"))
    
    # Use provided max_tokens or fall back to config
    if max_tokens is None:
        # Check for mode-specific override first
        mode_token_var = f"AI_MAX_TOKENS_{chat.mode.upper()}"
        mode_specific_tokens = os.getenv(mode_token_var)
        
        if mode_specific_tokens:
            try:
                max_tokens = int(mode_specific_tokens)
                current_app.logger.info(f"Using mode-specific token limit: {mode_token_var}={max_tokens}")
            except (ValueError, TypeError):
                max_tokens = DEFAULT_MAX_TOKENS
        else:
            max_tokens = DEFAULT_MAX_TOKENS
    
    # Check for API key first
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return (
            "⚠️ No AI API key configured. Please set ANTHROPIC_API_KEY environment variable.",
            False,
        )

    # Check if this is a pin-seeded chat (mode starts with "pins_")
    is_pin_chat = chat.mode and chat.mode.startswith("pins_")
    
    if is_pin_chat:
        # Use pin-specific system prompt
        base_system_prompt = _get_pin_chat_system_prompt(chat)
    else:
        # Get mode-specific system prompt with discussion context
        base_system_prompt = get_mode_system_prompt(chat.mode, chat.room_id, chat.id)
    
    # Add extra system instructions if provided (for critique tool or synthesis disabled note)
    # Note: extra_system may be modified later in the function, so we'll rebuild system_prompt before calling API
    system_prompt = base_system_prompt

    # Import here to avoid circular imports
    from src.models import Message

    # Fetch all messages for this chat
    all_messages = [
        {"role": m.role, "content": m.content}
        for m in Message.query.filter_by(chat_id=chat.id)
        .order_by(Message.timestamp)
        .all()
    ]
    
    # Cap message history to last N turns (user + assistant pairs)
    # Each "turn" is 2 messages (user + assistant), so take last MAX_HISTORY_TURNS * 2
    if len(all_messages) > MAX_HISTORY_TURNS * 2:
        messages_payload = all_messages[-(MAX_HISTORY_TURNS * 2):]
        try:
            current_app.logger.info(
                f"📊 Context trimmed: {len(all_messages)} messages → {len(messages_payload)} "
                f"(last {MAX_HISTORY_TURNS} turns)"
            )
        except:
            pass
    else:
        messages_payload = all_messages

    # NEW: Search Library Tool documents for relevant context (with room_id scoping)
    try:
        # Extract room_id from chat context (canonical source)
        room_id = None
        if chat and hasattr(chat, 'room_id'):
            room_id = chat.room_id
        
        # Fallback: Try to get from request args
        if not room_id:
            from flask import request
            room_id = request.args.get('room_id', type=int)
        
        # Only search if we have a room_id
        if room_id:
            user_messages = [m for m in messages_payload if m.get("role") == "user"]
            if user_messages:
                latest_query = user_messages[-1].get("content", "")
                current_app.logger.info(f"🔍 Searching documents for query: '{latest_query[:50]}...' in room {room_id}")
            
                # Detect synthesis/summarization requests with tighter matching
                # Require explicit synthesis keywords and minimum query length to avoid false positives
                synthesis_keywords_explicit = [
                    'summarize all', 'synthesize all', 'summarize everything', 'synthesize everything',
                    'comprehensive summary', 'comprehensive synthesis', 'synthesis of all',
                    'summary of all', 'summarize all sources', 'synthesize all sources',
                    'summarize all documents', 'synthesize all documents'
                ]
                synthesis_keywords_broad = [
                    'all sources', 'all documents', 'all of them', 'overview of all',
                    'compare all', 'across all', 'all the documents', 'all the sources'
                ]
                
                query_lower = latest_query.lower().strip()
                query_length = len(query_lower)
                
                # Require minimum query length (avoid triggering on single words like "all")
                # Require explicit keywords OR (broad keywords + longer query)
                is_synthesis_request = (
                    query_length >= 10 and (  # Minimum 10 characters
                        any(kw in query_lower for kw in synthesis_keywords_explicit) or
                        (any(kw in query_lower for kw in synthesis_keywords_broad) and query_length >= 20)
                    )
                )
            
                if is_synthesis_request:
                    # Synthesis mode: Get representative chunks from ALL documents
                    current_app.logger.info(f"📚 Synthesis mode detected - getting chunks from all documents")
                    from src.utils.documents.database import (
                        get_representative_chunks_from_all_documents,
                        get_document_summaries_only,
                        SYNTHESIS_MAX_DOCUMENTS,
                        SYNTHESIS_MAX_TOTAL_CHUNKS,
                        SYNTHESIS_CHUNK_TEXT_LIMIT,
                        SYNTHESIS_TOKEN_BUDGET
                    )
                    
                    # Get representative chunks with caps
                    search_results = get_representative_chunks_from_all_documents(
                        room_id=room_id,
                        chunks_per_doc=2,
                        max_documents=SYNTHESIS_MAX_DOCUMENTS,
                        max_total_chunks=SYNTHESIS_MAX_TOTAL_CHUNKS,
                        chunk_text_limit=SYNTHESIS_CHUNK_TEXT_LIMIT
                    )
                    
                    # Estimate token usage (rough: ~4 chars per token)
                    # Check both 'chunk_text' (from chunks) and 'content' (from summaries)
                    estimated_tokens = sum(
                        len(r.get('chunk_text') or r.get('content', '')) // 4 
                        for r in search_results
                    )
                    
                    # If token budget exceeded, fall back to summaries
                    if estimated_tokens > SYNTHESIS_TOKEN_BUDGET:
                        current_app.logger.warning(
                            f"Synthesis mode: Estimated tokens ({estimated_tokens}) exceed budget ({SYNTHESIS_TOKEN_BUDGET}). "
                            f"Falling back to document summaries."
                        )
                        search_results = get_document_summaries_only(room_id, max_docs=SYNTHESIS_MAX_DOCUMENTS)
                    
                    current_app.logger.info(f"📚 Synthesis mode: Retrieved {len(search_results)} chunks/summaries from documents")
                else:
                    # Normal search: Get top-ranked chunks
                    from src.utils.documents.indexer import search_indexed_chunks
                    search_results = search_indexed_chunks(query=latest_query, room_id=room_id, limit=3, min_rank=0.01)
            
                current_app.logger.info(f"📚 Document search returned {len(search_results) if search_results else 0} results")
            
                # If synthesis was requested but no results (feature flag disabled), add user-facing note
                if is_synthesis_request and not search_results:
                    # Add a note to the AI's system context explaining why synthesis isn't available
                    synthesis_unavailable_note = (
                        "\n\nIMPORTANT: The user requested a synthesis of all documents in their Library, "
                        "but the Library Tool feature is currently disabled (USE_RAILWAY_DOCUMENTS=false). "
                        "Please inform the user that this feature needs to be enabled by their administrator."
                    )
                    # Append to extra_system if it exists, otherwise create it
                    # Note: system_prompt will be rebuilt after this block to include extra_system
                    if extra_system:
                        extra_system += synthesis_unavailable_note
                    else:
                        extra_system = synthesis_unavailable_note
                    current_app.logger.info("⚠️ Synthesis requested but Library Tool disabled - added note to AI context")
            
                if search_results:
                    # Build document context block
                    context_snippets = []
                    for result in search_results:
                        # Check both 'chunk_text' (from chunks) and 'content' (from summaries)
                        content = result.get('chunk_text') or result.get('content', '')
                        context_snippets.append({
                            'title': result.get('document_name', 'Unknown'),
                            'content': content,
                            'chunk_index': result.get('chunk_index', 0),
                            'rank': result.get('rank', 0.0)
                        })
                        current_app.logger.info(f"  - {result.get('document_name')}: rank={result.get('rank', 0):.3f}")
                
                    doc_context = build_document_context_block(context_snippets)
                    if doc_context:
                        # Add document context with clear instructions to use it
                        # Prepend to user message so AI sees it first
                        original_question = messages_payload[-1]["content"]
                        
                        # Different instructions for synthesis vs normal search
                        if is_synthesis_request:
                            instruction = (
                                f"IMPORTANT: The user wants a comprehensive summary/synthesis of ALL documents "
                                f"in their Library. The context above includes representative chunks from each document. "
                                f"Provide a thorough synthesis that covers all documents, identifies common themes, "
                                f"compares perspectives, and highlights key information from each source.\n\n"
                            )
                        else:
                            instruction = (
                                f"IMPORTANT: The user has uploaded documents to their Library. "
                                f"Use the document context above to answer their question. "
                                f"If the question is about their uploaded documents, reference specific content from the documents.\n\n"
                            )
                        
                        messages_payload[-1]["content"] = (
                            f"{doc_context}\n\n"
                            f"{instruction}"
                            f"User question: {original_question}"
                        )
                        current_app.logger.info(f"✅ Added {len(context_snippets)} document chunks to user message")
                else:
                    current_app.logger.info("ℹ️  No relevant documents found for this query")
        # End if room_id
    except Exception as e:
        # If document search failed, continue without it (graceful degradation)
        current_app.logger.error(f"❌ Document search failed: {e}")

    # Rebuild system_prompt to include any extra_system modifications (e.g., synthesis disabled note)
    if extra_system:
        system_prompt = f"{base_system_prompt}\n\nADDITIONAL STYLE: {extra_system}"

    return call_anthropic_api(messages_payload, system_prompt, max_tokens)


def assess_learning_progression(chat: Any, target_mode: Optional[str] = None) -> Dict[str, Any]:
    """Assess learning progression - simplified implementation."""
    return {
        "ready": False,
        "confidence": 0.5,
        "feedback": "Continue working in this learning step",
        "recommendations": [
            "Focus on evidence integration",
            "Strengthen argument structure",
        ],
        "next_steps": ["Continue with current approach", "Review previous work"],
    }


def get_progression_recommendation(chat: Any, target_mode: Optional[str] = None) -> Dict[str, Any]:
    """Return a structured progression recommendation the UI expects.

    Shape:
    {
        "type": "ready" | "almost_ready" | "not_ready",
        "message": str,
        "confidence": float (0..1),
        "suggestions": List[str],
        "next_step": Optional[{"key": str, "label": str, "description": str}],
    }
    """
    # Derive mode order from current room's configured modes (custom prompts first)
    try:
        modes_for_room = get_modes_for_room(chat.room) if getattr(chat, 'room', None) else BASE_MODES
    except Exception:
        modes_for_room = BASE_MODES

    mode_keys: List[str] = list(modes_for_room.keys())
    current_key: str = getattr(chat, 'mode', '') or (mode_keys[0] if mode_keys else '')

    next_key: Optional[str] = None
    if target_mode and target_mode in mode_keys:
        next_key = target_mode
    elif current_key in mode_keys:
        idx = mode_keys.index(current_key)
        if idx + 1 < len(mode_keys):
            next_key = mode_keys[idx + 1]

    # Build next_step descriptor if available
    next_step: Optional[Dict[str, Any]] = None
    if next_key:
        try:
            mode_info = modes_for_room.get(next_key)
            next_step = {
                "key": next_key,
                "label": getattr(mode_info, 'label', str(mode_info)) or next_key,
                "description": (getattr(mode_info, 'prompt', '') or '')[:300],
            }
        except Exception:
            next_step = {"key": next_key, "label": next_key, "description": ""}

    # Very lightweight heuristic: if chat has >8 messages and last role is assistant, consider almost ready
    try:
        from src.models import Message
        messages = (
            Message.query.filter_by(chat_id=chat.id).order_by(Message.timestamp).all()
        )
        num_messages = len(messages)
        last_role = messages[-1].role if messages else 'assistant'
    except Exception:
        num_messages = 0
        last_role = 'assistant'

    if num_messages >= 12 and last_role == 'assistant':
        rec_type = 'ready'
        confidence = 0.82
        message = 'You appear ready to progress to the next step.'
        suggestions: List[str] = []
    elif num_messages >= 6:
        rec_type = 'almost_ready'
        confidence = 0.65
        message = 'You are close to ready. Address a few items below.'
        suggestions = [
            'Summarize what you have accomplished in this step.',
            'Note any open questions to revisit later.',
            'Check alignment between your goals and current outputs.',
        ]
    else:
        rec_type = 'not_ready'
        confidence = 0.45
        message = 'Keep working in this step before moving forward.'
        suggestions = [
            'Add one specific example to support your reasoning.',
            'Clarify your main objective for this step in one sentence.',
            'List two next micro‑tasks you will complete.',
        ]

    return {
        "type": rec_type,
        "message": message,
        "confidence": confidence,
        "suggestions": suggestions,
        "next_step": next_step,
    }


def get_progression_recommendation_with_rubric(chat: Any) -> Dict[str, Any]:
    """Assess progression using saved rubric for the chat's current step.

    If a rubric exists for (room_id, chat.mode), we ask the LLM to score each
    criterion and compute a weighted average. If no API key or rubric, we
    gracefully fall back to get_progression_recommendation().
    """
    try:
        # Lazy import to avoid circulars
        from src.models import RubricCriterion, RubricLevel, RoomRubric

        room_id = chat.room_id
        step_key = getattr(chat, 'mode', None)
        if not step_key:
            return get_progression_recommendation(chat)

        # Load rubric
        criteria = (
            RubricCriterion.query.filter_by(room_id=room_id, step_key=step_key)
            .order_by(RubricCriterion.order)
            .all()
        )
        if not criteria:
            return get_progression_recommendation(chat)

        rubric = []
        for c in criteria:
            levels = RubricLevel.query.filter_by(criterion_id=c.id).order_by(RubricLevel.score).all()
            rubric.append({
                'name': c.name,
                'weight': float(c.weight or 1.0),
                'levels': [
                    {
                        'level': lv.level,
                        'score': int(lv.score),
                        'description': lv.description or ''
                    } for lv in levels
                ]
            })

        room_rubric = RoomRubric.query.filter_by(room_id=room_id, step_key=step_key).first()
        progression_threshold = float(room_rubric.progression_threshold if room_rubric else 2.5)

        # Build transcript (limit to last ~15 messages for brevity)
        from src.models import Message
        messages = (
            Message.query.filter_by(chat_id=chat.id)
            .order_by(Message.timestamp)
            .all()
        )
        tail = messages[-15:]

        # Prepare LLM prompt
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            try:
                # Compose rubric summary
                rubric_text_lines: List[str] = []
                for rc in rubric:
                    rubric_text_lines.append(f"Criterion: {rc['name']} (weight {rc['weight']:.2f})")
                    for lv in rc['levels']:
                        rubric_text_lines.append(f"  - {lv['score']}: {lv['level']} — {lv['description']}")
                rubric_text = "\n".join(rubric_text_lines)

                # Compose transcript summary
                transcript_lines: List[str] = []
                for m in tail:
                    who = 'User' if m.role == 'user' else 'Assistant'
                    content = (m.content or '')[:800]
                    transcript_lines.append(f"[{who}] {content}")
                transcript_text = "\n".join(transcript_lines)

                system = (
                    "You are an expert assessor. Score the user's current progress in the current learning step "
                    "using the provided rubric. Choose one score (1-4) per criterion with a one-sentence rationale. "
                    "Return ONLY JSON with this shape: {\n"
                    "  \"criteria\": [{\"name\": str, \"score\": 1|2|3|4, \"rationale\": str}],\n"
                    "  \"suggestions\": [str,...]\n"
                    "}. Do not include any extra text."
                )

                user_content = (
                    f"Rubric for step '{step_key}':\n{rubric_text}\n\n"
                    f"Recent transcript (most recent last):\n{transcript_text}"
                )

                response_text, _ = call_anthropic_api(
                    [{"role": "user", "content": user_content}], system_prompt=system, max_tokens=800
                )

                # Extract JSON
                import json, re
                match = re.search(r"\{[\s\S]*\}", response_text)
                parsed = json.loads(match.group(0)) if match else {}
                crit_scores = parsed.get('criteria', []) if isinstance(parsed, dict) else []
                suggestions = parsed.get('suggestions', []) if isinstance(parsed, dict) else []

            except Exception as e:
                current_app = None
                try:
                    from flask import current_app as _ca
                    current_app = _ca
                except Exception:
                    pass
                if current_app:
                    current_app.logger.warning(f"Rubric LLM assessment failed, falling back: {e}")
                crit_scores = []
                suggestions = []
        else:
            crit_scores = []
            suggestions = []

        # If no LLM scores, build naive mid-scores and generic suggestions
        if not crit_scores:
            crit_scores = [{"name": rc['name'], "score": 2, "rationale": "Baseline estimate without AI scoring."} for rc in rubric]
            if not suggestions:
                # Suggest next level descriptors from first two criteria
                for rc in rubric[:2]:
                    lv3 = next((lv for lv in rc['levels'] if lv['score'] == 3), None)
                    if lv3:
                        suggestions.append(f"Strengthen: {rc['name']} — {lv3['description']}")

        # Compute weighted average
        # Map criterion names to weights for safety
        name_to_weight = {rc['name']: rc['weight'] for rc in rubric}
        total_weight = sum(name_to_weight.values()) or 1.0
        weighted_sum = 0.0
        for cs in crit_scores:
            w = float(name_to_weight.get(cs.get('name'), 1.0))
            s = float(cs.get('score') or 0)
            weighted_sum += w * s
        overall = weighted_sum / total_weight

        # Determine recommendation type
        if overall >= progression_threshold + 0.2:
            rec_type = 'ready'
            msg = f"Overall score {overall:.2f} meets the rubric threshold {progression_threshold:.2f}."
            confidence = 0.85
        elif overall >= progression_threshold - 0.2:
            rec_type = 'almost_ready'
            msg = f"Overall score {overall:.2f} is close to the threshold {progression_threshold:.2f}."
            confidence = 0.7
        else:
            rec_type = 'not_ready'
            msg = f"Overall score {overall:.2f} is below the threshold {progression_threshold:.2f}."
            confidence = 0.55

        # Build next_step similar to previous helper
        try:
            modes_for_room = get_modes_for_room(chat.room) if getattr(chat, 'room', None) else BASE_MODES
        except Exception:
            modes_for_room = BASE_MODES
        mode_keys: List[str] = list(modes_for_room.keys())
        current_key: str = getattr(chat, 'mode', '') or (mode_keys[0] if mode_keys else '')
        next_key = None
        if current_key in mode_keys:
            idx = mode_keys.index(current_key)
            if idx + 1 < len(mode_keys):
                next_key = mode_keys[idx + 1]
        next_step = None
        if next_key:
            mi = modes_for_room.get(next_key)
            next_step = {
                'key': next_key,
                'label': getattr(mi, 'label', str(mi)) or next_key,
                'description': (getattr(mi, 'prompt', '') or '')[:300]
            }

        # If suggestions empty, create from lowest scored criteria
        if not suggestions:
            # Pick up to 3 lowest
            sorted_crit = sorted(crit_scores, key=lambda x: x.get('score', 0))
            for cs in sorted_crit[:3]:
                suggestions.append(f"Improve: {cs.get('name')} — {cs.get('rationale') or 'Provide stronger evidence or clarity.'}")

        return {
            'type': rec_type,
            'message': msg,
            'confidence': confidence,
            'suggestions': suggestions,
            'next_step': next_step,
        }
    except Exception:
        # Any failure, fall back to heuristic
        return get_progression_recommendation(chat)


def get_next_learning_step(chat: Any, target_mode: Optional[str] = None) -> str:
    """Get next learning step - simplified implementation."""
    return "Focus on integrating evidence and strengthening your argument structure."


def generate_chat_introduction(room_goals: str, template_type: str = None, learning_step: str = "step1", room_id: int = None, chat_id: int = None) -> str:
    """Generate smart chat introduction with contextual goals and starting tasks."""
    
    print(f"=== INTRODUCTION: template_type={template_type}, learning_step={learning_step}, room_id={room_id}, chat_id={chat_id} ===")
    
    # Get learning context first
    learning_context = None
    if room_id and chat_id:
        try:
            from src.utils.learning.context_manager import get_learning_context_for_room
            learning_context = get_learning_context_for_room(room_id, exclude_chat_id=chat_id)
            if learning_context:
                print(f"=== FOUND LEARNING CONTEXT: {len(learning_context)} chars ===")
            else:
                print(f"=== NO LEARNING CONTEXT found for room {room_id} ===")
        except Exception as e:
            print(f"=== ERROR getting learning context: {e} ===")
    
    # Use AI-generated smart welcome system (works with or without template_type)
    if learning_step:  # Only need learning_step, template_type can be None
        try:
            result = generate_ai_smart_welcome(
                room_goals=room_goals,
                template_type=template_type, 
                learning_step=learning_step,
                room_id=room_id,
                chat_id=chat_id,
                learning_context=learning_context
            )
            print(f"=== AI SMART WELCOME SUCCESS: {len(result)} chars ===")
            print(f"=== RETURNING AI RESULT: {result[:300]}... ===")
            return result
        except Exception as e:
            print(f"=== AI SMART WELCOME FAILED: {e} ===")
            # Continue to fallback
    
    # Enhanced fallback with learning context
    print(f"=== USING FALLBACK METHOD ===" )
    print(f"=== FALLBACK PARAMS: room_goals={room_goals[:100] if room_goals else 'None'}... learning_context={len(learning_context) if learning_context else 0} chars ===")
    
    if learning_context:
        context_preview = learning_context[:300] + "..." if len(learning_context) > 300 else learning_context
        
        # STEP 1 ENHANCEMENT: Add room goals to the working fallback
        room_goals_section = ""
        print(f"=== PROCESSING ROOM GOALS: '{room_goals}' ===")
        
        if room_goals and room_goals.strip():
            # Format room goals as bullet points
            goals = [goal.strip() for goal in room_goals.split('\n') if goal.strip()]
            print(f"=== PARSED GOALS: {goals} ===")
            
            if goals:
                formatted_goals = []
                for goal in goals[:3]:  # Take first 3 goals
                    if goal.startswith('To '):
                        goal = goal[3:]
                    goal = goal[0].upper() + goal[1:] if goal else goal
                    if not goal.endswith('.'):
                        goal += '.'
                    formatted_goals.append(f"• {goal}")
                
                print(f"=== FORMATTED GOALS: {formatted_goals} ===")
                
                if formatted_goals:
                    goals_text = '\n'.join(formatted_goals)
                    room_goals_section = f"\n\n🎯 Your Learning Goals:\n{goals_text}"
                    print(f"=== ROOM GOALS SECTION: {repr(room_goals_section)} ===")
        else:
            print(f"=== NO ROOM GOALS TO PROCESS ===")
        
        # STEP 2 ENHANCEMENT: Add learning mode information and starting task
        mode_section = ""
        if room_id:
            try:
                from src.models import CustomPrompt
                custom_prompt = CustomPrompt.query.filter_by(
                    room_id=room_id, mode_key=learning_step
                ).first()
                
                if custom_prompt:
                    mode_label = custom_prompt.label
                    mode_description = custom_prompt.prompt[:200] + "..." if len(custom_prompt.prompt) > 200 else custom_prompt.prompt
                    
                    mode_section = f"\n\n🚀 Your Starting Task:\n**{mode_label}**\n{mode_description}\n\nThis step builds on your previous insights and focuses on advancing your learning objectives."
                    print(f"=== MODE SECTION ADDED: {mode_label} ===")
                else:
                    print(f"=== NO CUSTOM PROMPT FOUND for {learning_step} ===")
            except Exception as e:
                print(f"=== ERROR getting mode info: {e} ===")
        
        enhanced_welcome = f"Welcome! Building on your previous discussion:\n\n{context_preview}{room_goals_section}{mode_section}\n\nReady to continue? Tell me what aspect you'd like to explore first!"
        print(f"=== STEP 2 ENHANCED FALLBACK: {len(enhanced_welcome)} chars ===")
        print(f"=== STEP 2 FULL CONTENT: {enhanced_welcome[:300]}... ===")
        return enhanced_welcome
    
    if not room_goals:
        print(f"=== FALLBACK: NO ROOM GOALS ===")
        return "Welcome! I'm here to help you with your learning. Let's work together to achieve your objectives.\n\nWhat would you like to work on today?"
    
    # Split goals by newlines and clean them up
    goals = [goal.strip() for goal in room_goals.split('\n') if goal.strip()]
    
    if not goals:
        return "Welcome! I'm here to help you with your learning. Let's work together to achieve your objectives.\n\nWhat would you like to work on today?"
    
    # Format goals as bullet points
    formatted_goals = []
    for goal in goals:
        # Remove "To " prefix if present and capitalize first letter
        if goal.startswith('To '):
            goal = goal[3:]  # Remove "To "
        # Capitalize first letter
        goal = goal[0].upper() + goal[1:] if goal else goal
        # Add period if not present
        if goal and not goal.endswith('.'):
            goal += '.'
        formatted_goals.append(f"• {goal}")
    
    goals_text = '\n'.join(formatted_goals)
    
    # Use double line breaks to ensure proper spacing in chat display
    return f"Welcome! I'm here to help you with your learning goals:\n\n{goals_text}\n\nLet's work together to achieve these objectives.\n\n**What would you like to do first?** You can:\n\n• Ask me questions about any of these goals\n• Tell me what you're currently working on\n• Ask for help with a specific problem or concept\n• Get guidance on how to approach your learning\n\nJust let me know how I can help you get started!"


def _get_openai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def call_openai_api(messages: List[Dict[str, str]], system_prompt: str = "", max_tokens: int = 300) -> Tuple[str, bool]:
    """Call OpenAI Chat Completions API with the given messages."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise Exception("OPENAI_API_KEY not found in environment variables")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    # Convert messages to OpenAI format (single combined user message for parity with Anthropic)
    user_messages: List[str] = []
    for msg in messages:
        if msg.get("role") != "system":
            user_messages.append(msg.get("content", ""))
    user_content = "\n\n".join(user_messages)

    chat_messages: List[Dict[str, str]] = []
    if system_prompt:
        chat_messages.append({"role": "system", "content": system_prompt})
    chat_messages.append({"role": "user", "content": user_content})

    data = {
        "model": _get_openai_model(),
        "max_tokens": max_tokens,
        "messages": chat_messages,
        # temperature kept default; parity with Anthropic usage
    }

    # Retry logic for transient errors
    import random
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions", 
                headers=headers, 
                json=data,
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Detect truncation: OpenAI returns finish_reason
            # Values: "stop" (natural), "length" (truncated), "content_filter"
            choice = result["choices"][0]
            finish_reason = choice.get("finish_reason", "")
            is_truncated = finish_reason == "length"
            
            text = choice["message"]["content"]
            
            if is_truncated:
                try:
                    current_app.logger.info(f"⚠️ OpenAI response truncated at {max_tokens} tokens")
                except:
                    pass
            
            return text, is_truncated
            
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 0
            
            # Retry on transient errors
            if status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                jitter = random.uniform(0.2, 0.5)
                backoff = jitter * (2 ** attempt)
                try:
                    current_app.logger.warning(
                        f"⚠️ OpenAI API error {status_code}, retrying in {backoff:.2f}s"
                    )
                except:
                    pass
                time.sleep(backoff)
                continue
            
            raise Exception(f"OpenAI API call failed: {str(e)}")
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                jitter = random.uniform(0.2, 0.5)
                try:
                    current_app.logger.warning(f"⚠️ OpenAI network error, retrying in {jitter:.2f}s")
                except:
                    pass
                time.sleep(jitter)
                continue
            raise Exception(f"OpenAI API call failed: {str(e)}")
        
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {str(e)}")


def call_ollama_api(messages: List[Dict[str, str]], system_prompt: str = "", max_tokens: int = 300) -> Tuple[str, bool]:
    """Call Ollama API - redirects to Anthropic for this simplified version."""
    return call_anthropic_api(messages, system_prompt, max_tokens)


def get_available_templates() -> Dict[str, Dict[str, str]]:
    """Get list of available base templates."""
    return {
        template_id: {
            "id": template_id,
            "name": template_data["name"],
            "description": template_data["description"],
        }
        for template_id, template_data in BASE_TEMPLATES.items()
    }


def generate_ai_smart_welcome(room_goals: str, template_type: str, learning_step: str, room_id: int, chat_id: int, learning_context: str = None) -> str:
    """
    Generate an AI-powered smart welcome message that integrates:
    1. Room goals (foundational objectives)
    2. Learning mode goals (specific step objectives) 
    3. Previous discussion context (notes from completed chats)
    4. Actionable guidance tailored to build on previous insights
    """
    
    # Get mode-specific information
    mode_info = None
    if room_id:
        try:
            from src.models import CustomPrompt
            custom_prompt = CustomPrompt.query.filter_by(
                room_id=room_id, mode_key=learning_step
            ).first()
            if custom_prompt:
                mode_info = {
                    "label": custom_prompt.label,
                    "prompt": custom_prompt.prompt
                }
        except Exception as e:
            print(f"Error getting mode info: {e}")
    
    # Fallback to base modes if no custom prompt
    if not mode_info and learning_step in BASE_MODES:
        mode_info = {
            "label": BASE_MODES[learning_step].label,
            "prompt": BASE_MODES[learning_step].prompt
        }
    
    # Template type mapping (handle None gracefully)
    template_names = {
        "academic-essay": "research academic essay",
        "study-group": "study group collaboration", 
        "business-hub": "business development",
        "creative-studio": "creative project",
        "writing-workshop": "writing workshop",
        "learning-lab": "hands-on learning",
        "community-space": "community building"
    }
    template_name = template_names.get(template_type, "learning project") if template_type else "learning project"
    
    # Build AI instruction (avoiding f-string with quotes)
    context_text = learning_context if learning_context else "This is the student's first chat in this room."
    mode_label = mode_info['label'] if mode_info else learning_step
    mode_objective = mode_info['prompt'][:200] if mode_info else 'General learning guidance'
    
    # Create clean, conversational AI instruction
    ai_instruction = f"""Create a welcoming, structured learning message that integrates:

ROOM GOALS: {room_goals}
CURRENT STEP: {mode_label}
STEP OBJECTIVE: {mode_objective}

PREVIOUS INSIGHTS: {context_text}

Create a message that:
1. Welcomes the learner with reference to previous work (if any)
2. Shows clear learning goals for this step
3. Provides specific guidance that builds on previous insights
4. Uses encouraging, professional tone

Format as:
- Conversational greeting
- "🎯 Learning Goals:" with 2-3 clear objectives
- "🚀 Your Next Step:" with specific guidance
- "Ready to continue?" call-to-action

Keep it clean, coherent, and encouraging. No technical metadata or truncated content."""

    # Call AI to generate the welcome message
    try:
        ai_welcome, _ = call_anthropic_api(
            [{"role": "user", "content": ai_instruction}],
            system_prompt="You are an expert instructional designer. Create structured, encouraging learning welcome messages.",
            max_tokens=800
        )
        
        print(f"=== AI GENERATED WELCOME: {len(ai_welcome)} chars ===")
        print(f"=== AI WELCOME CONTENT: {ai_welcome[:500]}... ===")
        print(f"=== ROOM GOALS USED: {room_goals[:200]}... ===")
        print(f"=== MODE INFO: {mode_info} ===")
        return ai_welcome
        
    except Exception as e:
        print(f"=== AI WELCOME GENERATION FAILED: {e} ===")
        # Fallback to enhanced template
        return generate_enhanced_template_welcome(room_goals, template_type, learning_step, learning_context, mode_info)


def generate_enhanced_template_welcome(room_goals: str, template_type: str, learning_step: str, learning_context: str = None, mode_info: dict = None) -> str:
    """Generate structured welcome using templates enhanced with learning context."""
    
    template_names = {
        "learning-lab": "hands-on learning",
        "academic-essay": "research academic essay",
        "study-group": "study group collaboration"
    }
    template_name = template_names.get(template_type, "learning project")
    
    # Parse room goals into bullet points
    goals = [goal.strip() for goal in room_goals.split('\n') if goal.strip()]
    formatted_goals = []
    for i, goal in enumerate(goals[:3]):  # Take first 3 goals
        if goal.startswith('To '):
            goal = goal[3:]
        goal = goal[0].upper() + goal[1:] if goal else goal
        if not goal.endswith('.'):
            goal += '.'
        formatted_goals.append(f"• {goal}")
    
    goals_text = '\n'.join(formatted_goals)
    
    # Build welcome message
    welcome = f"""Welcome! I'm here to help you with your {template_name}. Let's focus on these key goals for this step:

🎯 {learning_step.replace('step', 'Step ').title()} Learning Goals:
{goals_text}"""
    
    # Add learning context if available
    if learning_context:
        context_preview = learning_context[:300] + "..." if len(learning_context) > 300 else learning_context
        welcome += f"""

🧠 Building on Your Previous Discussion:
{context_preview}"""
    
    # Add starting task
    mode_label = mode_info['label'] if mode_info else f"Step {learning_step[-1]} Development"
    welcome += f"""

🚀 Your Starting Task:
{mode_label}
Let's begin by building on your previous insights and focusing on the specific objectives for this learning step.

Ready to start? Just say "Begin {mode_label.lower()}" or tell me about your {template_name}!

Alternative options:
• 📚 Tell me about your {template_name} progress first
• 🎯 Work on a different goal
• 📋 View all learning goals ({len(goals)} total available)

Just let me know how you'd like to begin!"""
    
    return welcome


def build_document_context_block(context_snippets: List[Dict[str, Any]]) -> str:
    """
    Build a formatted document context block from search results.
    
    Args:
        context_snippets: List of dicts with 'title', 'content', 'chunk_index', 'rank'
        
    Returns:
        Formatted string with document context, or empty string if no snippets
    """
    if not context_snippets:
        return ""
    
    context_lines = ["📚 Relevant Document Context:"]
    
    for snippet in context_snippets:
        title = snippet.get('title', 'Unknown Document')
        content = snippet.get('content', '')
        chunk_idx = snippet.get('chunk_index', 0)
        rank = snippet.get('rank', 0.0)
        
        # Truncate content if too long (keep first 400 chars to match synthesis limit)
        # Note: Chunks are already truncated in get_representative_chunks_from_all_documents,
        # but keep this as a safety net
        if len(content) > 400:
            content = content[:400] + "..."
        
        context_lines.append(f"\nFrom: {title} (chunk {chunk_idx}, relevance: {rank:.2f})")
        context_lines.append(f"{content}")
    
    return "\n".join(context_lines)
