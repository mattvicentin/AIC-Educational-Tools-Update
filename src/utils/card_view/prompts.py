"""
Card View Prompt Templates

Centralized prompt templates for AI-generated content:
- Guiding question (North Star for the message)
- Relationship hints (connections between adjacent cards)
"""

# Guiding Question Prompt
GUIDING_QUESTION_PROMPT = """You are writing one concise guiding question that the following message is trying to answer.

Rules:
- One sentence only
- Must end with a question mark (?)
- Do NOT summarize the content
- Focus on the central inquiry or goal of the message
- Keep it under 20 words

Message:
{message}

Guiding question:"""


# Relationship Hint Prompt (for a single pair)
RELATIONSHIP_HINT_PROMPT = """Given a guiding question and two adjacent cards from a segmented message, explain how Card B follows from Card A.

Guiding Question: {guiding_question}

Card A:
Header: {card_a_header}
Body: {card_a_body}

Card B:
Header: {card_b_header}
Body: {card_b_body}

Rules:
- One sentence only, maximum 25 words
- Do NOT summarize either card
- Focus on the logical or thematic CONNECTION between them
- Explain how B develops, extends, or shifts from A
- Reference the guiding question if relevant

Relationship hint:"""


# Batched Relationship Hints Prompt (all pairs at once)
RELATIONSHIP_HINTS_BATCH_PROMPT = """Given a guiding question and a series of card pairs, provide one-sentence relationship hints for each adjacent pair.

Guiding Question: {guiding_question}

{card_pairs}

Rules for EACH hint:
- One sentence only, maximum 25 words
- Do NOT summarize the cards
- Focus on the logical or thematic CONNECTION
- Explain how each card B develops, extends, or shifts from its card A

Return your hints as a numbered list matching the pair numbers:
1. [hint for pair 1]
2. [hint for pair 2]
...

Relationship hints:"""


# Template for formatting a single card pair in the batch prompt
CARD_PAIR_TEMPLATE = """
--- Pair {pair_num} ---
Card A ({card_a_header}):
{card_a_body}

Card B ({card_b_header}):
{card_b_body}
"""


# Fallback messages
FALLBACK_GUIDING_QUESTION = "What is the main point of this message?"  # Fallback for all failure cases
FALLBACK_RELATIONSHIP_HINT = "These sections are connected thematically."  # Non-empty fallback


def format_guiding_question_prompt(message: str, max_chars: int = 8000) -> str:
    """Format the guiding question prompt with truncated message."""
    truncated = message[:max_chars]
    if len(message) > max_chars:
        truncated += "\n\n[Message truncated for processing...]"
    return GUIDING_QUESTION_PROMPT.format(message=truncated)


def format_relationship_hint_prompt(
    guiding_question: str,
    card_a_header: str,
    card_a_body: str,
    card_b_header: str,
    card_b_body: str,
    max_body_chars: int = 600,
) -> str:
    """Format a single relationship hint prompt."""
    return RELATIONSHIP_HINT_PROMPT.format(
        guiding_question=guiding_question,
        card_a_header=card_a_header,
        card_a_body=card_a_body[:max_body_chars],
        card_b_header=card_b_header,
        card_b_body=card_b_body[:max_body_chars],
    )


def format_relationship_hints_batch_prompt(
    guiding_question: str,
    segments: list,
    max_body_chars: int = 400,
) -> str:
    """Format a batched relationship hints prompt for all adjacent pairs."""
    pairs_text = ""
    for i in range(len(segments) - 1):
        card_a = segments[i]
        card_b = segments[i + 1]
        
        # Add truncation marker if card is truncated
        card_a_body = card_a.body[:max_body_chars]
        card_b_body = card_b.body[:max_body_chars]
        
        if getattr(card_a, 'is_truncated', False):
            card_a_body = "[TRUNCATED] " + card_a_body
        if getattr(card_b, 'is_truncated', False):
            card_b_body = "[TRUNCATED] " + card_b_body
        
        pairs_text += CARD_PAIR_TEMPLATE.format(
            pair_num=i + 1,
            card_a_header=card_a.header,
            card_a_body=card_a_body,
            card_b_header=card_b.header,
            card_b_body=card_b_body,
        )
    
    return RELATIONSHIP_HINTS_BATCH_PROMPT.format(
        guiding_question=guiding_question,
        card_pairs=pairs_text,
    )
