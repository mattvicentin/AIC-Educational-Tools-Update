"""
Business Hub goal generation
Extracted from room.py for better maintainability and goal categorization
"""

from typing import Dict, List, Any
from .base import GoalGenerator


class BusinessHubGoalGenerator(GoalGenerator):
    """Goal generator for Business Hub template."""

    def generate_goals(self, answers: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Generate categorized goals for Business Hub template.
        
        Args:
            answers: Dictionary containing user selections from the wizard
            
        Returns:
            Dictionary with categorized goals: core_goals, collaboration_goals, reflection_goals
        """
        business_type = answers.get("business_type", "general")
        focus_area = answers.get("focus_area", "strategy")
        team_structure = answers.get("team_structure", "small")
        
        # Generate all goals using the original logic
        all_goals = self._generate_all_goals(business_type, focus_area, team_structure)
        
        # Categorize the goals
        return self._categorize_business_hub_goals(all_goals, team_structure)

    def _generate_all_goals(self, business_type: str, focus_area: str, team_structure: str) -> List[str]:
        """Generate all goals using the original logic."""
        # Business competency framework (adapted for different group sizes)
        business_competencies = {
            "startup": {
                "small": {
                    "ideation": "How might we validate startup ideas through intensive market research and customer discovery?",
                    "execution": "How can we develop minimum viable products through rapid prototyping and iteration?",
                    "funding": "How might we prepare compelling pitch decks and secure initial funding opportunities?",
                    "team_building": "How can we build a core founding team with complementary skills and shared vision?",
                    "scaling": "How might we establish scalable business processes and growth strategies?"
                },
                "medium": {
                    "ideation": "What comprehensive market analysis approaches can we leverage for competitive positioning?",
                    "execution": "How can we coordinate product development across multiple team functions effectively?",
                    "funding": "How might we develop sophisticated financial models and investor relations?",
                    "team_building": "How can we recruit and manage specialized talent across key business areas?",
                    "scaling": "How might we implement systematic growth strategies and operational excellence?"
                },
                "large": {
                    "ideation": "How can we lead market disruption through innovative business model development?",
                    "execution": "How might we orchestrate complex product ecosystems and platform strategies?",
                    "funding": "How can we manage multiple funding rounds and strategic partnerships?",
                    "team_building": "How might we build and scale high-performance teams across multiple locations?",
                    "scaling": "How can we establish industry leadership through systematic innovation and expansion?"
                }
            },
            "entrepreneurship": {
                "small": {
                    "opportunity": "How can we identify and evaluate business opportunities through systematic analysis?",
                    "planning": "How might we develop comprehensive business plans with realistic financial projections?",
                    "execution": "How can we launch ventures with lean startup methodology and rapid iteration?",
                    "networking": "How might we build strategic relationships with mentors, investors, and partners?",
                    "growth": "How can we scale successful ventures through systematic market expansion?"
                },
                "medium": {
                    "opportunity": "What market trends should we analyze to identify emerging business opportunities?",
                    "planning": "How can we create sophisticated business strategies with multiple growth scenarios?",
                    "execution": "How might we manage venture portfolios and optimize resource allocation?",
                    "networking": "How can we develop extensive professional networks and strategic alliances?",
                    "growth": "How might we implement multi-channel growth strategies and market penetration?"
                },
                "large": {
                    "opportunity": "How can we shape market trends and create new business categories?",
                    "planning": "How might we develop corporate entrepreneurship strategies and innovation pipelines?",
                    "execution": "How can we lead entrepreneurial initiatives across multiple business units?",
                    "networking": "How might we establish thought leadership and industry influence networks?",
                    "growth": "How can we drive organizational transformation through entrepreneurial leadership?"
                }
            },
            "consulting": {
                "small": {
                    "analysis": "How can we conduct deep client analysis and develop targeted recommendations?",
                    "communication": "How might we deliver compelling presentations and build client relationships?",
                    "problem_solving": "How can we solve complex business problems through structured methodologies?",
                    "project_management": "How might we manage consulting projects with clear deliverables and timelines?",
                    "expertise": "How can we develop specialized expertise in specific business domains?"
                },
                "medium": {
                    "analysis": "How might we lead comprehensive business assessments and strategic analysis?",
                    "communication": "How can we facilitate client workshops and stakeholder engagement effectively?",
                    "problem_solving": "How might we design innovative solutions and implementation roadmaps?",
                    "project_management": "How can we coordinate multi-disciplinary consulting teams and resources?",
                    "expertise": "How might we build consulting practice areas and thought leadership?"
                },
                "large": {
                    "analysis": "How can we conduct enterprise-wide transformation and strategic planning?",
                    "communication": "How might we lead organizational change and executive-level presentations?",
                    "problem_solving": "How can we architect complex business solutions and digital transformations?",
                    "project_management": "How might we manage large-scale consulting engagements and client portfolios?",
                    "expertise": "How can we establish consulting practice leadership and industry expertise?"
                }
            },
            "corporate": {
                "small": {
                    "strategy": "How can we develop departmental strategies aligned with corporate objectives?",
                    "operations": "How might we optimize business processes and improve operational efficiency?",
                    "leadership": "How can we lead small teams and drive performance improvement?",
                    "innovation": "How might we identify and implement process improvements and innovations?",
                    "collaboration": "How can we work effectively across functional boundaries and teams?"
                },
                "medium": {
                    "strategy": "How might we develop business unit strategies and competitive positioning?",
                    "operations": "How can we manage complex operations and implement best practices?",
                    "leadership": "How might we lead cross-functional teams and organizational change?",
                    "innovation": "How can we drive innovation initiatives and digital transformation?",
                    "collaboration": "How might we build strategic partnerships and stakeholder relationships?"
                },
                "large": {
                    "strategy": "How can we develop corporate strategy and long-term business planning?",
                    "operations": "How might we optimize enterprise operations and global supply chains?",
                    "leadership": "How can we lead organizational transformation and cultural change?",
                    "innovation": "How might we establish innovation ecosystems and R&D strategies?",
                    "collaboration": "How can we build industry partnerships and ecosystem relationships?"
                }
            },
            "freelance": {
                "small": {
                    "specialization": "To develop deep expertise in specific business domains",
                    "client_management": "To build and maintain strong client relationships",
                    "delivery": "To deliver high-quality work with clear value proposition",
                    "marketing": "To develop personal brand and attract ideal clients",
                    "business_development": "To grow freelance business through strategic networking"
                },
                "medium": {
                    "specialization": "To establish thought leadership in specialized business areas",
                    "client_management": "To manage client portfolios and long-term relationships",
                    "delivery": "To scale service delivery through systems and processes",
                    "marketing": "To build professional reputation and industry recognition",
                    "business_development": "To develop strategic partnerships and referral networks"
                },
                "large": {
                    "specialization": "To create specialized consulting practices and service offerings",
                    "client_management": "To manage enterprise clients and strategic accounts",
                    "delivery": "To build scalable service delivery models and teams",
                    "marketing": "To establish industry leadership and market positioning",
                    "business_development": "To develop strategic alliances and business partnerships"
                }
            }
        }
        
        # Focus area-specific learning objectives
        focus_area_goals = {
            "business_planning": {
                "small": "How can we develop comprehensive business plans with realistic financial projections and market analysis?",
                "medium": "How might we create sophisticated business strategies with multiple scenarios and risk assessment?",
                "large": "How can we design enterprise-wide strategic plans and long-term business roadmaps?"
            },
            "market_research": {
                "small": "How might we conduct targeted market research and competitive analysis for specific opportunities?",
                "medium": "How can we lead comprehensive market studies and customer insight development?",
                "large": "How might we establish market intelligence systems and strategic market positioning?"
            },
            "product_development": {
                "small": "How can we develop minimum viable products through rapid prototyping and user feedback?",
                "medium": "How might we coordinate product development across multiple functions and stakeholders?",
                "large": "How can we lead product strategy and innovation pipelines across business units?"
            },
            "financial_planning": {
                "small": "How might we create financial models and projections for business planning and funding?",
                "medium": "How can we develop sophisticated financial strategies and investment analysis?",
                "large": "How might we establish financial planning systems and capital allocation strategies?"
            },
            "team_management": {
                "small": "How can we lead small teams and develop individual performance and growth?",
                "medium": "How might we manage cross-functional teams and organizational development?",
                "large": "How can we lead organizational transformation and build high-performance cultures?"
            },
            "strategy_development": {
                "small": "How might we develop strategic plans aligned with business objectives and market opportunities?",
                "medium": "How can we create competitive strategies and strategic positioning frameworks?",
                "large": "How might we establish corporate strategy and long-term business planning systems?"
            }
        }
        
        # Collaborative learning goals based on team structure
        collaboration_goals = {
            "small": [
                "How can we develop intimate working relationships and deep collaborative skills?",
                "How might we practice direct communication and rapid decision-making processes?",
                "How does our small team size affect our ability to build trust and accountability?"
            ],
            "medium": [
                "How can we coordinate diverse expertise and perspectives for comprehensive solutions?",
                "How might we develop leadership skills while supporting team collaboration?",
                "How do we balance individual contributions with collective achievement?"
            ],
            "large": [
                "How can we orchestrate complex team dynamics and organizational collaboration?",
                "How might we develop systems thinking and cross-functional coordination skills?",
                "How do we build scalable collaboration frameworks and team structures?"
            ]
        }
        
        # Build comprehensive goal set
        goals = []
        
        # Add business type-specific competencies
        business_specific = business_competencies.get(business_type, business_competencies["startup"])
        team_specific = business_specific[team_structure]
        goals.extend([
            team_specific["ideation"] if "ideation" in team_specific else team_specific["opportunity"] if "opportunity" in team_specific else team_specific["analysis"] if "analysis" in team_specific else team_specific["strategy"] if "strategy" in team_specific else team_specific["specialization"],
            team_specific["execution"] if "execution" in team_specific else team_specific["planning"] if "planning" in team_specific else team_specific["communication"] if "communication" in team_specific else team_specific["operations"] if "operations" in team_specific else team_specific["client_management"],
            team_specific["team_building"] if "team_building" in team_specific else team_specific["networking"] if "networking" in team_specific else team_specific["problem_solving"] if "problem_solving" in team_specific else team_specific["leadership"] if "leadership" in team_specific else team_specific["delivery"],
            team_specific["scaling"] if "scaling" in team_specific else team_specific["growth"] if "growth" in team_specific else team_specific["project_management"] if "project_management" in team_specific else team_specific["innovation"] if "innovation" in team_specific else team_specific["marketing"]
        ])
        
        # Add focus area-specific goal
        focus_specific = focus_area_goals.get(focus_area, focus_area_goals["business_planning"])
        goals.append(focus_specific[team_structure])
        
        # Add collaboration goals
        goals.extend(collaboration_goals[team_structure])
        
        # Add metacognitive reflection goals based on team structure
        metacognitive_goals = {
            "small": [
                "How can we reflect on our intimate team dynamics and their impact on our decision-making?",
                "How might we learn from each other's complementary skills and knowledge gaps?",
                "How do we maintain focus and momentum in our small, close-knit team environment?"
            ],
            "medium": [
                "How can we leverage diverse perspectives while maintaining strategic alignment?",
                "How might we identify and address communication gaps across different expertise areas?",
                "How do we balance individual autonomy with collective responsibility?"
            ],
            "large": [
                "How can we maintain organizational coherence while fostering innovation across multiple teams?",
                "How might we create knowledge-sharing systems that scale across different locations?",
                "How do we balance centralized strategy with decentralized execution?"
            ]
        }
        
        # Add metacognitive goals
        goals.extend(metacognitive_goals[team_structure])
        
        return goals

    def _categorize_business_hub_goals(self, goals: List[str], team_structure: str) -> Dict[str, List[str]]:
        """
        Categorize business hub goals into core, collaboration, and reflection.
        """
        if not goals:
            return {
                "core_goals": [],
                "collaboration_goals": [],
                "reflection_goals": []
            }

        # Business Hub categorization: first 5 = core, next 3 = collaboration, rest = reflection
        core_count = min(5, len(goals))
        collab_count = min(3, max(0, len(goals) - core_count))

        return {
            "core_goals": goals[:core_count],
            "collaboration_goals": goals[core_count:core_count + collab_count],
            "reflection_goals": goals[core_count + collab_count:]
        }


# Backward compatibility function
def generate_business_hub_goals(answers: Dict[str, Any]) -> List[str]:
    """
    Backward compatibility function for business hub goal generation.
    Returns flat list for existing code compatibility.
    """
    generator = BusinessHubGoalGenerator()
    categorized_goals = generator.generate_goals(answers)

    # Flatten for backward compatibility
    all_goals = []
    all_goals.extend(categorized_goals.get("core_goals", []))
    all_goals.extend(categorized_goals.get("collaboration_goals", []))
    all_goals.extend(categorized_goals.get("reflection_goals", []))

    return all_goals


# Auto-register this generator with the registry
from .registry import GoalGeneratorRegistry
GoalGeneratorRegistry.register("business-hub", BusinessHubGoalGenerator)
