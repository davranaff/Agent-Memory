"""Code Review Assistant for Agent Brain."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import ast
from pathlib import Path

from app.models.git import CodeReviewRequest
from app.memory.embeddings import OllamaEmbeddingProvider
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class ReviewSeverity(str, Enum):
    """Severity levels for code review issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewCategory(str, Enum):
    """Categories for code review issues."""
    STYLE = "style"
    LOGIC = "logic"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    DOCUMENTATION = "documentation"
    TESTING = "testing"


@dataclass
class ReviewIssue:
    """A code review issue."""
    line_number: int
    severity: ReviewSeverity
    category: ReviewCategory
    message: str
    suggestion: str
    code_snippet: str
    rule_name: Optional[str] = None
    confidence: float = 1.0


@dataclass
class ReviewResult:
    """Complete code review result."""
    file_path: str
    language: str
    overall_score: float
    issues: List[ReviewIssue]
    suggestions: List[str]
    metrics: Dict[str, Any]
    summary: str


class CodeReviewAssistant:
    """Automated code review assistant."""
    
    def __init__(self) -> None:
        self.embedding_provider = OllamaEmbeddingProvider(
            base_url=get_settings().ollama_base_url,
            model="nomic-embed-text",
            dim=768
        )
        self._review_rules = self._initialize_review_rules()
    
    async def review_code(self, request: CodeReviewRequest) -> ReviewResult:
        """Perform comprehensive code review."""
        try:
            # Parse and analyze code
            code_analysis = self._analyze_code(request.code, request.language)
            
            # Detect issues
            issues = await self._detect_issues(request, code_analysis)
            
            # Calculate metrics
            metrics = self._calculate_metrics(request.code, issues, code_analysis)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(issues, metrics, request.language)
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(issues, metrics)
            
            # Generate summary
            summary = self._generate_summary(issues, metrics, overall_score)
            
            return ReviewResult(
                file_path=request.file_path or "unknown",
                language=request.language,
                overall_score=overall_score,
                issues=issues,
                suggestions=suggestions,
                metrics=metrics,
                summary=summary
            )
            
        except Exception as e:
            logger.error(f"Error in code review: {e}")
            raise
    
    def _analyze_code(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code structure and properties."""
        lines = code.split('\n')
        
        analysis = {
            "line_count": len(lines),
            "character_count": len(code),
            "language": language,
            "structure": {},
            "complexity": {},
            "patterns": {}
        }
        
        # Language-specific analysis
        if language == "python":
            analysis.update(self._analyze_python_code(code))
        elif language in ["javascript", "typescript"]:
            analysis.update(self._analyze_javascript_code(code))
        elif language == "java":
            analysis.update(self._analyze_java_code(code))
        else:
            analysis.update(self._analyze_generic_code(code))
        
        return analysis
    
    def _analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Analyze Python code structure."""
        try:
            tree = ast.parse(code)
            
            functions = []
            classes = []
            imports = []
            complexity_indicators = {
                "nested_loops": 0,
                "nested_conditions": 0,
                "try_blocks": 0,
                "list_comprehensions": 0
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args_count": len(node.args.args),
                        "decorators": len(node.decorator_list),
                        "returns": ast.unparse(node.returns) if node.returns else None
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                        "bases": [ast.unparse(base) for base in node.bases]
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend([alias.name for alias in node.names])
                    else:
                        imports.append(node.module or "")
                elif isinstance(node, ast.For):
                    complexity_indicators["nested_loops"] += 1
                elif isinstance(node, ast.If):
                    complexity_indicators["nested_conditions"] += 1
                elif isinstance(node, ast.Try):
                    complexity_indicators["try_blocks"] += 1
                elif isinstance(node, ast.ListComp):
                    complexity_indicators["list_comprehensions"] += 1
            
            return {
                "structure": {
                    "functions": functions,
                    "classes": classes,
                    "imports": imports
                },
                "complexity": complexity_indicators
            }
            
        except SyntaxError:
            return {"structure": {}, "complexity": {}, "error": "Syntax error in code"}
    
    def _analyze_javascript_code(self, code: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code structure."""
        lines = code.split('\n')
        
        functions = []
        classes = []
        imports = []
        complexity_indicators = {
            "nested_loops": 0,
            "nested_conditions": 0,
            "try_blocks": 0,
            "arrow_functions": 0
        }
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Function detection
            if line.startswith('function ') or 'function ' in line:
                func_match = re.search(r'function\s+(\w+)', line)
                if func_match:
                    functions.append({
                        "name": func_match.group(1),
                        "line": i,
                        "type": "function"
                    })
            
            # Arrow function detection
            if '=>' in line:
                arrow_match = re.search(r'(\w+)\s*=', line.split('=>')[0])
                if arrow_match:
                    complexity_indicators["arrow_functions"] += 1
                    functions.append({
                        "name": arrow_match.group(1),
                        "line": i,
                        "type": "arrow_function"
                    })
            
            # Class detection
            if line.startswith('class '):
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match:
                    classes.append({
                        "name": class_match.group(1),
                        "line": i
                    })
            
            # Import detection
            if line.startswith('import ') or line.startswith('const ') and 'require' in line:
                imports.append(line)
            
            # Complexity indicators
            complexity_indicators["nested_loops"] += line.count('for') + line.count('while')
            complexity_indicators["nested_conditions"] += line.count('if')
            complexity_indicators["try_blocks"] += line.count('try')
        
        return {
            "structure": {
                "functions": functions,
                "classes": classes,
                "imports": imports
            },
            "complexity": complexity_indicators
        }
    
    def _analyze_java_code(self, code: str) -> Dict[str, Any]:
        """Analyze Java code structure."""
        lines = code.split('\n')
        
        classes = []
        methods = []
        imports = []
        complexity_indicators = {
            "nested_loops": 0,
            "nested_conditions": 0,
            "try_blocks": 0
        }
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Class detection
            if re.match(r'(public|private|protected)?\s*class\s+\w+', line):
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match:
                    classes.append({
                        "name": class_match.group(1),
                        "line": i
                    })
            
            # Method detection
            if re.match(r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', line):
                method_match = re.search(r'\w+\s+(\w+)\s*\(', line)
                if method_match:
                    methods.append({
                        "name": method_match.group(1),
                        "line": i
                    })
            
            # Import detection
            if line.startswith('import ') or line.startswith('package '):
                imports.append(line)
            
            # Complexity indicators
            complexity_indicators["nested_loops"] += line.count('for') + line.count('while')
            complexity_indicators["nested_conditions"] += line.count('if')
            complexity_indicators["try_blocks"] += line.count('try')
        
        return {
            "structure": {
                "classes": classes,
                "methods": methods,
                "imports": imports
            },
            "complexity": complexity_indicators
        }
    
    def _analyze_generic_code(self, code: str) -> Dict[str, Any]:
        """Generic code analysis for unknown languages."""
        lines = code.split('\n')
        
        complexity_indicators = {
            "nested_loops": 0,
            "nested_conditions": 0,
            "functions": 0
        }
        
        for line in lines:
            line = line.strip()
            complexity_indicators["nested_loops"] += line.count('for') + line.count('while')
            complexity_indicators["nested_conditions"] += line.count('if')
            complexity_indicators["functions"] += line.count('function') + line.count('def')
        
        return {
            "structure": {},
            "complexity": complexity_indicators
        }
    
    async def _detect_issues(self, request: CodeReviewRequest, analysis: Dict[str, Any]) -> List[ReviewIssue]:
        """Detect code issues based on review type."""
        issues = []
        
        # Common issues across all review types
        issues.extend(self._detect_common_issues(request.code, analysis))
        
        # Review type specific issues
        if request.review_type == "comprehensive":
            issues.extend(self._detect_comprehensive_issues(request.code, analysis))
        elif request.review_type == "security":
            issues.extend(self._detect_security_issues(request.code, analysis))
        elif request.review_type == "basic":
            issues.extend(self._detect_basic_issues(request.code, analysis))
        
        # Sort issues by severity
        issues.sort(key=lambda x: self._severity_priority(x.severity), reverse=True)
        
        return issues
    
    def _detect_common_issues(self, code: str, analysis: Dict[str, Any]) -> List[ReviewIssue]:
        """Detect common code issues."""
        issues = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Line length
            if len(line) > 120:
                issues.append(ReviewIssue(
                    line_number=i,
                    severity=ReviewSeverity.LOW,
                    category=ReviewCategory.STYLE,
                    message=f"Line too long ({len(line)} characters)",
                    suggestion="Break line into multiple lines",
                    code_snippet=line[:50] + "..." if len(line) > 50 else line
                ))
            
            # TODO/FIXME comments
            if "TODO" in line or "FIXME" in line:
                issues.append(ReviewIssue(
                    line_number=i,
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.MAINTAINABILITY,
                    message="TODO/FIXME comment found",
                    suggestion="Address the TODO item or create a ticket",
                    code_snippet=line
                ))
            
            # Magic numbers
            magic_numbers = re.findall(r'\b\d{2,}\b', line)
            if magic_numbers and not any(keyword in line.lower() for keyword in ['max', 'min', 'size', 'count', 'len']):
                for num in magic_numbers:
                    if int(num) > 10:  # Ignore small numbers
                        issues.append(ReviewIssue(
                            line_number=i,
                            severity=ReviewSeverity.LOW,
                            category=ReviewCategory.MAINTAINABILITY,
                            message=f"Magic number found: {num}",
                            suggestion="Use named constant instead of magic number",
                            code_snippet=line
                        ))
        
        return issues
    
    def _detect_comprehensive_issues(self, code: str, analysis: Dict[str, Any]) -> List[ReviewIssue]:
        """Detect comprehensive code issues."""
        issues = []
        lines = code.split('\n')
        
        complexity = analysis.get("complexity", {})
        
        # High complexity
        total_complexity = sum(complexity.values())
        if total_complexity > 10:
            issues.append(ReviewIssue(
                line_number=1,
                severity=ReviewSeverity.MEDIUM,
                category=ReviewCategory.COMPLEXITY,
                message=f"High complexity detected (score: {total_complexity})",
                suggestion="Consider breaking down complex logic into smaller functions",
                code_snippet="High complexity in code"
            ))
        
        # Nested loops
        if complexity.get("nested_loops", 0) > 2:
            issues.append(ReviewIssue(
                line_number=1,
                severity=ReviewSeverity.HIGH,
                category=ReviewCategory.COMPLEXITY,
                message=f"Too many nested loops ({complexity['nested_loops']})",
                suggestion="Extract nested loops into separate methods",
                code_snippet="Nested loops detected"
            ))
        
        # Missing documentation
        structure = analysis.get("structure", {})
        functions = structure.get("functions", [])
        classes = structure.get("classes", [])
        
        for func in functions:
            if not func.get("docstring") and func.get("args_count", 0) > 0:
                issues.append(ReviewIssue(
                    line_number=func["line"],
                    severity=ReviewSeverity.MEDIUM,
                    category=ReviewCategory.DOCUMENTATION,
                    message=f"Function '{func['name']}' missing docstring",
                    suggestion="Add docstring to document function purpose and parameters",
                    code_snippet=f"def {func['name']}(...)"
                ))
        
        return issues
    
    def _detect_security_issues(self, code: str, analysis: Dict[str, Any]) -> List[ReviewIssue]:
        """Detect security-related issues."""
        issues = []
        lines = code.split('\n')
        
        # Security patterns
        security_patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "Hardcoded token"),
            (r'eval\s*\(', "Use of eval()"),
            (r'exec\s*\(', "Use of exec()"),
            (r'shell\s*=\s*True', "Shell=True in subprocess"),
            (r'sql\s*\.\s*format\s*\(', "SQL injection risk"),
            (r'cursor\.execute\s*\(', "SQL injection risk"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, message in security_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ReviewIssue(
                        line_number=i,
                        severity=ReviewSeverity.HIGH,
                        category=ReviewCategory.SECURITY,
                        message=message,
                        suggestion="Use secure alternatives and environment variables",
                        code_snippet=line[:50] + "..." if len(line) > 50 else line
                    ))
        
        return issues
    
    def _detect_basic_issues(self, code: str, analysis: Dict[str, Any]) -> List[ReviewIssue]:
        """Detect basic code issues."""
        issues = []
        lines = code.split('\n')
        
        # Only check for critical issues in basic mode
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Critical security issues
            if "eval(" in line or "exec(" in line:
                issues.append(ReviewIssue(
                    line_number=i,
                    severity=ReviewSeverity.CRITICAL,
                    category=ReviewCategory.SECURITY,
                    message="Use of eval/exec detected",
                    suggestion="Avoid using eval/exec functions",
                    code_snippet=line
                ))
        
        return issues
    
    def _calculate_metrics(self, code: str, issues: List[ReviewIssue], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate code metrics."""
        lines = code.split('\n')
        
        metrics = {
            "line_count": len(lines),
            "character_count": len(code),
            "issue_count": len(issues),
            "severity_distribution": {
                "critical": len([i for i in issues if i.severity == ReviewSeverity.CRITICAL]),
                "high": len([i for i in issues if i.severity == ReviewSeverity.HIGH]),
                "medium": len([i for i in issues if i.severity == ReviewSeverity.MEDIUM]),
                "low": len([i for i in issues if i.severity == ReviewSeverity.LOW])
            },
            "category_distribution": {
                "style": len([i for i in issues if i.category == ReviewCategory.STYLE]),
                "logic": len([i for i in issues if i.category == ReviewCategory.LOGIC]),
                "security": len([i for i in issues if i.category == ReviewCategory.SECURITY]),
                "performance": len([i for i in issues if i.category == ReviewCategory.PERFORMANCE]),
                "maintainability": len([i for i in issues if i.category == ReviewCategory.MAINTAINABILITY]),
                "documentation": len([i for i in issues if i.category == ReviewCategory.DOCUMENTATION]),
                "testing": len([i for i in issues if i.category == ReviewCategory.TESTING])
            },
            "complexity_score": sum(analysis.get("complexity", {}).values()),
            "structure_metrics": {
                "functions": len(analysis.get("structure", {}).get("functions", [])),
                "classes": len(analysis.get("structure", {}).get("classes", [])),
                "imports": len(analysis.get("structure", {}).get("imports", []))
            }
        }
        
        return metrics
    
    def _generate_suggestions(self, issues: List[ReviewIssue], metrics: Dict[str, Any], language: str) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []
        
        # General suggestions based on issues
        if metrics["severity_distribution"]["critical"] > 0:
            suggestions.append("Address critical security issues immediately")
        
        if metrics["severity_distribution"]["high"] > 3:
            suggestions.append("Consider refactoring high-severity issues")
        
        if metrics["category_distribution"]["documentation"] > 2:
            suggestions.append("Improve code documentation")
        
        if metrics["complexity_score"] > 10:
            suggestions.append("Reduce code complexity by extracting methods")
        
        # Language-specific suggestions
        if language == "python":
            suggestions.extend([
                "Consider using type hints for better code clarity",
                "Add unit tests for critical functions",
                "Use f-strings for string formatting"
            ])
        elif language in ["javascript", "typescript"]:
            suggestions.extend([
                "Consider using ESLint for code quality",
                "Add JSDoc comments for functions",
                "Use const/let instead of var"
            ])
        elif language == "java":
            suggestions.extend([
                "Follow Java naming conventions",
                "Add proper exception handling",
                "Consider using modern Java features"
            ])
        
        # Remove duplicates
        suggestions = list(dict.fromkeys(suggestions))
        
        return suggestions[:5]  # Limit to top 5 suggestions
    
    def _calculate_overall_score(self, issues: List[ReviewIssue], metrics: Dict[str, Any]) -> float:
        """Calculate overall code quality score."""
        base_score = 100.0
        
        # Deduct points for issues
        severity_weights = {
            ReviewSeverity.CRITICAL: 20,
            ReviewSeverity.HIGH: 10,
            ReviewSeverity.MEDIUM: 5,
            ReviewSeverity.LOW: 2
        }
        
        for issue in issues:
            base_score -= severity_weights.get(issue.severity, 2)
        
        # Deduct points for high complexity
        if metrics["complexity_score"] > 15:
            base_score -= 10
        elif metrics["complexity_score"] > 10:
            base_score -= 5
        
        # Bonus for good structure
        if metrics["structure_metrics"]["functions"] > 0 and metrics["category_distribution"]["documentation"] == 0:
            base_score -= 5  # Penalty for missing documentation
        
        return max(0.0, base_score)
    
    def _generate_summary(self, issues: List[ReviewIssue], metrics: Dict[str, Any], overall_score: float) -> str:
        """Generate review summary."""
        if overall_score >= 90:
            quality = "excellent"
        elif overall_score >= 80:
            quality = "good"
        elif overall_score >= 70:
            quality = "fair"
        elif overall_score >= 60:
            quality = "poor"
        else:
            quality = "very poor"
        
        critical_count = metrics["severity_distribution"]["critical"]
        high_count = metrics["severity_distribution"]["high"]
        
        summary_parts = [
            f"Code quality is {quality} (score: {overall_score:.1f}/100)",
            f"Found {len(issues)} issues"
        ]
        
        if critical_count > 0:
            summary_parts.append(f"including {critical_count} critical issues")
        
        if high_count > 0:
            summary_parts.append(f"and {high_count} high-priority issues")
        
        return ". ".join(summary_parts) + "."
    
    def _severity_priority(self, severity: ReviewSeverity) -> int:
        """Get priority for severity level."""
        priorities = {
            ReviewSeverity.CRITICAL: 4,
            ReviewSeverity.HIGH: 3,
            ReviewSeverity.MEDIUM: 2,
            ReviewSeverity.LOW: 1
        }
        return priorities.get(severity, 1)
    
    def _initialize_review_rules(self) -> Dict[str, Any]:
        """Initialize review rules and configurations."""
        return {
            "max_line_length": 120,
            "max_complexity_score": 15,
            "require_docstrings": True,
            "security_patterns": [
                "password",
                "api_key",
                "secret",
                "token",
                "eval",
                "exec"
            ],
            "ignore_patterns": [
                "*.min.js",
                "*.bundle.js",
                "node_modules/*"
            ]
        }
