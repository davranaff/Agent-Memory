"""Technology stack data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any
from enum import Enum


class TechnologyCategory(str, Enum):
    """Categories of technologies."""
    LANGUAGE = "language"
    FRAMEWORK = "framework"
    DATABASE = "database"
    BUILD_TOOL = "build_tool"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    SECURITY = "security"
    COMMUNICATION = "communication"
    STORAGE = "storage"
    CACHING = "caching"
    SEARCH = "search"
    QUEUE = "queue"
    CONTAINER = "container"
    ORCHESTRATION = "orchestration"


class MaturityLevel(str, Enum):
    """Maturity levels of technologies."""
    EXPERIMENTAL = "experimental"
    EMERGING = "emerging"
    MATURING = "maturing"
    MATURE = "mature"
    LEGACY = "legacy"


@dataclass
class Technology:
    """A technology in the stack."""
    name: str
    category: TechnologyCategory
    version: Optional[str] = None
    confidence: float = 1.0  # 0.0 to 1.0
    usage_count: int = 0
    files_involved: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Properties
    is_main_tech: bool = False
    is_optional: bool = False
    maturity_level: MaturityLevel = MaturityLevel.MATURE
    
    def __post_init__(self) -> None:
        """Post-initialization processing."""
        if self.version and not self.version.startswith(('v', '^', '~', '>', '<', '=')):
            # Clean up version string
            self.version = self.version.lstrip('v').strip()
    
    @property
    def display_name(self) -> str:
        """Get display name with version."""
        if self.version:
            return f"{self.name}@{self.version}"
        return self.name
    
    @property
    def is_deprecated(self) -> bool:
        """Check if technology is deprecated."""
        return self.maturity_level == MaturityLevel.LEGACY


@dataclass
class Framework(Technology):
    """A framework technology."""
    architecture_pattern: Optional[str] = None  # MVC, MVP, MVVM, etc.
    is_full_stack: bool = False
    is_microframework: bool = False
    frontend_framework: bool = False
    backend_framework: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization for framework."""
        super().__post_init__()
        self.category = TechnologyCategory.FRAMEWORK


@dataclass
class Database(Technology):
    """A database technology."""
    database_type: Optional[str] = None  # relational, document, key-value, etc.
    is_primary: bool = False
    is_cache: bool = False
    is_message_store: bool = False
    
    # Database-specific properties
    supports_transactions: bool = False
    supports_indexes: bool = True
    is_sql: bool = False
    is_nosql: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization for database."""
        super().__post_init__()
        self.category = TechnologyCategory.DATABASE
        
        # Auto-detect database type
        if self.database_type is None:
            self.database_type = self._detect_database_type()
    
    def _detect_database_type(self) -> Optional[str]:
        """Detect database type from name."""
        nosql_patterns = ["mongo", "cassandra", "dynamo", "couch", "redis", "neo4j"]
        relational_patterns = ["postgres", "mysql", "sqlite", "oracle", "sqlserver"]
        
        name_lower = self.name.lower()
        
        if any(pattern in name_lower for pattern in nosql_patterns):
            self.is_nosql = True
            return "document" if "mongo" in name_lower else "nosql"
        elif any(pattern in name_lower for pattern in relational_patterns):
            self.is_sql = True
            return "relational"
        
        return None


@dataclass
class BuildTool(Technology):
    """A build tool technology."""
    tool_type: Optional[str] = None  # package_manager, task_runner, bundler, etc.
    is_package_manager: bool = False
    is_task_runner: bool = False
    is_bundler: bool = False
    
    def __post_init__(self) -> None:
        """Post-initialization for build tool."""
        super().__post_init__()
        self.category = TechnologyCategory.BUILD_TOOL
        
        # Auto-detect tool type
        if self.tool_type is None:
            self.tool_type = self._detect_tool_type()
    
    def _detect_tool_type(self) -> Optional[str]:
        """Detect build tool type from name."""
        name_lower = self.name.lower()
        
        if any(pm in name_lower for pm in ["npm", "yarn", "pip", "conda", "maven", "gradle", "cargo"]):
            self.is_package_manager = True
            return "package_manager"
        elif any(tr in name_lower for tr in ["webpack", "vite", "rollup", "parcel"]):
            self.is_bundler = True
            return "bundler"
        elif any(tr in name_lower for tr in ["gulp", "grunt", "make", "cmake"]):
            self.is_task_runner = True
            return "task_runner"
        
        return None


@dataclass
class TechnologyStack:
    """Complete technology stack for a project."""
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    # Core technologies
    languages: List[Technology] = field(default_factory=list)
    frameworks: List[Framework] = field(default_factory=list)
    databases: List[Database] = field(default_factory=list)
    build_tools: List[BuildTool] = field(default_factory=list)
    
    # Additional technologies
    testing_tools: List[Technology] = field(default_factory=list)
    deployment_tools: List[Technology] = field(default_factory=list)
    monitoring_tools: List[Technology] = field(default_factory=list)
    security_tools: List[Technology] = field(default_factory=list)
    communication_tools: List[Technology] = field(default_factory=list)
    storage_tools: List[Technology] = field(default_factory=list)
    caching_tools: List[Technology] = field(default_factory=list)
    search_tools: List[Technology] = field(default_factory=list)
    queue_tools: List[Technology] = field(default_factory=list)
    container_tools: List[Technology] = field(default_factory=list)
    orchestration_tools: List[Technology] = field(default_factory=list)
    
    # Stack metadata
    stack_type: Optional[str] = None  # full_stack, backend_only, frontend_only, etc.
    architecture_pattern: Optional[str] = None
    deployment_pattern: Optional[str] = None
    
    # Analysis results
    confidence_score: float = 0.0
    complexity_score: float = 0.0  # 1-10
    modernization_score: float = 0.0  # 0-100
    security_score: float = 0.0  # 0-100
    
    # Metadata
    detection_timestamp: Optional[str] = None
    analyzer_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_all_technologies(self) -> List[Technology]:
        """Get all technologies in the stack."""
        all_tech = []
        all_tech.extend(self.languages)
        all_tech.extend(self.frameworks)
        all_tech.extend(self.databases)
        all_tech.extend(self.build_tools)
        all_tech.extend(self.testing_tools)
        all_tech.extend(self.deployment_tools)
        all_tech.extend(self.monitoring_tools)
        all_tech.extend(self.security_tools)
        all_tech.extend(self.communication_tools)
        all_tech.extend(self.storage_tools)
        all_tech.extend(self.caching_tools)
        all_tech.extend(self.search_tools)
        all_tech.extend(self.queue_tools)
        all_tech.extend(self.container_tools)
        all_tech.extend(self.orchestration_tools)
        return all_tech
    
    def get_technologies_by_category(self, category: TechnologyCategory) -> List[Technology]:
        """Get technologies by category."""
        category_mapping = {
            TechnologyCategory.LANGUAGE: self.languages,
            TechnologyCategory.FRAMEWORK: self.frameworks,
            TechnologyCategory.DATABASE: self.databases,
            TechnologyCategory.BUILD_TOOL: self.build_tools,
            TechnologyCategory.TESTING: self.testing_tools,
            TechnologyCategory.DEPLOYMENT: self.deployment_tools,
            TechnologyCategory.MONITORING: self.monitoring_tools,
            TechnologyCategory.SECURITY: self.security_tools,
            TechnologyCategory.COMMUNICATION: self.communication_tools,
            TechnologyCategory.STORAGE: self.storage_tools,
            TechnologyCategory.CACHING: self.caching_tools,
            TechnologyCategory.SEARCH: self.search_tools,
            TechnologyCategory.QUEUE: self.queue_tools,
            TechnologyCategory.CONTAINER: self.container_tools,
            TechnologyCategory.ORCHESTRATION: self.orchestration_tools,
        }
        return category_mapping.get(category, [])
    
    def get_primary_language(self) -> Optional[Technology]:
        """Get the primary language of the project."""
        if not self.languages:
            return None
        
        # Return language with highest usage count
        return max(self.languages, key=lambda lang: lang.usage_count)
    
    def get_primary_framework(self) -> Optional[Framework]:
        """Get the primary framework of the project."""
        if not self.frameworks:
            return None
        
        # Return framework with highest usage count
        return max(self.frameworks, key=lambda fw: fw.usage_count)
    
    def get_primary_database(self) -> Optional[Database]:
        """Get the primary database of the project."""
        # Look for primary database first
        primary_dbs = [db for db in self.databases if db.is_primary]
        if primary_dbs:
            return primary_dbs[0]
        
        # Return database with highest usage count
        if self.databases:
            return max(self.databases, key=lambda db: db.usage_count)
        
        return None
    
    def is_monolithic(self) -> bool:
        """Check if the stack suggests a monolithic architecture."""
        # Heuristics for monolithic detection
        has_single_database = len(self.databases) <= 1
        has_single_language = len(self.languages) <= 2
        has_full_stack_framework = any(fw.is_full_stack for fw in self.frameworks)
        has_microservices = any("microservice" in fw.name.lower() for fw in self.frameworks)
        
        return (has_single_database and has_single_language and 
                (has_full_stack_framework or not has_microservices))
    
    def is_microservices(self) -> bool:
        """Check if the stack suggests a microservices architecture."""
        microservice_indicators = [
            any("microservice" in fw.name.lower() for fw in self.frameworks),
            len(self.databases) > 2,
            any(tool.name.lower() in ["kubernetes", "docker", "helm"] for tool in self.container_tools + self.orchestration_tools),
            any("gateway" in tool.name.lower() or "api" in tool.name.lower() for tool in self.communication_tools)
        ]
        
        return sum(microservice_indicators) >= 2
    
    def is_serverless(self) -> bool:
        """Check if the stack suggests a serverless architecture."""
        serverless_indicators = [
            any(tool.name.lower() in ["lambda", "functions", "serverless"] for tool in self.deployment_tools),
            any("serverless" in fw.name.lower() for fw in self.frameworks),
            len(self.container_tools) == 0,
            any("faas" in tool.name.lower() for tool in self.deployment_tools)
        ]
        
        return any(serverless_indicators)
    
    def calculate_stack_complexity(self) -> float:
        """Calculate overall stack complexity (1-10)."""
        complexity = 1.0
        
        # Base complexity for number of technologies
        tech_count = len(self.get_all_technologies())
        if tech_count > 20:
            complexity += 3
        elif tech_count > 10:
            complexity += 2
        elif tech_count > 5:
            complexity += 1
        
        # Complexity for multiple languages
        if len(self.languages) > 3:
            complexity += 2
        elif len(self.languages) > 1:
            complexity += 1
        
        # Complexity for multiple databases
        if len(self.databases) > 2:
            complexity += 2
        elif len(self.databases) > 1:
            complexity += 1
        
        # Complexity for container orchestration
        if self.orchestration_tools:
            complexity += 2
        elif self.container_tools:
            complexity += 1
        
        # Complexity for monitoring/security tools
        if len(self.monitoring_tools) > 2 or len(self.security_tools) > 2:
            complexity += 1
        
        return min(10.0, complexity)
    
    def calculate_modernization_score(self) -> float:
        """Calculate modernization score (0-100)."""
        score = 50.0  # Base score
        
        # Modern languages bonus
        modern_languages = ["rust", "go", "typescript", "kotlin", "swift", "dart"]
        for lang in self.languages:
            if lang.name.lower() in modern_languages:
                score += 10
            elif lang.name.lower() in ["python", "javascript", "java"]:
                score += 5
        
        # Modern frameworks bonus
        modern_frameworks = ["react", "vue", "angular", "fastapi", "django", "flask", "express"]
        for fw in self.frameworks:
            if fw.name.lower() in modern_frameworks:
                score += 10
        
        # Container/orchestration bonus
        if self.container_tools:
            score += 15
        if self.orchestration_tools:
            score += 10
        
        # Modern databases bonus
        modern_dbs = ["postgresql", "mongodb", "redis", "elasticsearch"]
        for db in self.databases:
            if db.name.lower() in modern_dbs:
                score += 5
        
        # Modern build tools bonus
        modern_build_tools = ["webpack", "vite", "docker", "kubernetes"]
        for tool in self.build_tools:
            if tool.name.lower() in modern_build_tools:
                score += 5
        
        # Legacy technologies penalty
        legacy_indicators = ["php", "perl", "cobol", "fortran"]
        for lang in self.languages:
            if lang.name.lower() in legacy_indicators:
                score -= 20
        
        return max(0.0, min(100.0, score))
    
    def get_stack_summary(self) -> Dict[str, Any]:
        """Get a summary of the technology stack."""
        return {
            "total_technologies": len(self.get_all_technologies()),
            "primary_language": self.get_primary_language().name if self.get_primary_language() else None,
            "primary_framework": self.get_primary_framework().name if self.get_primary_framework() else None,
            "primary_database": self.get_primary_database().name if self.get_primary_database() else None,
            "architecture_type": "microservices" if self.is_microservices() else "serverless" if self.is_serverless() else "monolithic" if self.is_monolithic() else "unknown",
            "complexity_score": self.calculate_stack_complexity(),
            "modernization_score": self.calculate_modernization_score(),
            "confidence_score": self.confidence_score,
            "categories": {
                "languages": len(self.languages),
                "frameworks": len(self.frameworks),
                "databases": len(self.databases),
                "build_tools": len(self.build_tools),
                "testing": len(self.testing_tools),
                "deployment": len(self.deployment_tools),
                "monitoring": len(self.monitoring_tools),
                "security": len(self.security_tools)
            }
        }
