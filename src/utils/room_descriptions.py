"""
Room Description Generation
Generates short narrative descriptions for rooms based on template type and characteristics.
"""

from typing import Dict, Optional
from src.models.room import Room
from src.app import db


# Predefined short descriptions for each template type
TEMPLATE_DESCRIPTIONS = {
    "academic-essay": {
        "name": "Academic Research Essay",
        "short_description": "Transform your research ideas into compelling academic essays with expert AI guidance! Master the complete research process from topic selection to final presentation. Join fellow scholars to develop critical thinking skills and create papers that stand out. Your path to academic excellence starts here!"
    },
    "study-group": {
        "name": "Study Group",
        "short_description": "Unlock the power of collaborative learning! Join forces with peers to tackle challenging concepts, share insights, and accelerate your understanding. Experience the magic of group problem-solving where everyone's perspective makes the whole team stronger. Together, you'll achieve more than you ever could alone!"
    },
    "business-hub": {
        "name": "Business Hub",
        "short_description": "Launch your entrepreneurial dreams into reality! Connect with ambitious professionals to develop business strategies, validate ideas, and build your network. Whether you're starting a startup or scaling an enterprise, this is where innovative minds converge to create the next big thing!"
    },
    "creative-studio": {
        "name": "Creative Studio",
        "short_description": "Ignite your artistic passion and push creative boundaries! Experiment with new mediums, techniques, and styles in a supportive environment. Collaborate with fellow artists to inspire each other and develop your unique creative voice. Your masterpiece is waiting to be discovered!"
    },
    "writing-workshop": {
        "name": "Writing Workshop",
        "short_description": "Craft compelling stories and powerful prose that captivates readers! Whether you're writing fiction, academic papers, or professional content, develop your voice with expert guidance. Join a community of writers who will challenge, inspire, and elevate your writing to new heights!"
    },
    "learning-lab": {
        "name": "Learning Lab",
        "short_description": "Learn by doing in this hands-on experimentation space! Master new skills through practical projects, real-world applications, and guided discovery. Perfect for those who learn best through active engagement. Turn theory into practice and watch your confidence soar!"
    },
    "community-space": {
        "name": "Community Space",
        "short_description": "Build meaningful connections and create lasting impact! Connect with like-minded individuals who share your passions and goals. Whether you're networking professionally or building personal relationships, this space fosters authentic connections that can change your life!"
    }
}


def generate_unique_room_name(base_name: str, user_id: int) -> str:
    """
    Generate a unique room name by checking for existing names and appending numbers.
    
    Args:
        base_name: The base room name to make unique
        user_id: The user ID to check against
        
    Returns:
        A unique room name (e.g., "Research Academic Essay", "Research Academic Essay (2)")
    """
    # Check if the base name already exists for this user
    existing_room = Room.query.filter_by(
        owner_id=user_id,
        name=base_name,
        is_active=True
    ).first()
    
    if not existing_room:
        return base_name
    
    # If base name exists, try with numbers
    counter = 2
    while True:
        new_name = f"{base_name} ({counter})"
        existing_room = Room.query.filter_by(
            owner_id=user_id,
            name=new_name,
            is_active=True
        ).first()
        
        if not existing_room:
            return new_name
        
        counter += 1
        
        # Safety check to prevent infinite loops
        if counter > 100:
            # Fallback: add timestamp to make it unique
            from datetime import datetime
            timestamp = datetime.now().strftime("%m-%d")
            return f"{base_name} ({timestamp})"


def generate_room_short_description(template_type: str, room_name: str = "", group_size: str = "", goals: str = "") -> str:
    """
    Generate a short narrative description for a room based on template type and characteristics.
    
    Args:
        template_type: The template type (e.g., "academic-essay", "study-group")
        room_name: Optional room name for customization
        group_size: Optional group size for context
        goals: Optional goals for additional context
        
    Returns:
        Short narrative description (max 300 characters)
    """
    
    # Get base description for template type
    template_key = template_type or "general"
    template_info = TEMPLATE_DESCRIPTIONS.get(template_key, {})
    base_description = template_info.get("short_description", "")
    
    if not base_description:
        # Enhanced description for custom rooms - use goals if available
        if template_key == "general" and goals:
            # Clean up goals text
            goals_cleaned = goals.strip()
            
            # Try to extract multiple sentences/goals
            # First, split by newlines (for bullet-point style goals)
            lines = [line.strip() for line in goals_cleaned.splitlines() if line.strip()]
            
            # If we have multiple lines, use first two
            if len(lines) > 1:
                first_goal = lines[0].strip('.').strip()
                second_goal = lines[1].strip('.').strip()
            else:
                # Single paragraph - split by sentences
                # Handle common sentence endings
                sentences = []
                for part in goals_cleaned.replace('? ', '.|').replace('! ', '.|').split('.'):
                    cleaned = part.replace('|', '. ').strip()
                    if cleaned and len(cleaned) > 10:  # Ignore very short fragments
                        sentences.append(cleaned)
                
                first_goal = sentences[0] if len(sentences) > 0 else ""
                second_goal = sentences[1] if len(sentences) > 1 else ""
            
            # Build description from goals
            if first_goal and len(first_goal) > 10:
                # Capitalize first letter if needed
                if first_goal[0].islower():
                    first_goal = first_goal[0].upper() + first_goal[1:]
                
                # Build the description
                if second_goal and len(second_goal) > 10:
                    # Capitalize second goal if needed
                    if second_goal[0].islower():
                        second_goal = second_goal[0].upper() + second_goal[1:]
                    
                    description = f"{first_goal}. {second_goal}."
                else:
                    # Only one goal - just use it
                    description = f"{first_goal}."
                
                # Ensure it's not too long (max 300 chars)
                if len(description) > 300:
                    # Truncate at word boundary
                    description = description[:297]
                    last_space = description.rfind(' ')
                    if last_space > 200:
                        description = description[:last_space] + "..."
                    else:
                        description = description + "..."
                
                return description
        
        # Fallback to room name if no goals
        if template_key == "general" and room_name:
            title_lower = room_name.lower()
            if title_lower and len(title_lower) > 3:
                return (
                    f"A collaborative learning space focused on {title_lower}. "
                    f"Designed to help you achieve your learning goals through structured guidance and support."
                )
        
        # Final fallback for unknown template types
        safe_label = str(template_key).replace('-', ' ')
        return (
            f"A collaborative learning space for {safe_label} learning. Designed to help you "
            f"achieve your learning goals through structured guidance and support."
        )
    
    # Customize based on group size if provided
    if group_size:
        size_context = {
            "individual": "individual learners",
            "small": "small groups (2-3 people)",
            "medium": "medium groups (4-6 people)", 
            "large": "larger teams (7+ people)"
        }.get(group_size, "collaborative teams")
        
        # Replace generic terms with specific group size (only once)
        if "students" in base_description:
            base_description = base_description.replace("students", size_context, 1)
        elif "teams" in base_description:
            base_description = base_description.replace("teams", size_context, 1)
        elif "groups" in base_description:
            base_description = base_description.replace("groups", size_context, 1)
    
    # Ensure description doesn't exceed 300 characters
    if len(base_description) > 300:
        # Truncate at word boundary
        truncated = base_description[:297] + "..."
        # Find last complete word
        last_space = truncated.rfind(' ')
        if last_space > 250:  # Only truncate if we have a reasonable word boundary
            base_description = truncated[:last_space] + "..."
        else:
            base_description = truncated
    
    return base_description


def get_template_display_name(template_type: str) -> str:
    """
    Get the display name for a template type.
    
    Args:
        template_type: The template type
        
    Returns:
        Display name for the template
    """
    template_key = template_type or "general"
    template_info = TEMPLATE_DESCRIPTIONS.get(template_key, {})
    return template_info.get("name", str(template_key).replace("-", " ").title())


def get_available_template_descriptions() -> Dict[str, Dict[str, str]]:
    """
    Get all available template descriptions for UI display.
    
    Returns:
        Dictionary of template types with their names and descriptions
    """
    return TEMPLATE_DESCRIPTIONS


def infer_template_type_from_room(room_name: str, goals: str = "", description: str = "") -> Optional[str]:
    """
    Infer template type from room characteristics for auto-generation.
    
    Args:
        room_name: Room name
        goals: Room goals
        description: Room description
        
    Returns:
        Inferred template type or None
    """
    if not room_name and not goals and not description:
        return None
    
    # Combine all text for analysis
    text_to_analyze = f"{room_name} {goals} {description}".lower()
    
    # Template detection patterns
    template_patterns = {
        "academic-essay": [
            "research", "essay", "academic", "writing", "literature review",
            "thesis", "argument", "citation", "academic writing"
        ],
        "study-group": [
            "study", "collaborative", "peer", "group", "learning together",
            "shared", "collective", "team study"
        ],
        "business-hub": [
            "business", "entrepreneur", "startup", "market", "strategy",
            "commercial", "enterprise", "corporate", "business plan"
        ],
        "creative-studio": [
            "creative", "art", "design", "artistic", "visual", "portfolio",
            "creative project", "artistic expression", "design thinking"
        ],
        "writing-workshop": [
            "writing", "workshop", "creative writing", "storytelling",
            "narrative", "composition", "writing skills"
        ],
        "learning-lab": [
            "lab", "experiment", "hands-on", "practical", "skills",
            "experiential", "learning lab", "practical skills"
        ],
        "community-space": [
            "community", "network", "social", "connection", "collaboration",
            "community building", "networking", "social learning"
        ]
    }
    
    # Score each template based on pattern matches
    template_scores = {}
    for template, patterns in template_patterns.items():
        score = 0
        for pattern in patterns:
            if pattern in text_to_analyze:
                score += 1
        template_scores[template] = score
    
    # Return the template with the highest score
    if template_scores:
        best_template = max(template_scores.items(), key=lambda x: x[1])
        if best_template[1] > 0:  # Only return if we have some confidence
            return best_template[0]
    
    return None
