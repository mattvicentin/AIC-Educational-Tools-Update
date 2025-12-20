#!/usr/bin/env python3
"""
pin_synthesis.py
Purpose: AI prompts and generation for pin-seeded chats
Status: [ACTIVE]
Created: 2025-12-04
Author: AI Collab Team

Provides PIN_SYNTHESIS_OPTIONS with prompts for each option type,
and functions to generate AI introductions and ongoing context for pin chats.
"""

from typing import List, Dict, Any, Optional
import json
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# PIN SYNTHESIS OPTIONS
# =============================================================================

PIN_SYNTHESIS_OPTIONS: Dict[str, Dict[str, str]] = {
    "explore": {
        "label": "Explore & Brainstorm",
        "prompt": """You are a creative thinking facilitator helping users explore ideas and connections.

Using the pinned insights provided as context, help the user:
- Discover unexpected connections between ideas
- Generate new possibilities and directions
- Ask probing questions to deepen exploration
- Encourage divergent thinking and creative leaps

Be curious, encouraging, and help them see their pinned content from new angles.""",
        "intro_focus": "exploring connections and brainstorming new ideas"
    },
    
    "study": {
        "label": "Study & Master",
        "prompt": """You are an expert tutor helping users deeply understand and master content.

Using the pinned insights as study material, help the user:
- Explain concepts clearly and thoroughly
- Test understanding through questions and scenarios
- Identify knowledge gaps and address them
- Use active recall and spaced repetition principles
- Create mental models and connections between concepts

Be patient, thorough, and adapt your teaching to their level of understanding.""",
        "intro_focus": "studying and mastering the key concepts"
    },
    
    "research_essay": {
        "label": "Draft Research Essay",
        "prompt": """You are an academic writing coach helping users draft well-structured essays.

Using the pinned insights as source material, help the user:
- Identify a clear thesis or central argument
- Organize ideas into a logical structure
- Synthesize evidence from the pinned content
- Develop strong topic sentences and transitions
- Maintain academic tone and proper attribution

Guide them through the drafting process step by step.""",
        "intro_focus": "drafting a research essay from these insights"
    },
    
    "presentation": {
        "label": "Build Presentation",
        "prompt": """You are a presentation coach helping users create compelling presentations.

Using the pinned insights as content, help the user:
- Structure a clear narrative arc
- Identify key messages and supporting points
- Design engaging slide content (not visuals)
- Develop strong openings and closings
- Prepare for Q&A and audience engagement

Focus on clarity, impact, and audience connection.""",
        "intro_focus": "building a compelling presentation"
    },
    
    "learning_exercise": {
        "label": "Create Learning Exercise",
        "prompt": """You are a pedagogical designer creating engaging learning exercises.

Using the pinned insights as subject matter, help the user create:
- Interactive debates or discussions
- Role-play scenarios or simulations
- Quiz questions and assessments
- Problem-based learning activities
- Collaborative group exercises

Design exercises that promote active learning and deep engagement.""",
        "intro_focus": "creating engaging learning exercises"
    },
    
    "startup": {
        "label": "Plan Startup",
        "prompt": """You are a startup advisor helping users develop business ideas.

Using the pinned insights as inspiration or market research, help the user:
- Identify business opportunities and gaps
- Develop value propositions
- Analyze target markets and customers
- Consider business models and revenue streams
- Plan next steps and validation approaches

Be practical, encouraging, and help them think through assumptions.""",
        "intro_focus": "developing startup ideas and business plans"
    },
    
    "artistic": {
        "label": "Create Something Artistic",
        "prompt": """You are a creative collaborator helping users with artistic projects.

Using the pinned insights as inspiration, help the user:
- Explore creative interpretations and expressions
- Develop artistic concepts and themes
- Brainstorm formats (writing, visual, performance, etc.)
- Refine creative vision and voice
- Work through creative blocks

Be imaginative, supportive, and honor their creative instincts.""",
        "intro_focus": "creating artistic work inspired by these insights"
    },
    
    "social_impact": {
        "label": "Create Social Impact",
        "prompt": """You are a social impact strategist helping users create positive change.

Using the pinned insights as context, help the user:
- Identify opportunities for meaningful impact
- Understand stakeholders and communities affected
- Develop actionable intervention strategies
- Consider sustainability and scalability
- Plan for measuring outcomes

Be thoughtful about ethics, equity, and unintended consequences.""",
        "intro_focus": "creating positive social impact"
    },
    
    "analyze": {
        "label": "Analyze & Summarize",
        "prompt": """You are an analytical assistant helping users make sense of information.

Using the pinned insights, help the user:
- Identify patterns, themes, and key takeaways
- Synthesize information across multiple sources
- Highlight contradictions or gaps
- Create clear summaries and conclusions
- Generate actionable insights

Be thorough, objective, and help them see the big picture.""",
        "intro_focus": "analyzing and synthesizing these insights"
    }
}


# =============================================================================
# CONTEXT FORMATTING
# =============================================================================

def format_pins_for_context(
    pins: List[Dict[str, Any]], 
    max_chars: int = 15000
) -> str:
    """
    Format pins into a context string for AI prompts.
    
    Args:
        pins: List of pin dictionaries (from PinChatMetadata.pins)
        max_chars: Maximum characters for the combined context
        
    Returns:
        Formatted string with pin content
    """
    if not pins:
        return ""
    
    lines = []
    total_chars = 0
    
    for i, pin in enumerate(pins, 1):
        content = pin.get("content", "")
        author = pin.get("author", "Unknown")
        role = pin.get("role", "")
        
        # Format each pin
        role_label = f" ({role})" if role else ""
        pin_text = f"[Pin {i}]{role_label} by {author}:\n{content}"
        
        # Check if adding this pin would exceed limit
        if total_chars + len(pin_text) + 2 > max_chars:
            remaining = len(pins) - i + 1
            lines.append(f"\n[...{remaining} more pins truncated for length]")
            break
        
        lines.append(pin_text)
        total_chars += len(pin_text) + 2  # +2 for newlines
    
    return "\n\n".join(lines)


def get_pin_chat_system_prompt(
    option: str,
    pins: List[Dict[str, Any]],
    room_goals: Optional[str] = None
) -> str:
    """
    Build the full system prompt for a pin chat.
    
    Args:
        option: The pin synthesis option (e.g., "explore", "study")
        pins: List of pin dictionaries
        room_goals: Optional room goals for additional context
        
    Returns:
        Complete system prompt string
    """
    # Get option config (fallback to analyze if unknown)
    option_config = PIN_SYNTHESIS_OPTIONS.get(option, PIN_SYNTHESIS_OPTIONS["analyze"])
    base_prompt = option_config["prompt"]
    
    # Format pins as context
    pins_context = format_pins_for_context(pins)
    
    # Build full prompt
    prompt_parts = [base_prompt]
    
    if pins_context:
        prompt_parts.append(f"\n\n=== PINNED INSIGHTS ({len(pins)} pins) ===\n{pins_context}")
    
    if room_goals:
        # Truncate very long goals
        goals_text = room_goals[:500] + "..." if len(room_goals) > 500 else room_goals
        prompt_parts.append(f"\n\n=== ROOM GOALS ===\n{goals_text}")
    
    return "\n".join(prompt_parts)


# =============================================================================
# INTRODUCTION GENERATION
# =============================================================================

def generate_pin_chat_introduction(
    pins: List[Dict[str, Any]],
    option: str,
    room_goals: Optional[str] = None,
    room_name: Optional[str] = None
) -> str:
    """
    Generate an AI introduction for a pin-seeded chat.
    
    This function calls the AI API to generate a contextual welcome message.
    Falls back to a template if AI fails.
    
    Args:
        pins: List of pin dictionaries
        option: The synthesis option selected
        room_goals: Optional room goals
        room_name: Optional room name for context
        
    Returns:
        Introduction message string
    """
    option_config = PIN_SYNTHESIS_OPTIONS.get(option, PIN_SYNTHESIS_OPTIONS["analyze"])
    option_label = option_config["label"]
    intro_focus = option_config["intro_focus"]
    pin_count = len(pins)
    
    # Try AI-generated intro
    try:
        from src.utils.openai_utils import call_anthropic_api
        
        # Build pin summaries for the prompt
        pin_summaries = []
        for i, pin in enumerate(pins[:5], 1):  # First 5 pins for intro
            content = pin.get("content", "")[:200]
            pin_summaries.append(f"Pin {i}: {content}...")
        pins_preview = "\n".join(pin_summaries)
        
        prompt = f"""Generate a welcoming introduction for a chat focused on {intro_focus}.

The user has selected {pin_count} pinned insights to work with. Here's a preview:
{pins_preview}

Write a warm, engaging introduction (150-200 words) that:
1. Welcomes them and acknowledges the {pin_count} pins they've gathered
2. Briefly mentions what you notice about the content themes
3. Explains how you'll help them with {intro_focus}
4. Offers 2-3 specific ways to get started

Use markdown formatting. Be encouraging but professional."""

        response, _ = call_anthropic_api(
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are a helpful AI assistant creating a welcome message.",
            max_tokens=400
        )
        
        if response and len(response.strip()) > 50:
            logger.info(f"AI intro generated for pin chat, option={option}, pins={pin_count}")
            return response.strip()
            
    except Exception as e:
        logger.warning(f"AI intro generation failed for pin chat: {e}")
    
    # Fallback to template
    return _generate_template_intro(pins, option, option_label, intro_focus, room_goals, room_name)


def _generate_template_intro(
    pins: List[Dict[str, Any]],
    option: str,
    option_label: str,
    intro_focus: str,
    room_goals: Optional[str] = None,
    room_name: Optional[str] = None
) -> str:
    """Generate a template-based introduction as fallback."""
    pin_count = len(pins)
    
    # Build pin preview
    pin_previews = []
    for pin in pins[:3]:
        content = pin.get("content", "")
        preview = content[:100] + "..." if len(content) > 100 else content
        pin_previews.append(f"• {preview}")
    
    if pin_count > 3:
        pin_previews.append(f"• ...and {pin_count - 3} more pins")
    
    pins_text = "\n".join(pin_previews)
    
    # Room context
    room_context = ""
    if room_name:
        room_context = f" in **{room_name}**"
    
    goals_section = ""
    if room_goals:
        goals_preview = room_goals[:150] + "..." if len(room_goals) > 150 else room_goals
        goals_section = f"\n\n🎯 **Room Goals:** {goals_preview}"
    
    return f"""Welcome! I'm here to help you with **{option_label}**{room_context} using your **{pin_count} pinned insights**.

📌 **Your Pinned Context:**
{pins_text}
{goals_section}

I'll focus on {intro_focus} based on this content.

**How would you like to begin?**
• Share what drew you to these particular insights
• Ask me to identify themes or patterns
• Tell me your specific goal for this session

Let me know how I can help!"""


# =============================================================================
# TITLE GENERATION
# =============================================================================

def generate_pin_chat_title(
    room_name: str,
    option: str,
    pins: Optional[List[Dict[str, Any]]] = None
) -> str:
    """
    Generate a title for a pin-seeded chat.
    
    Args:
        room_name: Name of the room
        option: The synthesis option
        pins: Optional list of pins (for future AI-based title generation)
        
    Returns:
        Chat title string
    """
    option_config = PIN_SYNTHESIS_OPTIONS.get(option, PIN_SYNTHESIS_OPTIONS["analyze"])
    option_label = option_config["label"]
    
    title = f"Pinned Insights — {option_label} — {room_name}"
    
    # Truncate if too long
    if len(title) > 120:
        title = title[:117] + "..."
    
    return title

