#!/usr/bin/env python3
"""
study_group.py
Purpose: Study Group goal generation with inquiry-based learning approach
Status: [ACTIVE] - Enhanced with goal categorization and pedagogical improvements
Created: 2025-01-27
Author: writeian

Study Group template with enhanced UX, goal categorization, and inquiry-based learning approach.
Features metacognitive reflection and group size-specific collaborative strategies.
"""

from typing import Dict, List, Any
from .base import GoalGenerator
from .types import AnswersDict, CategorizedGoals, GoalList, SubjectType, GroupSizeType, GoalTypeType


class StudyGroupGoalGenerator(GoalGenerator):
    """Goal generator for Study Group template with inquiry-based learning approach."""
    
    def generate_goals(self, answers: AnswersDict) -> CategorizedGoals:
        """
        Generate categorized goals for Study Group template.
        
        Args:
            answers: Template form answers containing subject, group_size, and goal_type
            
        Returns:
            Categorized goals dictionary with core, collaboration, and reflection goals
        """
        # Extract and validate inputs with proper type annotations
        subject: SubjectType = answers.get("subject", "general")
        group_size: GroupSizeType = answers.get("group_size", "small")
        goal_type: GoalTypeType = answers.get("goal_type", "understanding")
        
        # Generate comprehensive goal set
        goals = self._generate_all_goals(subject, group_size, goal_type)
        
        # Categorize goals using template-specific logic
        return self._categorize_study_group_goals(goals, group_size)
    
    def _generate_all_goals(self, subject: str, group_size: str, goal_type: str) -> List[str]:
        """Generate all goals using the original logic."""
        
        # Subject-specific learning objectives (Bloom's taxonomy aligned)
        subject_goals = {
            "math": {
                "remember": f"How can we recall and apply fundamental {subject} formulas, theorems, and procedures?",
                "understand": f"How might we explain {subject} concepts in our own words and demonstrate comprehension?",
                "apply": f"How can we solve {subject} problems using appropriate strategies and methods?",
                "analyze": f"How might we break down complex {subject} problems and identify solution approaches?",
                "evaluate": f"How can we assess the validity of {subject} solutions and alternative methods?",
                "create": f"How might we develop original {subject} problems and explore mathematical patterns?"
            },
            "science": {
                "remember": f"How can we recall key {subject} principles, laws, and scientific terminology?",
                "understand": f"How might we explain {subject} phenomena and demonstrate conceptual understanding?",
                "apply": f"How can we conduct {subject} experiments and apply scientific methods?",
                "analyze": f"How might we interpret {subject} data and identify patterns and relationships?",
                "evaluate": f"How can we assess the reliability of {subject} evidence and experimental design?",
                "create": f"How might we design {subject} experiments and develop scientific hypotheses?"
            },
            "literature": {
                "remember": f"How can we recall key {subject} texts, authors, and literary elements?",
                "understand": f"How might we interpret {subject} themes, characters, and narrative techniques?",
                "apply": f"How can we analyze {subject} texts using appropriate literary frameworks?",
                "analyze": f"How might we examine {subject} texts for deeper meaning and authorial intent?",
                "evaluate": f"How can we assess the quality and significance of {subject} literary works?",
                "create": f"How might we develop original {subject} interpretations and critical responses?"
            },
            "history": {
                "remember": f"How can we recall key {subject} events, dates, and historical figures?",
                "understand": f"How might we explain {subject} historical contexts and causal relationships?",
                "apply": f"How can we analyze {subject} primary sources and historical evidence?",
                "analyze": f"How might we examine {subject} historical patterns and multiple perspectives?",
                "evaluate": f"How can we assess the reliability of {subject} historical sources and interpretations?",
                "create": f"How might we develop original {subject} historical arguments and narratives?"
            },
            "languages": {
                "remember": f"How can we recall {subject} vocabulary, grammar rules, and cultural contexts?",
                "understand": f"How might we comprehend {subject} texts and spoken language?",
                "apply": f"How can we use {subject} language in authentic communication contexts?",
                "analyze": f"How might we examine {subject} language structures and cultural nuances?",
                "evaluate": f"How can we assess {subject} language proficiency and cultural appropriateness?",
                "create": f"How might we produce original {subject} language content and cultural expressions?"
            },
            "other": {
                "remember": f"How can we recall key {subject} concepts, terminology, and foundational knowledge?",
                "understand": f"How might we explain {subject} principles and demonstrate comprehension?",
                "apply": f"How can we use {subject} knowledge in practical situations?",
                "analyze": f"How might we examine {subject} concepts from multiple perspectives?",
                "evaluate": f"How can we assess {subject} information and arguments critically?",
                "create": f"How might we develop original {subject} insights and applications?"
            }
        }
        
        # Group size-specific collaborative strategies
        collaboration_goals = {
            "small": {
                "intimate": "How can we develop deep peer teaching relationships through focused one-on-one interactions?",
                "personalized": "How might we provide individualized feedback and support within our close-knit group?",
                "mentoring": "How can we engage in reciprocal mentoring and detailed concept exploration?",
                "accountability": "How might we maintain high accountability through direct peer relationships?",
                "flexibility": "How can we adapt study methods quickly based on individual needs and preferences?"
            },
            "medium": {
                "diverse": "How can we leverage diverse perspectives and experiences for comprehensive learning?",
                "structured": "How might we balance individual growth with collaborative achievement through organized activities?",
                "leadership": "How can we develop leadership and facilitation skills while supporting peer learning?",
                "specialization": "How might we assign roles and responsibilities based on individual strengths?",
                "networking": "How can we build a supportive learning network with multiple peer connections?"
            },
            "large": {
                "scalable": "How can we create a scalable learning community that supports mastery at scale?",
                "subgroups": "How might we organize into focused subgroups for specialized learning areas?",
                "resources": "How can we develop community-wide study strategies and resource sharing systems?",
                "mentoring_networks": "How might we establish peer mentoring networks and knowledge transfer systems?",
                "collective_intelligence": "How can we harness collective intelligence through diverse perspectives and expertise?"
            }
        }
        
        # Goal type-specific learning strategies
        strategy_goals = {
            "exam_prep": {
                "small": "How can we achieve high exam scores through intensive peer review and targeted practice sessions?",
                "medium": "How might we prepare for exams through diverse study strategies and group accountability systems?",
                "large": "How can we create comprehensive exam preparation resources and peer support networks?"
            },
            "project_work": {
                "small": "How can we complete collaborative projects with shared responsibility and close coordination?",
                "medium": "How might we execute projects through role-based collaboration and team synergy?",
                "large": "How can we coordinate complex projects through subgroup specialization and community coordination?"
            },
            "homework_help": {
                "small": "How can we provide personalized homework support and concept clarification?",
                "medium": "How might we offer diverse approaches to homework problems and collaborative solutions?",
                "large": "How can we create a comprehensive homework support system with peer tutoring networks?"
            },
            "concept_review": {
                "small": "How can we achieve deep concept mastery through focused discussion and peer explanation?",
                "medium": "How might we explore concepts from multiple angles through diverse group perspectives?",
                "large": "How can we build a comprehensive knowledge base through community-wide concept exploration?"
            }
        }
        
        # Metacognitive and self-regulation goals
        metacognitive_goals = {
            "small": [
                "How can we develop self-awareness of individual learning styles and preferences?",
                "How might we practice self-monitoring and adjustment of study strategies?",
                "How can we reflect on personal learning progress and areas for improvement?"
            ],
            "medium": [
                "How can we develop group awareness and collaborative learning strategies?",
                "How might we practice peer feedback and collaborative problem-solving?",
                "How can we reflect on group dynamics and individual contributions?"
            ],
            "large": [
                "How can we develop community awareness and collective learning strategies?",
                "How might we practice knowledge sharing and community building?",
                "How can we reflect on community impact and individual role in collective learning?"
            ]
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add subject-specific goals (focus on higher-order thinking)
        subject_specific = subject_goals.get(subject, subject_goals["other"])
        goals.extend([
            subject_specific["understand"],  # Foundation
            subject_specific["apply"],       # Application
            subject_specific["analyze"],     # Analysis
            subject_specific["evaluate"]     # Evaluation
        ])
        
        # Add collaboration goals based on group size
        collab_specific = collaboration_goals[group_size]
        goals.extend([
            collab_specific["intimate"] if group_size == "small" else collab_specific["diverse"] if group_size == "medium" else collab_specific["scalable"],
            collab_specific["personalized"] if group_size == "small" else collab_specific["structured"] if group_size == "medium" else collab_specific["subgroups"],
            collab_specific["mentoring"] if group_size == "small" else collab_specific["leadership"] if group_size == "medium" else collab_specific["mentoring_networks"]
        ])
        
        # Add goal type-specific strategy
        strategy_specific = strategy_goals[goal_type]
        goals.append(strategy_specific[group_size])
        
        # Add metacognitive goals
        goals.extend(metacognitive_goals[group_size])
        
        return goals
    
    def _categorize_study_group_goals(self, goals: List[str], group_size: str) -> Dict[str, List[str]]:
        """
        Categorize study group goals into core, collaboration, and reflection.
        
        Args:
            goals: Complete list of goals
            group_size: Size of the study group
            
        Returns:
            Categorized goals dictionary
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }
        
        # Study Group specific categorization:
        # - Core goals: Subject-specific learning objectives (first 4)
        # - Collaboration goals: Group size-specific strategies (next 3)
        # - Reflection goals: Metacognitive goals (last 3)
        
        core_count = min(4, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))
        
        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_study_group_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for study group goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = StudyGroupGoalGenerator()
    categorized_goals = generator.generate_goals(answers)
    
    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))
    
    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("study-group", StudyGroupGoalGenerator)
