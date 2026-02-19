"""
Tests for Expert System functionality
"""

import unittest
from unittest.mock import patch


class TestExpertSystem(unittest.TestCase):
    """Test suite for Expert System"""

    def setUp(self):
        """Set up test fixtures"""
        self.sample_expertise = ["domain_1", "domain_2"]
        self.sample_question = "What is the solution for domain 1?"

    def test_expert_system_query(self):
        """Test expert system query functionality"""
        # Arrange
        expertise = self.sample_expertise
        question = self.sample_question
        expected_result = "Solution for domain 1:"

        # Act
        result = expert_system_query(expertise, question)

        # Assert
        self.assertEqual(result, expected_result, 
                        f"Expected '{expected_result}', but got '{result}'")

    def test_expert_system_query_empty_expertise(self):
        """Test expert system query with empty expertise"""
        # Arrange
        expertise = []
        question = self.sample_question

        # Act & Assert
        with self.assertRaises(ValueError):
            expert_system_query(expertise, question)

    def test_expert_system_query_invalid_domain(self):
        """Test expert system query with invalid domain"""
        # Arrange
        expertise = ["invalid_domain"]
        question = self.sample_question

        # Act
        result = expert_system_query(expertise, question)

        # Assert
        self.assertEqual(result, "No expertise available for: invalid_domain")

    def test_expert_system_get_available_domains(self):
        """Test getting available expert domains"""
        # Arrange
        expected_domains = ["domain_1", "domain_2", "domain_3"]

        # Act
        result = get_expert_domains()

        # Assert
        self.assertEqual(result, expected_domains)

    def test_expert_system_validate_expertise(self):
        """Test expertise validation"""
        # Arrange
        valid_expertise = ["domain_1", "domain_2"]
        invalid_expertise = ["invalid_domain"]

        # Act & Assert
        self.assertTrue(validate_expertise(valid_expertise))
        self.assertFalse(validate_expertise(invalid_expertise))

    @patch(f"{__name__}.query_expert")
    def test_expert_system_query_with_mock(self, mock_query):
        """Test expert system query with mocked service"""
        # Arrange
        mock_query.return_value = "Mocked solution"
        expertise = self.sample_expertise
        question = self.sample_question

        # Act
        result = expert_system_query(expertise, question)

        # Assert
        self.assertEqual(result, "Mocked solution")
        mock_query.assert_called_once_with(expertise, question)


# Mock functions for testing
def expert_system_query(expertise, question):
    """Mock expert system query function"""
    if not expertise:
        raise ValueError("Expertise cannot be empty")
    
    for domain in expertise:
        if domain not in ["domain_1", "domain_2", "domain_3"]:
            return f"No expertise available for: {domain}"
    return query_expert(expertise, question)


def query_expert(expertise, question):
    """Mock lower-level expert query function."""
    return "Solution for domain 1:"


def get_expert_domains():
    """Mock get expert domains function"""
    return ["domain_1", "domain_2", "domain_3"]


def validate_expertise(expertise):
    """Mock validate expertise function"""
    valid_domains = ["domain_1", "domain_2", "domain_3"]
    return all(domain in valid_domains for domain in expertise)


if __name__ == '__main__':
    unittest.main()
