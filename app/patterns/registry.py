"""Pattern registry implementation."""

from __future__ import annotations

from typing import Dict, List, Any


class PatternRegistry:
    """Registry for architecture patterns."""
    
    def __init__(self) -> None:
        self._patterns = {}
    
    def register_pattern(self, name: str, pattern: Any) -> None:
        """Register a pattern."""
        self._patterns[name] = pattern
    
    def get_pattern(self, name: str) -> Any:
        """Get a pattern by name."""
        return self._patterns.get(name)
    
    def list_patterns(self) -> List[str]:
        """List all registered patterns."""
        return list(self._patterns.keys())
