"""Technology detection from project files and structure."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass

from .models import (
    Technology, Framework, Database, BuildTool,
    TechnologyCategory, MaturityLevel
)


@dataclass
class DetectionPattern:
    """Pattern for detecting a technology."""
    name: str
    patterns: List[str]
    file_patterns: List[str]
    category: TechnologyCategory
    confidence: float = 0.8
    version_pattern: Optional[str] = None
    metadata: Dict[str, Any] = None


class TechnologyDetector:
    """Detects technologies from project files and structure."""
    
    def __init__(self) -> None:
        self.detection_patterns = self._init_detection_patterns()
        self.language_patterns = self._init_language_patterns()
        self.framework_patterns = self._init_framework_patterns()
        self.database_patterns = self._init_database_patterns()
        self.build_tool_patterns = self._init_build_tool_patterns()

    def _init_detection_patterns(self) -> Dict[str, DetectionPattern]:
        """Initialize detection patterns for various technologies."""
        return {
            # Languages
            "python": DetectionPattern(
                name="Python",
                patterns=[r"import\s+\w+", r"from\s+\w+\s+import", r"def\s+\w+\s*\(", r"class\s+\w+\s*\("],
                file_patterns=["*.py", "*.pyi", "requirements.txt", "Pipfile", "pyproject.toml"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "javascript": DetectionPattern(
                name="JavaScript",
                patterns=[r"function\s+\w+\s*\(", r"const\s+\w+\s*=", r"let\s+\w+\s*=", r"var\s+\w+\s*="],
                file_patterns=["*.js", "*.jsx", "package.json", "yarn.lock"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "typescript": DetectionPattern(
                name="TypeScript",
                patterns=[r"interface\s+\w+", r"type\s+\w+\s*=", r"as\s+\w+", r":\s*\w+"],
                file_patterns=["*.ts", "*.tsx", "tsconfig.json"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "java": DetectionPattern(
                name="Java",
                patterns=[r"public\s+class\s+\w+", r"import\s+\w+", r"package\s+\w+", r"@Override"],
                file_patterns=["*.java", "pom.xml", "build.gradle"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "go": DetectionPattern(
                name="Go",
                patterns=[r"func\s+\w+\s*\(", r"package\s+\w+", r"import\s+\(", r"type\s+\w+\s+"],
                file_patterns=["*.go", "go.mod", "go.sum"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "rust": DetectionPattern(
                name="Rust",
                patterns=[r"fn\s+\w+\s*\(", r"use\s+::", r"let\s+mut\s+", r"struct\s+\w+"],
                file_patterns=["*.rs", "Cargo.toml", "Cargo.lock"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "csharp": DetectionPattern(
                name="C#",
                patterns=[r"public\s+class\s+\w+", r"using\s+\w+", r"namespace\s+\w+", r"void\s+\w+\s*\("],
                file_patterns=["*.cs", "*.csproj", "packages.config"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "cpp": DetectionPattern(
                name="C++",
                patterns=[r"#include\s*<\w+>", r"class\s+\w+", r"std::", r"namespace\s+\w+"],
                file_patterns=["*.cpp", "*.hpp", "*.cc", "*.cxx", "CMakeLists.txt"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "php": DetectionPattern(
                name="PHP",
                patterns=[r"<\?php", r"function\s+\w+\s*\(", r"class\s+\w+", r"\$\w+\s*="],
                file_patterns=["*.php", "composer.json"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            "ruby": DetectionPattern(
                name="Ruby",
                patterns=[r"def\s+\w+", r"class\s+\w+", r"require\s+", r"module\s+\w+"],
                file_patterns=["*.rb", "Gemfile", "Rakefile"],
                category=TechnologyCategory.LANGUAGE,
                confidence=0.9
            ),
            
            # Frameworks
            "react": DetectionPattern(
                name="React",
                patterns=[r"import.*React", r"from\s+['\"]react['\"]", r"React\.", r"useState"],
                file_patterns=["*.jsx", "*.tsx"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"frontend_framework": True, "is_full_stack": False}
            ),
            "vue": DetectionPattern(
                name="Vue.js",
                patterns=[r"import.*vue", r"from\s+['\"]vue['\"]", r"Vue\.", r"<template>"],
                file_patterns=["*.vue", "*.js", "*.ts"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"frontend_framework": True, "is_full_stack": False}
            ),
            "angular": DetectionPattern(
                name="Angular",
                patterns=[r"@Component", r"@NgModule", r"@Injectable", r"@angular/"],
                file_patterns=["*.ts", "*.js", "angular.json"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"frontend_framework": True, "is_full_stack": False}
            ),
            "fastapi": DetectionPattern(
                name="FastAPI",
                patterns=[r"from\s+fastapi", r"FastAPI\(", r"@app\.", r"APIRouter"],
                file_patterns=["*.py"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"backend_framework": True, "is_full_stack": True}
            ),
            "django": DetectionPattern(
                name="Django",
                patterns=[r"from\s+django", r"django\.", r"models\.Model", r"views\."],
                file_patterns=["*.py", "settings.py", "urls.py"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"backend_framework": True, "is_full_stack": True}
            ),
            "flask": DetectionPattern(
                name="Flask",
                patterns=[r"from\s+flask", r"Flask\(", r"@app\.route", r"render_template"],
                file_patterns=["*.py"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"backend_framework": True, "is_full_stack": False}
            ),
            "express": DetectionPattern(
                name="Express.js",
                patterns=[r"require\(['\"]express['\"]", r"express\(\)", r"app\.get", r"app\.post"],
                file_patterns=["*.js", "*.ts"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"backend_framework": True, "is_full_stack": False}
            ),
            "spring": DetectionPattern(
                name="Spring",
                patterns=[r"@SpringBootApplication", r"@RestController", r"@Service", r"org\.springframework"],
                file_patterns=["*.java", "pom.xml", "application.yml"],
                category=TechnologyCategory.FRAMEWORK,
                confidence=0.9,
                metadata={"backend_framework": True, "is_full_stack": True}
            ),
            
            # Databases
            "postgresql": DetectionPattern(
                name="PostgreSQL",
                patterns=[r"postgresql", r"psycopg2", r"pg8000", r"postgres"],
                file_patterns=["*.py", "*.js", "*.java", "*.go", "*.rs"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_sql": True, "supports_transactions": True}
            ),
            "mysql": DetectionPattern(
                name="MySQL",
                patterns=[r"mysql", r"pymysql", r"mysql2", r"mysql-connector"],
                file_patterns=["*.py", "*.js", "*.java"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_sql": True, "supports_transactions": True}
            ),
            "mongodb": DetectionPattern(
                name="MongoDB",
                patterns=[r"mongodb", r"pymongo", r"mongoose", r"mongoengine"],
                file_patterns=["*.py", "*.js", "*.ts"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_nosql": True, "database_type": "document"}
            ),
            "redis": DetectionPattern(
                name="Redis",
                patterns=[r"redis", r"redis-py", r"ioredis", r"redis-client"],
                file_patterns=["*.py", "*.js", "*.java", "*.go"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_nosql": True, "database_type": "key-value", "is_cache": True}
            ),
            "sqlite": DetectionPattern(
                name="SQLite",
                patterns=[r"sqlite", r"sqlite3", r"\.db$", r"\.sqlite$"],
                file_patterns=["*.py", "*.js", "*.db", "*.sqlite"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_sql": True, "database_type": "relational"}
            ),
            "elasticsearch": DetectionPattern(
                name="Elasticsearch",
                patterns=[r"elasticsearch", r"elasticsearch-py", r"@elastic/elasticsearch"],
                file_patterns=["*.py", "*.js", "*.json", "*.yml"],
                category=TechnologyCategory.DATABASE,
                confidence=0.8,
                metadata={"is_nosql": True, "database_type": "search"}
            ),
            
            # Build Tools
            "npm": DetectionPattern(
                name="npm",
                patterns=[r"npm\s+", r"package\.json"],
                file_patterns=["package.json", "package-lock.json"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "yarn": DetectionPattern(
                name="Yarn",
                patterns=[r"yarn\s+", r"yarn\.lock"],
                file_patterns=["yarn.lock", "package.json"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "pip": DetectionPattern(
                name="pip",
                patterns=[r"pip\s+", r"requirements\.txt", r"Pipfile"],
                file_patterns=["requirements.txt", "Pipfile", "pyproject.toml"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "maven": DetectionPattern(
                name="Maven",
                patterns=[r"mvn\s+", r"pom\.xml"],
                file_patterns=["pom.xml", "mvnw"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "gradle": DetectionPattern(
                name="Gradle",
                patterns=[r"gradle\s+", r"build\.gradle"],
                file_patterns=["build.gradle", "gradlew", "settings.gradle"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "cargo": DetectionPattern(
                name="Cargo",
                patterns=[r"cargo\s+", r"Cargo\.toml"],
                file_patterns=["Cargo.toml", "Cargo.lock"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_package_manager": True}
            ),
            "docker": DetectionPattern(
                name="Docker",
                patterns=[r"docker\s+", r"FROM\s+", r"RUN\s+", r"COPY\s+"],
                file_patterns=["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_container": True}
            ),
            "webpack": DetectionPattern(
                name="Webpack",
                patterns=[r"webpack", r"webpack\.config", r"module\.exports"],
                file_patterns=["webpack.config.js", "webpack.config.ts", "*.webpackrc"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_bundler": True}
            ),
            "vite": DetectionPattern(
                name="Vite",
                patterns=[r"vite", r"vite\.config", r"import\.vite"],
                file_patterns=["vite.config.js", "vite.config.ts"],
                category=TechnologyCategory.BUILD_TOOL,
                confidence=0.9,
                metadata={"is_bundler": True}
            ),
        }

    def _init_language_patterns(self) -> Dict[str, List[str]]:
        """Initialize language-specific patterns."""
        return {
            "python": [r"def\s+\w+\s*\(", r"class\s+\w+\s*\(", r"import\s+\w+", r"from\s+\w+\s+import"],
            "javascript": [r"function\s+\w+\s*\(", r"const\s+\w+\s*=", r"let\s+\w+\s*=", r"var\s+\w+\s*="],
            "typescript": [r"interface\s+\w+", r"type\s+\w+\s*=", r"as\s+\w+", r":\s*\w+"],
            "java": [r"public\s+class\s+\w+", r"import\s+\w+", r"package\s+\w+", r"@Override"],
            "go": [r"func\s+\w+\s*\(", r"package\s+\w+", r"import\s+\(", r"type\s+\w+\s+"],
            "rust": [r"fn\s+\w+\s*\(", r"use\s+::", r"let\s+mut\s+", r"struct\s+\w+"],
            "csharp": [r"public\s+class\s+\w+", r"using\s+\w+", r"namespace\s+\w+", r"void\s+\w+\s*\("],
            "cpp": [r"#include\s*<\w+>", r"class\s+\w+", r"std::", r"namespace\s+\w+"],
            "php": [r"<\?php", r"function\s+\w+\s*\(", r"class\s+\w+", r"\$\w+\s*="],
            "ruby": [r"def\s+\w+", r"class\s+\w+", r"require\s+", r"module\s+\w+"],
        }

    def _init_framework_patterns(self) -> Dict[str, List[str]]:
        """Initialize framework-specific patterns."""
        return {
            "react": [r"import.*React", r"from\s+['\"]react['\"]", r"React\.", r"useState"],
            "vue": [r"import.*vue", r"from\s+['\"]vue['\"]", r"Vue\.", r"<template>"],
            "angular": [r"@Component", r"@NgModule", r"@Injectable", r"@angular/"],
            "fastapi": [r"from\s+fastapi", r"FastAPI\(", r"@app\.", r"APIRouter"],
            "django": [r"from\s+django", r"django\.", r"models\.Model", r"views\."],
            "flask": [r"from\s+flask", r"Flask\(", r"@app\.route", r"render_template"],
            "express": [r"require\(['\"]express['\"]", r"express\(\)", r"app\.get", r"app\.post"],
            "spring": [r"@SpringBootApplication", r"@RestController", r"@Service", r"org\.springframework"],
        }

    def _init_database_patterns(self) -> Dict[str, List[str]]:
        """Initialize database-specific patterns."""
        return {
            "postgresql": [r"postgresql", r"psycopg2", r"pg8000", r"postgres"],
            "mysql": [r"mysql", r"pymysql", r"mysql2", r"mysql-connector"],
            "mongodb": [r"mongodb", r"pymongo", r"mongoose", r"mongoengine"],
            "redis": [r"redis", r"redis-py", r"ioredis", r"redis-client"],
            "sqlite": [r"sqlite", r"sqlite3", r"\.db$", r"\.sqlite$"],
            "elasticsearch": [r"elasticsearch", r"elasticsearch-py", r"@elastic/elasticsearch"],
        }

    def _init_build_tool_patterns(self) -> Dict[str, List[str]]:
        """Initialize build tool-specific patterns."""
        return {
            "npm": [r"npm\s+", r"package\.json"],
            "yarn": [r"yarn\s+", r"yarn\.lock"],
            "pip": [r"pip\s+", r"requirements\.txt", r"Pipfile"],
            "maven": [r"mvn\s+", r"pom\.xml"],
            "gradle": [r"gradle\s+", r"build\.gradle"],
            "cargo": [r"cargo\s+", r"Cargo\.toml"],
            "docker": [r"docker\s+", r"FROM\s+", r"RUN\s+", r"COPY\s+"],
            "webpack": [r"webpack", r"webpack\.config", r"module\.exports"],
            "vite": [r"vite", r"vite\.config", r"import\.vite"],
        }

    async def detect_from_files(self, file_paths: List[str]) -> Dict[str, Technology]:
        """Detect technologies from a list of file paths."""
        detected_tech = {}
        
        # Group files by type for efficiency
        file_groups = self._group_files_by_type(file_paths)
        
        # Detect from file names first (fastest)
        for file_path in file_paths:
            tech_from_file = self._detect_from_filename(file_path)
            for tech_name, tech in tech_from_file.items():
                if tech_name not in detected_tech:
                    detected_tech[tech_name] = tech
                else:
                    # Merge with existing detection
                    detected_tech[tech_name].usage_count += tech.usage_count
                    detected_tech[tech_name].files_involved.extend(tech.files_involved)
        
        # Detect from file content for higher confidence
        for file_type, files in file_groups.items():
            if file_type in ["text", "code"]:
                for file_path in files:
                    try:
                        tech_from_content = await self._detect_from_file_content(file_path)
                        for tech_name, tech in tech_from_content.items():
                            if tech_name not in detected_tech:
                                detected_tech[tech_name] = tech
                            else:
                                # Update confidence and merge
                                detected_tech[tech_name].confidence = max(
                                    detected_tech[tech_name].confidence, 
                                    tech.confidence
                                )
                                detected_tech[tech_name].usage_count += tech.usage_count
                                detected_tech[tech_name].files_involved.extend(tech.files_involved)
                    except Exception:
                        continue
        
        return detected_tech

    def _group_files_by_type(self, file_paths: List[str]) -> Dict[str, List[str]]:
        """Group files by type for efficient processing."""
        groups = {
            "text": [],
            "code": [],
            "config": [],
            "binary": []
        }
        
        text_extensions = {".txt", ".md", ".rst", ".log", ".json", ".yaml", ".yml", ".toml", ".xml"}
        code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cs", ".cpp", ".hpp", ".php", ".rb"}
        config_extensions = {".json", ".yaml", ".yml", ".toml", ".xml", ".ini", ".cfg", ".conf"}
        
        for file_path in file_paths:
            ext = Path(file_path).suffix.lower()
            
            if ext in code_extensions:
                groups["code"].append(file_path)
            elif ext in config_extensions:
                groups["config"].append(file_path)
            elif ext in text_extensions:
                groups["text"].append(file_path)
            else:
                groups["binary"].append(file_path)
        
        return groups

    def _detect_from_filename(self, file_path: str) -> Dict[str, Technology]:
        """Detect technologies from filename only."""
        detected = {}
        filename = Path(file_path).name.lower()
        
        for tech_name, pattern in self.detection_patterns.items():
            for file_pattern in pattern.file_patterns:
                if self._matches_file_pattern(filename, file_pattern):
                    tech = self._create_technology_from_pattern(tech_name, pattern, file_path)
                    detected[tech_name] = tech
                    break
        
        return detected

    def _matches_file_pattern(self, filename: str, pattern: str) -> bool:
        """Check if filename matches a pattern."""
        if pattern.startswith("*."):
            return filename.endswith(pattern[1:])
        elif pattern.startswith("*") and "." in pattern:
            # Handle patterns like *.py, *.js, etc.
            return filename.endswith(pattern[1:])
        else:
            return pattern in filename

    async def _detect_from_file_content(self, file_path: str) -> Dict[str, Technology]:
        """Detect technologies from file content."""
        detected = {}
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for tech_name, pattern in self.detection_patterns.items():
                matches = 0
                for regex_pattern in pattern.patterns:
                    if re.search(regex_pattern, content, re.IGNORECASE):
                        matches += 1
                
                if matches > 0:
                    confidence = min(0.95, pattern.confidence + (matches * 0.05))
                    tech = self._create_technology_from_pattern(
                        tech_name, pattern, file_path, confidence
                    )
                    detected[tech_name] = tech
        
        except (IOError, UnicodeDecodeError):
            pass
        
        return detected

    def _create_technology_from_pattern(self, 
                                       tech_name: str, 
                                       pattern: DetectionPattern,
                                       file_path: str,
                                       confidence: Optional[float] = None) -> Technology:
        """Create a technology object from detection pattern."""
        # Determine technology type
        if pattern.category == TechnologyCategory.FRAMEWORK:
            tech = Framework(
                name=pattern.name,
                category=pattern.category,
                confidence=confidence or pattern.confidence,
                files_involved=[file_path],
                usage_count=1,
                metadata=pattern.metadata or {}
            )
        elif pattern.category == TechnologyCategory.DATABASE:
            tech = Database(
                name=pattern.name,
                category=pattern.category,
                confidence=confidence or pattern.confidence,
                files_involved=[file_path],
                usage_count=1,
                metadata=pattern.metadata or {}
            )
        elif pattern.category == TechnologyCategory.BUILD_TOOL:
            tech = BuildTool(
                name=pattern.name,
                category=pattern.category,
                confidence=confidence or pattern.confidence,
                files_involved=[file_path],
                usage_count=1,
                metadata=pattern.metadata or {}
            )
        else:
            tech = Technology(
                name=pattern.name,
                category=pattern.category,
                confidence=confidence or pattern.confidence,
                files_involved=[file_path],
                usage_count=1,
                metadata=pattern.metadata or {}
            )
        
        return tech

    async def detect_version(self, tech_name: str, file_paths: List[str]) -> Optional[str]:
        """Detect version of a specific technology."""
        version_patterns = {
            "python": [r"python\s+(\d+\.\d+)", r"python:\s*(\d+\.\d+)"],
            "node": [r"node\s*['\"]?(\d+\.\d+\.\d+)", r"node:\s*['\"]?(\d+\.\d+\.\d+)"],
            "npm": [r"npm\s*['\"]?(\d+\.\d+\.\d+)", r"\"npm\":\s*\"(\d+\.\d+\.\d+)"],
            "react": [r"\"react\":\s*\"(\d+\.\d+\.\d+)"],
            "vue": [r"\"vue\":\s*\"(\d+\.\d+\.\d+)"],
            "django": [r"django==(\d+\.\d+\.\d+)", r"django\s*>=\s*(\d+\.\d+)"],
            "fastapi": [r"fastapi==(\d+\.\d+\.\d+)", r"fastapi\s*>=\s*(\d+\.\d+)"],
        }
        
        if tech_name not in version_patterns:
            return None
        
        patterns = version_patterns[tech_name]
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return match.group(1)
            
            except (IOError, UnicodeDecodeError):
                continue
        
        return None

    def calculate_confidence_score(self, detected_tech: Dict[str, Technology]) -> float:
        """Calculate overall confidence score for detection."""
        if not detected_tech:
            return 0.0
        
        total_confidence = sum(tech.confidence for tech in detected_tech.values())
        avg_confidence = total_confidence / len(detected_tech)
        
        # Boost confidence if we detected core technologies
        has_language = any(tech.category == TechnologyCategory.LANGUAGE for tech in detected_tech.values())
        has_build_tool = any(tech.category == TechnologyCategory.BUILD_TOOL for tech in detected_tech.values())
        
        if has_language and has_build_tool:
            avg_confidence = min(1.0, avg_confidence + 0.1)
        
        return avg_confidence

    def filter_low_confidence(self, detected_tech: Dict[str, Technology], threshold: float = 0.5) -> Dict[str, Technology]:
        """Filter out technologies with low confidence."""
        return {
            name: tech for name, tech in detected_tech.items()
            if tech.confidence >= threshold
        }

    def merge_duplicate_detections(self, detected_tech: Dict[str, Technology]) -> Dict[str, Technology]:
        """Merge duplicate technology detections."""
        merged = {}
        
        for tech_name, tech in detected_tech.items():
            if tech_name in merged:
                # Merge with existing
                existing = merged[tech_name]
                existing.confidence = max(existing.confidence, tech.confidence)
                existing.usage_count += tech.usage_count
                existing.files_involved.extend(tech.files_involved)
                existing.metadata.update(tech.metadata)
            else:
                merged[tech_name] = tech
        
        return merged
