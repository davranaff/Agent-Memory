"""Project analyzer for extracting insights from scanned projects."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any

from .scanner import FileInfo, DirectoryInfo
from app.parsing import parse_file


class ProjectAnalyzer:
    """Analyzes scanned project structure to extract insights."""

    def __init__(self) -> None:
        self.framework_patterns = self._init_framework_patterns()
        self.architecture_patterns = self._init_architecture_patterns()
        self.database_patterns = self._init_database_patterns()

    def _init_framework_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns to detect frameworks."""
        return {
            "react": [
                r"import.*react", r"from\s+['\"]react['\"]", r"React\.",
                r"ReactDOM", r"jsx", r"tsx", r"\.jsx?$"
            ],
            "vue": [
                r"import.*vue", r"from\s+['\"]vue['\"]", r"Vue\.",
                r"<template>", r"<script>", r"<style>",
                r"\.vue$"
            ],
            "angular": [
                r"import.*@angular", r"@angular/", r"Component\(",
                r"@Component", r"NgModule", r"FormsModule"
            ],
            "fastapi": [
                r"from\s+fastapi", r"import\s+fastapi", r"FastAPI\(",
                r"@app\.", r"APIRouter", r"Depends"
            ],
            "django": [
                r"from\s+django", r"import\s+django", r"django\.",
                r"models\.Model", r"views\.", r"urls\.",
                r"settings\.py"
            ],
            "flask": [
                r"from\s+flask", r"import\s+flask", r"Flask\(",
                r"@app\.route", r"render_template", r"request\."
            ],
            "express": [
                r"require\(['\"]express['\"]", r"import.*express",
                r"express\(\)", r"app\.get", r"app\.post",
                r"router\."
            ],
            "spring": [
                r"@SpringBootApplication", r"@RestController", r"@Service",
                r"@Repository", r"@Entity", r"org\.springframework",
                r"spring-boot"
            ],
            "rails": [
                r"Rails\.application", r"ApplicationController", r"ActiveRecord",
                r"has_many", r"belongs_to", r"validates",
                r"config/routes\.rb"
            ]
        }

    def _init_architecture_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns to detect architecture types."""
        return {
            "microservices": [
                r"docker-compose", r"kubernetes", r"helm", r"istio",
                r"service-discovery", r"api-gateway", r"config-server",
                r"circuit-breaker", r"load-balancer"
            ],
            "serverless": [
                r"serverless\.yml", r"serverless\.json", r"aws\-lambda",
                r"azure\-functions", r"google\-cloud\-functions",
                r"vercel\.json", r"netlify\.toml", r"firebase\.json"
            ],
            "mvc": [
                r"models?/", r"views?/", r"controllers?/",
                r"Model\s+class", r"Controller\s+class", r"View\s+class",
                r"mvc", r"model-view-controller"
            ],
            "monolith": [
                r"app\.py", r"main\.py", r"server\.js", r"index\.js",
                r"single-page", r"monolithic", r"all-in-one"
            ],
            "event-driven": [
                r"kafka", r"rabbitmq", r"event-sourcing", r"cqrs",
                r"message-broker", r"pub-sub", r"event-bus"
            ]
        }

    def _init_database_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns to detect databases."""
        return {
            "postgresql": [
                r"postgresql", r"psycopg2", r"pg8000", r"sqlalchemy",
                r"postgres", r"pg_dump", r"psql"
            ],
            "mysql": [
                r"mysql", r"pymysql", r"mysql-connector", r"mysqldb",
                r"mysql2", r"sequelize"
            ],
            "mongodb": [
                r"mongodb", r"pymongo", r"mongoose", r"mongoengine",
                r"mongo-client"
            ],
            "redis": [
                r"redis", r"redis-py", r"ioredis", r"redis-client",
                r"redis-cluster"
            ],
            "sqlite": [
                r"sqlite", r"sqlite3", r"sqlalchemy.*sqlite",
                r"\.db$", r"\.sqlite$", r"\.sqlite3$"
            ],
            "elasticsearch": [
                r"elasticsearch", r"elasticsearch-py", r"elastic",
                r"es-client", r"elasticsearch-client"
            ]
        }

    def detect_technology_stack(self, files: List[FileInfo]) -> Dict[str, List[str]]:
        """Detect the technology stack from files."""
        detected = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "build_tools": [],
            "testing_tools": [],
            "package_managers": []
        }

        # Language distribution
        language_counter = Counter(f.language for f in files if f.language)
        detected["languages"] = [lang for lang, _ in language_counter.most_common()]

        # Detect frameworks
        framework_matches = defaultdict(int)
        for file_info in files:
            if file_info.is_binary or file_info.is_generated:
                continue
            
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for framework, patterns in self.framework_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                framework_matches[framework] += 1
                                break
            except (IOError, UnicodeDecodeError):
                continue

        detected["frameworks"] = [fw for fw, count in framework_matches.items() if count > 0]

        # Detect databases
        database_matches = defaultdict(int)
        for file_info in files:
            if file_info.is_binary or file_info.is_generated:
                continue
            
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for db, patterns in self.database_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                database_matches[db] += 1
                                break
            except (IOError, UnicodeDecodeError):
                continue

        detected["databases"] = [db for db, count in database_matches.items() if count > 0]

        # Detect build tools from file names and content
        build_tool_patterns = {
            "docker": [r"dockerfile", r"\.dockerfile$", r"docker-compose"],
            "webpack": [r"webpack\.config", r"webpack\.", r"\.webpackrc"],
            "vite": [r"vite\.config", r"vite\."],
            "gradle": [r"build\.gradle", r"gradle\.wrapper"],
            "maven": [r"pom\.xml", r"maven-", r"\.m2/"],
            "npm": [r"package\.json", r"npm-", r"\.npmrc"],
            "yarn": [r"yarn\.lock", r"yarn\.", r"\.yarnrc"],
            "pip": [r"requirements\.txt", r"pipfile", r"pyproject\.toml"],
            "cargo": [r"cargo\.toml", r"cargo\.lock"],
            "cmake": [r"cmakelists\.txt", r"cmake"],
            "makefile": [r"makefile", r"\.mk$", r"make\."]
        }

        build_tool_matches = defaultdict(int)
        for file_info in files:
            filename = file_info.path.lower()
            
            for tool, patterns in build_tool_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, filename, re.IGNORECASE):
                        build_tool_matches[tool] += 1
                        break

        detected["build_tools"] = [tool for tool, count in build_tool_matches.items() if count > 0]

        # Detect testing tools
        testing_patterns = {
            "pytest": [r"pytest", r"test_", r"_test\.py"],
            "jest": [r"jest", r"\.test\.js", r"\.spec\.js"],
            "mocha": [r"mocha", r"describe\(", r"it\("],
            "junit": [r"@Test", r"junit", r"testng"],
            "rspec": [r"rspec", r"describe\s+", r"it\s+"],
            "go-test": [r"testing\.T", r"func Test", r"\.go$"]
        }

        testing_matches = defaultdict(int)
        for file_info in files:
            if not file_info.is_test:
                continue
                
            filename = file_info.path.lower()
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for tool, patterns in testing_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE) or re.search(pattern, filename, re.IGNORECASE):
                                testing_matches[tool] += 1
                                break
            except (IOError, UnicodeDecodeError):
                continue

        detected["testing_tools"] = [tool for tool, count in testing_matches.items() if count > 0]

        # Detect package managers
        package_manager_files = {
            "npm": ["package.json", "package-lock.json"],
            "yarn": ["yarn.lock", "package.json"],
            "pip": ["requirements.txt", "Pipfile", "pyproject.toml"],
            "conda": ["environment.yml", "conda.yml"],
            "cargo": ["Cargo.toml", "Cargo.lock"],
            "maven": ["pom.xml"],
            "gradle": ["build.gradle"],
            "composer": ["composer.json"],
            "nuget": ["packages.config", "*.csproj"],
            "go-mod": ["go.mod", "go.sum"]
        }

        for manager, files_list in package_manager_files.items():
            for file_info in files:
                if any(file_info.path.endswith(f) for f in files_list):
                    if manager not in detected["package_managers"]:
                        detected["package_managers"].append(manager)

        return detected

    def detect_architecture_type(self, files: List[FileInfo], directories: List[DirectoryInfo]) -> Optional[str]:
        """Detect the architectural pattern of the project."""
        architecture_scores = defaultdict(int)

        # Analyze directory structure
        dir_names = [Path(d.path).name.lower() for d in directories]
        
        # Check for microservices patterns
        if any("service" in name or "microservice" in name for name in dir_names):
            architecture_scores["microservices"] += 3
        if any("docker" in name or "k8s" in name or "kube" in name for name in dir_names):
            architecture_scores["microservices"] += 2

        # Check for serverless patterns
        serverless_files = ["serverless.yml", "serverless.json", "vercel.json", "netlify.toml"]
        if any(any(f.path.endswith(sf) for sf in serverless_files) for f in files):
            architecture_scores["serverless"] += 3

        # Check for MVC patterns
        mvc_dirs = ["model", "view", "controller", "models", "views", "controllers"]
        mvc_score = sum(1 for pattern in mvc_dirs if any(pattern in name for name in dir_names))
        if mvc_score >= 2:
            architecture_scores["mvc"] += mvc_score

        # Check for monolith patterns
        if len([f for f in files if f.language]) > 100 and architecture_scores["microservices"] < 3:
            architecture_scores["monolith"] += 2

        # Analyze file content for architecture patterns
        for file_info in files[:50]:  # Sample first 50 files for performance
            if file_info.is_binary or file_info.is_generated:
                continue
            
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    for arch, patterns in self.architecture_patterns.items():
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                architecture_scores[arch] += 1
                                break
            except (IOError, UnicodeDecodeError):
                continue

        # Return architecture with highest score
        if architecture_scores:
            return max(architecture_scores.items(), key=lambda x: x[1])[0]
        
        return None

    def analyze_project_complexity(self, files: List[FileInfo], directories: List[DirectoryInfo]) -> Dict[str, Any]:
        """Analyze project complexity metrics."""
        total_files = len(files)
        total_dirs = len(directories)
        source_files = [f for f in files if f.language and not f.is_binary]
        
        # Language diversity
        languages = set(f.language for f in source_files if f.language)
        
        # File size distribution
        file_sizes = [f.size_bytes for f in files]
        avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        
        # Directory depth
        max_depth = max(len(Path(d.relative_path).parts) for d in directories) if directories else 0
        
        # Configuration complexity
        config_files = [f for f in files if f.is_config]
        test_files = [f for f in files if f.is_test]
        
        # Calculate complexity score (1-10)
        complexity_score = 1
        
        # Base score for file count
        if total_files > 1000:
            complexity_score += 2
        elif total_files > 500:
            complexity_score += 1
        
        # Language diversity
        if len(languages) > 5:
            complexity_score += 2
        elif len(languages) > 3:
            complexity_score += 1
        
        # Directory structure complexity
        if max_depth > 8:
            complexity_score += 2
        elif max_depth > 5:
            complexity_score += 1
        
        # Configuration complexity
        if len(config_files) > 20:
            complexity_score += 1
        
        # Test coverage indicator
        if len(test_files) > 0:
            test_ratio = len(test_files) / len(source_files) if source_files else 0
            if test_ratio > 0.3:
                complexity_score -= 1  # Well-tested projects are less complex to maintain
        
        complexity_score = max(1, min(10, complexity_score))

        return {
            "complexity_score": complexity_score,
            "total_files": total_files,
            "total_directories": total_dirs,
            "source_files": len(source_files),
            "languages_count": len(languages),
            "language_diversity": list(languages),
            "max_directory_depth": max_depth,
            "config_files_count": len(config_files),
            "test_files_count": len(test_files),
            "test_ratio": len(test_files) / len(source_files) if source_files else 0,
            "average_file_size_bytes": avg_file_size
        }

    def extract_project_metadata(self, files: List[FileInfo]) -> Dict[str, Any]:
        """Extract project metadata from common files."""
        metadata = {
            "name": None,
            "version": None,
            "description": None,
            "author": None,
            "license": None,
            "repository": None,
            "keywords": []
        }

        # Look for package.json
        package_json = next((f for f in files if f.path.endswith("package.json")), None)
        if package_json:
            try:
                with open(package_json.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata.update({
                        "name": data.get("name"),
                        "version": data.get("version"),
                        "description": data.get("description"),
                        "author": str(data.get("author", "")),
                        "license": data.get("license"),
                        "repository": str(data.get("repository", {}).get("url", "")) if isinstance(data.get("repository"), dict) else str(data.get("repository", "")),
                        "keywords": data.get("keywords", [])
                    })
            except (json.JSONDecodeError, IOError):
                pass

        # Look for pyproject.toml
        pyproject = next((f for f in files if f.path.endswith("pyproject.toml")), None)
        if pyproject:
            try:
                import toml
                with open(pyproject.path, 'r', encoding='utf-8') as f:
                    data = toml.load(f)
                    project_data = data.get("project", data.get("tool", {}).get("poetry", {}))
                    metadata.update({
                        "name": metadata["name"] or project_data.get("name"),
                        "version": metadata["version"] or project_data.get("version"),
                        "description": metadata["description"] or project_data.get("description"),
                        "authors": project_data.get("authors", []),
                        "license": metadata["license"] or project_data.get("license")
                    })
            except Exception:
                pass

        # Look for README
        readme = next((f for f in files if f.is_documentation and "readme" in f.path.lower()), None)
        if readme:
            try:
                with open(readme.path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract first line as description if not found
                    if not metadata["description"]:
                        first_line = content.split('\n')[0].strip()
                        if first_line and not first_line.startswith('#'):
                            metadata["description"] = first_line[:200]
            except IOError:
                pass

        return metadata
