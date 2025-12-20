"""
Goal generation factory
Provides backward compatibility while using the registry pattern for template discovery
"""

from typing import Dict, List, Any, Callable, Optional
from .base import GoalGenerator
from .registry import GoalGeneratorRegistry
from .types import (
    AnswersDict, 
    CategorizedGoals, 
    GoalList, 
    TemplateType, 
    FactoryResult, 
    LegacyGoalFunction,
    CategorizationResult,
    TemplateValidation,
    GoalStats
)

# Import all generators to ensure they register themselves
from .study_group import StudyGroupGoalGenerator, generate_study_group_goals
from .business_hub import BusinessHubGoalGenerator, generate_business_hub_goals
from .creative_studio import CreativeStudioGoalGenerator, generate_creative_studio_goals
from .writing_workshop import WritingWorkshopGoalGenerator, generate_writing_workshop_goals
from .learning_lab import LearningLabGoalGenerator, generate_learning_lab_goals
from .community_space import CommunitySpaceGoalGenerator, generate_community_space_goals
from .academic_essay import AcademicEssayGoalGenerator, generate_academic_essay_goals


def generate_template_goals(template_type: TemplateType) -> FactoryResult:
    """
    Factory function to generate goals for a specific template.
    This maintains backward compatibility while using the registry pattern.
    
    Args:
        template_type: Type of template (study-group, business-hub, etc.)
        
    Returns:
        Goal generation function for the specified template, or None if not supported
    """
    # Map template types to their backward compatibility functions
    template_functions: Dict[TemplateType, LegacyGoalFunction] = {
        "study-group": generate_study_group_goals,
        "business-hub": generate_business_hub_goals,
        "creative-studio": generate_creative_studio_goals,
        "writing-workshop": generate_writing_workshop_goals,
        "learning-lab": generate_learning_lab_goals,
        "community-space": generate_community_space_goals,
        "academic-essay": generate_academic_essay_goals,
    }
    
    return template_functions.get(template_type)


def generate_categorized_goals(template_type: TemplateType, answers: AnswersDict) -> CategorizedGoals:
    """
    Generate categorized goals for a template using the registry pattern.
    This is the new interface that returns categorized goals.
    
    Args:
        template_type: Type of template
        answers: Template form answers
        
    Returns:
        Categorized goals dictionary
    """
    generator = GoalGeneratorRegistry.create_generator(template_type)
    
    if generator:
        return generator.generate_goals(answers)
    
    # For any other templates, return empty categorized goals
    # This ensures we don't break existing functionality
    return {
        "core_goals": [],
        "collaboration_goals": [],
        "reflection_goals": []
    }


def get_supported_templates() -> List[TemplateType]:
    """
    Get list of supported templates from registry.
    
    Returns:
        List of supported template type identifiers
    """
    return GoalGeneratorRegistry.get_supported_templates()


def is_template_supported(template_type: TemplateType) -> bool:
    """
    Check if a template type is supported.
    
    Args:
        template_type: The template type identifier
        
    Returns:
        True if the template type is supported, False otherwise
    """
    return GoalGeneratorRegistry.is_supported(template_type)


def validate_template(template_type: TemplateType) -> TemplateValidation:
    """
    Validate a template type and provide detailed information.
    
    Args:
        template_type: The template type identifier
        
    Returns:
        Validation result with detailed information
    """
    supported_templates = get_supported_templates()
    is_valid = is_template_supported(template_type)
    
    return {
        "is_valid": is_valid,
        "supported_templates": supported_templates,
        "error_message": None if is_valid else f"Template type '{template_type}' is not supported"
    }


def get_goal_stats(template_type: TemplateType, answers: AnswersDict) -> GoalStats:
    """
    Get statistics about generated goals for a template.
    
    Args:
        template_type: The template type identifier
        answers: Template form answers
        
    Returns:
        Goal statistics including counts for each category
    """
    goals = generate_categorized_goals(template_type, answers)
    
    return {
        "total_goals": len(goals.get("core_goals", [])) + len(goals.get("collaboration_goals", [])) + len(goals.get("reflection_goals", [])),
        "core_count": len(goals.get("core_goals", [])),
        "collaboration_count": len(goals.get("collaboration_goals", [])),
        "reflection_count": len(goals.get("reflection_goals", [])),
        "template_type": template_type
    }


def categorize_legacy_goals(goals: GoalList) -> CategorizationResult:
    """
    Categorize legacy flat goal list into categories.
    
    Args:
        goals: Flat list of goals
        
    Returns:
        Categorized goals dictionary
    """
    if not goals:
        return {
            "core_goals": [],
            "collaboration_goals": [],
            "reflection_goals": []
        }
    
    # Default categorization: first 4 = core, next 3 = collaboration, rest = reflection
    core_count = min(4, len(goals))
    collab_count = min(3, max(0, len(goals) - core_count))
    
    return {
        "core_goals": goals[:core_count],
        "collaboration_goals": goals[core_count:core_count + collab_count],
        "reflection_goals": goals[core_count + collab_count:]
    }
