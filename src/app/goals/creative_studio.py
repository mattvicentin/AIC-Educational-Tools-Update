"""
Creative Studio goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class CreativeStudioGoalGenerator(GoalGenerator):
    """Goal generator for Creative Studio template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Creative Studio template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        medium = answers.get("medium", "general")
        project_type = answers.get("project_type", "portfolio")
        skill_level = answers.get("skill_level", "developing")
        group_size = answers.get("group_size", "small")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(medium, project_type, skill_level, group_size)
        
        # Categorize the goals
        return self._categorize_creative_studio_goals(all_goals, skill_level)

    def _generate_all_goals(self, medium: str, project_type: str, skill_level: str, group_size: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Creative process framework (adapted for different group sizes)
        creative_processes = {
            "visual_arts": {
                "small": {
                    "inspiration": "How can we develop personal artistic vision through intimate creative exploration?",
                    "technique": "How might we master fundamental techniques through focused practice and peer feedback?",
                    "composition": "How can we create compelling compositions through collaborative critique and refinement?",
                    "expression": "How might we develop authentic artistic voice through deep creative dialogue?",
                    "presentation": "How can we curate personal portfolios through supportive peer review?"
                },
                "medium": {
                    "inspiration": "How might we explore diverse artistic influences and develop collaborative creative vision?",
                    "technique": "How can we advance technical skills through structured workshops and peer learning?",
                    "composition": "How might we create sophisticated compositions through multi-perspective critique?",
                    "expression": "How can we develop unique artistic styles through collaborative experimentation?",
                    "presentation": "How might we organize group exhibitions and collaborative portfolio development?"
                },
                "large": {
                    "inspiration": "How can we lead artistic movements and inspire collective creative vision?",
                    "technique": "How might we establish technical mastery and mentor emerging artists?",
                    "composition": "How can we create groundbreaking compositions through interdisciplinary collaboration?",
                    "expression": "How might we develop innovative artistic approaches through community engagement?",
                    "presentation": "How can we curate major exhibitions and establish artistic community leadership?"
                }
            },
            "digital_design": {
                "small": {
                    "concept": "How can we develop design concepts through intimate creative collaboration?",
                    "tools": "How might we master design software through focused skill development?",
                    "workflow": "How can we optimize design workflows through peer feedback and iteration?",
                    "innovation": "How might we create innovative designs through collaborative experimentation?",
                    "delivery": "How can we deliver polished design solutions through supportive critique?"
                },
                "medium": {
                    "concept": "How might we develop comprehensive design strategies through diverse perspectives?",
                    "tools": "How can we advance technical proficiency through structured skill workshops?",
                    "workflow": "How might we establish efficient design systems through collaborative optimization?",
                    "innovation": "How can we create cutting-edge designs through interdisciplinary collaboration?",
                    "delivery": "How might we deliver complex design solutions through coordinated team effort?"
                },
                "large": {
                    "concept": "How can we lead design innovation and establish industry best practices?",
                    "tools": "How might we develop advanced design methodologies and mentor design teams?",
                    "workflow": "How can we architect scalable design systems and collaborative frameworks?",
                    "innovation": "How might we pioneer new design approaches through community-driven innovation?",
                    "delivery": "How can we deliver enterprise design solutions and establish design leadership?"
                }
            },
            "content_creation": {
                "small": {
                    "ideation": "How can we develop content ideas through intimate creative brainstorming?",
                    "production": "How might we create compelling content through focused collaboration?",
                    "editing": "How can we refine content through supportive peer review and feedback?",
                    "distribution": "How might we optimize content distribution through collaborative strategy?",
                    "engagement": "How can we build audience engagement through authentic creative expression?"
                },
                "medium": {
                    "ideation": "How might we develop content strategies through diverse creative perspectives?",
                    "production": "How can we create sophisticated content through coordinated team effort?",
                    "editing": "How might we establish content quality standards through collaborative refinement?",
                    "distribution": "How can we implement multi-channel content distribution strategies?",
                    "engagement": "How might we build community engagement through collaborative content creation?"
                },
                "large": {
                    "ideation": "How can we lead content innovation and establish creative content frameworks?",
                    "production": "How might we orchestrate large-scale content production and creative direction?",
                    "editing": "How can we establish industry content standards and quality assurance systems?",
                    "distribution": "How might we architect comprehensive content distribution networks?",
                    "engagement": "How can we build global audience engagement through community-driven content?"
                }
            },
            "creative_writing": {
                "small": {
                    "inspiration": "How can we develop writing inspiration through intimate creative dialogue?",
                    "craft": "How might we master writing techniques through focused peer workshops?",
                    "revision": "How can we refine writing through supportive critique and feedback?",
                    "voice": "How might we develop authentic writing voice through collaborative exploration?",
                    "publication": "How can we prepare writing for publication through peer review and editing?"
                },
                "medium": {
                    "inspiration": "How might we explore diverse writing influences and collaborative creative processes?",
                    "craft": "How can we advance writing skills through structured workshops and peer learning?",
                    "revision": "How might we establish writing quality standards through collaborative refinement?",
                    "voice": "How can we develop unique writing styles through group experimentation?",
                    "publication": "How might we organize collaborative publications and writing showcases?"
                },
                "large": {
                    "inspiration": "How can we lead writing communities and inspire collective creative expression?",
                    "craft": "How might we establish writing mastery and mentor emerging writers?",
                    "revision": "How can we develop writing frameworks and quality assurance systems?",
                    "voice": "How might we pioneer new writing approaches through community collaboration?",
                    "publication": "How can we establish publishing platforms and writing community leadership?"
                }
            },
            "music_performance": {
                "small": {
                    "composition": "How can we develop musical compositions through intimate creative collaboration?",
                    "technique": "How might we master performance techniques through focused practice and feedback?",
                    "arrangement": "How can we create musical arrangements through collaborative experimentation?",
                    "expression": "How might we develop musical expression through supportive peer guidance?",
                    "performance": "How can we deliver compelling performances through collaborative preparation?"
                },
                "medium": {
                    "composition": "How might we develop sophisticated compositions through diverse musical perspectives?",
                    "technique": "How can we advance performance skills through structured workshops and peer learning?",
                    "arrangement": "How might we create complex arrangements through coordinated collaboration?",
                    "expression": "How can we develop unique musical styles through group experimentation?",
                    "performance": "How might we organize ensemble performances and collaborative showcases?"
                },
                "large": {
                    "composition": "How can we lead musical innovation and establish collaborative composition frameworks?",
                    "technique": "How might we establish performance mastery and mentor emerging musicians?",
                    "arrangement": "How can we orchestrate complex musical productions and collaborative direction?",
                    "expression": "How might we pioneer new musical approaches through community collaboration?",
                    "performance": "How can we lead major performances and establish musical community leadership?"
                }
            }
        }
        
        # Project type-specific learning objectives
        project_goals = {
            "portfolio": {
                "small": "How can we develop compelling personal portfolios through intimate creative collaboration and peer feedback?",
                "medium": "How might we create sophisticated portfolio collections through diverse creative perspectives and group critique?",
                "large": "How can we establish portfolio leadership and mentor emerging artists through community collaboration?"
            },
            "collaboration": {
                "small": "How might we engage in intimate creative partnerships and develop deep collaborative skills?",
                "medium": "How can we coordinate creative projects across diverse perspectives and establish collaborative frameworks?",
                "large": "How might we lead major creative collaborations and establish community creative leadership?"
            },
            "skill_development": {
                "small": "How can we advance technical skills through focused practice and supportive peer learning?",
                "medium": "How might we develop comprehensive skill sets through structured workshops and collaborative learning?",
                "large": "How can we establish skill mastery and mentor emerging artists through community education?"
            },
            "content_creation": {
                "small": "How might we create compelling content through intimate creative collaboration and peer feedback?",
                "medium": "How can we develop sophisticated content strategies through diverse creative perspectives?",
                "large": "How might we lead content innovation and establish creative content frameworks?"
            },
            "exhibition": {
                "small": "How can we prepare for intimate exhibitions through collaborative curation and peer support?",
                "medium": "How might we organize group exhibitions through coordinated creative direction and diverse perspectives?",
                "large": "How can we lead major exhibitions and establish community creative leadership?"
            }
        }
        
        # Skill level-specific development goals
        skill_development_goals = {
            "beginner": {
                "small": [
                    "How can we build foundational creative skills through supportive peer learning?",
                    "How might we develop creative confidence through intimate collaborative experiences?",
                    "How can we establish creative practice habits through peer accountability?"
                ],
                "medium": [
                    "How might we develop foundational skills through structured workshops and diverse perspectives?",
                    "How can we build creative confidence through collaborative learning environments?",
                    "How might we establish creative practice through group accountability and support?"
                ],
                "large": [
                    "How can we develop foundational skills through community learning and mentorship?",
                    "How might we build creative confidence through community engagement and support?",
                    "How can we establish creative practice through community accountability and guidance?"
                ]
            },
            "developing": {
                "small": [
                    "How can we advance creative skills through focused peer collaboration and feedback?",
                    "How might we refine creative voice through intimate artistic dialogue?",
                    "How can we develop creative independence while maintaining collaborative connections?"
                ],
                "medium": [
                    "How might we advance skills through structured collaboration and diverse feedback?",
                    "How can we refine creative voice through multi-perspective artistic dialogue?",
                    "How might we develop creative independence while contributing to collaborative growth?"
                ],
                "large": [
                    "How can we advance skills through community collaboration and mentorship?",
                    "How might we refine creative voice through community artistic dialogue?",
                    "How can we develop creative independence while contributing to community growth?"
                ]
            },
            "advanced": {
                "small": [
                    "How can we achieve creative mastery through intimate peer mentorship and collaboration?",
                    "How might we establish artistic leadership through supportive creative partnerships?",
                    "How can we mentor emerging artists while continuing personal creative development?"
                ],
                "medium": [
                    "How might we achieve creative mastery through collaborative mentorship and diverse perspectives?",
                    "How can we establish artistic leadership through coordinated creative direction?",
                    "How might we mentor emerging artists while contributing to collaborative growth?"
                ],
                "large": [
                    "How can we achieve creative mastery through community leadership and mentorship?",
                    "How might we establish artistic leadership through community creative direction?",
                    "How can we mentor emerging artists while contributing to community growth?"
                ]
            }
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add medium-specific creative process goals
        medium_specific = creative_processes.get(medium, creative_processes["visual_arts"])
        size_specific = medium_specific[group_size if group_size in medium_specific else "small"]
        # Helper function to safely get the first available key
        def get_first_available(keys, default=""):
            for key in keys:
                if key in size_specific:
                    return size_specific[key]
            return default
        
        # Add medium-specific creative process goals
        goals.extend([
            get_first_available(["inspiration", "concept", "ideation", "composition"]),
            get_first_available(["technique", "tools", "production", "craft"]),
            get_first_available(["composition", "workflow", "editing", "revision", "arrangement"]),
            get_first_available(["expression", "innovation", "voice"]),
            get_first_available(["presentation", "delivery", "distribution", "publication", "performance"])
        ])
        
        # Add project type-specific goal
        project_specific = project_goals.get(project_type, project_goals["portfolio"])
        goals.append(project_specific[group_size if group_size in project_specific else "small"])
        
        # Add skill development goals
        skill_specific = skill_development_goals.get(skill_level, skill_development_goals["developing"])
        size_skill_specific = skill_specific[group_size if group_size in skill_specific else "small"]
        goals.extend(size_skill_specific)
        
        # Add metacognitive reflection goals based on skill level
        metacognitive_goals = {
            "beginner": {
                "small": [
                    "How can we reflect on our creative process and identify what inspires us most?",
                    "How might we learn from each other's creative approaches and techniques?",
                    "How do we maintain creative momentum in our intimate collaborative environment?"
                ],
                "medium": [
                    "How can we leverage diverse creative perspectives while maintaining focus?",
                    "How might we identify and address creative blocks through group support?",
                    "How do we balance individual creative expression with collaborative learning?"
                ],
                "large": [
                    "How can we maintain creative coherence while fostering individual expression?",
                    "How might we create knowledge-sharing systems that support creative growth?",
                    "How do we balance structured learning with creative freedom?"
                ]
            },
            "developing": {
                "small": [
                    "How can we reflect on our artistic growth and creative breakthroughs?",
                    "How might we challenge each other's creative boundaries while maintaining support?",
                    "How do we balance artistic experimentation with skill development?"
                ],
                "medium": [
                    "How can we leverage diverse artistic perspectives for creative innovation?",
                    "How might we identify and overcome creative challenges through collaboration?",
                    "How do we balance individual artistic vision with collective creative goals?"
                ],
                "large": [
                    "How can we maintain artistic integrity while fostering collaborative creativity?",
                    "How might we create mentorship systems that support artistic development?",
                    "How do we balance artistic leadership with community creative growth?"
                ]
            },
            "advanced": {
                "small": [
                    "How can we reflect on our artistic mastery and creative evolution?",
                    "How might we mentor emerging artists while continuing our own growth?",
                    "How do we balance artistic leadership with collaborative learning?"
                ],
                "medium": [
                    "How can we leverage our expertise to elevate collaborative creative work?",
                    "How might we identify opportunities for artistic innovation and mentorship?",
                    "How do we balance artistic leadership with fostering creative independence?"
                ],
                "large": [
                    "How can we maintain artistic excellence while building creative community?",
                    "How might we create systems that support both individual mastery and collective growth?",
                    "How do we balance artistic leadership with community creative empowerment?"
                ]
            }
        }
        
        # Add metacognitive goals
        metacognitive_specific = metacognitive_goals.get(skill_level, metacognitive_goals["developing"])
        size_metacognitive_specific = metacognitive_specific[group_size if group_size in metacognitive_specific else "small"]
        goals.extend(size_metacognitive_specific)
        
        return goals

    def _categorize_creative_studio_goals(self, goals: List[str], skill_level: str) -> Dict[str, List[str]]:
        """
        Categorize creative studio goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Creative Studio categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_creative_studio_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for creative studio goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = CreativeStudioGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("creative-studio", CreativeStudioGoalGenerator)
