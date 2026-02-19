"""
Tests for Multi-Project Intelligence functionality
"""

import unittest
from unittest.mock import AsyncMock, patch
import json


class TestMultiProjectIntelligence(unittest.TestCase):
    """Test suite for Multi-Project Intelligence"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_projects = [
            {"id": "project_1", "tasks": ["task_1", "task_2"]},
            {"id": "project_2", "tasks": ["task_3", "task_4"]}
        ]
        self.sample_priority = 5

    def test_multi_project_intelligence(self):
        """Test multi-project intelligence functionality"""
        # Arrange
        projects = self.sample_projects
        priority = self.sample_priority
        expected_result = {"projects": projects, "priority": priority}

        # Act
        result = multi_project_intelligence(projects, priority)

        # Assert
        self.assertEqual(result, expected_result, 
                        f"Expected {expected_result}, but got {result}")

    def test_multi_project_intelligence_empty_projects(self):
        """Test multi-project intelligence with empty projects"""
        # Arrange
        projects = []
        priority = self.sample_priority
        expected_result = {"projects": [], "priority": priority}

        # Act
        result = multi_project_intelligence(projects, priority)

        # Assert
        self.assertEqual(result, expected_result)

    def test_multi_project_intelligence_invalid_priority(self):
        """Test multi-project intelligence with invalid priority"""
        # Arrange
        projects = self.sample_projects
        priority = -1

        # Act & Assert
        with self.assertRaises(ValueError):
            multi_project_intelligence(projects, priority)

    def test_multi_project_intelligence_project_analysis(self):
        """Test project analysis functionality"""
        # Arrange
        projects = self.sample_projects
        expected_analysis = {
            "total_projects": 2,
            "total_tasks": 4,
            "avg_tasks_per_project": 2.0
        }

        # Act
        result = analyze_projects(projects)

        # Assert
        self.assertEqual(result["total_projects"], expected_analysis["total_projects"])
        self.assertEqual(result["total_tasks"], expected_analysis["total_tasks"])

    def test_multi_project_intelligence_task_distribution(self):
        """Test task distribution across projects"""
        # Arrange
        projects = self.sample_projects

        # Act
        result = get_task_distribution(projects)

        # Assert
        self.assertEqual(result["project_1"], 2)
        self.assertEqual(result["project_2"], 2)

    def test_multi_project_intelligence_priority_sorting(self):
        """Test project sorting by priority"""
        # Arrange
        projects_with_priority = [
            {"id": "project_1", "priority": 3},
            {"id": "project_2", "priority": 1},
            {"id": "project_3", "priority": 5}
        ]

        # Act
        result = sort_projects_by_priority(projects_with_priority)

        # Assert
        self.assertEqual(result[0]["id"], "project_3")  # Highest priority first
        self.assertEqual(result[2]["id"], "project_2")  # Lowest priority last

    @patch(f"{__name__}.get_project_insights")
    def test_multi_project_intelligence_with_mock(self, mock_insights):
        """Test multi-project intelligence with mocked service"""
        # Arrange
        mock_insights.return_value = {"insights": "mocked_data"}
        projects = self.sample_projects
        priority = self.sample_priority

        # Act
        result = multi_project_intelligence(projects, priority)

        # Assert
        self.assertIn("projects", result)
        self.assertIn("priority", result)


def get_project_insights():
    """Mock get project insights function"""
    return {"insights": "default_data"}


# Mock functions for testing
def multi_project_intelligence(projects, priority):
    """Mock multi-project intelligence function"""
    if priority < 0:
        raise ValueError("Priority cannot be negative")
    
    return {"projects": projects, "priority": priority}


def analyze_projects(projects):
    """Mock analyze projects function"""
    total_tasks = sum(len(project.get("tasks", [])) for project in projects)
    return {
        "total_projects": len(projects),
        "total_tasks": total_tasks,
        "avg_tasks_per_project": total_tasks / len(projects) if projects else 0
    }


def get_task_distribution(projects):
    """Mock get task distribution function"""
    distribution = {}
    for project in projects:
        distribution[project["id"]] = len(project.get("tasks", []))
    return distribution


def sort_projects_by_priority(projects):
    """Mock sort projects by priority function"""
    return sorted(projects, key=lambda x: x.get("priority", 0), reverse=True)


if __name__ == '__main__':
    unittest.main()
