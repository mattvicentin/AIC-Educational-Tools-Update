#!/usr/bin/env python3
"""
Test the improved room description logic with real production data.
Uses the sample data from room_sample.csv to verify improvements.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.room_descriptions import generate_room_short_description


# Test cases from production data (room_sample.csv)
TEST_CASES = [
    {
        "id": 100,
        "name": "Tuberculosis Study",
        "goals": "To learn about the history, pathology, treatment, social dimensions, and cultural influences of tuberculosis.",
        "group_size": None,
        "old_description": "To learn about the history, pathology, treatment, social dimensions, and cultural influences of tuberculosis. Designed to help you achieve your learning goals.",
        "expected": "To learn about the history, pathology, treatment, social dimensions, and cultural influences of tuberculosis."
    },
    {
        "id": 101,
        "name": "Two Sentence Goals",
        "goals": "Learn Python programming fundamentals. Build real-world applications with best practices.",
        "group_size": None,
        "old_description": "Generic description",
        "expected": "Learn Python programming fundamentals. Build real-world applications with best practices."
    },
    {
        "id": 102,
        "name": "Multi-line Goals",
        "goals": """Understand machine learning algorithms
Apply them to real datasets
Build predictive models""",
        "group_size": None,
        "old_description": "Generic description",
        "expected": "Understand machine learning algorithms. Apply them to real datasets."
    },
    {
        "id": 90,
        "name": "Python Sudoku Solver Development",
        "goals": "To build a Soduku program in Python that solves all levels of puzzle.",
        "group_size": None,
        "old_description": "A collaborative learning space focused on python sudoku solver development. Designed to help you achieve your learning goals through structured guidance and support."
    },
    {
        "id": 89,
        "name": "Systems Thinking for Student Leadership",
        "goals": "Help college student leaders learn and understand systems thinking and how it can help them become better leaders in their decision making process",
        "group_size": None,
        "old_description": "A collaborative learning space focused on systems thinking for student leadership. Designed to help you achieve your learning goals through structured guidance and support."
    },
    {
        "id": 86,
        "name": "Costa Rica's Earth Charter Performance Analysis",
        "goals": "To use theories and methods in Education for Sustainable Development and priciples of creative coexistence of nature and humanity to assess Costa Rica success or failure in implementing or living up to the Earth Charter.",
        "group_size": None,
        "old_description": "A collaborative learning space focused on costa rica's earth charter performance analysis. Designed to help you achieve your learning goals through structured guidance and support."
    },
    {
        "id": 84,
        "name": "Science Study Group",
        "goals": """How might we explain science phenomena and demonstrate conceptual understanding?
How can we conduct science experiments and apply scientific methods?
How might we interpret science data and identify patterns and relationships?
How can we assess the reliability of science evidence and experimental design?""",
        "group_size": "medium",
        "old_description": "Unlock the power of collaborative learning! Join forces with peers to tackle challenging concepts, share insights, and accelerate your understanding. Experience the magic of group problem-solving where everyone's perspective makes the whole team stronger. Together, you'll achieve more than you ever could alone!"
    },
    {
        "id": 81,
        "name": "Latin America: A Historical Journey",
        "goals": "To learn the history of Latin America",
        "group_size": None,
        "old_description": "A collaborative learning space focused on latin america: a historical journey. Designed to help you achieve your learning goals through structured guidance and support."
    },
]


def test_description_improvements():
    """Test the improved description logic with production data."""
    
    print("🧪 Testing Improved Room Description Logic")
    print("=" * 80)
    print()
    
    for i, test_case in enumerate(TEST_CASES, 1):
        room_id = test_case['id']
        name = test_case['name']
        goals = test_case['goals']
        group_size = test_case.get('group_size') or ""
        old_desc = test_case['old_description']
        
        # Generate new description
        new_desc = generate_room_short_description(
            template_type="general",
            room_name=name,
            group_size=group_size,
            goals=goals
        )
        
        # Check if it changed
        changed = new_desc != old_desc
        status = "✅ IMPROVED" if changed else "⚠️  NO CHANGE"
        
        print(f"Test {i}/{len(TEST_CASES)}: Room {room_id} - {name}")
        print("-" * 80)
        print(f"Goals: {goals[:100]}..." if len(goals) > 100 else f"Goals: {goals}")
        print()
        print(f"OLD: {old_desc}")
        print()
        print(f"NEW: {new_desc}")
        print()
        print(f"Status: {status}")
        print(f"Length: {len(old_desc)} → {len(new_desc)} chars")
        print("=" * 80)
        print()
    
    # Summary
    improved_count = sum(1 for tc in TEST_CASES if generate_room_short_description(
        "general", tc['name'], tc.get('group_size') or "", tc['goals']
    ) != tc['old_description'])
    
    print(f"📊 SUMMARY")
    print(f"Total test cases: {len(TEST_CASES)}")
    print(f"Descriptions improved: {improved_count}")
    print(f"Unchanged: {len(TEST_CASES) - improved_count}")
    print()
    print(f"✅ Improvement rate: {(improved_count/len(TEST_CASES)*100):.1f}%")


if __name__ == '__main__':
    test_description_improvements()

