"""Dependency graph data structures."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
from enum import Enum


class DependencyType(str, Enum):
    """Types of dependencies."""
    IMPORT = "import"
    INHERITANCE = "inheritance"
    COMPOSITION = "composition"
    REFERENCE = "reference"
    CALL = "call"
    IMPLEMENTATION = "implementation"


class NodeType(str, Enum):
    """Types of nodes in the dependency graph."""
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    MODULE = "module"
    PACKAGE = "package"


@dataclass
class DependencyNode:
    """A node in the dependency graph."""
    id: str
    name: str
    type: NodeType
    path: str
    language: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    
    # Metrics
    complexity_score: int = 1
    lines_of_code: int = 0
    cyclomatic_complexity: int = 1
    
    # Analysis data
    is_entry_point: bool = False
    is_utility: bool = False
    is_test: bool = False
    is_generated: bool = False
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DependencyNode):
            return False
        return self.id == other.id
    
    def add_dependency(self, node_id: str) -> None:
        """Add a dependency to this node."""
        self.dependencies.add(node_id)
    
    def add_dependent(self, node_id: str) -> None:
        """Add a dependent to this node."""
        self.dependents.add(node_id)
    
    def remove_dependency(self, node_id: str) -> None:
        """Remove a dependency from this node."""
        self.dependencies.discard(node_id)
    
    def remove_dependent(self, node_id: str) -> None:
        """Remove a dependent from this node."""
        self.dependents.discard(node_id)
    
    @property
    def dependency_count(self) -> int:
        """Get the number of dependencies."""
        return len(self.dependencies)
    
    @property
    def dependent_count(self) -> int:
        """Get the number of dependents."""
        return len(self.dependents)
    
    @property
    def is_isolated(self) -> bool:
        """Check if this node has no dependencies or dependents."""
        return self.dependency_count == 0 and self.dependent_count == 0
    
    @property
    def is_leaf(self) -> bool:
        """Check if this node has no dependents."""
        return self.dependent_count == 0
    
    @property
    def is_root(self) -> bool:
        """Check if this node has no dependencies."""
        return self.dependency_count == 0


@dataclass
class DependencyEdge:
    """An edge in the dependency graph."""
    source_id: str
    target_id: str
    type: DependencyType
    weight: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.type))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DependencyEdge):
            return False
        return (self.source_id == other.source_id and 
                self.target_id == other.target_id and 
                self.type == other.type)


class DependencyGraph:
    """A directed graph representing dependencies between components."""
    
    def __init__(self) -> None:
        self.nodes: Dict[str, DependencyNode] = {}
        self.edges: Dict[Tuple[str, str, DependencyType], DependencyEdge] = {}
        self._adjacency_list: Dict[str, Set[str]] = {}
        self._reverse_adjacency_list: Dict[str, Set[str]] = {}
    
    def add_node(self, node: DependencyNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self._adjacency_list:
            self._adjacency_list[node.id] = set()
        if node.id not in self._reverse_adjacency_list:
            self._reverse_adjacency_list[node.id] = set()
    
    def remove_node(self, node_id: str) -> None:
        """Remove a node from the graph."""
        if node_id not in self.nodes:
            return
        
        # Remove all edges connected to this node
        edges_to_remove = []
        for edge_key, edge in self.edges.items():
            if edge.source_id == node_id or edge.target_id == node_id:
                edges_to_remove.append(edge_key)
        
        for edge_key in edges_to_remove:
            self.remove_edge_by_key(edge_key)
        
        # Remove from adjacency lists
        if node_id in self._adjacency_list:
            for dependent in self._adjacency_list[node_id]:
                self._reverse_adjacency_list[dependent].discard(node_id)
            del self._adjacency_list[node_id]
        
        if node_id in self._reverse_adjacency_list:
            for dependency in self._reverse_adjacency_list[node_id]:
                self._adjacency_list[dependency].discard(node_id)
            del self._reverse_adjacency_list[node_id]
        
        # Remove node
        del self.nodes[node_id]
    
    def add_edge(self, edge: DependencyEdge) -> None:
        """Add an edge to the graph."""
        edge_key = (edge.source_id, edge.target_id, edge.type)
        self.edges[edge_key] = edge
        
        # Update adjacency lists
        if edge.source_id not in self._adjacency_list:
            self._adjacency_list[edge.source_id] = set()
        if edge.target_id not in self._reverse_adjacency_list:
            self._reverse_adjacency_list[edge.target_id] = set()
        
        self._adjacency_list[edge.source_id].add(edge.target_id)
        self._reverse_adjacency_list[edge.target_id].add(edge.source_id)
        
        # Update node dependencies/dependents
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].add_dependency(edge.target_id)
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].add_dependent(edge.source_id)
    
    def remove_edge(self, source_id: str, target_id: str, edge_type: DependencyType) -> None:
        """Remove an edge from the graph."""
        edge_key = (source_id, target_id, edge_type)
        self.remove_edge_by_key(edge_key)
    
    def remove_edge_by_key(self, edge_key: Tuple[str, str, DependencyType]) -> None:
        """Remove an edge by its key."""
        if edge_key not in self.edges:
            return
        
        edge = self.edges[edge_key]
        
        # Update adjacency lists
        if edge.source_id in self._adjacency_list:
            self._adjacency_list[edge.source_id].discard(edge.target_id)
        if edge.target_id in self._reverse_adjacency_list:
            self._reverse_adjacency_list[edge.target_id].discard(edge.source_id)
        
        # Update node dependencies/dependents
        if edge.source_id in self.nodes:
            self.nodes[edge.source_id].remove_dependency(edge.target_id)
        if edge.target_id in self.nodes:
            self.nodes[edge.target_id].remove_dependent(edge.source_id)
        
        # Remove edge
        del self.edges[edge_key]
    
    def get_node(self, node_id: str) -> Optional[DependencyNode]:
        """Get a node by ID."""
        return self.nodes.get(node_id)
    
    def get_edge(self, source_id: str, target_id: str, edge_type: DependencyType) -> Optional[DependencyEdge]:
        """Get an edge by source, target, and type."""
        edge_key = (source_id, target_id, edge_type)
        return self.edges.get(edge_key)
    
    def get_dependencies(self, node_id: str) -> List[DependencyNode]:
        """Get all dependencies of a node."""
        if node_id not in self._adjacency_list:
            return []
        
        dependencies = []
        for dep_id in self._adjacency_list[node_id]:
            if dep_id in self.nodes:
                dependencies.append(self.nodes[dep_id])
        
        return dependencies
    
    def get_dependents(self, node_id: str) -> List[DependencyNode]:
        """Get all dependents of a node."""
        if node_id not in self._reverse_adjacency_list:
            return []
        
        dependents = []
        for dep_id in self._reverse_adjacency_list[node_id]:
            if dep_id in self.nodes:
                dependents.append(self.nodes[dep_id])
        
        return dependents
    
    def get_edges_from(self, node_id: str) -> List[DependencyEdge]:
        """Get all edges originating from a node."""
        edges = []
        for edge_key, edge in self.edges.items():
            if edge.source_id == node_id:
                edges.append(edge)
        return edges
    
    def get_edges_to(self, node_id: str) -> List[DependencyEdge]:
        """Get all edges pointing to a node."""
        edges = []
        for edge_key, edge in self.edges.items():
            if edge.target_id == node_id:
                edges.append(edge)
        return edges
    
    def find_path(self, source_id: str, target_id: str) -> Optional[List[str]]:
        """Find a path from source to target using BFS."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return None
        
        from collections import deque
        
        queue = deque([(source_id, [source_id])])
        visited = {source_id}
        
        while queue:
            current_id, path = queue.popleft()
            
            if current_id == target_id:
                return path
            
            for neighbor_id in self._adjacency_list.get(current_id, set()):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, path + [neighbor_id]))
        
        return None
    
    def find_all_paths(self, source_id: str, target_id: str, max_depth: int = 10) -> List[List[str]]:
        """Find all paths from source to target (up to max_depth)."""
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        
        paths = []
        
        def dfs(current_id: str, path: List[str], visited: Set[str]) -> None:
            if len(path) > max_depth:
                return
            
            if current_id == target_id:
                paths.append(path.copy())
                return
            
            for neighbor_id in self._adjacency_list.get(current_id, set()):
                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    path.append(neighbor_id)
                    dfs(neighbor_id, path, visited)
                    path.pop()
                    visited.remove(neighbor_id)
        
        dfs(source_id, [source_id], {source_id})
        return paths
    
    def detect_cycles(self) -> List[List[str]]:
        """Detect all cycles in the graph using DFS."""
        cycles = []
        visited = set()
        recursion_stack = set()
        path = []
        
        def dfs(node_id: str) -> bool:
            visited.add(node_id)
            recursion_stack.add(node_id)
            path.append(node_id)
            
            for neighbor_id in self._adjacency_list.get(node_id, set()):
                if neighbor_id in recursion_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor_id)
                    cycle = path[cycle_start:] + [neighbor_id]
                    cycles.append(cycle)
                elif neighbor_id not in visited:
                    dfs(neighbor_id)
            
            recursion_stack.remove(node_id)
            path.pop()
            return False
        
        for node_id in self.nodes:
            if node_id not in visited:
                dfs(node_id)
        
        return cycles
    
    def get_strongly_connected_components(self) -> List[List[str]]:
        """Get strongly connected components using Tarjan's algorithm."""
        index = 0
        indices: Dict[str, int] = {}
        low_link: Dict[str, int] = {}
        stack: List[str] = []
        on_stack: Set[str] = set()
        sccs: List[List[str]] = []
        
        def strongconnect(node_id: str) -> None:
            nonlocal index
            indices[node_id] = index
            low_link[node_id] = index
            index += 1
            stack.append(node_id)
            on_stack.add(node_id)
            
            for neighbor_id in self._adjacency_list.get(node_id, set()):
                if neighbor_id not in indices:
                    strongconnect(neighbor_id)
                    low_link[node_id] = min(low_link[node_id], low_link[neighbor_id])
                elif neighbor_id in on_stack:
                    low_link[node_id] = min(low_link[node_id], indices[neighbor_id])
            
            if low_link[node_id] == indices[node_id]:
                scc = []
                while True:
                    w = stack.pop()
                    on_stack.remove(w)
                    scc.append(w)
                    if w == node_id:
                        break
                sccs.append(scc)
        
        for node_id in self.nodes:
            if node_id not in indices:
                strongconnect(node_id)
        
        return sccs
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)
        
        # Node type distribution
        type_counts = {}
        for node in self.nodes.values():
            type_counts[node.type] = type_counts.get(node.type, 0) + 1
        
        # Edge type distribution
        edge_type_counts = {}
        for edge in self.edges.values():
            edge_type_counts[edge.type] = edge_type_counts.get(edge.type, 0) + 1
        
        # Dependency statistics
        dependency_counts = [len(node.dependencies) for node in self.nodes.values()]
        dependent_counts = [len(node.dependents) for node in self.nodes.values()]
        
        cycles = self.detect_cycles()
        sccs = self.get_strongly_connected_components()
        
        return {
            "total_nodes": total_nodes,
            "total_edges": total_edges,
            "node_types": type_counts,
            "edge_types": edge_type_counts,
            "avg_dependencies": sum(dependency_counts) / total_nodes if total_nodes > 0 else 0,
            "avg_dependents": sum(dependent_counts) / total_nodes if total_nodes > 0 else 0,
            "max_dependencies": max(dependency_counts) if dependency_counts else 0,
            "max_dependents": max(dependent_counts) if dependent_counts else 0,
            "cycles_count": len(cycles),
            "cycles": cycles[:10],  # Limit to first 10 cycles
            "strongly_connected_components_count": len(sccs),
            "largest_scc_size": max(len(scc) for scc in sccs) if sccs else 0,
            "isolated_nodes": len([n for n in self.nodes.values() if n.is_isolated]),
            "leaf_nodes": len([n for n in self.nodes.values() if n.is_leaf]),
            "root_nodes": len([n for n in self.nodes.values() if n.is_root])
        }
