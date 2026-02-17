"""Dependency graph analyzer for extracting insights."""

from __future__ import annotations

import logging
from typing import Dict, List, Set, Optional, Tuple, Any
from collections import defaultdict, Counter
from dataclasses import dataclass

from .graph import DependencyGraph, DependencyNode, DependencyEdge, DependencyType

logger = logging.getLogger(__name__)


@dataclass
class ArchitectureInsight:
    """Insight about project architecture."""
    type: str
    description: str
    confidence: float
    components: List[str]
    recommendations: List[str]


@dataclass
class DependencyIssue:
    """Issue found in dependency graph."""
    type: str
    severity: str  # low, medium, high, critical
    description: str
    components: List[str]
    suggestion: str


class DependencyAnalyzer:
    """Analyzes dependency graphs to extract insights and detect issues."""
    
    def __init__(self) -> None:
        self.architecture_patterns = self._init_architecture_patterns()
        self.issue_patterns = self._init_issue_patterns()

    def _init_architecture_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize architecture detection patterns."""
        return {
            "layered": {
                "description": "Layered architecture with clear separation of concerns",
                "indicators": ["layer", "tier", "level"],
                "structure": "hierarchical",
                "confidence_threshold": 0.7
            },
            "microservices": {
                "description": "Microservices architecture with independent services",
                "indicators": ["service", "api", "gateway", "microservice"],
                "structure": "distributed",
                "confidence_threshold": 0.6
            },
            "event_driven": {
                "description": "Event-driven architecture with loose coupling",
                "indicators": ["event", "message", "queue", "publisher", "subscriber"],
                "structure": "decoupled",
                "confidence_threshold": 0.6
            },
            "plugin": {
                "description": "Plugin architecture with extensible components",
                "indicators": ["plugin", "extension", "module", "addon"],
                "structure": "extensible",
                "confidence_threshold": 0.5
            },
            "monolith": {
                "description": "Monolithic architecture with tightly coupled components",
                "indicators": ["tight_coupling", "high_connectivity"],
                "structure": "centralized",
                "confidence_threshold": 0.8
            }
        }

    def _init_issue_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Initialize issue detection patterns."""
        return {
            "circular_dependency": {
                "severity": "high",
                "description": "Circular dependencies can cause maintenance issues",
                "suggestion": "Refactor to break the cycle using dependency inversion"
            },
            "high_coupling": {
                "severity": "medium",
                "description": "High coupling indicates tight dependencies between components",
                "suggestion": "Consider introducing interfaces or abstraction layers"
            },
            "god_object": {
                "severity": "high",
                "description": "Component with too many dependencies may be a god object",
                "suggestion": "Break down into smaller, more focused components"
            },
            "unstable_dependency": {
                "severity": "medium",
                "description": "Depending on unstable components can be risky",
                "suggestion": "Add abstraction layers or use dependency inversion"
            },
            "deep_hierarchy": {
                "severity": "low",
                "description": "Very deep dependency hierarchies can be hard to understand",
                "suggestion": "Consider flattening the hierarchy where possible"
            }
        }

    async def analyze_architecture(self, graph: DependencyGraph) -> List[ArchitectureInsight]:
        """Analyze the architecture pattern of the project."""
        insights = []
        
        # Detect architecture type
        arch_type = self._detect_architecture_type(graph)
        if arch_type:
            pattern = self.architecture_patterns[arch_type]
            
            # Find components that match the pattern
            matching_components = self._find_architecture_components(graph, arch_type)
            
            insight = ArchitectureInsight(
                type=arch_type,
                description=pattern["description"],
                confidence=self._calculate_architecture_confidence(graph, arch_type),
                components=matching_components,
                recommendations=self._get_architecture_recommendations(arch_type, graph)
            )
            insights.append(insight)
        
        # Detect layered structure
        layers = self._detect_layers(graph)
        if layers:
            insight = ArchitectureInsight(
                type="layered_structure",
                description=f"Detected {len(layers)} layers in the architecture",
                confidence=0.8,
                components=list(layers.keys()),
                recommendations=self._get_layer_recommendations(layers)
            )
            insights.append(insight)
        
        return insights

    def _detect_architecture_type(self, graph: DependencyGraph) -> Optional[str]:
        """Detect the primary architecture type."""
        scores = {}
        
        for arch_type, pattern in self.architecture_patterns.items():
            score = self._calculate_architecture_score(graph, arch_type)
            scores[arch_type] = score
        
        if not scores:
            return None
        
        # Return the type with highest score above threshold
        best_type = max(scores.items(), key=lambda x: x[1])
        threshold = self.architecture_patterns[best_type[0]]["confidence_threshold"]
        
        return best_type[0] if best_type[1] >= threshold else None

    def _calculate_architecture_score(self, graph: DependencyGraph, arch_type: str) -> float:
        """Calculate score for a specific architecture type."""
        if arch_type == "microservices":
            return self._score_microservices(graph)
        elif arch_type == "layered":
            return self._score_layered(graph)
        elif arch_type == "event_driven":
            return self._score_event_driven(graph)
        elif arch_type == "plugin":
            return self._score_plugin(graph)
        elif arch_type == "monolith":
            return self._score_monolith(graph)
        
        return 0.0

    def _score_microservices(self, graph: DependencyGraph) -> float:
        """Score for microservices architecture."""
        score = 0.0
        
        # Check for service-like components
        service_indicators = ["service", "api", "controller", "handler"]
        service_components = [
            node for node in graph.nodes.values()
            if any(indicator in node.name.lower() for indicator in service_indicators)
        ]
        
        if service_components:
            score += 0.3
        
        # Check for low coupling between services
        avg_dependencies = sum(node.dependency_count for node in graph.nodes.values()) / len(graph.nodes)
        if avg_dependencies < 3:
            score += 0.3
        
        # Check for independent components
        isolated_components = [node for node in graph.nodes.values() if node.dependency_count <= 2]
        if len(isolated_components) / len(graph.nodes) > 0.3:
            score += 0.2
        
        # Check for API-like naming
        api_components = [
            node for node in graph.nodes.values()
            if "api" in node.name.lower() or "endpoint" in node.name.lower()
        ]
        if len(api_components) > 0:
            score += 0.2
        
        return min(score, 1.0)

    def _score_layered(self, graph: DependencyGraph) -> float:
        """Score for layered architecture."""
        score = 0.0
        
        # Check for hierarchical structure
        layers = self._detect_layers(graph)
        if len(layers) >= 3:
            score += 0.4
        elif len(layers) >= 2:
            score += 0.2
        
        # Check for unidirectional dependencies
        cycles = graph.detect_cycles()
        if len(cycles) == 0:
            score += 0.3
        elif len(cycles) <= len(graph.nodes) * 0.1:  # Less than 10% of nodes in cycles
            score += 0.1
        
        # Check for clear abstraction levels
        abstraction_levels = self._detect_abstraction_levels(graph)
        if len(abstraction_levels) >= 3:
            score += 0.3
        
        return min(score, 1.0)

    def _score_event_driven(self, graph: DependencyGraph) -> float:
        """Score for event-driven architecture."""
        score = 0.0
        
        # Check for event-related components
        event_indicators = ["event", "message", "queue", "publisher", "subscriber", "listener"]
        event_components = [
            node for node in graph.nodes.values()
            if any(indicator in node.name.lower() for indicator in event_indicators)
        ]
        
        if len(event_components) > 0:
            score += 0.4
        
        # Check for loose coupling
        avg_dependencies = sum(node.dependency_count for node in graph.nodes.values()) / len(graph.nodes)
        if avg_dependencies < 2:
            score += 0.3
        
        # Check for mediator/broker patterns
        mediator_indicators = ["mediator", "broker", "dispatcher", "router"]
        mediator_components = [
            node for node in graph.nodes.values()
            if any(indicator in node.name.lower() for indicator in mediator_indicators)
        ]
        
        if len(mediator_components) > 0:
            score += 0.3
        
        return min(score, 1.0)

    def _score_plugin(self, graph: DependencyGraph) -> float:
        """Score for plugin architecture."""
        score = 0.0
        
        # Check for plugin-related components
        plugin_indicators = ["plugin", "extension", "module", "addon", "component"]
        plugin_components = [
            node for node in graph.nodes.values()
            if any(indicator in node.name.lower() for indicator in plugin_indicators)
        ]
        
        if len(plugin_components) > 0:
            score += 0.4
        
        # Check for extensible interfaces
        interface_components = [
            node for node in graph.nodes.values()
            if node.type.value == "interface"
        ]
        
        if len(interface_components) > 0:
            score += 0.3
        
        # Check for registry/factory patterns
        registry_indicators = ["registry", "factory", "loader", "manager"]
        registry_components = [
            node for node in graph.nodes.values()
            if any(indicator in node.name.lower() for indicator in registry_indicators)
        ]
        
        if len(registry_components) > 0:
            score += 0.3
        
        return min(score, 1.0)

    def _score_monolith(self, graph: DependencyGraph) -> float:
        """Score for monolithic architecture."""
        score = 0.0
        
        # Check for high coupling
        avg_dependencies = sum(node.dependency_count for node in graph.nodes.values()) / len(graph.nodes)
        if avg_dependencies > 5:
            score += 0.3
        
        # Check for many cycles
        cycles = graph.detect_cycles()
        if len(cycles) > len(graph.nodes) * 0.2:  # More than 20% of nodes in cycles
            score += 0.3
        
        # Check for central components
        central_components = [
            node for node in graph.nodes.values()
            if node.dependent_count > 5
        ]
        
        if len(central_components) > 0:
            score += 0.2
        
        # Check for deep hierarchies
        max_depth = self._calculate_max_depth(graph)
        if max_depth > 5:
            score += 0.2
        
        return min(score, 1.0)

    def _detect_layers(self, graph: DependencyGraph) -> Dict[str, List[str]]:
        """Detect layers in the architecture."""
        layers = defaultdict(list)
        
        # Use topological sorting to assign layers
        visited = set()
        in_degree = {node_id: 0 for node_id in graph.nodes}
        
        # Calculate in-degrees
        for edge in graph.edges.values():
            in_degree[edge.target_id] += 1
        
        # Topological sort with layer assignment
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        current_layer = 0
        
        while queue:
            next_queue = []
            
            for node_id in queue:
                if node_id not in visited:
                    visited.add(node_id)
                    layer_name = f"layer_{current_layer}"
                    layers[layer_name].append(node_id)
                    
                    # Add dependents to next queue
                    for dependent_id in graph._adjacency_list.get(node_id, set()):
                        in_degree[dependent_id] -= 1
                        if in_degree[dependent_id] == 0:
                            next_queue.append(dependent_id)
            
            queue = next_queue
            current_layer += 1
        
        return dict(layers)

    def _detect_abstraction_levels(self, graph: DependencyGraph) -> List[str]:
        """Detect different abstraction levels."""
        levels = set()
        
        for node in graph.nodes.values():
            # Determine abstraction level based on naming and type
            if node.type.value in ["interface", "abstract"]:
                levels.add("abstract")
            elif "base" in node.name.lower() or "abstract" in node.name.lower():
                levels.add("abstract")
            elif node.type.value in ["class", "struct"]:
                levels.add("implementation")
            elif "util" in node.name.lower() or "helper" in node.name.lower():
                levels.add("utility")
            else:
                levels.add("concrete")
        
        return list(levels)

    def _calculate_max_depth(self, graph: DependencyGraph) -> int:
        """Calculate maximum dependency depth."""
        max_depth = 0
        
        def dfs(node_id: str, depth: int, visited: Set[str]) -> None:
            nonlocal max_depth
            max_depth = max(max_depth, depth)
            
            if node_id in visited:
                return
            
            visited.add(node_id)
            for dependent_id in graph._adjacency_list.get(node_id, set()):
                dfs(dependent_id, depth + 1, visited.copy())
        
        for node_id in graph.nodes:
            dfs(node_id, 0, set())
        
        return max_depth

    def _find_architecture_components(self, graph: DependencyGraph, arch_type: str) -> List[str]:
        """Find components that match an architecture pattern."""
        pattern = self.architecture_patterns[arch_type]
        matching_components = []
        
        for node in graph.nodes.values():
            if any(indicator in node.name.lower() for indicator in pattern["indicators"]):
                matching_components.append(node.id)
        
        return matching_components

    def _calculate_architecture_confidence(self, graph: DependencyGraph, arch_type: str) -> float:
        """Calculate confidence in architecture detection."""
        return self._calculate_architecture_score(graph, arch_type)

    def _get_architecture_recommendations(self, arch_type: str, graph: DependencyGraph) -> List[str]:
        """Get recommendations for a specific architecture type."""
        recommendations = {
            "microservices": [
                "Consider implementing service discovery",
                "Add API gateway for external access",
                "Implement circuit breakers for resilience",
                "Consider containerization with Docker/Kubernetes"
            ],
            "layered": [
                "Ensure dependencies flow only upward",
                "Consider dependency inversion for better testability",
                "Add clear interfaces between layers",
                "Document layer responsibilities"
            ],
            "event_driven": [
                "Implement event schema validation",
                "Add event replay capabilities",
                "Consider event sourcing for critical events",
                "Monitor event flow and performance"
            ],
            "plugin": [
                "Define clear plugin interfaces",
                "Implement plugin lifecycle management",
                "Add plugin discovery mechanism",
                "Consider plugin isolation and security"
            ],
            "monolith": [
                "Consider modularization within the monolith",
                "Identify bounded contexts for future extraction",
                "Implement proper dependency management",
                "Consider strangler fig pattern for gradual migration"
            ]
        }
        
        return recommendations.get(arch_type, [])

    def _get_layer_recommendations(self, layers: Dict[str, List[str]]) -> List[str]:
        """Get recommendations for layered architecture."""
        return [
            f"Ensure {len(layers)} layers have clear responsibilities",
            "Verify dependencies flow only between adjacent layers",
            "Consider adding interfaces between layers",
            "Document layer contracts and boundaries"
        ]

    async def detect_issues(self, graph: DependencyGraph) -> List[DependencyIssue]:
        """Detect dependency issues in the graph."""
        issues = []
        
        # Detect circular dependencies
        cycles = graph.detect_cycles()
        for cycle in cycles:
            issue = DependencyIssue(
                type="circular_dependency",
                severity=self.issue_patterns["circular_dependency"]["severity"],
                description=f"Circular dependency detected: {' -> '.join(cycle)}",
                components=cycle,
                suggestion=self.issue_patterns["circular_dependency"]["suggestion"]
            )
            issues.append(issue)
        
        # Detect high coupling
        high_coupling_nodes = [
            node for node in graph.nodes.values()
            if node.dependency_count > 10
        ]
        
        for node in high_coupling_nodes:
            issue = DependencyIssue(
                type="high_coupling",
                severity=self.issue_patterns["high_coupling"]["severity"],
                description=f"Component {node.name} has high coupling ({node.dependency_count} dependencies)",
                components=[node.id],
                suggestion=self.issue_patterns["high_coupling"]["suggestion"]
            )
            issues.append(issue)
        
        # Detect god objects
        god_object_nodes = [
            node for node in graph.nodes.values()
            if node.dependent_count > 15 and node.dependency_count > 5
        ]
        
        for node in god_object_nodes:
            issue = DependencyIssue(
                type="god_object",
                severity=self.issue_patterns["god_object"]["severity"],
                description=f"Component {node.name} appears to be a god object ({node.dependent_count} dependents, {node.dependency_count} dependencies)",
                components=[node.id],
                suggestion=self.issue_patterns["god_object"]["suggestion"]
            )
            issues.append(issue)
        
        # Detect deep hierarchies
        max_depth = self._calculate_max_depth(graph)
        if max_depth > 7:
            issue = DependencyIssue(
                type="deep_hierarchy",
                severity=self.issue_patterns["deep_hierarchy"]["severity"],
                description=f"Deep dependency hierarchy detected (max depth: {max_depth})",
                components=[],
                suggestion=self.issue_patterns["deep_hierarchy"]["suggestion"]
            )
            issues.append(issue)
        
        return issues

    async def calculate_metrics(self, graph: DependencyGraph) -> Dict[str, Any]:
        """Calculate comprehensive dependency metrics."""
        stats = graph.get_statistics()
        
        # Additional metrics
        metrics = {
            **stats,
            
            # Coupling metrics
            "coupling_metrics": self._calculate_coupling_metrics(graph),
            
            # Cohesion metrics
            "cohesion_metrics": self._calculate_cohesion_metrics(graph),
            
            # Stability metrics
            "stability_metrics": self._calculate_stability_metrics(graph),
            
            # Complexity metrics
            "complexity_metrics": self._calculate_complexity_metrics(graph),
            
            # Maintainability index
            "maintainability_index": self._calculate_maintainability_index(graph)
        }
        
        return metrics

    def _calculate_coupling_metrics(self, graph: DependencyGraph) -> Dict[str, float]:
        """Calculate coupling metrics."""
        if not graph.nodes:
            return {"afferent_coupling": 0, "efferent_coupling": 0, "instability": 0}
        
        total_ca = sum(node.dependent_count for node in graph.nodes.values())  # Afferent coupling
        total_ce = sum(node.dependency_count for node in graph.nodes.values())   # Efferent coupling
        
        # Instability = Ce / (Ca + Ce)
        instability = total_ce / (total_ca + total_ce) if (total_ca + total_ce) > 0 else 0
        
        return {
            "afferent_coupling": total_ca / len(graph.nodes),
            "efferent_coupling": total_ce / len(graph.nodes),
            "instability": instability
        }

    def _calculate_cohesion_metrics(self, graph: DependencyGraph) -> Dict[str, float]:
        """Calculate cohesion metrics."""
        # Simplified cohesion calculation based on internal connectivity
        if not graph.nodes:
            return {"cohesion": 0}
        
        # Calculate average internal connectivity
        total_internal_edges = 0
        total_possible_internal = 0
        
        for node in graph.nodes.values():
            # Count edges to nodes in the same "package" (simplified)
            same_package_deps = 0
            for dep_id in node.dependencies:
                if dep_id in graph.nodes:
                    dep_node = graph.nodes[dep_id]
                    # Simple heuristic: same directory = same package
                    if dep_node.path.split('/')[-2] == node.path.split('/')[-2]:
                        same_package_deps += 1
            
            total_internal_edges += same_package_deps
            total_possible_internal += len(node.dependencies)
        
        cohesion = total_internal_edges / total_possible_internal if total_possible_internal > 0 else 0
        
        return {"cohesion": cohesion}

    def _calculate_stability_metrics(self, graph: DependencyGraph) -> Dict[str, float]:
        """Calculate stability metrics for each node."""
        stability_scores = {}
        
        for node_id, node in graph.nodes.items():
            ca = node.dependent_count  # Afferent coupling
            ce = node.dependency_count  # Efferent coupling
            
            # Instability = Ce / (Ca + Ce)
            instability = ce / (ca + ce) if (ca + ce) > 0 else 0
            stability_scores[node_id] = 1 - instability  # Stability = 1 - Instability
        
        avg_stability = sum(stability_scores.values()) / len(stability_scores) if stability_scores else 0
        
        return {
            "individual_stability": stability_scores,
            "average_stability": avg_stability,
            "stable_components": len([s for s in stability_scores.values() if s > 0.7]),
            "unstable_components": len([s for s in stability_scores.values() if s < 0.3])
        }

    def _calculate_complexity_metrics(self, graph: DependencyGraph) -> Dict[str, float]:
        """Calculate complexity metrics."""
        if not graph.nodes:
            return {"graph_complexity": 0, "cognitive_complexity": 0}
        
        # Graph complexity based on edges and nodes
        graph_complexity = len(graph.edges) / len(graph.nodes) if graph.nodes else 0
        
        # Cognitive complexity based on cycles and depth
        cycles = len(graph.detect_cycles())
        max_depth = self._calculate_max_depth(graph)
        cognitive_complexity = (cycles * 2) + (max_depth * 0.5)
        
        return {
            "graph_complexity": graph_complexity,
            "cognitive_complexity": cognitive_complexity,
            "cyclomatic_complexity": len(graph.edges) - len(graph.nodes) + 2  # Standard formula
        }

    def _calculate_maintainability_index(self, graph: DependencyGraph) -> float:
        """Calculate maintainability index (0-100)."""
        if not graph.nodes:
            return 100
        
        # Factors that affect maintainability
        coupling = self._calculate_coupling_metrics(graph)
        complexity = self._calculate_complexity_metrics(graph)
        cycles = len(graph.detect_cycles())
        
        # Simplified maintainability index
        maintainability = 100
        
        # Penalty for high coupling
        maintainability -= coupling["instability"] * 30
        
        # Penalty for complexity
        maintainability -= min(complexity["graph_complexity"] * 10, 30)
        
        # Penalty for cycles
        maintainability -= min(cycles * 5, 20)
        
        return max(0, min(100, maintainability))
