"""Architecture pattern detector implementation."""

from __future__ import annotations

from typing import Dict, List, Any

from .patterns import MicroservicesPattern, LayeredPattern, MVCPattern


class ArchitecturePatternDetector:
    """Main detector for architecture patterns."""
    
    def __init__(self) -> None:
        self.microservices_pattern = MicroservicesPattern()
        self.layered_pattern = LayeredPattern()
        self.mvc_pattern = MVCPattern()
    
    async def detect_patterns(self, project_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect all architecture patterns in project data."""
        detected_patterns = []
        
        # Detect microservices
        microservices_matches = self.microservices_pattern.detect(project_data)
        detected_patterns.extend([
            {
                "pattern": match.pattern_name,
                "confidence": match.confidence.value,
                "score": match.score,
                "indicators_found": match.indicators_found,
                "components_involved": match.components_involved,
                "suggestions": match.suggestions
            }
            for match in microservices_matches
        ])
        
        # Detect layered
        layered_matches = self.layered_pattern.detect(project_data)
        detected_patterns.extend([
            {
                "pattern": match.pattern_name,
                "confidence": match.confidence.value,
                "score": match.score,
                "indicators_found": match.indicators_found,
                "components_involved": match.components_involved,
                "suggestions": match.suggestions
            }
            for match in layered_matches
        ])
        
        # Detect MVC
        mvc_matches = self.mvc_pattern.detect(project_data)
        detected_patterns.extend([
            {
                "pattern": match.pattern_name,
                "confidence": match.confidence.value,
                "score": match.score,
                "indicators_found": match.indicators_found,
                "components_involved": match.components_involved,
                "suggestions": match.suggestions
            }
            for match in mvc_matches
        ])
        
        return detected_patterns
