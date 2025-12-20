"""
Writing Workshop goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class WritingWorkshopGoalGenerator(GoalGenerator):
    """Goal generator for Writing Workshop template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Writing Workshop template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        writing_type = answers.get("writing_type", "general")
        workshop_focus = answers.get("workshop_focus", "drafting")
        experience_level = answers.get("experience_level", "intermediate")
        group_size = answers.get("group_size", "small")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(writing_type, workshop_focus, experience_level, group_size)
        
        # Categorize the goals
        return self._categorize_writing_workshop_goals(all_goals, experience_level)

    def _generate_all_goals(self, writing_type: str, workshop_focus: str, experience_level: str, group_size: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Writing process framework (adapted for different group sizes)
        writing_processes = {
            "academic": {
                "small": {
                    "research": "How can we conduct focused research through intimate collaborative inquiry?",
                    "analysis": "How might we develop critical analysis through peer discussion and feedback?",
                    "argument": "How can we construct compelling arguments through supportive peer review?",
                    "structure": "How might we organize academic writing through collaborative outline development?",
                    "revision": "How can we refine academic writing through detailed peer critique?"
                },
                "medium": {
                    "research": "How might we conduct comprehensive research through diverse collaborative perspectives?",
                    "analysis": "How can we develop sophisticated analysis through multi-perspective discussion?",
                    "argument": "How might we construct complex arguments through structured peer review?",
                    "structure": "How can we organize academic writing through collaborative framework development?",
                    "revision": "How might we refine academic writing through systematic peer critique?"
                },
                "large": {
                    "research": "How can we lead research initiatives and establish collaborative inquiry frameworks?",
                    "analysis": "How might we develop advanced analysis through community-driven discussion?",
                    "argument": "How can we construct innovative arguments through community peer review?",
                    "structure": "How might we organize academic writing through community framework development?",
                    "revision": "How can we refine academic writing through community critique systems?"
                }
            },
            "creative": {
                "small": {
                    "inspiration": "How can we develop writing inspiration through intimate creative dialogue?",
                    "craft": "How might we master writing techniques through focused peer workshops?",
                    "voice": "How can we develop authentic writing voice through supportive peer feedback?",
                    "revision": "How might we refine creative writing through collaborative critique?",
                    "publication": "How can we prepare writing for publication through peer review?"
                },
                "medium": {
                    "inspiration": "How might we explore diverse writing influences and collaborative creative processes?",
                    "craft": "How can we advance writing skills through structured workshops and peer learning?",
                    "voice": "How might we develop unique writing styles through group experimentation?",
                    "revision": "How can we establish writing quality standards through collaborative refinement?",
                    "publication": "How might we organize collaborative publications and writing showcases?"
                },
                "large": {
                    "inspiration": "How can we lead writing communities and inspire collective creative expression?",
                    "craft": "How might we establish writing mastery and mentor emerging writers?",
                    "voice": "How can we pioneer new writing approaches through community collaboration?",
                    "revision": "How might we develop writing frameworks and quality assurance systems?",
                    "publication": "How can we establish publishing platforms and writing community leadership?"
                }
            },
            "technical": {
                "small": {
                    "clarity": "How can we achieve writing clarity through focused peer review and feedback?",
                    "precision": "How might we develop technical precision through collaborative editing?",
                    "structure": "How can we organize technical content through peer outline development?",
                    "audience": "How might we adapt writing for specific audiences through peer feedback?",
                    "documentation": "How can we create effective documentation through collaborative review?"
                },
                "medium": {
                    "clarity": "How might we achieve writing clarity through diverse peer perspectives and feedback?",
                    "precision": "How can we develop technical precision through structured collaborative editing?",
                    "structure": "How might we organize technical content through collaborative framework development?",
                    "audience": "How can we adapt writing for multiple audiences through peer feedback systems?",
                    "documentation": "How might we create comprehensive documentation through collaborative review?"
                },
                "large": {
                    "clarity": "How can we establish writing clarity standards and mentor technical writers?",
                    "precision": "How might we develop technical precision frameworks and quality assurance systems?",
                    "structure": "How can we organize technical content through community framework development?",
                    "audience": "How might we adapt writing for diverse audiences through community feedback systems?",
                    "documentation": "How can we establish documentation standards and community review systems?"
                }
            },
            "business": {
                "small": {
                    "persuasion": "How can we develop persuasive writing through intimate peer feedback?",
                    "clarity": "How might we achieve business writing clarity through focused peer review?",
                    "structure": "How can we organize business content through collaborative outline development?",
                    "tone": "How might we develop appropriate business tone through peer feedback?",
                    "impact": "How can we create impactful business writing through collaborative refinement?"
                },
                "medium": {
                    "persuasion": "How might we develop persuasive writing through diverse peer perspectives?",
                    "clarity": "How can we achieve business writing clarity through structured peer review?",
                    "structure": "How might we organize business content through collaborative framework development?",
                    "tone": "How can we develop appropriate business tone through peer feedback systems?",
                    "impact": "How might we create impactful business writing through collaborative refinement?"
                },
                "large": {
                    "persuasion": "How can we establish persuasive writing standards and mentor business writers?",
                    "clarity": "How might we achieve business writing clarity through community review systems?",
                    "structure": "How can we organize business content through community framework development?",
                    "tone": "How might we develop appropriate business tone through community feedback systems?",
                    "impact": "How can we create impactful business writing through community refinement?"
                }
            }
        }
        
        # Workshop focus-specific learning objectives
        focus_goals = {
            "drafting": {
                "small": "How can we develop effective drafting strategies through intimate peer collaboration and feedback?",
                "medium": "How might we advance drafting skills through structured workshops and diverse peer perspectives?",
                "large": "How can we establish drafting frameworks and mentor emerging writers through community collaboration?"
            },
            "revision": {
                "small": "How might we master revision techniques through focused peer critique and collaborative editing?",
                "medium": "How can we develop sophisticated revision strategies through structured peer review systems?",
                "large": "How might we establish revision frameworks and quality assurance systems through community collaboration?"
            },
            "peer_review": {
                "small": "How can we develop peer review skills through intimate collaborative feedback sessions?",
                "medium": "How might we advance peer review techniques through structured feedback systems and diverse perspectives?",
                "large": "How can we establish peer review frameworks and mentor reviewers through community collaboration?"
            },
            "publishing": {
                "small": "How might we prepare writing for publication through intimate peer review and collaborative editing?",
                "medium": "How can we develop publication strategies through structured peer review and diverse perspectives?",
                "large": "How might we establish publication frameworks and mentor writers through community collaboration?"
            }
        }
        
        # Experience level-specific development goals
        experience_goals = {
            "beginner": {
                "small": [
                    "How can we build foundational writing skills through supportive peer learning?",
                    "How might we develop writing confidence through intimate collaborative experiences?",
                    "How can we establish writing practice habits through peer accountability?"
                ],
                "medium": [
                    "How might we develop foundational writing skills through structured workshops and diverse perspectives?",
                    "How can we build writing confidence through collaborative learning environments?",
                    "How might we establish writing practice through group accountability and support?"
                ],
                "large": [
                    "How can we develop foundational writing skills through community learning and mentorship?",
                    "How might we build writing confidence through community engagement and support?",
                    "How can we establish writing practice through community accountability and guidance?"
                ]
            },
            "intermediate": {
                "small": [
                    "How can we advance writing skills through focused peer collaboration and feedback?",
                    "How might we refine writing voice through intimate collaborative dialogue?",
                    "How can we develop writing independence while maintaining collaborative connections?"
                ],
                "medium": [
                    "How might we advance writing skills through structured collaboration and diverse feedback?",
                    "How can we refine writing voice through multi-perspective collaborative dialogue?",
                    "How might we develop writing independence while contributing to collaborative growth?"
                ],
                "large": [
                    "How can we advance writing skills through community collaboration and mentorship?",
                    "How might we refine writing voice through community collaborative dialogue?",
                    "How can we develop writing independence while contributing to community growth?"
                ]
            },
            "advanced": {
                "small": [
                    "How can we achieve writing mastery through intimate peer mentorship and collaboration?",
                    "How might we establish writing leadership through supportive collaborative partnerships?",
                    "How can we mentor emerging writers while continuing personal writing development?"
                ],
                "medium": [
                    "How might we achieve writing mastery through collaborative mentorship and diverse perspectives?",
                    "How can we establish writing leadership through coordinated collaborative direction?",
                    "How might we mentor emerging writers while contributing to collaborative growth?"
                ],
                "large": [
                    "How can we achieve writing mastery through community leadership and mentorship?",
                    "How might we establish writing leadership through community collaborative direction?",
                    "How might we mentor emerging writers while contributing to community growth?"
                ]
            }
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add writing type-specific process goals
        type_specific = writing_processes.get(writing_type, writing_processes["academic"])
        size_specific = type_specific[group_size if group_size in type_specific else "small"]
        
        # Helper function to safely get the first available key
        def get_first_available(keys, default=""):
            for key in keys:
                if key in size_specific:
                    return size_specific[key]
            return default
        
        goals.extend([
            get_first_available(["research", "inspiration", "clarity", "persuasion"]),
            get_first_available(["analysis", "craft", "precision", "clarity"]),
            get_first_available(["argument", "voice", "structure", "structure"]),
            get_first_available(["structure", "revision", "audience", "tone"]),
            get_first_available(["revision", "publication", "documentation", "impact"])
        ])
        
        # Add workshop focus-specific goal
        focus_specific = focus_goals.get(workshop_focus, focus_goals["drafting"])
        goals.append(focus_specific[group_size if group_size in focus_specific else "small"])
        
        # Add experience level-specific goals
        exp_specific = experience_goals.get(experience_level, experience_goals["intermediate"])
        size_exp_specific = exp_specific[group_size if group_size in exp_specific else "small"]
        goals.extend(size_exp_specific)
        
        # Add metacognitive reflection goals based on experience level
        metacognitive_goals = {
            "beginner": {
                "small": [
                    "How can we reflect on our writing process and identify what helps us write most effectively?",
                    "How might we learn from each other's writing approaches and techniques?",
                    "How do we maintain writing momentum in our intimate collaborative environment?"
                ],
                "medium": [
                    "How can we leverage diverse writing perspectives while maintaining focus?",
                    "How might we identify and address writing blocks through group support?",
                    "How do we balance individual writing expression with collaborative learning?"
                ],
                "large": [
                    "How can we maintain writing coherence while fostering individual expression?",
                    "How might we create knowledge-sharing systems that support writing growth?",
                    "How do we balance structured learning with writing freedom?"
                ]
            },
            "intermediate": {
                "small": [
                    "How can we reflect on our writing growth and creative breakthroughs?",
                    "How might we challenge each other's writing boundaries while maintaining support?",
                    "How do we balance writing experimentation with skill development?"
                ],
                "medium": [
                    "How can we leverage diverse writing perspectives for creative innovation?",
                    "How might we identify and overcome writing challenges through collaboration?",
                    "How do we balance individual writing vision with collective writing goals?"
                ],
                "large": [
                    "How can we maintain writing integrity while fostering collaborative creativity?",
                    "How might we create mentorship systems that support writing development?",
                    "How do we balance writing leadership with community writing growth?"
                ]
            },
            "advanced": {
                "small": [
                    "How can we reflect on our writing mastery and creative evolution?",
                    "How might we mentor emerging writers while continuing our own growth?",
                    "How do we balance writing leadership with collaborative learning?"
                ],
                "medium": [
                    "How can we leverage our expertise to elevate collaborative writing work?",
                    "How might we identify opportunities for writing innovation and mentorship?",
                    "How do we balance writing leadership with fostering writing independence?"
                ],
                "large": [
                    "How can we maintain writing excellence while building writing community?",
                    "How might we create systems that support both individual mastery and collective growth?",
                    "How do we balance writing leadership with community writing empowerment?"
                ]
            }
        }
        
        # Add metacognitive goals
        metacognitive_specific = metacognitive_goals.get(experience_level, metacognitive_goals["intermediate"])
        size_metacognitive_specific = metacognitive_specific[group_size if group_size in metacognitive_specific else "small"]
        goals.extend(size_metacognitive_specific)
        
        return goals

    def _categorize_writing_workshop_goals(self, goals: List[str], experience_level: str) -> Dict[str, List[str]]:
        """
        Categorize writing workshop goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Writing Workshop categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_writing_workshop_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for writing workshop goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = WritingWorkshopGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("writing-workshop", WritingWorkshopGoalGenerator)
