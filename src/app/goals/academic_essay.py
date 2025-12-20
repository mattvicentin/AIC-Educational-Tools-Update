"""
Academic Essay goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class AcademicEssayGoalGenerator(GoalGenerator):
    """Goal generator for Academic Essay template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Academic Essay template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        essay_type = answers.get("essay_type", "research")
        group_size = answers.get("group_size", "individual")
        writing_focus = answers.get("writing_focus", "research_process")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(essay_type, group_size, writing_focus)
        
        # Categorize the goals
        return self._categorize_academic_essay_goals(all_goals, essay_type)

    def _generate_all_goals(self, essay_type: str, group_size: str, writing_focus: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Academic writing process framework (adapted for different group sizes)
        writing_processes = {
            "research": {
                "individual": {
                    "exploration": "How can we conduct independent research exploration and develop personal inquiry skills?",
                    "analysis": "How might we analyze research findings through individual critical thinking?",
                    "synthesis": "How can we synthesize research through independent interpretation?",
                    "argument": "How might we construct research arguments through individual reasoning?",
                    "presentation": "How can we present research findings through individual academic communication?"
                },
                "small": {
                    "exploration": "How can we conduct collaborative research exploration and develop peer inquiry skills?",
                    "analysis": "How might we analyze research findings through intimate peer discussion?",
                    "synthesis": "How can we synthesize research through collaborative interpretation?",
                    "argument": "How might we construct research arguments through peer feedback and refinement?",
                    "presentation": "How can we present research findings through collaborative academic communication?"
                },
                "medium": {
                    "exploration": "How can we conduct comprehensive research exploration and develop group inquiry skills?",
                    "analysis": "How might we analyze research findings through diverse peer perspectives?",
                    "synthesis": "How can we synthesize research through coordinated group interpretation?",
                    "argument": "How might we construct research arguments through structured peer review?",
                    "presentation": "How can we present research findings through group academic communication?"
                }
            },
            "argumentative": {
                "individual": {
                    "position": "How can we develop independent argumentative positions and personal reasoning?",
                    "evidence": "How might we gather evidence through individual research and analysis?",
                    "counterarguments": "How can we address counterarguments through independent critical thinking?",
                    "persuasion": "How might we develop persuasive arguments through individual rhetorical skills?",
                    "presentation": "How can we present arguments through individual academic communication?"
                },
                "small": {
                    "position": "How can we develop collaborative argumentative positions and peer reasoning?",
                    "evidence": "How might we gather evidence through intimate peer research and analysis?",
                    "counterarguments": "How can we address counterarguments through collaborative critical thinking?",
                    "persuasion": "How might we develop persuasive arguments through peer rhetorical feedback?",
                    "presentation": "How can we present arguments through collaborative academic communication?"
                },
                "medium": {
                    "position": "How can we develop comprehensive argumentative positions and group reasoning?",
                    "evidence": "How might we gather evidence through diverse peer research and analysis?",
                    "counterarguments": "How can we address counterarguments through coordinated group critical thinking?",
                    "persuasion": "How might we develop persuasive arguments through structured peer rhetorical review?",
                    "presentation": "How can we present arguments through group academic communication?"
                }
            },
            "analytical": {
                "individual": {
                    "interpretation": "How can we develop independent textual interpretation and personal analysis?",
                    "criticism": "How might we apply critical theory through individual analytical thinking?",
                    "context": "How can we analyze context through independent research and understanding?",
                    "insight": "How might we develop analytical insights through individual critical thinking?",
                    "presentation": "How can we present analysis through individual academic communication?"
                },
                "small": {
                    "interpretation": "How can we develop collaborative textual interpretation and peer analysis?",
                    "criticism": "How might we apply critical theory through intimate peer analytical thinking?",
                    "context": "How can we analyze context through collaborative research and understanding?",
                    "insight": "How might we develop analytical insights through peer critical feedback?",
                    "presentation": "How can we present analysis through collaborative academic communication?"
                },
                "medium": {
                    "interpretation": "How can we develop comprehensive textual interpretation and group analysis?",
                    "criticism": "How might we apply critical theory through diverse peer analytical thinking?",
                    "context": "How can we analyze context through coordinated group research and understanding?",
                    "insight": "How might we develop analytical insights through structured peer critical review?",
                    "presentation": "How can we present analysis through group academic communication?"
                }
            }
        }
        
        # Team structure-specific learning objectives
        team_goals = {
            "individual": [
                "How can we work independently with AI guidance through the complete writing process?",
                "How might we develop self-directed learning skills and personal writing voice?",
                "How can we practice autonomous research and independent critical thinking?"
            ],
            "small": [
                "How can we collaborate with peers for feedback and peer review?",
                "How might we develop collaborative writing skills and shared understanding?",
                "How can we practice peer learning and mutual support in writing development?"
            ],
            "medium": [
                "How can we participate in writing workshops and group critique sessions?",
                "How might we develop group writing skills and collective knowledge building?",
                "How can we practice community learning and shared writing development?"
            ]
        }
        
        # Writing focus-specific learning objectives
        focus_goals = {
            "research_process": {
                "individual": "How can we follow systematic research methodology from exploration to final draft through independent inquiry?",
                "small": "How might we follow systematic research methodology from exploration to final draft through collaborative inquiry?",
                "medium": "How can we follow systematic research methodology from exploration to final draft through group inquiry?"
            },
            "writing_development": {
                "individual": "How can we focus on drafting, revision, and refinement techniques through independent practice?",
                "small": "How might we focus on drafting, revision, and refinement techniques through peer collaboration?",
                "medium": "How can we focus on drafting, revision, and refinement techniques through group workshops?"
            },
            "argument_construction": {
                "individual": "How can we build strong arguments with evidence integration and logical flow through independent reasoning?",
                "small": "How might we build strong arguments with evidence integration and logical flow through peer feedback?",
                "medium": "How can we build strong arguments with evidence integration and logical flow through group discussion?"
            },
            "academic_skills": {
                "individual": "How can we master citation, formatting, and academic conventions through independent study?",
                "small": "How might we master citation, formatting, and academic conventions through peer learning?",
                "medium": "How can we master citation, formatting, and academic conventions through group workshops?"
            }
        }
        
        # Academic competency goals based on team structure
        competency_goals = {
            "individual": [
                "How can we develop independent research skills and personal academic voice?",
                "How might we practice autonomous writing and self-directed learning?",
                "How can we build confidence in individual academic capabilities?"
            ],
            "small": [
                "How can we develop collaborative research skills and peer academic dialogue?",
                "How might we practice peer writing support and mutual learning?",
                "How can we build confidence in collaborative academic capabilities?"
            ],
            "medium": [
                "How can we develop group research skills and community academic discourse?",
                "How might we practice group writing support and collective learning?",
                "How can we build confidence in community academic capabilities?"
            ]
        }
        
        # Add metacognitive reflection goals based on essay type
        metacognitive_goals = {
            "research": {
                "individual": [
                    "How can we reflect on our research journey and identify what inquiry methods work best for us?",
                    "How might we learn from our research process and develop our personal academic voice?",
                    "How do we maintain momentum in our independent research work?"
                ],
                "small": [
                    "How can we leverage diverse research perspectives while maintaining focus?",
                    "How might we identify and address research challenges through peer support?",
                    "How do we balance individual research with collaborative inquiry?"
                ],
                "medium": [
                    "How can we maintain research coherence while fostering individual academic growth?",
                    "How might we create knowledge-sharing systems that support research development?",
                    "How do we balance structured research with academic freedom?"
                ]
            },
            "argumentative": {
                "individual": [
                    "How can we reflect on our argumentative journey and identify what reasoning methods work best for us?",
                    "How might we learn from our argument construction process and develop our persuasive voice?",
                    "How do we maintain momentum in our independent argumentative work?"
                ],
                "small": [
                    "How can we leverage diverse argumentative perspectives while maintaining focus?",
                    "How might we identify and address argument challenges through peer support?",
                    "How do we balance individual reasoning with collaborative argument building?"
                ],
                "medium": [
                    "How can we maintain argumentative coherence while fostering individual academic growth?",
                    "How might we create knowledge-sharing systems that support argument development?",
                    "How do we balance structured argumentation with academic freedom?"
                ]
            },
            "analytical": {
                "individual": [
                    "How can we reflect on our analytical journey and identify what interpretation methods work best for us?",
                    "How might we learn from our analytical process and develop our critical voice?",
                    "How do we maintain momentum in our independent analytical work?"
                ],
                "small": [
                    "How can we leverage diverse analytical perspectives while maintaining focus?",
                    "How might we identify and address analytical challenges through peer support?",
                    "How do we balance individual analysis with collaborative interpretation?"
                ],
                "medium": [
                    "How can we maintain analytical coherence while fostering individual academic growth?",
                    "How might we create knowledge-sharing systems that support analytical development?",
                    "How do we balance structured analysis with academic freedom?"
                ]
            }
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add essay type-specific process goals
        type_specific = writing_processes.get(essay_type, writing_processes["research"])
        structure_specific = type_specific[group_size if group_size in type_specific else "individual"]
        
        # Helper function to safely get the first available key
        def get_first_available(keys, default=""):
            for key in keys:
                if key in structure_specific:
                    return structure_specific[key]
            return default
        
        goals.extend([
            get_first_available(["exploration", "position", "interpretation"]),
            get_first_available(["analysis", "evidence", "criticism"]),
            get_first_available(["synthesis", "counterarguments", "context"]),
            get_first_available(["argument", "persuasion", "insight"]),
            structure_specific["presentation"]
        ])
        
        # Add team structure-specific goals
        goals.extend(team_goals[group_size if group_size in team_goals else "individual"])
        
        # Add writing focus-specific goal
        focus_specific = focus_goals.get(writing_focus, focus_goals["research_process"])
        goals.append(focus_specific[group_size if group_size in focus_specific else "individual"])
        
        # Add competency goals
        goals.extend(competency_goals[group_size if group_size in competency_goals else "individual"])
        
        # Add metacognitive goals
        metacognitive_specific = metacognitive_goals.get(essay_type, metacognitive_goals["research"])
        size_metacognitive_specific = metacognitive_specific[group_size if group_size in metacognitive_specific else "individual"]
        goals.extend(size_metacognitive_specific)
        
        return goals

    def _categorize_academic_essay_goals(self, goals: List[str], essay_type: str) -> Dict[str, List[str]]:
        """
        Categorize academic essay goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Academic Essay categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_academic_essay_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for academic essay goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = AcademicEssayGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("academic-essay", AcademicEssayGoalGenerator)
