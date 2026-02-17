"""Component metadata models and schemas."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union, Set
from datetime import datetime, timezone
from enum import Enum


class ComponentType(str, Enum):
    """Types of components."""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    MODULE = "module"
    PACKAGE = "package"
    FILE = "file"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"


class AccessLevel(str, Enum):
    """Access levels for components."""
    PUBLIC = "public"
    PRIVATE = "private"
    PROTECTED = "protected"
    INTERNAL = "internal"
    PACKAGE_PRIVATE = "package_private"


class DocumentationLevel(str, Enum):
    """Documentation levels."""
    NONE = "none"
    BASIC = "basic"
    GOOD = "good"
    COMPREHENSIVE = "comprehensive"
    EXCELLENT = "excellent"


@dataclass
class CodeMetrics:
    """Code quality metrics for a component."""
    lines_of_code: int = 0
    lines_of_comments: int = 0
    cyclomatic_complexity: int = 1
    cognitive_complexity: int = 1
    maintainability_index: float = 100.0
    technical_debt_ratio: float = 0.0
    
    # Test coverage
    test_coverage: float = 0.0
    has_tests: bool = False
    
    # Code smells
    code_smells: List[str] = field(default_factory=list)
    duplicated_lines: int = 0
    
    @property
    def comment_ratio(self) -> float:
        """Ratio of comments to code."""
        if self.lines_of_code == 0:
            return 0.0
        return self.lines_of_comments / self.lines_of_code
    
    @property
    def complexity_score(self) -> str:
        """Complexity classification."""
        if self.cyclomatic_complexity <= 5:
            return "simple"
        elif self.cyclomatic_complexity <= 10:
            return "moderate"
        elif self.cyclomatic_complexity <= 20:
            return "complex"
        else:
            return "very_complex"


@dataclass
class UsageMetrics:
    """Usage metrics for a component."""
    # Dependency metrics
    dependencies_count: int = 0
    dependents_count: int = 0
    fan_in: int = 0  # Number of incoming dependencies
    fan_out: int = 0  # Number of outgoing dependencies
    
    # Instability metrics
    instability: float = 0.0  # Ce / (Ca + Ce)
    abstractness: float = 0.0  # Na / Nc
    distance_from_main_sequence: float = 0.0  # |A + I - 1|
    
    # Usage patterns
    usage_frequency: int = 0
    last_used: Optional[datetime] = None
    usage_contexts: List[str] = field(default_factory=list)
    
    @property
    def stability_score(self) -> str:
        """Stability classification."""
        if self.instability <= 0.2:
            return "very_stable"
        elif self.instability <= 0.5:
            return "stable"
        elif self.instability <= 0.8:
            return "unstable"
        else:
            return "very_unstable"


@dataclass
class SecurityMetrics:
    """Security metrics for a component."""
    # Vulnerability indicators
    has_security_issues: bool = False
    security_issues: List[str] = field(default_factory=list)
    vulnerability_score: float = 0.0
    
    # Security patterns
    uses_encryption: bool = False
    validates_input: bool = False
    handles_authentication: bool = False
    handles_authorization: bool = False
    
    # Data sensitivity
    handles_sensitive_data: bool = False
    data_classification: str = "public"  # public, internal, confidential, restricted
    
    # Security best practices
    follows_security_practices: bool = False
    security_score: float = 0.0


@dataclass
class PerformanceMetrics:
    """Performance metrics for a component."""
    # Performance characteristics
    time_complexity: Optional[str] = None  # O(1), O(n), O(n^2), etc.
    space_complexity: Optional[str] = None
    
    # Resource usage
    memory_usage: Optional[str] = None
    cpu_usage: Optional[str] = None
    
    # Performance indicators
    is_cpu_intensive: bool = False
    is_memory_intensive: bool = False
    is_io_intensive: bool = False
    
    # Optimization opportunities
    optimization_suggestions: List[str] = field(default_factory=list)
    performance_score: float = 0.0


@dataclass
class DocumentationMetadata:
    """Documentation metadata for a component."""
    level: DocumentationLevel = DocumentationLevel.NONE
    has_docstring: bool = False
    has_examples: bool = False
    has_parameters_documented: bool = False
    has_returns_documented: bool = False
    has_exceptions_documented: bool = False
    
    # Documentation content
    docstring_content: Optional[str] = None
    examples_count: int = 0
    parameters_documented: int = 0
    total_parameters: int = 0
    
    # Quality metrics
    documentation_score: float = 0.0
    last_documented: Optional[datetime] = None
    
    @property
    def documentation_completeness(self) -> float:
        """How complete is the documentation (0-1)."""
        factors = [
            self.has_docstring,
            self.has_examples,
            self.has_parameters_documented if self.total_parameters > 0 else True,
            self.has_returns_documented,
            self.has_exceptions_documented
        ]
        return sum(factors) / len(factors)


@dataclass
class ComponentMetadata:
    """Comprehensive metadata for a component."""
    # Basic information
    component_id: str
    name: str
    type: ComponentType
    language: str
    file_path: str
    relative_path: str
    
    # Structural information
    access_level: AccessLevel = AccessLevel.PUBLIC
    is_abstract: bool = False
    is_static: bool = False
    is_final: bool = False
    is_async: bool = False
    is_generator: bool = False
    
    # Location information
    line_start: int = 0
    line_end: int = 0
    column_start: int = 0
    column_end: int = 0
    
    # Relationships
    parent_component: Optional[str] = None
    child_components: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    dependents: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    
    # Signatures
    signature: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    exceptions: List[str] = field(default_factory=list)
    
    # Metrics
    code_metrics: CodeMetrics = field(default_factory=CodeMetrics)
    usage_metrics: UsageMetrics = field(default_factory=UsageMetrics)
    security_metrics: SecurityMetrics = field(default_factory=SecurityMetrics)
    performance_metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    documentation: DocumentationMetadata = field(default_factory=DocumentationMetadata)
    
    # Classification
    tags: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    domain: Optional[str] = None
    business_context: Optional[str] = None
    
    # Quality indicators
    quality_score: float = 0.0
    health_score: float = 0.0
    maintainability_score: float = 0.0
    
    # Evolution
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_modified: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    changelog: List[str] = field(default_factory=list)
    
    # Analysis metadata
    analysis_version: str = "1.0.0"
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    
    # Custom metadata
    custom_metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        
        # Handle datetime serialization
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
            elif isinstance(value, set):
                data[key] = list(value)
        
        # Handle nested objects
        data["code_metrics"] = asdict(self.code_metrics)
        data["usage_metrics"] = asdict(self.usage_metrics)
        data["security_metrics"] = asdict(self.security_metrics)
        data["performance_metrics"] = asdict(self.performance_metrics)
        data["documentation"] = asdict(self.documentation)
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComponentMetadata":
        """Create from dictionary."""
        # Handle datetime deserialization
        for key in ["created_at", "last_modified", "analysis_timestamp"]:
            if key in data and isinstance(data[key], str):
                data[key] = datetime.fromisoformat(data[key])
        
        # Handle nested objects
        if "code_metrics" in data:
            data["code_metrics"] = CodeMetrics(**data["code_metrics"])
        if "usage_metrics" in data:
            data["usage_metrics"] = UsageMetrics(**data["usage_metrics"])
        if "security_metrics" in data:
            data["security_metrics"] = SecurityMetrics(**data["security_metrics"])
        if "performance_metrics" in data:
            data["performance_metrics"] = PerformanceMetrics(**data["performance_metrics"])
        if "documentation" in data:
            data["documentation"] = DocumentationMetadata(**data["documentation"])
        
        # Handle sets
        if "tags" in data and isinstance(data["tags"], list):
            data["tags"] = set(data["tags"])
        if "categories" in data and isinstance(data["categories"], list):
            data["categories"] = set(data["categories"])
        
        return cls(**data)
    
    def calculate_quality_score(self) -> float:
        """Calculate overall quality score (0-100)."""
        scores = []
        
        # Code quality (40%)
        code_score = (
            (100 - self.code_metrics.cyclomatic_complexity * 2) * 0.3 +
            self.code_metrics.maintainability_index * 0.4 +
            (100 - self.code_metrics.technical_debt_ratio * 100) * 0.3
        )
        scores.append(min(100, max(0, code_score)))
        
        # Documentation quality (25%)
        doc_score = self.documentation.documentation_score * 100
        scores.append(min(100, max(0, doc_score)))
        
        # Test coverage (20%)
        test_score = self.code_metrics.test_coverage * 100
        scores.append(min(100, max(0, test_score)))
        
        # Security (15%)
        security_score = self.security_metrics.security_score * 100
        scores.append(min(100, max(0, security_score)))
        
        # Calculate weighted average
        weights = [0.4, 0.25, 0.2, 0.15]
        quality_score = sum(score * weight for score, weight in zip(scores, weights))
        
        return quality_score
    
    def calculate_health_score(self) -> float:
        """Calculate component health score (0-100)."""
        factors = []
        
        # Stability factor
        stability_factor = 1.0 - self.usage_metrics.instability
        factors.append(stability_factor * 100)
        
        # Complexity factor (inverse)
        if self.code_metrics.cyclomatic_complexity <= 5:
            complexity_factor = 100
        elif self.code_metrics.cyclomatic_complexity <= 10:
            complexity_factor = 80
        elif self.code_metrics.cyclomatic_complexity <= 20:
            complexity_factor = 60
        else:
            complexity_factor = 40
        factors.append(complexity_factor)
        
        # Documentation factor
        doc_factor = self.documentation.documentation_score * 100
        factors.append(doc_factor)
        
        # Test coverage factor
        test_factor = self.code_metrics.test_coverage * 100
        factors.append(test_factor)
        
        # Security factor
        security_factor = self.security_metrics.security_score * 100
        factors.append(security_factor)
        
        # Calculate average
        health_score = sum(factors) / len(factors)
        
        return min(100, max(0, health_score))
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of component metadata."""
        return {
            "component_id": self.component_id,
            "name": self.name,
            "type": self.type.value,
            "language": self.language,
            "file_path": self.relative_path,
            "quality_score": self.calculate_quality_score(),
            "health_score": self.calculate_health_score(),
            "complexity": self.code_metrics.complexity_score,
            "stability": self.usage_metrics.stability_score,
            "documentation_level": self.documentation.level.value,
            "test_coverage": self.code_metrics.test_coverage,
            "security_score": self.security_metrics.security_score,
            "dependencies_count": len(self.dependencies),
            "dependents_count": len(self.dependents),
            "tags": list(self.tags),
            "categories": list(self.categories)
        }


class MetadataSchema:
    """Schema definition for component metadata."""
    
    REQUIRED_FIELDS = {
        "component_id",
        "name", 
        "type",
        "language",
        "file_path",
        "relative_path"
    }
    
    OPTIONAL_FIELDS = {
        "access_level",
        "is_abstract",
        "is_static",
        "is_final",
        "is_async",
        "is_generator",
        "line_start",
        "line_end",
        "column_start",
        "column_end",
        "parent_component",
        "child_components",
        "dependencies",
        "dependents",
        "imports",
        "exports",
        "signature",
        "parameters",
        "return_type",
        "exceptions",
        "tags",
        "categories",
        "domain",
        "business_context",
        "custom_metadata"
    }
    
    METRIC_FIELDS = {
        "code_metrics",
        "usage_metrics", 
        "security_metrics",
        "performance_metrics",
        "documentation"
    }
    
    @classmethod
    def validate(cls, metadata: ComponentMetadata) -> List[str]:
        """Validate metadata against schema."""
        errors = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if not hasattr(metadata, field) or getattr(metadata, field) is None:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if not isinstance(metadata.type, ComponentType):
            errors.append(f"Invalid component type: {metadata.type}")
        
        if not isinstance(metadata.access_level, AccessLevel):
            errors.append(f"Invalid access level: {metadata.access_level}")
        
        # Validate ranges
        if metadata.line_start < 0:
            errors.append("Line start must be non-negative")
        
        if metadata.line_end < metadata.line_start:
            errors.append("Line end must be greater than or equal to line start")
        
        # Validate metrics
        if metadata.code_metrics.cyclomatic_complexity < 1:
            errors.append("Cyclomatic complexity must be at least 1")
        
        if not (0 <= metadata.code_metrics.test_coverage <= 100):
            errors.append("Test coverage must be between 0 and 100")
        
        if not (0 <= metadata.code_metrics.maintainability_index <= 100):
            errors.append("Maintainability index must be between 0 and 100")
        
        return errors
    
    @classmethod
    def get_field_description(cls, field: str) -> Optional[str]:
        """Get description for a field."""
        descriptions = {
            "component_id": "Unique identifier for the component",
            "name": "Name of the component",
            "type": "Type of component (class, function, etc.)",
            "language": "Programming language",
            "file_path": "Absolute file path",
            "relative_path": "Relative file path from project root",
            "access_level": "Access level (public, private, etc.)",
            "is_abstract": "Whether the component is abstract",
            "is_static": "Whether the component is static",
            "is_final": "Whether the component is final",
            "is_async": "Whether the component is asynchronous",
            "is_generator": "Whether the component is a generator",
            "line_start": "Starting line number",
            "line_end": "Ending line number",
            "dependencies": "List of component dependencies",
            "dependents": "List of components that depend on this one",
            "tags": "Tags for categorization",
            "categories": "Categories for organization",
            "quality_score": "Overall quality score (0-100)",
            "health_score": "Component health score (0-100)"
        }
        
        return descriptions.get(field)
    
    @classmethod
    def get_schema_definition(cls) -> Dict[str, Any]:
        """Get the complete schema definition."""
        return {
            "required_fields": list(cls.REQUIRED_FIELDS),
            "optional_fields": list(cls.OPTIONAL_FIELDS),
            "metric_fields": list(cls.METRIC_FIELDS),
            "enums": {
                "ComponentType": [t.value for t in ComponentType],
                "AccessLevel": [a.value for a in AccessLevel],
                "DocumentationLevel": [d.value for d in DocumentationLevel]
            },
            "field_descriptions": {
                field: cls.get_field_description(field)
                for field in cls.REQUIRED_FIELDS | cls.OPTIONAL_FIELDS
            }
        }
