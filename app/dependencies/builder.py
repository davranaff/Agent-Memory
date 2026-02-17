"""Dependency graph builder from parsed components."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Set, Optional, Tuple
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.models import Component, Project
from .graph import DependencyGraph, DependencyNode, DependencyEdge, DependencyType, NodeType

logger = logging.getLogger(__name__)


class DependencyGraphBuilder:
    """Builds dependency graphs from parsed project components."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def build_graph(self, project_id: str) -> DependencyGraph:
        """Build a complete dependency graph for a project."""
        graph = DependencyGraph()
        
        # Get all components for the project
        components = await self._get_project_components(project_id)
        
        if not components:
            logger.warning(f"No components found for project {project_id}")
            return graph
        
        # Create nodes
        await self._create_nodes(graph, components)
        
        # Create edges
        await self._create_edges(graph, components)
        
        logger.info(f"Built dependency graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        return graph

    async def build_incremental_graph(
        self,
        project_id: str,
        changed_files: List[str],
    ) -> Tuple[DependencyGraph, Set[str], List[str]]:
        """Build a partial graph projection for components affected by changed files."""
        graph = DependencyGraph()
        normalized_paths = self._normalize_paths(changed_files)

        if not normalized_paths:
            return graph, set(), []

        components = await self._get_project_components(project_id)
        if not components:
            return graph, set(), normalized_paths

        changed_components = [
            component
            for component in components
            if self._component_matches_paths(component, normalized_paths)
        ]
        changed_ids = {str(component.id) for component in changed_components}

        if not changed_components:
            # The file can still represent a deletion. Caller can remove stale
            # graph nodes by changed path.
            return graph, set(), normalized_paths

        await self._create_nodes(graph, changed_components)

        name_to_id, path_to_id = self._build_lookup_maps(components)
        for component in components:
            source_id = str(component.id)
            for dep in component.dependencies or []:
                target_id = self._resolve_dependency(dep, name_to_id, path_to_id, source_id)
                if not target_id or target_id == source_id:
                    continue
                if source_id not in changed_ids and target_id not in changed_ids:
                    continue

                graph.add_edge(
                    DependencyEdge(
                        source_id=source_id,
                        target_id=target_id,
                        type=self._determine_edge_type(component, dep),
                        weight=self._calculate_edge_weight(component, dep),
                        metadata={
                            "dependency_name": dep,
                            "resolved_to": target_id,
                        },
                    )
                )

        return graph, changed_ids, normalized_paths

    async def _get_project_components(self, project_id: str) -> List[Component]:
        """Get all components for a project."""
        stmt = select(Component).where(Component.project_id == project_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _create_nodes(self, graph: DependencyGraph, components: List[Component]) -> None:
        """Create nodes from components."""
        for component in components:
            node_type = self._determine_node_type(component)
            
            node = DependencyNode(
                id=str(component.id),
                name=component.name,
                type=node_type,
                path=component.path,
                language=component.language or "unknown",
                metadata={
                    "relative_path": component.relative_path,
                    "file_extension": component.file_extension,
                    "line_start": component.line_start,
                    "line_end": component.line_end,
                    "exports": component.exports,
                    "component_metadata": component.metadata_
                },
                complexity_score=component.complexity_score,
                lines_of_code=component.line_count,
                is_test=component.metadata_.get("is_test", False) if component.metadata_ else False,
                is_generated=component.metadata_.get("is_generated", False) if component.metadata_ else False,
                is_utility=self._is_utility_component(component),
                is_entry_point=self._is_entry_point(component)
            )
            
            graph.add_node(node)

    def _determine_node_type(self, component: Component) -> NodeType:
        """Determine the node type from component type."""
        type_mapping = {
            "class": NodeType.CLASS,
            "function": NodeType.FUNCTION,
            "async_function": NodeType.FUNCTION,
            "interface": NodeType.INTERFACE,
            "struct": NodeType.STRUCT,
            "enum": NodeType.ENUM,
            "file": NodeType.FILE,
            "directory": NodeType.MODULE,
            "method": NodeType.FUNCTION,
        }
        
        return type_mapping.get(component.type, NodeType.FILE)

    def _is_utility_component(self, component: Component) -> bool:
        """Check if a component is a utility/helper."""
        utility_patterns = [
            "util", "helper", "common", "shared", "base", "core",
            "lib", "tools", "utils", "misc"
        ]
        
        name_lower = component.name.lower()
        path_lower = component.relative_path.lower()
        
        return any(pattern in name_lower or pattern in path_lower for pattern in utility_patterns)

    def _is_entry_point(self, component: Component) -> bool:
        """Check if a component is an entry point."""
        entry_point_patterns = [
            "main", "index", "app", "server", "start", "init",
            "bootstrap", "run", "__main__"
        ]
        
        name_lower = component.name.lower()
        path_lower = component.relative_path.lower()
        
        return any(pattern in name_lower or pattern in path_lower for pattern in entry_point_patterns)

    async def _create_edges(self, graph: DependencyGraph, components: List[Component]) -> None:
        """Create edges from component dependencies."""
        name_to_id, path_to_id = self._build_lookup_maps(components)
        
        for component in components:
            source_id = str(component.id)
            
            # Process dependencies
            for dep in component.dependencies or []:
                target_id = self._resolve_dependency(dep, name_to_id, path_to_id, source_id)
                
                if target_id and target_id != source_id:
                    edge_type = self._determine_edge_type(component, dep)
                    
                    edge = DependencyEdge(
                        source_id=source_id,
                        target_id=target_id,
                        type=edge_type,
                        weight=self._calculate_edge_weight(component, dep),
                        metadata={
                            "dependency_name": dep,
                            "resolved_to": target_id
                        }
                    )
                    
                    graph.add_edge(edge)

    def _build_lookup_maps(
        self,
        components: Iterable[Component],
    ) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Build component lookup maps used by dependency resolution."""
        name_to_id: Dict[str, str] = {}
        path_to_id: Dict[str, str] = {}

        for component in components:
            cid = str(component.id)
            name_to_id[component.name] = cid

            rel_norm = self._normalize_file_path(component.relative_path)
            abs_norm = self._normalize_file_path(component.path)
            for path_value in (rel_norm, abs_norm):
                if not path_value:
                    continue
                path_to_id[path_value] = cid
                path_to_id[str(Path(path_value).with_suffix(""))] = cid

        return name_to_id, path_to_id

    def _normalize_file_path(self, value: str | None) -> str:
        """Normalize paths for resilient matching between git and DB values."""
        if not value:
            return ""
        normalized = str(value).replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        while normalized.startswith("/"):
            normalized = normalized[1:]
        return normalized

    def _normalize_paths(self, paths: Iterable[str]) -> List[str]:
        """Normalize and deduplicate changed file paths."""
        result: List[str] = []
        seen: Set[str] = set()
        for path in paths:
            normalized = self._normalize_file_path(path)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            result.append(normalized)
        return result

    def _component_matches_paths(self, component: Component, changed_paths: List[str]) -> bool:
        """Check if component absolute/relative path intersects changed file paths."""
        component_paths = [
            self._normalize_file_path(component.path),
            self._normalize_file_path(component.relative_path),
        ]
        component_paths = [p for p in component_paths if p]
        if not component_paths:
            return False

        for component_path in component_paths:
            for changed in changed_paths:
                if (
                    component_path == changed
                    or component_path.endswith(f"/{changed}")
                    or changed.endswith(f"/{component_path}")
                ):
                    return True
        return False

    def _resolve_dependency(self, 
                          dependency: str, 
                          name_to_id: Dict[str, str],
                          path_to_id: Dict[str, str],
                          source_id: str) -> Optional[str]:
        """Resolve a dependency string to a component ID."""
        # Try exact name match first
        if dependency in name_to_id:
            return name_to_id[dependency]
        
        # Try path match
        if dependency in path_to_id:
            return path_to_id[dependency]
        
        # Try name without module path
        simple_name = dependency.split('.')[-1]
        if simple_name in name_to_id:
            return name_to_id[simple_name]
        
        # Try partial matches
        for name, node_id in name_to_id.items():
            if dependency.endswith(name) or name.endswith(dependency):
                return node_id
        
        for path, node_id in path_to_id.items():
            if dependency in path or path in dependency:
                return node_id
        
        return None

    def _determine_edge_type(self, component: Component, dependency: str) -> DependencyType:
        """Determine the type of dependency edge."""
        # Check for inheritance patterns
        inheritance_keywords = ["extends", "implements", "inherits", "super", "base"]
        if any(keyword in dependency.lower() for keyword in inheritance_keywords):
            return DependencyType.INHERITANCE
        
        # Check for composition patterns
        composition_keywords = ["import", "require", "include", "using"]
        if any(keyword in dependency.lower() for keyword in composition_keywords):
            return DependencyType.IMPORT
        
        # Check for implementation patterns
        implementation_keywords = ["implements", "realizes", "fulfills"]
        if any(keyword in dependency.lower() for keyword in implementation_keywords):
            return DependencyType.IMPLEMENTATION
        
        # Default to reference
        return DependencyType.REFERENCE

    def _calculate_edge_weight(self, component: Component, dependency: str) -> float:
        """Calculate the weight of a dependency edge."""
        weight = 1.0
        
        # Increase weight for strong dependencies
        if dependency in component.exports:
            weight += 0.5
        
        # Increase weight for frequently used patterns
        common_imports = ["os", "sys", "json", "datetime", "pathlib"]
        if any(imp in dependency.lower() for imp in common_imports):
            weight += 0.2
        
        # Increase weight for same-file dependencies
        if "." not in dependency:  # Local import
            weight += 0.3
        
        return min(weight, 2.0)  # Cap at 2.0

    async def build_layered_graph(self, project_id: str) -> Tuple[DependencyGraph, Dict[str, int]]:
        """Build a dependency graph with layer information."""
        graph = await self.build_graph(project_id)
        
        # Calculate layers using longest path algorithm
        layers = self._calculate_layers(graph)
        
        # Add layer information to nodes
        for node_id, layer in layers.items():
            if node_id in graph.nodes:
                graph.nodes[node_id].metadata["layer"] = layer
        
        return graph, layers

    def _calculate_layers(self, graph: DependencyGraph) -> Dict[str, int]:
        """Calculate layers using topological sorting."""
        layers = {}
        visited = set()
        
        def calculate_node_layer(node_id: str) -> int:
            if node_id in layers:
                return layers[node_id]
            
            if node_id in visited:
                # Cycle detected, assign current layer
                return 0
            
            visited.add(node_id)
            
            # Get all dependencies
            dependencies = graph.get_dependencies(node_id)
            
            if not dependencies:
                # No dependencies, this is layer 0
                layers[node_id] = 0
            else:
                # Layer is max of dependency layers + 1
                max_dep_layer = max(calculate_node_layer(dep.id) for dep in dependencies)
                layers[node_id] = max_dep_layer + 1
            
            visited.remove(node_id)
            return layers[node_id]
        
        # Calculate layers for all nodes
        for node_id in graph.nodes:
            calculate_node_layer(node_id)
        
        return layers

    async def build_package_graph(self, project_id: str) -> DependencyGraph:
        """Build a package-level dependency graph."""
        components = await self._get_project_components(project_id)
        
        # Group components by package/directory
        packages = defaultdict(list)
        for component in components:
            package_path = str(Path(component.relative_path).parent)
            packages[package_path].append(component)
        
        # Create package nodes
        graph = DependencyGraph()
        package_nodes = {}
        
        for package_path, package_components in packages.items():
            node_id = f"package_{package_path}"
            
            # Aggregate package information
            languages = set(comp.language for comp in package_components if comp.language)
            total_loc = sum(comp.line_count for comp in package_components)
            
            node = DependencyNode(
                id=node_id,
                name=Path(package_path).name or "root",
                type=NodeType.PACKAGE,
                path=package_path,
                language=next(iter(languages)) if languages else "unknown",
                metadata={
                    "package_path": package_path,
                    "component_count": len(package_components),
                    "languages": list(languages),
                    "components": [str(comp.id) for comp in package_components]
                },
                lines_of_code=total_loc
            )
            
            graph.add_node(node)
            package_nodes[package_path] = node_id
        
        # Create package-level dependencies
        for package_path, package_components in packages.items():
            source_package_id = package_nodes[package_path]
            
            # Collect all dependencies of components in this package
            all_dependencies = set()
            for component in package_components:
                all_dependencies.update(component.dependencies)
            
            # Map dependencies to packages
            for dep in all_dependencies:
                target_package_id = self._find_package_for_dependency(dep, package_nodes, packages)
                
                if target_package_id and target_package_id != source_package_id:
                    edge = DependencyEdge(
                        source_id=source_package_id,
                        target_id=target_package_id,
                        type=DependencyType.IMPORT,
                        weight=1.0,
                        metadata={"dependency": dep}
                    )
                    graph.add_edge(edge)
        
        return graph

    def _find_package_for_dependency(self, 
                                   dependency: str, 
                                   package_nodes: Dict[str, str],
                                   packages: Dict[str, List[Component]]) -> Optional[str]:
        """Find which package contains a dependency."""
        # Try to match dependency with component names
        for package_path, package_components in packages.items():
            for component in package_components:
                if dependency == component.name or dependency.endswith(component.name):
                    return package_nodes[package_path]
        
        return None

    async def analyze_impact(self, 
                           project_id: str, 
                           component_id: str) -> Dict[str, any]:
        """Analyze the impact of changing a component."""
        graph = await self.build_graph(project_id)
        
        if component_id not in graph.nodes:
            return {"error": "Component not found"}
        
        # Get all dependents (components that depend on this one)
        dependents = graph.get_dependents(component_id)
        
        # Calculate impact metrics
        direct_impact = len(dependents)
        
        # Calculate indirect impact (transitive dependents)
        all_affected = set()
        queue = [dep.id for dep in dependents]
        
        while queue:
            current = queue.pop(0)
            if current not in all_affected:
                all_affected.add(current)
                current_dependents = graph.get_dependents(current)
                queue.extend([dep.id for dep in current_dependents])
        
        indirect_impact = len(all_affected) - direct_impact
        
        # Find critical paths
        critical_paths = []
        for dependent in dependents:
            path = graph.find_path(dependent.id, component_id)
            if path:
                critical_paths.append(path)
        
        return {
            "component_id": component_id,
            "component_name": graph.nodes[component_id].name,
            "direct_impact": direct_impact,
            "indirect_impact": indirect_impact,
            "total_impact": len(all_affected),
            "affected_components": list(all_affected),
            "critical_paths": critical_paths[:10],  # Limit to 10 paths
            "is_critical": direct_impact > 5 or len(all_affected) > 20
        }
