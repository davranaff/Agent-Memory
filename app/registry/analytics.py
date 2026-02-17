"""Component analytics and insights for the registry."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, Counter

from .metadata import ComponentMetadata, ComponentType, AccessLevel

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of analytics metrics."""
    QUALITY = "quality"
    COMPLEXITY = "complexity"
    USAGE = "usage"
    COVERAGE = "coverage"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"


class TrendDirection(str, Enum):
    """Trend directions."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"
    UNKNOWN = "unknown"


@dataclass
class MetricValue:
    """A metric value with timestamp."""
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class MetricTrend:
    """Trend analysis for a metric."""
    current_value: float
    previous_value: float
    direction: TrendDirection
    change_percentage: float
    confidence: float
    period: str  # "daily", "weekly", "monthly"


@dataclass
class ComponentInsight:
    """An insight about a component."""
    component_id: str
    insight_type: str
    title: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    confidence: float
    suggestions: List[str]
    metrics: Dict[str, float]
    created_at: datetime = None


@dataclass
class ProjectInsight:
    """An insight about a project."""
    project_id: str
    insight_type: str
    title: str
    description: str
    severity: str
    confidence: float
    affected_components: List[str]
    suggestions: List[str]
    metrics: Dict[str, float]
    created_at: datetime = None


class ComponentAnalytics:
    """Analytics engine for component insights and metrics."""
    
    def __init__(self, registry) -> None:
        self.registry = registry
        self._metric_history: Dict[str, List[MetricValue]] = defaultdict(list)
        self._insight_cache: Dict[str, List[ComponentInsight]] = {}

    async def analyze_component(self, component_id: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of a component."""
        component = await self.registry.get_component(component_id)
        if not component:
            raise ValueError(f"Component {component_id} not found")
        
        analysis = {
            "component_id": component_id,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": self._calculate_component_metrics(component),
            "insights": await self._generate_component_insights(component),
            "comparisons": await self._generate_comparisons(component),
            "recommendations": self._generate_recommendations(component),
            "trends": self._calculate_trends(component_id)
        }
        
        return analysis

    async def analyze_project(self, project_id: str) -> Dict[str, Any]:
        """Perform comprehensive analysis of a project."""
        components = await self.registry.get_components_by_project(project_id)
        
        if not components:
            raise ValueError(f"No components found for project {project_id}")
        
        analysis = {
            "project_id": project_id,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": self._calculate_project_summary(components),
            "metrics": self._calculate_project_metrics(components),
            "insights": await self._generate_project_insights(project_id, components),
            "trends": self._calculate_project_trends(project_id),
            "recommendations": self._generate_project_recommendations(components),
            "quality_distribution": self._calculate_quality_distribution(components),
            "complexity_distribution": self._calculate_complexity_distribution(components),
            "dependency_analysis": await self._analyze_dependencies(components)
        }
        
        return analysis

    def _calculate_component_metrics(self, component: ComponentMetadata) -> Dict[str, Any]:
        """Calculate comprehensive metrics for a component."""
        return {
            "quality_metrics": {
                "overall_score": component.calculate_quality_score(),
                "health_score": component.calculate_health_score(),
                "maintainability_score": component.maintainability_score,
                "documentation_score": component.documentation.documentation_score
            },
            "complexity_metrics": {
                "cyclomatic_complexity": component.code_metrics.cyclomatic_complexity,
                "cognitive_complexity": component.code_metrics.cognitive_complexity,
                "complexity_class": component.code_metrics.complexity_score,
                "lines_of_code": component.code_metrics.lines_of_code,
                "lines_of_comments": component.code_metrics.lines_of_comments,
                "comment_ratio": component.code_metrics.comment_ratio
            },
            "usage_metrics": {
                "dependencies_count": len(component.dependencies),
                "dependents_count": len(component.dependents),
                "fan_in": component.usage_metrics.fan_in,
                "fan_out": component.usage_metrics.fan_out,
                "instability": component.usage_metrics.instability,
                "stability_class": component.usage_metrics.stability_score
            },
            "testing_metrics": {
                "test_coverage": component.code_metrics.test_coverage,
                "has_tests": component.code_metrics.has_tests,
                "test_quality": "good" if component.code_metrics.test_coverage > 80 else "needs_improvement"
            },
            "security_metrics": {
                "security_score": component.security_metrics.security_score,
                "has_security_issues": component.security_metrics.has_security_issues,
                "handles_sensitive_data": component.security_metrics.handles_sensitive_data,
                "security_level": self._get_security_level(component.security_metrics.security_score)
            },
            "performance_metrics": {
                "performance_score": component.performance_metrics.performance_score,
                "time_complexity": component.performance_metrics.time_complexity,
                "space_complexity": component.performance_metrics.space_complexity,
                "is_cpu_intensive": component.performance_metrics.is_cpu_intensive,
                "is_memory_intensive": component.performance_metrics.is_memory_intensive
            }
        }

    async def _generate_component_insights(self, component: ComponentMetadata) -> List[ComponentInsight]:
        """Generate insights for a component."""
        insights = []
        
        # Quality insights
        quality_score = component.calculate_quality_score()
        if quality_score < 50:
            insights.append(ComponentInsight(
                component_id=component.component_id,
                insight_type="quality_issue",
                title="Low Quality Score",
                description=f"Component has a quality score of {quality_score:.1f}, which is below acceptable levels.",
                severity="high",
                confidence=0.9,
                suggestions=[
                    "Improve code documentation",
                    "Add unit tests to increase coverage",
                    "Reduce cyclomatic complexity",
                    "Address code smells"
                ],
                metrics={"quality_score": quality_score}
            ))
        
        # Complexity insights
        if component.code_metrics.cyclomatic_complexity > 15:
            insights.append(ComponentInsight(
                component_id=component.component_id,
                insight_type="complexity_issue",
                title="High Complexity",
                description=f"Component has cyclomatic complexity of {component.code_metrics.cyclomatic_complexity}, which is very high.",
                severity="medium",
                confidence=0.95,
                suggestions=[
                    "Break down into smaller functions",
                    "Extract common logic into helper methods",
                    "Reduce nesting levels",
                    "Use early returns to reduce complexity"
                ],
                metrics={"cyclomatic_complexity": component.code_metrics.cyclomatic_complexity}
            ))
        
        # Test coverage insights
        if component.code_metrics.test_coverage < 50 and component.type in [ComponentType.CLASS, ComponentType.FUNCTION]:
            insights.append(ComponentInsight(
                component_id=component.component_id,
                insight_type="testing_issue",
                title="Low Test Coverage",
                description=f"Component has only {component.code_metrics.test_coverage:.1f}% test coverage.",
                severity="medium",
                confidence=0.8,
                suggestions=[
                    "Add unit tests for all public methods",
                    "Add integration tests for complex scenarios",
                    "Consider test-driven development for new features",
                    "Add edge case testing"
                ],
                metrics={"test_coverage": component.code_metrics.test_coverage}
            ))
        
        # Dependency insights
        if len(component.dependencies) > 10:
            insights.append(ComponentInsight(
                component_id=component.component_id,
                insight_type="dependency_issue",
                title="High Dependency Count",
                description=f"Component depends on {len(component.dependencies)} other components, which may indicate tight coupling.",
                severity="medium",
                confidence=0.7,
                suggestions=[
                    "Consider dependency injection",
                    "Extract common dependencies into interfaces",
                    "Apply single responsibility principle",
                    "Review if all dependencies are necessary"
                ],
                metrics={"dependencies_count": len(component.dependencies)}
            ))
        
        # Security insights
        if component.security_metrics.has_security_issues:
            insights.append(ComponentInsight(
                component_id=component.component_id,
                insight_type="security_issue",
                title="Security Issues Detected",
                description="Component has potential security vulnerabilities that should be addressed.",
                severity="high",
                confidence=0.85,
                suggestions=[
                    "Review and fix security vulnerabilities",
                    "Add input validation",
                    "Implement proper authentication/authorization",
                    "Use secure coding practices"
                ],
                metrics={"security_issues": len(component.security_metrics.security_issues)}
            ))
        
        return insights

    async def _generate_comparisons(self, component: ComponentMetadata) -> Dict[str, Any]:
        """Generate comparisons with similar components."""
        similar_components = await self.registry.get_similar_components(component.component_id)
        
        comparisons = {
            "similar_components": [],
            "percentile_rankings": {},
            "benchmarks": {}
        }
        
        if not similar_components:
            return comparisons
        
        # Calculate percentile rankings
        all_components = [comp for comp, _ in similar_components]
        all_components.append(component)
        
        metrics = ["quality_score", "complexity", "test_coverage", "security_score"]
        
        for metric in metrics:
            values = []
            if metric == "quality_score":
                values = [comp.calculate_quality_score() for comp in all_components]
            elif metric == "complexity":
                values = [comp.code_metrics.cyclomatic_complexity for comp in all_components]
            elif metric == "test_coverage":
                values = [comp.code_metrics.test_coverage for comp in all_components]
            elif metric == "security_score":
                values = [comp.security_metrics.security_score for comp in all_components]
            
            if values:
                sorted_values = sorted(values)
                component_value = values[-1]  # Our component is last
                
                percentile = (sorted_values.index(component_value) + 1) / len(sorted_values) * 100
                comparisons["percentile_rankings"][metric] = percentile
        
        # Similar components details
        for similar_comp, similarity_score in similar_components[:5]:
            comparisons["similar_components"].append({
                "component_id": similar_comp.component_id,
                "name": similar_comp.name,
                "similarity_score": similarity_score,
                "quality_score": similar_comp.calculate_quality_score(),
                "complexity": similar_comp.code_metrics.cyclomatic_complexity
            })
        
        return comparisons

    def _generate_recommendations(self, component: ComponentMetadata) -> List[Dict[str, Any]]:
        """Generate recommendations for improving the component."""
        recommendations = []
        
        quality_score = component.calculate_quality_score()
        
        # Quality recommendations
        if quality_score < 60:
            recommendations.append({
                "type": "quality",
                "priority": "high",
                "title": "Improve Code Quality",
                "description": "Focus on improving overall code quality through better practices.",
                "actions": [
                    "Add comprehensive documentation",
                    "Increase test coverage",
                    "Refactor complex methods",
                    "Address code smells"
                ],
                "expected_impact": "+20-30 quality score"
            })
        
        # Documentation recommendations
        if component.documentation.level.value in ["none", "basic"]:
            recommendations.append({
                "type": "documentation",
                "priority": "medium",
                "title": "Improve Documentation",
                "description": "Add better documentation to improve maintainability.",
                "actions": [
                    "Add docstrings to all public methods",
                    "Include usage examples",
                    "Document parameters and return values",
                    "Add inline comments for complex logic"
                ],
                "expected_impact": "+10-15 quality score"
            })
        
        # Testing recommendations
        if component.code_metrics.test_coverage < 70:
            recommendations.append({
                "type": "testing",
                "priority": "high",
                "title": "Increase Test Coverage",
                "description": "Improve test coverage to ensure code reliability.",
                "actions": [
                    "Write unit tests for all public methods",
                    "Add integration tests for workflows",
                    "Include edge case scenarios",
                    "Set up continuous testing"
                ],
                "expected_impact": "+15-25 quality score"
            })
        
        # Performance recommendations
        if component.performance_metrics.is_cpu_intensive or component.performance_metrics.is_memory_intensive:
            recommendations.append({
                "type": "performance",
                "priority": "medium",
                "title": "Optimize Performance",
                "description": "Component shows performance bottlenecks that should be addressed.",
                "actions": [
                    "Profile performance bottlenecks",
                    "Optimize algorithms and data structures",
                    "Consider caching for expensive operations",
                    "Review memory usage patterns"
                ],
                "expected_impact": "Improved performance and user experience"
            })
        
        return recommendations

    def _calculate_trends(self, component_id: str) -> Dict[str, MetricTrend]:
        """Calculate trends for component metrics."""
        trends = {}
        
        if component_id not in self._metric_history:
            return trends
        
        history = self._metric_history[component_id]
        if len(history) < 2:
            return trends
        
        # Calculate trends for different metrics
        metric_types = ["quality", "complexity", "coverage"]
        
        for metric_type in metric_types:
            metric_history = [m for m in history if metric_type in m.metadata]
            
            if len(metric_history) >= 2:
                current = metric_history[-1]
                previous = metric_history[-2]
                
                change_percentage = ((current.value - previous.value) / previous.value) * 100 if previous.value != 0 else 0
                
                if change_percentage > 5:
                    direction = TrendDirection.IMPROVING
                elif change_percentage < -5:
                    direction = TrendDirection.DECLINING
                else:
                    direction = TrendDirection.STABLE
                
                trends[metric_type] = MetricTrend(
                    current_value=current.value,
                    previous_value=previous.value,
                    direction=direction,
                    change_percentage=change_percentage,
                    confidence=0.8,
                    period="weekly"
                )
        
        return trends

    def _calculate_project_summary(self, components: List[ComponentMetadata]) -> Dict[str, Any]:
        """Calculate project summary statistics."""
        if not components:
            return {}
        
        total_components = len(components)
        avg_quality = sum(comp.calculate_quality_score() for comp in components) / total_components
        avg_complexity = sum(comp.code_metrics.cyclomatic_complexity for comp in components) / total_components
        avg_coverage = sum(comp.code_metrics.test_coverage for comp in components) / total_components
        
        # Component type distribution
        type_counts = Counter(comp.type for comp in components)
        
        # Language distribution
        language_counts = Counter(comp.language for comp in components)
        
        return {
            "total_components": total_components,
            "average_quality_score": avg_quality,
            "average_complexity": avg_complexity,
            "average_test_coverage": avg_coverage,
            "component_types": dict(type_counts),
            "languages": dict(language_counts),
            "health_distribution": self._calculate_health_distribution(components)
        }

    def _calculate_project_metrics(self, components: List[ComponentMetadata]) -> Dict[str, Any]:
        """Calculate comprehensive project metrics."""
        return {
            "quality_metrics": {
                "average_score": sum(comp.calculate_quality_score() for comp in components) / len(components),
                "score_distribution": self._calculate_score_distribution(components),
                "high_quality_components": len([c for c in components if c.calculate_quality_score() > 80]),
                "low_quality_components": len([c for c in components if c.calculate_quality_score() < 50])
            },
            "complexity_metrics": {
                "average_complexity": sum(comp.code_metrics.cyclomatic_complexity for comp in components) / len(components),
                "complex_components": len([c for c in components if c.code_metrics.cyclomatic_complexity > 15]),
                "simple_components": len([c for c in components if c.code_metrics.cyclomatic_complexity <= 5])
            },
            "testing_metrics": {
                "average_coverage": sum(comp.code_metrics.test_coverage for comp in components) / len(components),
                "well_tested_components": len([c for c in components if c.code_metrics.test_coverage > 80]),
                "untested_components": len([c for c in components if c.code_metrics.test_coverage < 20])
            },
            "dependency_metrics": {
                "average_dependencies": sum(len(comp.dependencies) for comp in components) / len(components),
                "highly_coupled_components": len([c for c in components if len(c.dependencies) > 10]),
                "isolated_components": len([c for c in components if len(c.dependencies) == 0])
            }
        }

    async def _generate_project_insights(self, project_id: str, components: List[ComponentMetadata]) -> List[ProjectInsight]:
        """Generate project-level insights."""
        insights = []
        
        # Quality insights
        avg_quality = sum(comp.calculate_quality_score() for comp in components) / len(components)
        if avg_quality < 60:
            low_quality_components = [c for c in components if c.calculate_quality_score() < 50]
            
            insights.append(ProjectInsight(
                project_id=project_id,
                insight_type="quality_issue",
                title="Low Overall Quality",
                description=f"Project has an average quality score of {avg_quality:.1f}, which needs improvement.",
                severity="high",
                confidence=0.9,
                affected_components=[c.component_id for c in low_quality_components],
                suggestions=[
                    "Establish code quality standards",
                    "Implement code review process",
                    "Add automated quality gates",
                    "Invest in refactoring efforts"
                ],
                metrics={"average_quality": avg_quality, "low_quality_count": len(low_quality_components)}
            ))
        
        # Testing insights
        avg_coverage = sum(comp.code_metrics.test_coverage for comp in components) / len(components)
        if avg_coverage < 50:
            insights.append(ProjectInsight(
                project_id=project_id,
                insight_type="testing_issue",
                title="Insufficient Test Coverage",
                description=f"Project has only {avg_coverage:.1f}% average test coverage.",
                severity="medium",
                confidence=0.85,
                affected_components=[c.component_id for c in components if c.code_metrics.test_coverage < 50],
                suggestions=[
                    "Set minimum coverage requirements",
                    "Invest in test automation",
                    "Allocate time for test writing",
                    "Consider test-driven development"
                ],
                metrics={"average_coverage": avg_coverage}
            ))
        
        # Complexity insights
        complex_components = [c for c in components if c.code_metrics.cyclomatic_complexity > 15]
        if len(complex_components) > len(components) * 0.2:  # More than 20% are complex
            insights.append(ProjectInsight(
                project_id=project_id,
                insight_type="complexity_issue",
                title="High Complexity Concentration",
                description=f"{len(complex_components)} components ({len(complex_components)/len(components)*100:.1f}%) have high complexity.",
                severity="medium",
                confidence=0.8,
                affected_components=[c.component_id for c in complex_components],
                suggestions=[
                    "Refactor complex components",
                    "Establish complexity limits",
                    "Provide training on clean code practices",
                    "Use complexity analysis tools"
                ],
                metrics={"complex_components_count": len(complex_components)}
            ))
        
        return insights

    def _calculate_project_trends(self, project_id: str) -> Dict[str, Any]:
        """Calculate project-level trends."""
        # This would typically use historical data
        # For now, return placeholder
        return {
            "quality_trend": TrendDirection.STABLE,
            "complexity_trend": TrendDirection.STABLE,
            "coverage_trend": TrendDirection.IMPROVING
        }

    def _generate_project_recommendations(self, components: List[ComponentMetadata]) -> List[Dict[str, Any]]:
        """Generate project-level recommendations."""
        recommendations = []
        
        # Overall quality improvement
        avg_quality = sum(comp.calculate_quality_score() for comp in components) / len(components)
        if avg_quality < 70:
            recommendations.append({
                "type": "quality",
                "priority": "high",
                "title": "Improve Project Quality",
                "description": "Focus on improving overall code quality across the project.",
                "actions": [
                    "Implement code quality standards",
                    "Set up automated code analysis",
                    "Establish regular refactoring sessions",
                    "Invest in developer training"
                ],
                "expected_impact": "Significant improvement in maintainability"
            })
        
        # Testing strategy
        avg_coverage = sum(comp.code_metrics.test_coverage for comp in components) / len(components)
        if avg_coverage < 60:
            recommendations.append({
                "type": "testing",
                "priority": "high",
                "title": "Improve Test Coverage",
                "description": "Develop a comprehensive testing strategy for the project.",
                "actions": [
                    "Define testing standards and practices",
                    "Invest in test infrastructure",
                    "Allocate dedicated testing time",
                    "Implement continuous integration testing"
                ],
                "expected_impact": "Better reliability and maintainability"
            })
        
        return recommendations

    def _calculate_quality_distribution(self, components: List[ComponentMetadata]) -> Dict[str, int]:
        """Calculate distribution of quality scores."""
        distribution = {
            "excellent": 0,  # 90-100
            "good": 0,       # 70-89
            "fair": 0,       # 50-69
            "poor": 0        # 0-49
        }
        
        for component in components:
            score = component.calculate_quality_score()
            if score >= 90:
                distribution["excellent"] += 1
            elif score >= 70:
                distribution["good"] += 1
            elif score >= 50:
                distribution["fair"] += 1
            else:
                distribution["poor"] += 1
        
        return distribution

    def _calculate_complexity_distribution(self, components: List[ComponentMetadata]) -> Dict[str, int]:
        """Calculate distribution of complexity scores."""
        distribution = {
            "simple": 0,    # 1-5
            "moderate": 0,  # 6-10
            "complex": 0,   # 11-20
            "very_complex": 0  # 21+
        }
        
        for component in components:
            complexity = component.code_metrics.cyclomatic_complexity
            if complexity <= 5:
                distribution["simple"] += 1
            elif complexity <= 10:
                distribution["moderate"] += 1
            elif complexity <= 20:
                distribution["complex"] += 1
            else:
                distribution["very_complex"] += 1
        
        return distribution

    async def _analyze_dependencies(self, components: List[ComponentMetadata]) -> Dict[str, Any]:
        """Analyze dependency patterns."""
        dependency_graph = defaultdict(set)
        
        for component in components:
            for dep in component.dependencies:
                dependency_graph[component.component_id].add(dep)
        
        # Find strongly connected components (cycles)
        cycles = self._find_cycles(dependency_graph)
        
        # Calculate coupling metrics
        coupling_metrics = self._calculate_coupling_metrics(components, dependency_graph)
        
        return {
            "total_dependencies": sum(len(comp.dependencies) for comp in components),
            "average_dependencies": sum(len(comp.dependencies) for comp in components) / len(components),
            "cycles_detected": len(cycles),
            "cycle_details": cycles[:5],  # Limit to first 5 cycles
            "coupling_metrics": coupling_metrics
        }

    def _find_cycles(self, graph: Dict[str, Set[str]]) -> List[List[str]]:
        """Find cycles in dependency graph using DFS."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node_id: str) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)
            
            for neighbor in graph.get(node_id, set()):
                if neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                elif neighbor not in visited:
                    dfs(neighbor)
            
            rec_stack.remove(node_id)
            path.pop()
        
        for node_id in graph:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles

    def _calculate_coupling_metrics(self, components: List[ComponentMetadata], graph: Dict[str, Set[str]]) -> Dict[str, Any]:
        """Calculate coupling metrics."""
        # Calculate afferent and efferent coupling
        afferent = defaultdict(int)  # Number of components that depend on this
        efferent = defaultdict(int)  # Number of components this depends on
        
        for component in components:
            efferent[component.component_id] = len(component.dependencies)
            for dep in component.dependencies:
                afferent[dep] += 1
        
        # Calculate instability
        instability_scores = {}
        for component in components:
            ca = afferent[component.component_id]
            ce = efferent[component.component_id]
            instability = ce / (ca + ce) if (ca + ce) > 0 else 0
            instability_scores[component.component_id] = instability
        
        avg_instability = sum(instability_scores.values()) / len(instability_scores) if instability_scores else 0
        
        return {
            "average_instability": avg_instability,
            "stable_components": len([s for s in instability_scores.values() if s < 0.3]),
            "unstable_components": len([s for s in instability_scores.values() if s > 0.7]),
            "instability_distribution": {
                "very_stable": len([s for s in instability_scores.values() if s < 0.2]),
                "stable": len([s for s in instability_scores.values() if 0.2 <= s < 0.5]),
                "unstable": len([s for s in instability_scores.values() if 0.5 <= s < 0.8]),
                "very_unstable": len([s for s in instability_scores.values() if s >= 0.8])
            }
        }

    def _get_security_level(self, score: float) -> str:
        """Get security level based on score."""
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        elif score >= 50:
            return "fair"
        else:
            return "poor"

    def _calculate_score_distribution(self, components: List[ComponentMetadata]) -> Dict[str, int]:
        """Calculate distribution of quality scores."""
        distribution = {
            "90-100": 0,
            "80-89": 0,
            "70-79": 0,
            "60-69": 0,
            "50-59": 0,
            "0-49": 0
        }
        
        for component in components:
            score = component.calculate_quality_score()
            if score >= 90:
                distribution["90-100"] += 1
            elif score >= 80:
                distribution["80-89"] += 1
            elif score >= 70:
                distribution["70-79"] += 1
            elif score >= 60:
                distribution["60-69"] += 1
            elif score >= 50:
                distribution["50-59"] += 1
            else:
                distribution["0-49"] += 1
        
        return distribution

    def _calculate_health_distribution(self, components: List[ComponentMetadata]) -> Dict[str, int]:
        """Calculate distribution of health scores."""
        distribution = {
            "healthy": 0,    # 80-100
            "at_risk": 0,    # 60-79
            "unhealthy": 0,  # 40-59
            "critical": 0    # 0-39
        }
        
        for component in components:
            health = component.calculate_health_score()
            if health >= 80:
                distribution["healthy"] += 1
            elif health >= 60:
                distribution["at_risk"] += 1
            elif health >= 40:
                distribution["unhealthy"] += 1
            else:
                distribution["critical"] += 1
        
        return distribution

    async def record_metric(self, component_id: str, metric_type: str, value: float, metadata: Dict[str, Any] = None) -> None:
        """Record a metric value for trend analysis."""
        metric_value = MetricValue(
            value=value,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {"type": metric_type}
        )
        
        self._metric_history[component_id].append(metric_value)
        
        # Keep only last 100 values per component
        if len(self._metric_history[component_id]) > 100:
            self._metric_history[component_id] = self._metric_history[component_id][-100:]
