"""Architecture pattern definitions and base classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum


class PatternType(str, Enum):
    """Types of architecture patterns."""
    ARCHITECTURAL = "architectural"
    DESIGN = "design"
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    ENTERPRISE = "enterprise"
    DISTRIBUTED_SYSTEMS = "distributed_systems"


class PatternConfidence(str, Enum):
    """Confidence levels for pattern detection."""
    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PatternIndicator:
    """Indicator that suggests the presence of a pattern."""
    name: str
    description: str
    weight: float = 1.0
    file_patterns: List[str] = field(default_factory=list)
    code_patterns: List[str] = field(default_factory=list)
    structure_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternMatch:
    """A match of a pattern in the codebase."""
    pattern_name: str
    confidence: PatternConfidence
    score: float
    indicators_found: List[str]
    components_involved: List[str]
    file_paths: List[str]
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)


class ArchitecturePattern(ABC):
    """Base class for architecture patterns."""
    
    def __init__(self, name: str, pattern_type: PatternType) -> None:
        self.name = name
        self.pattern_type = pattern_type
        self.indicators: List[PatternIndicator] = []
        self.min_confidence_threshold = 0.5
        self.required_indicators: Set[str] = set()
        self.optional_indicators: Set[str] = set()
    
    @abstractmethod
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect the pattern in project data."""
        pass
    
    @abstractmethod
    def get_indicators(self) -> List[PatternIndicator]:
        """Get pattern indicators."""
        pass
    
    def calculate_confidence(self, matches: Dict[str, bool]) -> Tuple[float, PatternConfidence]:
        """Calculate confidence score from indicator matches."""
        if not matches:
            return 0.0, PatternConfidence.VERY_LOW
        
        # Calculate weighted score
        total_weight = 0.0
        matched_weight = 0.0
        
        for indicator in self.indicators:
            total_weight += indicator.weight
            if indicator.name in matches and matches[indicator.name]:
                matched_weight += indicator.weight
        
        score = matched_weight / total_weight if total_weight > 0 else 0.0
        
        # Determine confidence level
        if score >= 0.9:
            confidence = PatternConfidence.VERY_HIGH
        elif score >= 0.7:
            confidence = PatternConfidence.HIGH
        elif score >= 0.5:
            confidence = PatternConfidence.MEDIUM
        elif score >= 0.3:
            confidence = PatternConfidence.LOW
        else:
            confidence = PatternConfidence.VERY_LOW
        
        return score, confidence


class MicroservicesPattern(ArchitecturePattern):
    """Microservices architecture pattern."""
    
    def __init__(self) -> None:
        super().__init__("Microservices", PatternType.ARCHITECTURAL)
        self.required_indicators = {"service_boundaries", "independent_deployment"}
        self.optional_indicators = {"api_gateway", "service_discovery", "circuit_breaker"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get microservices indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="service_boundaries",
                description="Clear service boundaries with separate codebases",
                weight=0.3,
                structure_patterns=[r"service-\w+", r"\w+-service", r"services/"],
                file_patterns=["*service*", "*/service/*", "*/services/*"]
            ),
            PatternIndicator(
                name="independent_deployment",
                description="Each service can be deployed independently",
                weight=0.25,
                file_patterns=["Dockerfile", "docker-compose.yml", "k8s/", "kubernetes/"],
                code_patterns=[r"docker", r"kubernetes", r"deployment"]
            ),
            PatternIndicator(
                name="api_gateway",
                description="API gateway pattern for external access",
                weight=0.15,
                file_patterns=["gateway*", "api-gateway*", "ingress*"],
                code_patterns=[r"gateway", r"api.*gateway", r"ingress"]
            ),
            PatternIndicator(
                name="service_discovery",
                description="Service discovery mechanism",
                weight=0.15,
                file_patterns=["consul*", "eureka*", "etcd*"],
                code_patterns=[r"service.*discovery", r"consul", r"eureka"]
            ),
            PatternIndicator(
                name="circuit_breaker",
                description="Circuit breaker pattern for resilience",
                weight=0.1,
                file_patterns=["circuit*", "breaker*", "hystrix*"],
                code_patterns=[r"circuit.*breaker", r"hystrix", r"resilience"]
            ),
            PatternIndicator(
                name="inter_service_communication",
                description="Communication between services",
                weight=0.05,
                code_patterns=[r"rest.*client", r"http.*client", r"grpc", r"message.*queue"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect microservices pattern."""
        indicators = self.get_indicators()
        matches = {}
        
        for indicator in indicators:
            matches[indicator.name] = self._check_indicator(indicator, project_data)
        
        score, confidence = self.calculate_confidence(matches)
        
        if score >= self.min_confidence_threshold:
            match = PatternMatch(
                pattern_name=self.name,
                confidence=confidence,
                score=score,
                indicators_found=[name for name, found in matches.items() if found],
                components_involved=self._extract_components(project_data, matches),
                file_paths=self._extract_file_paths(project_data, matches),
                evidence=self._build_evidence(matches),
                suggestions=self._get_suggestions(matches)
            )
            return [match]
        
        return []
    
    def _check_indicator(self, indicator: PatternIndicator, project_data: Dict[str, Any]) -> bool:
        """Check if an indicator is present."""
        # Check file patterns
        if indicator.file_patterns:
            file_paths = project_data.get("file_paths", [])
            for pattern in indicator.file_patterns:
                if any(self._matches_pattern(path, pattern) for path in file_paths):
                    return True
        
        # Check structure patterns
        if indicator.structure_patterns:
            directory_structure = project_data.get("directory_structure", [])
            for pattern in indicator.structure_patterns:
                if any(self._matches_pattern(path, pattern) for path in directory_structure):
                    return True
        
        # Check code patterns
        if indicator.code_patterns:
            code_content = project_data.get("code_content", "")
            for pattern in indicator.code_patterns:
                if self._matches_code_pattern(code_content, pattern):
                    return True
        
        return False
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches a pattern."""
        import fnmatch
        return fnmatch.fnmatch(text.lower(), pattern.lower())
    
    def _matches_code_pattern(self, content: str, pattern: str) -> bool:
        """Check if content matches a code pattern."""
        import re
        return bool(re.search(pattern, content, re.IGNORECASE))
    
    def _extract_components(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract components involved in the pattern."""
        components = []
        
        # Extract from file paths
        file_paths = project_data.get("file_paths", [])
        for path in file_paths:
            if "service" in path.lower():
                components.append(path)
        
        return components
    
    def _extract_file_paths(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract file paths involved in the pattern."""
        file_paths = []
        
        for indicator_name, found in matches.items():
            if found:
                indicator = next((ind for ind in self.indicators if ind.name == indicator_name), None)
                if indicator:
                    for pattern in indicator.file_patterns:
                        matching_files = [path for path in project_data.get("file_paths", []) 
                                       if self._matches_pattern(path, pattern)]
                        file_paths.extend(matching_files)
        
        return list(set(file_paths))
    
    def _build_evidence(self, matches: Dict[str, bool]) -> Dict[str, Any]:
        """Build evidence for the pattern detection."""
        return {
            "matched_indicators": [name for name, found in matches.items() if found],
            "missed_indicators": [name for name, found in matches.items() if not found],
            "required_indicators_found": len(self.required_indicators & set(matches.keys())),
            "total_indicators": len(self.indicators)
        }
    
    def _get_suggestions(self, matches: Dict[str, bool]) -> List[str]:
        """Get suggestions based on detection results."""
        suggestions = []
        
        # Check for missing required indicators
        missing_required = self.required_indicators - set(matches.keys())
        if missing_required:
            suggestions.append(f"Consider implementing: {', '.join(missing_required)}")
        
        # Check for missing optional indicators
        missing_optional = self.optional_indicators - set(matches.keys())
        if missing_optional:
            suggestions.append(f"Consider adding: {', '.join(missing_optional)}")
        
        return suggestions


class LayeredPattern(ArchitecturePattern):
    """Layered architecture pattern."""
    
    def __init__(self) -> None:
        super().__init__("Layered Architecture", PatternType.ARCHITECTURAL)
        self.required_indicators = {"layer_separation", "unidirectional_dependencies"}
        self.optional_indicators = {"abstraction_layers", "dependency_injection"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get layered architecture indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="layer_separation",
                description="Clear separation of layers (presentation, business, data)",
                weight=0.3,
                structure_patterns=[r"controller/", r"service/", r"repository/", r"model/", r"view/"],
                file_patterns=["*/controller/*", "*/service/*", "*/repository/*"]
            ),
            PatternIndicator(
                name="unidirectional_dependencies",
                description="Dependencies flow only in one direction",
                weight=0.3,
                code_patterns=[r"layer.*dependency", r"unidirectional", r"top.*down"]
            ),
            PatternIndicator(
                name="abstraction_layers",
                description="Abstract interfaces between layers",
                weight=0.2,
                file_patterns=["*interface*", "*abstract*"],
                code_patterns=[r"interface", r"abstract", r"protocol"]
            ),
            PatternIndicator(
                name="dependency_injection",
                description="Dependency injection for loose coupling",
                weight=0.2,
                code_patterns=[r"inject", r"di\s*container", r"ioc"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect layered architecture pattern."""
        indicators = self.get_indicators()
        matches = {}
        
        for indicator in indicators:
            matches[indicator.name] = self._check_indicator(indicator, project_data)
        
        score, confidence = self.calculate_confidence(matches)
        
        if score >= self.min_confidence_threshold:
            match = PatternMatch(
                pattern_name=self.name,
                confidence=confidence,
                score=score,
                indicators_found=[name for name, found in matches.items() if found],
                components_involved=self._extract_components(project_data, matches),
                file_paths=self._extract_file_paths(project_data, matches),
                evidence=self._build_evidence(matches),
                suggestions=self._get_suggestions(matches)
            )
            return [match]
        
        return []
    
    def _check_indicator(self, indicator: PatternIndicator, project_data: Dict[str, Any]) -> bool:
        """Check if an indicator is present."""
        # Similar implementation to MicroservicesPattern
        if indicator.file_patterns:
            file_paths = project_data.get("file_paths", [])
            for pattern in indicator.file_patterns:
                if any(self._matches_pattern(path, pattern) for path in file_paths):
                    return True
        
        if indicator.structure_patterns:
            directory_structure = project_data.get("directory_structure", [])
            for pattern in indicator.structure_patterns:
                if any(self._matches_pattern(path, pattern) for path in directory_structure):
                    return True
        
        if indicator.code_patterns:
            code_content = project_data.get("code_content", "")
            for pattern in indicator.code_patterns:
                if self._matches_code_pattern(code_content, pattern):
                    return True
        
        return False
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(text.lower(), pattern.lower())
    
    def _matches_code_pattern(self, content: str, pattern: str) -> bool:
        import re
        return bool(re.search(pattern, content, re.IGNORECASE))
    
    def _extract_components(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract components involved in the pattern."""
        components = []
        file_paths = project_data.get("file_paths", [])
        
        for path in file_paths:
            if any(layer in path.lower() for layer in ["controller", "service", "repository", "model"]):
                components.append(path)
        
        return components
    
    def _extract_file_paths(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract file paths involved in the pattern."""
        file_paths = []
        
        for indicator_name, found in matches.items():
            if found:
                indicator = next((ind for ind in self.indicators if ind.name == indicator_name), None)
                if indicator:
                    for pattern in indicator.file_patterns:
                        matching_files = [path for path in project_data.get("file_paths", []) 
                                       if self._matches_pattern(path, pattern)]
                        file_paths.extend(matching_files)
        
        return list(set(file_paths))
    
    def _build_evidence(self, matches: Dict[str, bool]) -> Dict[str, Any]:
        """Build evidence for the pattern detection."""
        return {
            "matched_indicators": [name for name, found in matches.items() if found],
            "missed_indicators": [name for name, found in matches.items() if not found],
            "required_indicators_found": len(self.required_indicators & set(matches.keys())),
            "total_indicators": len(self.indicators)
        }
    
    def _get_suggestions(self, matches: Dict[str, bool]) -> List[str]:
        """Get suggestions based on detection results."""
        suggestions = []
        
        missing_required = self.required_indicators - set(matches.keys())
        if missing_required:
            suggestions.append(f"Consider implementing: {', '.join(missing_required)}")
        
        missing_optional = self.optional_indicators - set(matches.keys())
        if missing_optional:
            suggestions.append(f"Consider adding: {', '.join(missing_optional)}")
        
        return suggestions


class MVCPattern(ArchitecturePattern):
    """Model-View-Controller pattern."""
    
    def __init__(self) -> None:
        super().__init__("Model-View-Controller", PatternType.ARCHITECTURAL)
        self.required_indicators = {"model_layer", "view_layer", "controller_layer"}
        self.optional_indicators = {"separation_of_concerns", "observer_pattern"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get MVC indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="model_layer",
                description="Model layer for data and business logic",
                weight=0.35,
                structure_patterns=[r"model/", r"models/", r"entity/"],
                file_patterns=["*model*", "*entity*"]
            ),
            PatternIndicator(
                name="view_layer",
                description="View layer for presentation",
                weight=0.35,
                structure_patterns=[r"view/", r"views/", r"template/", r"templates/"],
                file_patterns=["*view*", "*template*"]
            ),
            PatternIndicator(
                name="controller_layer",
                description="Controller layer for handling requests",
                weight=0.3,
                structure_patterns=[r"controller/", r"controllers/"],
                file_patterns=["*controller*"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect MVC pattern."""
        indicators = self.get_indicators()
        matches = {}
        
        for indicator in indicators:
            matches[indicator.name] = self._check_indicator(indicator, project_data)
        
        score, confidence = self.calculate_confidence(matches)
        
        if score >= self.min_confidence_threshold:
            match = PatternMatch(
                pattern_name=self.name,
                confidence=confidence,
                score=score,
                indicators_found=[name for name, found in matches.items() if found],
                components_involved=self._extract_components(project_data, matches),
                file_paths=self._extract_file_paths(project_data, matches),
                evidence=self._build_evidence(matches),
                suggestions=self._get_suggestions(matches)
            )
            return [match]
        
        return []
    
    def _check_indicator(self, indicator: PatternIndicator, project_data: Dict[str, Any]) -> bool:
        """Check if an indicator is present."""
        if indicator.file_patterns:
            file_paths = project_data.get("file_paths", [])
            for pattern in indicator.file_patterns:
                if any(self._matches_pattern(path, pattern) for path in file_paths):
                    return True
        
        if indicator.structure_patterns:
            directory_structure = project_data.get("directory_structure", [])
            for pattern in indicator.structure_patterns:
                if any(self._matches_pattern(path, pattern) for path in directory_structure):
                    return True
        
        return False
    
    def _matches_pattern(self, text: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(text.lower(), pattern.lower())
    
    def _extract_components(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract components involved in the pattern."""
        components = []
        file_paths = project_data.get("file_paths", [])
        
        for path in file_paths:
            if any(mvc_part in path.lower() for mvc_part in ["model", "view", "controller"]):
                components.append(path)
        
        return components
    
    def _extract_file_paths(self, project_data: Dict[str, Any], matches: Dict[str, bool]) -> List[str]:
        """Extract file paths involved in the pattern."""
        file_paths = []
        
        for indicator_name, found in matches.items():
            if found:
                indicator = next((ind for ind in self.indicators if ind.name == indicator_name), None)
                if indicator:
                    for pattern in indicator.file_patterns:
                        matching_files = [path for path in project_data.get("file_paths", []) 
                                       if self._matches_pattern(path, pattern)]
                        file_paths.extend(matching_files)
        
        return list(set(file_paths))
    
    def _build_evidence(self, matches: Dict[str, bool]) -> Dict[str, Any]:
        """Build evidence for the pattern detection."""
        return {
            "matched_indicators": [name for name, found in matches.items() if found],
            "missed_indicators": [name for name, found in matches.items() if not found],
            "required_indicators_found": len(self.required_indicators & set(matches.keys())),
            "total_indicators": len(self.indicators)
        }
    
    def _get_suggestions(self, matches: Dict[str, bool]) -> List[str]:
        """Get suggestions based on detection results."""
        suggestions = []
        
        missing_required = self.required_indicators - set(matches.keys())
        if missing_required:
            suggestions.append(f"Consider implementing: {', '.join(missing_required)}")
        
        return suggestions


# Design patterns
class RepositoryPattern(ArchitecturePattern):
    """Repository pattern for data access."""
    
    def __init__(self) -> None:
        super().__init__("Repository", PatternType.DESIGN)
        self.required_indicators = {"repository_interface", "repository_implementation"}
        self.optional_indicators = {"unit_of_work", "specification_pattern"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get repository pattern indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="repository_interface",
                description="Repository interface defining contract",
                weight=0.5,
                file_patterns=["*repository*", "*repo*"],
                code_patterns=[r"interface.*repository", r"abstract.*repository"]
            ),
            PatternIndicator(
                name="repository_implementation",
                description="Concrete repository implementations",
                weight=0.5,
                file_patterns=["*repository*", "*repo*"],
                code_patterns=[r"class.*repository", r"repository.*impl"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect repository pattern."""
        # Implementation similar to other patterns
        return []


class FactoryPattern(ArchitecturePattern):
    """Factory pattern for object creation."""
    
    def __init__(self) -> None:
        super().__init__("Factory", PatternType.CREATIONAL)
        self.required_indicators = {"factory_method", "product_creation"}
        self.optional_indicators = {"abstract_factory", "factory_hierarchy"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get factory pattern indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="factory_method",
                description="Factory method for creating objects",
                weight=0.6,
                file_patterns=["*factory*", "*creator*"],
                code_patterns=[r"factory", r"create.*method", r"build.*object"]
            ),
            PatternIndicator(
                name="product_creation",
                description="Products being created by factory",
                weight=0.4,
                code_patterns=[r"new.*product", r"instance.*creation"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect factory pattern."""
        # Implementation similar to other patterns
        return []


class ObserverPattern(ArchitecturePattern):
    """Observer pattern for event notification."""
    
    def __init__(self) -> None:
        super().__init__("Observer", PatternType.BEHAVIORAL)
        self.required_indicators = {"observer_interface", "subject_implementation"}
        self.optional_indicators = {"event_system", "notification_mechanism"}
    
    def get_indicators(self) -> List[PatternIndicator]:
        """Get observer pattern indicators."""
        if self.indicators:
            return self.indicators
        
        self.indicators = [
            PatternIndicator(
                name="observer_interface",
                description="Observer interface for subscribers",
                weight=0.5,
                file_patterns=["*observer*", "*subscriber*", "*listener*"],
                code_patterns=[r"interface.*observer", r"abstract.*observer"]
            ),
            PatternIndicator(
                name="subject_implementation",
                description="Subject implementation with observer management",
                weight=0.5,
                file_patterns=["*subject*", "*publisher*", "*notifier*"],
                code_patterns=[r"subject.*observer", r"notify.*observers"]
            )
        ]
        
        return self.indicators
    
    def detect(self, project_data: Dict[str, Any]) -> List[PatternMatch]:
        """Detect observer pattern."""
        # Implementation similar to other patterns
        return []
