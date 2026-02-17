"""Architecture Pattern Detection System for Agent Brain."""

from __future__ import annotations

from .detector import ArchitecturePatternDetector
from .patterns import (
    ArchitecturePattern, PatternType, PatternConfidence,
    MicroservicesPattern, LayeredPattern, MVCPattern,
    RepositoryPattern, FactoryPattern, ObserverPattern
)
from .analyzer import PatternAnalyzer
from .registry import PatternRegistry

__all__ = [
    "ArchitecturePatternDetector",
    "PatternAnalyzer",
    "PatternRegistry",
    "ArchitecturePattern",
    "PatternType",
    "PatternConfidence",
    "MicroservicesPattern",
    "LayeredPattern",
    "MVCPattern",
    "RepositoryPattern",
    "FactoryPattern",
    "ObserverPattern",
]
