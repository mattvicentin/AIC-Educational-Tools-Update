"""
Base goal generation interface
Provides common structure for all template goal generators
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from .types import AnswersDict, CategorizedGoals, GoalList


class GoalGenerator(ABC):
    """Base class for template goal generators."""
    
    @abstractmethod
    def generate_goals(self, answers: AnswersDict) -> CategorizedGoals:
        """
        Generate categorized goals for a template.
        
        Args:
            answers: Template form answers
            
        Returns:
            Dictionary with categorized goals:
            {
                "core_goals": List[str],
                "collaboration_goals": List[str], 
                "reflection_goals": List[str]
            }
        """
        pass
    
    def categorize_goals(self, goals: GoalList) -> CategorizedGoals:
        """
        Categorize a flat list of goals into core, collaboration, and reflection.
        Default implementation for backward compatibility.
        
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
        reflection_count = max(0, len(goals) - core_count - collab_count)
        
        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }
