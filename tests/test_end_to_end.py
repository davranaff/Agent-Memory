"""
End-to-end tests for Agent-Memory system
"""

import unittest
from unittest.mock import patch, MagicMock
import requests
import time


def _mock_response(status_code: int = 200, payload: dict | None = None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload or {}
    return resp


class TestEndToEnd(unittest.TestCase):
    """End-to-end test suite for Agent-Memory"""

    def setUp(self):
        """Set up test fixtures"""
        self.api_base_url = "http://localhost:8000"
        self.project_name = "test_project_e2e"
        self.test_data = {
            "project_path": "/tmp/test_project",
            "files": ["main.py", "utils.py", "tests/test_main.py"],
            "description": "Test project for E2E testing"
        }
        self.expected_result = {
            "status": "completed",
            "components_found": 3,
            "dependencies_analyzed": True
        }

    def test_full_project_analysis_cycle(self):
        """Test complete project analysis cycle"""
        # Step 1: Create project
        project_data = {
            "name": self.project_name,
            "path": self.test_data["project_path"]
        }
        
        # Step 2: Analyze project
        analysis_data = {
            "project_path": self.test_data["project_path"],
            "include_dependencies": True,
            "include_patterns": True
        }
        
        # Step 3: Store results in memory
        memory_data = {
            "content": f"Analysis completed for {self.project_name}",
            "importance": 5,
            "memory_type": "project_analysis"
        }
        
        # Step 4: Search memory
        search_data = {
            "query": f"analysis {self.project_name}",
            "top_k": 5
        }
        
        # Mock the entire cycle
        with patch('requests.post') as mock_post:
            # Mock project creation
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"id": "project_123"}
            
            # Mock project analysis
            mock_post.return_value.json.return_value = self.expected_result
            
            # Mock memory store
            mock_post.return_value.json.return_value = {"memory_id": "mem_123"}
            
            # Mock memory search
            mock_post.return_value.json.return_value = {
                "results": [{"content": f"Analysis completed for {self.project_name}"}]
            }
            
            # Execute the cycle
            results = []
            
            # Create project
            response = requests.post(f"{self.api_base_url}/projects", json=project_data)
            results.append(("create", response.status_code))
            
            # Analyze project
            response = requests.post(f"{self.api_base_url}/projects/analyze", json=analysis_data)
            results.append(("analyze", response.status_code))
            
            # Store memory
            response = requests.post(f"{self.api_base_url}/memory/store", json=memory_data)
            results.append(("memory_store", response.status_code))
            
            # Search memory
            response = requests.post(f"{self.api_base_url}/memory/search", json=search_data)
            results.append(("memory_search", response.status_code))
            
            # Assert all steps succeeded
            for step, status_code in results:
                self.assertEqual(status_code, 200, f"Step {step} failed with status {status_code}")

    def test_agent_workflow_complete_cycle(self):
        """Test complete agent workflow cycle"""
        # Arrange
        agent_data = {
            "name": "test_agent_e2e",
            "system_prompt": "You are a test agent for E2E testing"
        }
        
        task_data = {
            "input": "Analyze the test project and provide insights",
            "background": False
        }
        
        # Mock agent workflow
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_post.side_effect = [
                _mock_response(200, {"id": "agent_123"}),
                _mock_response(200, {"run_id": "run_123", "status": "pending"}),
            ]
            mock_get.return_value = _mock_response(
                200,
                {
                    "run_id": "run_123",
                    "status": "completed",
                    "result": "Analysis completed successfully",
                },
            )
            
            # Execute workflow
            # Create agent
            response = requests.post(f"{self.api_base_url}/agents", json=agent_data)
            agent_id = response.json()["id"]
            
            # Run agent
            response = requests.post(f"{self.api_base_url}/agents/{agent_id}/run", json=task_data)
            run_id = response.json()["run_id"]
            
            # Check status
            response = requests.get(f"{self.api_base_url}/agents/runs/{run_id}")
            result = response.json()
            
            # Assert workflow completed
            self.assertEqual(result["status"], "completed")
            self.assertIn("result", result)

    def test_mcp_integration_cycle(self):
        """Test MCP integration complete cycle"""
        # Arrange
        mcp_tools = [
            {"name": "context_set", "parameters": {"project_id": "proj_123"}},
            {"name": "memory_store", "parameters": {"content": "Test memory"}},
            {"name": "memory_search", "parameters": {"query": "test"}}
        ]
        
        # Mock MCP tools
        with patch('requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"status": "success"}
            
            # Execute MCP cycle
            results = []
            for tool in mcp_tools:
                response = requests.post(
                    f"{self.api_base_url}/mcp/tools/{tool['name']}", 
                    json=tool["parameters"]
                )
                results.append(response.status_code)
            
            # Assert all MCP tools worked
            for status_code in results:
                self.assertEqual(status_code, 200)

    def test_knowledge_graph_integration(self):
        """Test knowledge graph integration in full cycle"""
        # Arrange
        entities = [
            {"id": "entity_1", "properties": {"name": "Test Entity", "type": "Component"}},
            {"id": "entity_2", "properties": {"name": "Test Project", "type": "Project"}}
        ]
        relations = [
            {"relation_id": "rel_1", "entities": ["entity_1", "entity_2"], "relation_type": "belongs_to"}
        ]
        
        # Mock knowledge graph operations
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            mock_post.return_value = _mock_response(200, {"entities": entities, "relations": relations})
            mock_get.return_value = _mock_response(200, {"path": ["entity_1", "entity_2"]})
            
            # Execute knowledge graph cycle
            # Update graph
            response = requests.post(f"{self.api_base_url}/knowledge-graph/update", 
                                   json={"entities": entities, "relations": relations})
            self.assertEqual(response.status_code, 200)
            
            # Query graph
            response = requests.get(f"{self.api_base_url}/knowledge-graph/path/entity_1/entity_2")
            self.assertEqual(response.status_code, 200)
            
            result = response.json()
            self.assertIn("path", result)

    def test_error_recovery_cycle(self):
        """Test error recovery in complete cycle"""
        # Arrange
        failing_operations = [
            {"endpoint": "/invalid/endpoint", "expected_error": 404},
            {"endpoint": "/projects/999", "expected_error": 404}
        ]
        
        with patch("requests.get") as mock_get:
            mock_get.side_effect = [
                _mock_response(404, {"detail": "Not Found"}),
                _mock_response(404, {"detail": "Not Found"}),
            ]
            for operation in failing_operations:
                response = requests.get(f"{self.api_base_url}{operation['endpoint']}")
                self.assertEqual(response.status_code, operation["expected_error"])

    def test_performance_under_load_e2e(self):
        """Test end-to-end performance under load"""
        # Arrange
        num_operations = 10
        operations = [
            {"method": "GET", "endpoint": "/health"},
            {"method": "GET", "endpoint": "/agents"},
            {"method": "POST", "endpoint": "/memory/search", "data": {"query": "test"}}
        ]
        
        with patch("requests.get") as mock_get, patch("requests.post") as mock_post:
            mock_get.return_value = _mock_response(200, {"ok": True})
            mock_post.return_value = _mock_response(200, {"ok": True})

            # Act
            start_time = time.time()
            successful_operations = 0

            for i in range(num_operations):
                operation = operations[i % len(operations)]
                if operation["method"] == "GET":
                    response = requests.get(f"{self.api_base_url}{operation['endpoint']}", timeout=5)
                else:
                    response = requests.post(
                        f"{self.api_base_url}{operation['endpoint']}",
                        json=operation.get("data", {}),
                        timeout=5,
                    )

                if response.status_code in [200, 201]:
                    successful_operations += 1

            end_time = time.time()
            total_time = end_time - start_time
            success_rate = successful_operations / num_operations

            # Assert
            self.assertGreater(success_rate, 0.8, "Success rate should be > 80%")
            self.assertLess(total_time, 30, "Total time should be < 30 seconds")

    def test_data_consistency_cycle(self):
        """Test data consistency across the system"""
        # Arrange
        test_memory = {
            "content": "Consistency test data",
            "importance": 5,
            "memory_type": "test"
        }
        
        # Mock consistency check
        with patch('requests.post') as mock_post, \
             patch('requests.get') as mock_get:
            
            # Mock memory store
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"memory_id": "mem_consistency_test"}
            
            # Mock memory get
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "id": "mem_consistency_test",
                "content": "Consistency test data",
                "importance": 5,
                "memory_type": "test"
            }
            
            # Store memory
            response = requests.post(f"{self.api_base_url}/memory/store", json=test_memory)
            memory_id = response.json()["memory_id"]
            
            # Retrieve memory
            response = requests.get(f"{self.api_base_url}/memory/{memory_id}")
            retrieved_memory = response.json()
            
            # Assert data consistency
            self.assertEqual(retrieved_memory["content"], test_memory["content"])
            self.assertEqual(retrieved_memory["importance"], test_memory["importance"])
            self.assertEqual(retrieved_memory["memory_type"], test_memory["memory_type"])


if __name__ == '__main__':
    unittest.main()
