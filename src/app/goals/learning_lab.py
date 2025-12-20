"""
Learning Lab goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class LearningLabGoalGenerator(GoalGenerator):
    """Goal generator for Learning Lab template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Learning Lab template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        learning_style = answers.get("learning_style", "hands_on")
        subject_area = answers.get("subject_area", "general")
        goal = answers.get("goal", "skill_building")
        group_size = answers.get("group_size", "small")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(learning_style, subject_area, goal, group_size)
        
        # Categorize the goals
        return self._categorize_learning_lab_goals(all_goals, learning_style)

    def _generate_all_goals(self, learning_style: str, subject_area: str, goal: str, group_size: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Learning methodology framework (adapted for different group sizes)
        learning_methodologies = {
            "hands_on": {
                "small": {
                    "experimentation": "How can we conduct focused experiments through intimate collaborative inquiry?",
                    "practice": "How might we develop skills through intensive peer practice and feedback?",
                    "application": "How can we apply knowledge through collaborative problem-solving?",
                    "reflection": "How might we reflect on learning through intimate peer discussion?",
                    "iteration": "How can we iterate and improve through supportive peer feedback?"
                },
                "medium": {
                    "experimentation": "How might we conduct comprehensive experiments through diverse collaborative perspectives?",
                    "practice": "How can we develop skills through structured peer practice and diverse feedback?",
                    "application": "How might we apply knowledge through coordinated collaborative problem-solving?",
                    "reflection": "How can we reflect on learning through multi-perspective peer discussion?",
                    "iteration": "How might we iterate and improve through systematic peer feedback?"
                },
                "large": {
                    "experimentation": "How can we lead experimental initiatives and establish collaborative inquiry frameworks?",
                    "practice": "How might we develop skills through community practice and mentorship?",
                    "application": "How can we apply knowledge through community-driven problem-solving?",
                    "reflection": "How might we reflect on learning through community discussion and knowledge sharing?",
                    "iteration": "How can we iterate and improve through community feedback systems?"
                }
            },
            "project_based": {
                "small": {
                    "planning": "How can we plan projects through intimate collaborative design?",
                    "execution": "How might we execute projects through focused peer collaboration?",
                    "management": "How can we manage project timelines through supportive peer coordination?",
                    "evaluation": "How might we evaluate project outcomes through collaborative assessment?",
                    "presentation": "How can we present project results through peer review and feedback?"
                },
                "medium": {
                    "planning": "How might we plan projects through diverse collaborative design perspectives?",
                    "execution": "How can we execute projects through coordinated team collaboration?",
                    "management": "How might we manage project timelines through structured peer coordination?",
                    "evaluation": "How can we evaluate project outcomes through multi-perspective assessment?",
                    "presentation": "How might we present project results through group review and feedback?"
                },
                "large": {
                    "planning": "How can we lead project planning and establish collaborative design frameworks?",
                    "execution": "How might we orchestrate project execution through community collaboration?",
                    "management": "How can we manage complex project timelines through community coordination?",
                    "evaluation": "How might we evaluate project outcomes through community assessment systems?",
                    "presentation": "How can we present project results through community review and feedback?"
                }
            },
            "research_based": {
                "small": {
                    "inquiry": "How can we develop research questions through intimate collaborative inquiry?",
                    "investigation": "How might we conduct research through focused peer collaboration?",
                    "analysis": "How can we analyze findings through supportive peer discussion?",
                    "synthesis": "How might we synthesize results through collaborative interpretation?",
                    "communication": "How can we communicate findings through peer review and feedback?"
                },
                "medium": {
                    "inquiry": "How might we develop research questions through diverse collaborative perspectives?",
                    "investigation": "How can we conduct research through coordinated team collaboration?",
                    "analysis": "How might we analyze findings through multi-perspective peer discussion?",
                    "synthesis": "How can we synthesize results through collaborative interpretation frameworks?",
                    "communication": "How might we communicate findings through group review and feedback?"
                },
                "large": {
                    "inquiry": "How can we lead research initiatives and establish collaborative inquiry frameworks?",
                    "investigation": "How might we orchestrate research through community collaboration?",
                    "analysis": "How can we analyze findings through community discussion and knowledge sharing?",
                    "synthesis": "How might we synthesize results through community interpretation frameworks?",
                    "communication": "How can we communicate findings through community review and feedback?"
                }
            },
            "collaborative": {
                "small": {
                    "teamwork": "How can we develop teamwork skills through intimate collaborative experiences?",
                    "communication": "How might we enhance communication through focused peer interaction?",
                    "leadership": "How can we develop leadership skills through supportive peer guidance?",
                    "conflict_resolution": "How might we practice conflict resolution through collaborative problem-solving?",
                    "collective_intelligence": "How can we harness collective intelligence through intimate peer collaboration?"
                },
                "medium": {
                    "teamwork": "How might we develop teamwork skills through diverse collaborative experiences?",
                    "communication": "How can we enhance communication through structured peer interaction?",
                    "leadership": "How might we develop leadership skills through coordinated peer guidance?",
                    "conflict_resolution": "How can we practice conflict resolution through collaborative problem-solving frameworks?",
                    "collective_intelligence": "How might we harness collective intelligence through diverse peer collaboration?"
                },
                "large": {
                    "teamwork": "How can we develop teamwork skills through community collaborative experiences?",
                    "communication": "How might we enhance communication through community interaction frameworks?",
                    "leadership": "How can we develop leadership skills through community guidance and mentorship?",
                    "conflict_resolution": "How might we practice conflict resolution through community problem-solving systems?",
                    "collective_intelligence": "How can we harness collective intelligence through community collaboration?"
                }
            }
        }
        
        # Subject area-specific learning objectives
        subject_goals = {
            "technology": {
                "small": "How can we master technology skills through intimate collaborative learning and peer support?",
                "medium": "How might we advance technology skills through structured collaborative learning and diverse perspectives?",
                "large": "How can we establish technology leadership and mentor emerging technologists through community collaboration?"
            },
            "business": {
                "small": "How might we develop business skills through intimate collaborative learning and peer feedback?",
                "medium": "How can we advance business skills through structured collaborative learning and diverse perspectives?",
                "large": "How might we establish business leadership and mentor emerging professionals through community collaboration?"
            },
            "science": {
                "small": "How can we develop scientific skills through intimate collaborative inquiry and peer experimentation?",
                "medium": "How might we advance scientific skills through structured collaborative inquiry and diverse perspectives?",
                "large": "How can we establish scientific leadership and mentor emerging researchers through community collaboration?"
            },
            "arts": {
                "small": "How might we develop artistic skills through intimate collaborative creation and peer feedback?",
                "medium": "How can we advance artistic skills through structured collaborative creation and diverse perspectives?",
                "large": "How might we establish artistic leadership and mentor emerging artists through community collaboration?"
            },
            "language": {
                "small": "How can we develop language skills through intimate collaborative practice and peer interaction?",
                "medium": "How might we advance language skills through structured collaborative practice and diverse perspectives?",
                "large": "How can we establish language leadership and mentor emerging speakers through community collaboration?"
            }
        }
        
        # Goal-specific learning objectives
        goal_goals = {
            "skill_building": {
                "small": "How can we build foundational skills through intimate collaborative learning and peer support?",
                "medium": "How might we develop comprehensive skills through structured collaborative learning and diverse perspectives?",
                "large": "How can we establish skill mastery and mentor emerging learners through community collaboration?"
            },
            "certification": {
                "small": "How might we prepare for certification through intimate collaborative study and peer accountability?",
                "medium": "How can we prepare for certification through structured collaborative study and diverse perspectives?",
                "large": "How might we prepare for certification through community collaboration and mentorship?"
            },
            "career_advancement": {
                "small": "How can we advance career opportunities through intimate collaborative skill development and peer networking?",
                "medium": "How might we advance career opportunities through structured collaborative skill development and diverse perspectives?",
                "large": "How can we advance career opportunities through community collaboration and mentorship?"
            },
            "personal_development": {
                "small": "How might we develop personal growth through intimate collaborative learning and peer support?",
                "medium": "How can we develop personal growth through structured collaborative learning and diverse perspectives?",
                "large": "How might we develop personal growth through community collaboration and mentorship?"
            }
        }
        
        # Collaborative learning goals based on group size
        collaboration_goals = {
            "small": [
                "How can we develop intimate learning relationships and deep collaborative skills?",
                "How might we practice direct communication and rapid learning feedback?",
                "How can we build trust and accountability through close peer interactions?"
            ],
            "medium": [
                "How might we coordinate diverse expertise and perspectives for comprehensive learning?",
                "How can we develop leadership skills while supporting peer learning?",
                "How might we balance individual learning with collective achievement?"
            ],
            "large": [
                "How can we orchestrate complex learning dynamics and community collaboration?",
                "How might we develop systems thinking and cross-functional learning coordination?",
                "How can we build scalable learning frameworks and community structures?"
            ]
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add learning methodology-specific goals
        method_specific = learning_methodologies.get(learning_style, learning_methodologies["hands_on"])
        size_specific = method_specific[group_size if group_size in method_specific else "small"]
        
        # Helper function to safely get the first available key
        def get_first_available(keys, default=""):
            for key in keys:
                if key in size_specific:
                    return size_specific[key]
            return default
        
        goals.extend([
            get_first_available(["experimentation", "planning", "inquiry", "teamwork"]),
            get_first_available(["practice", "execution", "investigation", "communication"]),
            get_first_available(["application", "management", "analysis", "leadership"]),
            get_first_available(["reflection", "evaluation", "synthesis", "conflict_resolution"]),
            get_first_available(["iteration", "presentation", "communication", "collective_intelligence"])
        ])
        
        # Add subject area-specific goal
        subject_specific = subject_goals.get(subject_area, subject_goals["technology"])
        goals.append(subject_specific[group_size if group_size in subject_specific else "small"])
        
        # Add goal-specific objective
        goal_specific = goal_goals.get(goal, goal_goals["skill_building"])
        goals.append(goal_specific[group_size if group_size in goal_specific else "small"])
        
        # Add collaboration goals
        goals.extend(collaboration_goals[group_size if group_size in collaboration_goals else "small"])
        
        # Add metacognitive reflection goals based on learning style
        metacognitive_goals = {
            "hands_on": {
                "small": [
                    "How can we reflect on our experimental process and identify what learning methods work best for us?",
                    "How might we learn from each other's hands-on approaches and techniques?",
                    "How do we maintain learning momentum in our intimate experimental environment?"
                ],
                "medium": [
                    "How can we leverage diverse experimental perspectives while maintaining focus?",
                    "How might we identify and address learning challenges through group support?",
                    "How do we balance individual experimentation with collaborative learning?"
                ],
                "large": [
                    "How can we maintain experimental coherence while fostering individual learning?",
                    "How might we create knowledge-sharing systems that support experimental growth?",
                    "How do we balance structured learning with experimental freedom?"
                ]
            },
            "project_based": {
                "small": [
                    "How can we reflect on our project planning process and identify what strategies work best?",
                    "How might we learn from each other's project management approaches?",
                    "How do we maintain project momentum in our intimate collaborative environment?"
                ],
                "medium": [
                    "How can we leverage diverse project perspectives while maintaining focus?",
                    "How might we identify and address project challenges through group support?",
                    "How do we balance individual project work with collaborative learning?"
                ],
                "large": [
                    "How can we maintain project coherence while fostering individual contribution?",
                    "How might we create project management systems that support collaborative growth?",
                    "How do we balance structured project work with creative problem-solving?"
                ]
            },
            "research_based": {
                "small": [
                    "How can we reflect on our research process and identify what inquiry methods work best?",
                    "How might we learn from each other's research approaches and methodologies?",
                    "How do we maintain research momentum in our intimate collaborative environment?"
                ],
                "medium": [
                    "How can we leverage diverse research perspectives while maintaining focus?",
                    "How might we identify and address research challenges through group support?",
                    "How do we balance individual research with collaborative inquiry?"
                ],
                "large": [
                    "How can we maintain research coherence while fostering individual inquiry?",
                    "How might we create research systems that support collaborative knowledge building?",
                    "How do we balance structured research with creative inquiry?"
                ]
            },
            "collaborative": {
                "small": [
                    "How can we reflect on our collaborative process and identify what teamwork strategies work best?",
                    "How might we learn from each other's collaboration styles and approaches?",
                    "How do we maintain collaborative momentum in our intimate learning environment?"
                ],
                "medium": [
                    "How can we leverage diverse collaboration perspectives while maintaining focus?",
                    "How might we identify and address collaborative challenges through group support?",
                    "How do we balance individual learning with collaborative teamwork?"
                ],
                "large": [
                    "How can we maintain collaborative coherence while fostering individual contribution?",
                    "How might we create collaboration systems that support community learning?",
                    "How do we balance structured collaboration with creative teamwork?"
                ]
            }
        }
        
        # Add metacognitive goals
        metacognitive_specific = metacognitive_goals.get(learning_style, metacognitive_goals["hands_on"])
        size_metacognitive_specific = metacognitive_specific[group_size if group_size in metacognitive_specific else "small"]
        goals.extend(size_metacognitive_specific)
        
        return goals

    def _categorize_learning_lab_goals(self, goals: List[str], learning_style: str) -> Dict[str, List[str]]:
        """
        Categorize learning lab goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Learning Lab categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_learning_lab_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for learning lab goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = LearningLabGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("learning-lab", LearningLabGoalGenerator)
