"""Main technology stack profiler."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Project, Component
from .detector import TechnologyDetector
from .models import (
    TechnologyStack, Technology, Framework, Database, BuildTool,
    TechnologyCategory, MaturityLevel
)

logger = logging.getLogger(__name__)


class TechnologyStackProfiler:
    """Main profiler for analyzing technology stacks."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.detector = TechnologyDetector()

    async def profile_project(self, project_id: str) -> TechnologyStack:
        """Profile the technology stack of a project."""
        # Get project information
        project = await self._get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get all components for the project
        components = await self._get_project_components(project_id)
        
        # Extract file paths
        file_paths = [comp.path for comp in components]
        
        # Detect technologies
        detected_tech = await self.detector.detect_from_files(file_paths)
        
        # Filter and merge detections
        detected_tech = self.detector.filter_low_confidence(detected_tech, threshold=0.3)
        detected_tech = self.detector.merge_duplicate_detections(detected_tech)
        
        # Create technology stack
        stack = TechnologyStack(
            project_id=str(project.id),
            project_name=project.name,
            detection_timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Categorize technologies
        self._categorize_technologies(stack, detected_tech)
        
        # Detect versions
        await self._detect_versions(stack, file_paths)
        
        # Analyze stack characteristics
        self._analyze_stack_characteristics(stack)
        
        # Calculate scores
        stack.confidence_score = self.detector.calculate_confidence_score(detected_tech)
        stack.complexity_score = stack.calculate_stack_complexity()
        stack.modernization_score = stack.calculate_modernization_score()
        
        logger.info(f"Profiled technology stack for {project.name}: "
                   f"{len(stack.get_all_technologies())} technologies detected")
        
        return stack

    async def _get_project(self, project_id: str) -> Optional[Project]:
        """Get project by ID."""
        from sqlalchemy import select
        
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project_components(self, project_id: str) -> List[Component]:
        """Get all components for a project."""
        from sqlalchemy import select
        
        stmt = select(Component).where(Component.project_id == project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _categorize_technologies(self, stack: TechnologyStack, detected_tech: Dict[str, Technology]) -> None:
        """Categorize detected technologies into appropriate lists."""
        for tech_name, tech in detected_tech.items():
            if isinstance(tech, Framework):
                stack.frameworks.append(tech)
            elif isinstance(tech, Database):
                stack.databases.append(tech)
            elif isinstance(tech, BuildTool):
                stack.build_tools.append(tech)
            elif tech.category == TechnologyCategory.LANGUAGE:
                stack.languages.append(tech)
            elif tech.category == TechnologyCategory.TESTING:
                stack.testing_tools.append(tech)
            elif tech.category == TechnologyCategory.DEPLOYMENT:
                stack.deployment_tools.append(tech)
            elif tech.category == TechnologyCategory.MONITORING:
                stack.monitoring_tools.append(tech)
            elif tech.category == TechnologyCategory.SECURITY:
                stack.security_tools.append(tech)
            elif tech.category == TechnologyCategory.COMMUNICATION:
                stack.communication_tools.append(tech)
            elif tech.category == TechnologyCategory.STORAGE:
                stack.storage_tools.append(tech)
            elif tech.category == TechnologyCategory.CACHING:
                stack.caching_tools.append(tech)
            elif tech.category == TechnologyCategory.SEARCH:
                stack.search_tools.append(tech)
            elif tech.category == TechnologyCategory.QUEUE:
                stack.queue_tools.append(tech)
            elif tech.category == TechnologyCategory.CONTAINER:
                stack.container_tools.append(tech)
            elif tech.category == TechnologyCategory.ORCHESTRATION:
                stack.orchestration_tools.append(tech)
            else:
                # Default to languages if uncategorized
                stack.languages.append(tech)

    async def _detect_versions(self, stack: TechnologyStack, file_paths: List[str]) -> None:
        """Detect versions for technologies."""
        all_tech = stack.get_all_technologies()
        
        for tech in all_tech:
            version = await self.detector.detect_version(tech.name.lower(), file_paths)
            if version:
                tech.version = version

    def _analyze_stack_characteristics(self, stack: TechnologyStack) -> None:
        """Analyze stack characteristics and patterns."""
        # Determine stack type
        stack.stack_type = self._determine_stack_type(stack)
        
        # Determine architecture pattern
        stack.architecture_pattern = self._determine_architecture_pattern(stack)
        
        # Determine deployment pattern
        stack.deployment_pattern = self._determine_deployment_pattern(stack)
        
        # Mark primary technologies
        self._mark_primary_technologies(stack)

    def _determine_stack_type(self, stack: TechnologyStack) -> str:
        """Determine the type of stack."""
        has_frontend = any(fw.frontend_framework for fw in stack.frameworks)
        has_backend = any(fw.backend_framework for fw in stack.frameworks)
        has_database = len(stack.databases) > 0
        
        if has_frontend and has_backend and has_database:
            return "full_stack"
        elif has_backend and has_database:
            return "backend_only"
        elif has_frontend:
            return "frontend_only"
        elif len(stack.languages) > 0:
            return "library_or_tool"
        else:
            return "unknown"

    def _determine_architecture_pattern(self, stack: TechnologyStack) -> Optional[str]:
        """Determine the architecture pattern."""
        if stack.is_microservices():
            return "microservices"
        elif stack.is_serverless():
            return "serverless"
        elif stack.is_monolithic():
            return "monolithic"
        elif len(stack.frameworks) > 0:
            return "framework_based"
        else:
            return None

    def _determine_deployment_pattern(self, stack: TechnologyStack) -> Optional[str]:
        """Determine the deployment pattern."""
        if stack.orchestration_tools:
            return "container_orchestration"
        elif stack.container_tools:
            return "containerized"
        elif any("serverless" in tool.name.lower() for tool in stack.deployment_tools):
            return "serverless"
        elif any("heroku" in tool.name.lower() or "vercel" in tool.name.lower() for tool in stack.deployment_tools):
            return "paas"
        else:
            return "traditional"

    def _mark_primary_technologies(self, stack: TechnologyStack) -> None:
        """Mark primary technologies in the stack."""
        # Primary language is the one with most usage
        if stack.languages:
            primary_lang = max(stack.languages, key=lambda lang: lang.usage_count)
            primary_lang.is_main_tech = True
        
        # Primary framework is the one with most usage
        if stack.frameworks:
            primary_fw = max(stack.frameworks, key=lambda fw: fw.usage_count)
            primary_fw.is_main_tech = True
        
        # Primary database
        if stack.databases:
            # Check for explicitly marked primary
            primary_dbs = [db for db in stack.databases if db.is_primary]
            if primary_dbs:
                primary_dbs[0].is_main_tech = True
            else:
                # Mark the most used as primary
                primary_db = max(stack.databases, key=lambda db: db.usage_count)
                primary_db.is_primary = True
                primary_db.is_main_tech = True

    async def compare_stacks(self, stack1_id: str, stack2_id: str) -> Dict[str, Any]:
        """Compare two technology stacks."""
        stack1 = await self.profile_project(stack1_id)
        stack2 = await self.profile_project(stack2_id)
        
        # Get technology sets
        tech1_set = {tech.name.lower(): tech for tech in stack1.get_all_technologies()}
        tech2_set = {tech.name.lower(): tech for tech in stack2.get_all_technologies()}
        
        # Calculate similarities and differences
        common_tech = set(tech1_set.keys()) & set(tech2_set.keys())
        unique_to_1 = set(tech1_set.keys()) - set(tech2_set.keys())
        unique_to_2 = set(tech2_set.keys()) - set(tech1_set.keys())
        
        # Calculate similarity score
        total_unique = len(tech1_set) + len(tech2_set) - len(common_tech)
        similarity_score = len(common_tech) / total_unique if total_unique > 0 else 0
        
        return {
            "similarity_score": similarity_score,
            "common_technologies": list(common_tech),
            "unique_to_stack1": list(unique_to_1),
            "unique_to_stack2": list(unique_to_2),
            "stack1_summary": stack1.get_stack_summary(),
            "stack2_summary": stack2.get_stack_summary(),
            "comparison": {
                "complexity_diff": stack1.complexity_score - stack2.complexity_score,
                "modernization_diff": stack1.modernization_score - stack2.modernization_score,
                "architecture_match": stack1.architecture_pattern == stack2.architecture_pattern,
                "stack_type_match": stack1.stack_type == stack2.stack_type
            }
        }

    async def get_stack_recommendations(self, project_id: str) -> List[Dict[str, Any]]:
        """Get recommendations for improving the technology stack."""
        stack = await self.profile_project(project_id)
        recommendations = []
        
        # Security recommendations
        if not stack.security_tools:
            recommendations.append({
                "type": "security",
                "priority": "high",
                "title": "Add Security Tools",
                "description": "Consider adding security scanning tools like Snyk, OWASP ZAP, or CodeQL",
                "suggested_tools": ["Snyk", "OWASP ZAP", "CodeQL", "Bandit", "ESLint Security"]
            })
        
        # Monitoring recommendations
        if not stack.monitoring_tools:
            recommendations.append({
                "type": "monitoring",
                "priority": "medium",
                "title": "Add Monitoring",
                "description": "Consider adding monitoring and observability tools",
                "suggested_tools": ["Prometheus", "Grafana", "ELK Stack", "Datadog", "New Relic"]
            })
        
        # Testing recommendations
        if not stack.testing_tools:
            recommendations.append({
                "type": "testing",
                "priority": "high",
                "title": "Add Testing Framework",
                "description": "Consider adding testing frameworks and tools",
                "suggested_tools": self._suggest_testing_tools(stack)
            })
        
        # Modernization recommendations
        if stack.modernization_score < 50:
            recommendations.append({
                "type": "modernization",
                "priority": "medium",
                "title": "Modernize Technology Stack",
                "description": "Consider upgrading to more modern technologies",
                "suggested_tools": self._suggest_modernization(stack)
            })
        
        # Container recommendations
        if not stack.container_tools and not stack.is_serverless():
            recommendations.append({
                "type": "containerization",
                "priority": "low",
                "title": "Consider Containerization",
                "description": "Consider containerizing your application for better deployment",
                "suggested_tools": ["Docker", "Docker Compose", "Kubernetes"]
            })
        
        # Complexity recommendations
        if stack.complexity_score > 7:
            recommendations.append({
                "type": "complexity",
                "priority": "medium",
                "title": "Reduce Stack Complexity",
                "description": "Your technology stack is quite complex. Consider simplifying",
                "suggestions": [
                    "Consolidate similar tools",
                    "Remove unused dependencies",
                    "Consider microservices if monolithic",
                    "Standardize on fewer technologies"
                ]
            })
        
        return recommendations

    def _suggest_testing_tools(self, stack: TechnologyStack) -> List[str]:
        """Suggest testing tools based on the stack."""
        suggestions = []
        
        primary_lang = stack.get_primary_language()
        if primary_lang:
            lang_name = primary_lang.name.lower()
            
            if lang_name == "python":
                suggestions.extend(["pytest", "unittest", "pytest-cov", "mock"])
            elif lang_name == "javascript":
                suggestions.extend(["Jest", "Mocha", "Chai", "Cypress"])
            elif lang_name == "typescript":
                suggestions.extend(["Jest", "Mocha", "Chai", "Cypress", "ts-jest"])
            elif lang_name == "java":
                suggestions.extend(["JUnit", "Mockito", "TestNG", "Selenium"])
            elif lang_name == "go":
                suggestions.extend(["Go testing", "Testify", "Ginkgo"])
            elif lang_name == "rust":
                suggestions.extend(["Rust testing", "criterion", "mockall"])
        
        # Add framework-specific testing tools
        for fw in stack.frameworks:
            fw_name = fw.name.lower()
            if "react" in fw_name:
                suggestions.extend(["React Testing Library", "Jest", "Enzyme"])
            elif "vue" in fw_name:
                suggestions.extend(["Vue Test Utils", "Jest", "Cypress"])
            elif "angular" in fw_name:
                suggestions.extend(["Jasmine", "Karma", "Protractor"])
            elif "django" in fw_name:
                suggestions.extend(["Django Test Framework", "pytest-django"])
            elif "fastapi" in fw_name:
                suggestions.extend(["pytest", "httpx", "TestClient"])
        
        return list(set(suggestions))

    def _suggest_modernization(self, stack: TechnologyStack) -> List[str]:
        """Suggest modernization improvements."""
        suggestions = []
        
        # Check for legacy languages
        for lang in stack.languages:
            if lang.name.lower() in ["php", "perl", "cobol"]:
                if lang.name.lower() == "php":
                    suggestions.append("Consider upgrading to PHP 8+ or migrating to a modern framework")
                elif lang.name.lower() == "perl":
                    suggestions.append("Consider migrating to Python, Go, or Rust")
                elif lang.name.lower() == "cobol":
                    suggestions.append("Consider modernizing with COBOL modernization tools or migration")
        
        # Check for legacy frameworks
        for fw in stack.frameworks:
            fw_name = fw.name.lower()
            if "jquery" in fw_name:
                suggestions.append("Consider migrating from jQuery to modern frameworks like React or Vue")
            elif "backbone" in fw_name:
                suggestions.append("Consider migrating from Backbone.js to modern frameworks")
        
        # Suggest modern alternatives
        if not stack.container_tools:
            suggestions.append("Adopt containerization with Docker")
        
        if not stack.monitoring_tools:
            suggestions.append("Add modern monitoring with Prometheus/Grafana")
        
        if stack.modernization_score < 30:
            suggestions.append("Consider a complete technology stack overhaul")
        
        return suggestions

    async def get_stack_evolution(self, project_id: str) -> Dict[str, Any]:
        """Analyze the evolution of the technology stack over time."""
        # This would require historical data - for now, return current state
        stack = await self.profile_project(project_id)
        
        return {
            "current_state": stack.get_stack_summary(),
            "evolution_trend": "stable",  # Would be calculated from historical data
            "recent_changes": [],  # Would be calculated from version control
            "recommendations": await self.get_stack_recommendations(project_id)
        }

    async def export_stack(self, project_id: str, format: str = "json") -> Dict[str, Any]:
        """Export technology stack in specified format."""
        stack = await self.profile_project(project_id)
        
        if format.lower() == "json":
            return {
                "project": {
                    "id": stack.project_id,
                    "name": stack.project_name
                },
                "stack": stack.get_stack_summary(),
                "technologies": {
                    "languages": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.languages],
                    "frameworks": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.frameworks],
                    "databases": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.databases],
                    "build_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.build_tools],
                    "testing_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.testing_tools],
                    "deployment_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.deployment_tools],
                    "monitoring_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.monitoring_tools],
                    "security_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.security_tools]
                },
                "analysis": {
                    "confidence_score": stack.confidence_score,
                    "complexity_score": stack.complexity_score,
                    "modernization_score": stack.modernization_score,
                    "architecture_type": stack.architecture_pattern,
                    "deployment_pattern": stack.deployment_pattern
                },
                "metadata": {
                    "detection_timestamp": stack.detection_timestamp,
                    "analyzer_version": stack.analyzer_version
                }
            }
        else:
            raise ValueError(f"Unsupported export format: {format}")
