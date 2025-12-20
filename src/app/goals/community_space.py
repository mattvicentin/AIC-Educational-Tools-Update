"""
Community Space goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class CommunitySpaceGoalGenerator(GoalGenerator):
    """Goal generator for Community Space template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Community Space template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        community_type = answers.get("community_type", "general")
        purpose = answers.get("purpose", "networking")
        group_size = answers.get("group_size", "small")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(community_type, purpose, group_size)
        
        # Categorize the goals
        return self._categorize_community_space_goals(all_goals, community_type)

    def _generate_all_goals(self, community_type: str, purpose: str, group_size: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Community development framework (adapted for different group sizes)
        community_development = {
            "social_justice": {
                "small": {
                    "awareness": "How can we develop deep awareness of social justice issues through intimate dialogue?",
                    "education": "How might we educate ourselves and others through focused peer learning?",
                    "advocacy": "How can we develop advocacy skills through supportive peer collaboration?",
                    "action": "How might we take meaningful action through intimate community organizing?",
                    "impact": "How can we create measurable impact through focused community initiatives?"
                },
                "medium": {
                    "awareness": "How can we develop comprehensive awareness of social justice issues through diverse perspectives?",
                    "education": "How might we educate communities through structured peer learning and workshops?",
                    "advocacy": "How can we develop advocacy campaigns through coordinated peer collaboration?",
                    "action": "How might we take collective action through organized community initiatives?",
                    "impact": "How can we create significant impact through coordinated community efforts?"
                },
                "large": {
                    "awareness": "How can we lead awareness campaigns and establish community education frameworks?",
                    "education": "How might we establish educational programs and mentor community educators?",
                    "advocacy": "How can we lead advocacy movements and establish community organizing frameworks?",
                    "action": "How might we orchestrate large-scale community action and social movements?",
                    "impact": "How can we create systemic impact through community leadership and policy change?"
                }
            },
            "environmental": {
                "small": {
                    "awareness": "How can we develop environmental awareness through intimate peer education?",
                    "action": "How might we take environmental action through focused community initiatives?",
                    "education": "How can we educate others through supportive peer learning?",
                    "advocacy": "How might we advocate for environmental causes through intimate collaboration?",
                    "sustainability": "How can we promote sustainability through local community engagement?"
                },
                "medium": {
                    "awareness": "How can we develop environmental awareness through diverse community perspectives?",
                    "action": "How might we take environmental action through coordinated community initiatives?",
                    "education": "How can we educate communities through structured peer learning?",
                    "advocacy": "How might we advocate for environmental causes through organized collaboration?",
                    "sustainability": "How can we promote sustainability through community-wide engagement?"
                },
                "large": {
                    "awareness": "How can we lead environmental awareness campaigns and establish community education?",
                    "action": "How might we orchestrate large-scale environmental action and community initiatives?",
                    "education": "How can we establish environmental education programs and mentor educators?",
                    "advocacy": "How might we lead environmental advocacy movements and policy change?",
                    "sustainability": "How can we establish sustainability frameworks and community leadership?"
                }
            },
            "health_wellness": {
                "small": {
                    "support": "How can we provide intimate peer support and wellness guidance?",
                    "education": "How might we educate about health and wellness through focused peer learning?",
                    "advocacy": "How can we advocate for health access through supportive collaboration?",
                    "action": "How might we take health action through intimate community initiatives?",
                    "wellness": "How can we promote wellness through local community engagement?"
                },
                "medium": {
                    "support": "How can we provide comprehensive peer support and wellness programs?",
                    "education": "How might we educate communities about health and wellness through structured learning?",
                    "advocacy": "How can we advocate for health access through organized collaboration?",
                    "action": "How might we take health action through coordinated community initiatives?",
                    "wellness": "How can we promote wellness through community-wide engagement?"
                },
                "large": {
                    "support": "How can we establish support networks and mentor wellness leaders?",
                    "education": "How might we establish health education programs and community wellness frameworks?",
                    "advocacy": "How can we lead health advocacy movements and policy change?",
                    "action": "How might we orchestrate large-scale health initiatives and community programs?",
                    "wellness": "How can we establish wellness frameworks and community health leadership?"
                }
            },
            "education": {
                "small": {
                    "learning": "How can we facilitate intimate peer learning and educational support?",
                    "mentoring": "How might we provide mentoring through focused peer relationships?",
                    "resources": "How can we share educational resources through supportive collaboration?",
                    "access": "How might we advocate for educational access through intimate community action?",
                    "impact": "How can we create educational impact through focused community initiatives?"
                },
                "medium": {
                    "learning": "How can we facilitate comprehensive peer learning and educational programs?",
                    "mentoring": "How might we provide mentoring through structured peer relationships?",
                    "resources": "How can we share educational resources through organized collaboration?",
                    "access": "How might we advocate for educational access through coordinated community action?",
                    "impact": "How can we create educational impact through coordinated community initiatives?"
                },
                "large": {
                    "learning": "How can we establish learning frameworks and mentor educational leaders?",
                    "mentoring": "How might we establish mentoring programs and community education leadership?",
                    "resources": "How can we establish resource sharing networks and educational frameworks?",
                    "access": "How might we lead educational advocacy movements and policy change?",
                    "impact": "How can we create systemic educational impact through community leadership?"
                }
            }
        }
        
        # Purpose-specific learning objectives
        purpose_goals = {
            "networking": {
                "small": "How can we build intimate professional networks through focused peer connections and relationship building?",
                "medium": "How might we develop comprehensive professional networks through diverse community connections and relationship building?",
                "large": "How can we establish networking frameworks and mentor community connectors through large-scale relationship building?"
            },
            "advocacy": {
                "small": "How can we develop advocacy skills through intimate peer collaboration and focused community action?",
                "medium": "How might we advance advocacy campaigns through coordinated peer collaboration and organized community action?",
                "large": "How can we lead advocacy movements and establish community organizing frameworks through large-scale action?"
            },
            "volunteer_coordination": {
                "small": "How can we coordinate volunteer efforts through intimate peer collaboration and focused community engagement?",
                "medium": "How might we coordinate volunteer programs through structured peer collaboration and organized community engagement?",
                "large": "How can we establish volunteer coordination frameworks and mentor community organizers through large-scale engagement?"
            },
            "grassroots_movements": {
                "small": "How can we develop grassroots movements through intimate peer organizing and focused community mobilization?",
                "medium": "How might we advance grassroots movements through coordinated peer organizing and organized community mobilization?",
                "large": "How can we lead grassroots movements and establish community organizing frameworks through large-scale mobilization?"
            },
            "community_development": {
                "small": "How can we develop communities through intimate peer collaboration and focused community building?",
                "medium": "How might we advance community development through coordinated peer collaboration and organized community building?",
                "large": "How can we lead community development and establish community building frameworks through large-scale collaboration?"
            }
        }
        
        # Collaborative community goals based on group size
        collaboration_goals = {
            "small": [
                "How can we develop intimate community relationships and deep collaborative skills?",
                "How might we practice direct communication and rapid community feedback?",
                "How can we build trust and accountability through close peer interactions?"
            ],
            "medium": [
                "How can we coordinate diverse community perspectives and expertise for comprehensive impact?",
                "How might we develop leadership skills while supporting community collaboration?",
                "How can we balance individual contributions with collective community achievement?"
            ],
            "large": [
                "How can we orchestrate complex community dynamics and organizational collaboration?",
                "How might we develop systems thinking and cross-functional community coordination?",
                "How can we build scalable community frameworks and organizational structures?"
            ]
        }
        
        # Social impact goals based on group size
        impact_goals = {
            "small": [
                "How can we create focused social impact through intimate community initiatives?",
                "How might we develop personal leadership skills through supportive peer relationships?",
                "How can we build sustainable community practices through local engagement?"
            ],
            "medium": [
                "How can we create significant social impact through coordinated community initiatives?",
                "How might we develop organizational leadership skills through structured collaboration?",
                "How can we build sustainable community systems through organized engagement?"
            ],
            "large": [
                "How can we create systemic social impact through large-scale community initiatives?",
                "How might we develop community leadership skills through mentorship and guidance?",
                "How can we build sustainable community frameworks through comprehensive engagement?"
            ]
        }
        
        # Add metacognitive reflection goals based on community type
        metacognitive_goals = {
            "social_justice": {
                "small": [
                    "How can we reflect on our social justice journey and identify what community organizing methods work best for us?",
                    "How might we learn from each other's advocacy approaches and community building techniques?",
                    "How do we maintain momentum in our intimate social justice work?"
                ],
                "medium": [
                    "How can we leverage diverse social justice perspectives while maintaining focus?",
                    "How might we identify and address community organizing challenges through group support?",
                    "How do we balance individual advocacy with collaborative social justice work?"
                ],
                "large": [
                    "How can we maintain social justice coherence while fostering individual community leadership?",
                    "How might we create knowledge-sharing systems that support social justice growth?",
                    "How do we balance structured organizing with grassroots social justice freedom?"
                ]
            },
            "environmental": {
                "small": [
                    "How can we reflect on our environmental advocacy journey and identify what sustainability methods work best for us?",
                    "How might we learn from each other's environmental approaches and community building techniques?",
                    "How do we maintain momentum in our intimate environmental work?"
                ],
                "medium": [
                    "How can we leverage diverse environmental perspectives while maintaining focus?",
                    "How might we identify and address sustainability challenges through group support?",
                    "How do we balance individual environmental action with collaborative community work?"
                ],
                "large": [
                    "How can we maintain environmental coherence while fostering individual community leadership?",
                    "How might we create knowledge-sharing systems that support environmental growth?",
                    "How do we balance structured environmental organizing with grassroots sustainability freedom?"
                ]
            },
            "health_wellness": {
                "small": [
                    "How can we reflect on our health advocacy journey and identify what wellness methods work best for us?",
                    "How might we learn from each other's health approaches and community support techniques?",
                    "How do we maintain momentum in our intimate health and wellness work?"
                ],
                "medium": [
                    "How can we leverage diverse health perspectives while maintaining focus?",
                    "How might we identify and address wellness challenges through group support?",
                    "How do we balance individual health advocacy with collaborative community work?"
                ],
                "large": [
                    "How can we maintain health coherence while fostering individual community leadership?",
                    "How might we create knowledge-sharing systems that support health and wellness growth?",
                    "How do we balance structured health organizing with grassroots wellness freedom?"
                ]
            },
            "education": {
                "small": [
                    "How can we reflect on our educational advocacy journey and identify what learning methods work best for us?",
                    "How might we learn from each other's educational approaches and community teaching techniques?",
                    "How do we maintain momentum in our intimate educational work?"
                ],
                "medium": [
                    "How can we leverage diverse educational perspectives while maintaining focus?",
                    "How might we identify and address learning challenges through group support?",
                    "How do we balance individual educational advocacy with collaborative community work?"
                ],
                "large": [
                    "How can we maintain educational coherence while fostering individual community leadership?",
                    "How might we create knowledge-sharing systems that support educational growth?",
                    "How do we balance structured educational organizing with grassroots learning freedom?"
                ]
            }
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add community type-specific development goals
        type_specific = community_development.get(community_type, community_development["social_justice"])
        size_specific = type_specific[group_size if group_size in type_specific else "small"]
        
        # Helper function to safely get the first available key
        def get_first_available(keys, default=""):
            for key in keys:
                if key in size_specific:
                    return size_specific[key]
            return default
        
        goals.extend([
            get_first_available(["awareness", "support", "learning"]),
            get_first_available(["education", "action", "mentoring"]),
            get_first_available(["advocacy", "resources", "access"]),
            get_first_available(["action", "sustainability", "wellness", "impact"]),
            get_first_available(["impact", "wellness", "sustainability", "access"])
        ])
        
        # Add purpose-specific goal
        purpose_specific = purpose_goals.get(purpose, purpose_goals["networking"])
        goals.append(purpose_specific[group_size if group_size in purpose_specific else "small"])
        
        # Add collaboration goals
        goals.extend(collaboration_goals[group_size if group_size in collaboration_goals else "small"])
        
        # Add impact goals
        goals.extend(impact_goals[group_size if group_size in impact_goals else "small"])
        
        # Add metacognitive goals
        metacognitive_specific = metacognitive_goals.get(community_type, metacognitive_goals["social_justice"])
        size_metacognitive_specific = metacognitive_specific[group_size if group_size in metacognitive_specific else "small"]
        goals.extend(size_metacognitive_specific)
        
        return goals

    def _categorize_community_space_goals(self, goals: List[str], community_type: str) -> Dict[str, List[str]]:
        """
        Categorize community space goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Community Space categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_community_space_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for community space goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = CommunitySpaceGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("community-space", CommunitySpaceGoalGenerator)
