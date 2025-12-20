"""
Type definitions for the goal generation system
Provides comprehensive type safety for all template goal generators
"""

from typing import Literal, Dict, List, Any, TypedDict, Union, Optional

# Template-specific literal types
SubjectType = Literal["math", "science", "literature", "history", "languages", "other", "general"]
GroupSizeType = Literal["small", "medium", "large", "individual"]
EssayTypeType = Literal["research", "argumentative", "analytical"]
BusinessTypeType = Literal["startup", "entrepreneurship", "consulting", "corporate", "freelance"]
CreativeMediumType = Literal["visual_arts", "digital_design", "content_creation", "creative_writing", "music_performance"]
WritingTypeType = Literal["academic", "creative", "technical", "business"]
LearningStyleType = Literal["hands_on", "project_based", "research_based", "collaborative"]
CommunityTypeType = Literal["social_justice", "environmental", "health_wellness", "education"]
SkillLevelType = Literal["beginner", "developing", "advanced"]
ExperienceLevelType = Literal["beginner", "intermediate", "advanced"]
TeamStructureType = Literal["small", "medium", "large"]
GoalTypeType = Literal["exam_prep", "project_work", "homework_help", "concept_review"]

# Common type aliases
AnswersDict = Dict[str, Any]
CategorizedGoals = Dict[str, List[str]]
GoalList = List[str]
TemplateType = str

# Structured types for template answers
class StudyGroupAnswers(TypedDict, total=False):
    subject: SubjectType
    group_size: GroupSizeType
    goal_type: GoalTypeType

class BusinessHubAnswers(TypedDict, total=False):
    business_type: BusinessTypeType
    team_structure: TeamStructureType
    focus_area: str

class CreativeStudioAnswers(TypedDict, total=False):
    medium: CreativeMediumType
    skill_level: SkillLevelType
    project_type: str
    group_size: GroupSizeType

class WritingWorkshopAnswers(TypedDict, total=False):
    writing_type: WritingTypeType
    experience_level: ExperienceLevelType
    workshop_focus: str
    group_size: GroupSizeType

class LearningLabAnswers(TypedDict, total=False):
    learning_style: LearningStyleType
    subject_area: str
    goal: str
    group_size: GroupSizeType

class CommunitySpaceAnswers(TypedDict, total=False):
    community_type: CommunityTypeType
    purpose: str
    group_size: GroupSizeType

class AcademicEssayAnswers(TypedDict, total=False):
    essay_type: EssayTypeType
    writing_focus: str
    group_size: GroupSizeType

# Union type for all possible answer types
TemplateAnswers = Union[
    StudyGroupAnswers,
    BusinessHubAnswers,
    CreativeStudioAnswers,
    WritingWorkshopAnswers,
    LearningLabAnswers,
    CommunitySpaceAnswers,
    AcademicEssayAnswers
]

# Type for goal generation results
class GoalGenerationResult(TypedDict):
    core_goals: List[str]
    collaboration_goals: List[str]
    reflection_goals: List[str]

# Type for registry operations
class RegistryInfo(TypedDict):
    template_type: TemplateType
    generator_class: str
    is_supported: bool

# Type for factory function results
FactoryResult = Optional[Any]  # Callable[[AnswersDict], GoalList] | None

# Type for categorization results
CategorizationResult = Dict[str, List[str]]

# Type for template validation
class TemplateValidation(TypedDict):
    is_valid: bool
    supported_templates: List[TemplateType]
    error_message: Optional[str]

# Type for goal generation statistics
class GoalStats(TypedDict):
    total_goals: int
    core_count: int
    collaboration_count: int
    reflection_count: int
    template_type: TemplateType

# Type for registry statistics
class RegistryStats(TypedDict):
    total_templates: int
    supported_templates: List[TemplateType]
    registry_health: str

# Type for error handling
class GoalGenerationError(TypedDict):
    error_type: str
    template_type: TemplateType
    message: str
    details: Optional[Dict[str, Any]]

# Type for backward compatibility functions
LegacyGoalFunction = Any  # Callable[[AnswersDict], GoalList]

# Type for generator creation
GeneratorInstance = Optional[Any]  # GoalGenerator | None

# Type for template discovery
class TemplateDiscovery(TypedDict):
    discovered_templates: List[TemplateType]
    auto_registered: bool
    registration_count: int
