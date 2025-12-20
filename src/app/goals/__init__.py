"""
Goal generation module for AI Collab Online
Extracted from room.py to improve maintainability and enable goal categorization
"""

from .factory import (
    generate_template_goals, 
    generate_categorized_goals, 
    get_supported_templates, 
    is_template_supported,
    validate_template,
    get_goal_stats
)
from .base import GoalGenerator
from .registry import GoalGeneratorRegistry
from .types import (
    AnswersDict,
    CategorizedGoals,
    GoalList,
    TemplateType,
    SubjectType,
    GroupSizeType,
    EssayTypeType,
    BusinessTypeType,
    CreativeMediumType,
    WritingTypeType,
    LearningStyleType,
    CommunityTypeType,
    SkillLevelType,
    ExperienceLevelType,
    TeamStructureType,
    GoalTypeType
)
from .study_group import StudyGroupGoalGenerator, generate_study_group_goals
from .business_hub import BusinessHubGoalGenerator, generate_business_hub_goals
from .creative_studio import CreativeStudioGoalGenerator, generate_creative_studio_goals
from .writing_workshop import WritingWorkshopGoalGenerator, generate_writing_workshop_goals
from .learning_lab import LearningLabGoalGenerator, generate_learning_lab_goals
from .community_space import CommunitySpaceGoalGenerator, generate_community_space_goals
from .academic_essay import AcademicEssayGoalGenerator, generate_academic_essay_goals

__all__ = [
    # Factory functions
    "generate_template_goals",
    "generate_categorized_goals",
    "get_supported_templates",
    "is_template_supported",
    "validate_template",
    "get_goal_stats",
    
    # Base classes
    "GoalGenerator",
    "GoalGeneratorRegistry",
    
    # Type definitions
    "AnswersDict",
    "CategorizedGoals",
    "GoalList",
    "TemplateType",
    "SubjectType",
    "GroupSizeType",
    "EssayTypeType",
    "BusinessTypeType",
    "CreativeMediumType",
    "WritingTypeType",
    "LearningStyleType",
    "CommunityTypeType",
    "SkillLevelType",
    "ExperienceLevelType",
    "TeamStructureType",
    "GoalTypeType",
    
    # Template generators
    "StudyGroupGoalGenerator",
    "generate_study_group_goals",
    "BusinessHubGoalGenerator",
    "generate_business_hub_goals",
    "CreativeStudioGoalGenerator",
    "generate_creative_studio_goals",
    "WritingWorkshopGoalGenerator",
    "generate_writing_workshop_goals",
    "LearningLabGoalGenerator",
    "generate_learning_lab_goals",
    "CommunitySpaceGoalGenerator",
    "generate_community_space_goals",
    "AcademicEssayGoalGenerator",
    "generate_academic_essay_goals"
]
