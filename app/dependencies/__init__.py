"""Dependency Graph Builder for Agent Brain."""

from __future__ import annotations

from .graph import DependencyGraph, DependencyNode, DependencyEdge, NodeType, DependencyType
from .builder import DependencyGraphBuilder
from .analyzer import DependencyAnalyzer, ArchitectureInsight, DependencyIssue
from .store import GraphStore, InMemoryGraphStore, Neo4jGraphStore, ResilientGraphStore
from .service import GraphDependencyService
from .runtime import get_graph_store, close_graph_store

__all__ = [
    "DependencyGraph",
    "DependencyNode", 
    "DependencyEdge",
    "NodeType",
    "DependencyType",
    "DependencyGraphBuilder",
    "DependencyAnalyzer",
    "ArchitectureInsight",
    "DependencyIssue",
    "GraphStore",
    "InMemoryGraphStore",
    "Neo4jGraphStore",
    "ResilientGraphStore",
    "GraphDependencyService",
    "get_graph_store",
    "close_graph_store",
]
