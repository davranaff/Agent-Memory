"""Models for error prevention system."""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Categories of errors."""
    SYNTAX = "syntax"
    LOGIC = "logic"
    RUNTIME = "runtime"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TYPE = "type"
    IMPORT = "import"
    MEMORY = "memory"
    CONCURRENCY = "concurrency"


class ErrorIssue(BaseModel):
    """Error issue detected by the prevention system."""
    id: str = Field(..., description="Unique issue identifier")
    title: str = Field(..., description="Issue title")
    description: str = Field(..., description="Detailed description")
    severity: ErrorSeverity = Field(..., description="Error severity")
    category: ErrorCategory = Field(..., description="Error category")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    column_number: Optional[int] = Field(None, description="Column number where issue occurs")
    code_snippet: Optional[str] = Field(None, description="Code snippet containing the issue")
    suggestion: str = Field(..., description="Suggested fix")
    auto_fix: bool = Field(False, description="Can be automatically fixed")
    confidence: float = Field(..., description="Confidence score (0-1)")
    rule_name: str = Field(..., description="Name of the rule that detected this")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ErrorPreventionRequest(BaseModel):
    """Error prevention request."""
    code: str = Field(..., description="Code to analyze")
    language: str = Field(..., description="Programming language")
    file_path: Optional[str] = Field(None, description="File path for context")
    check_categories: List[ErrorCategory] = Field(default_factory=list, description="Categories to check")
    severity_threshold: ErrorSeverity = Field(ErrorSeverity.LOW, description="Minimum severity to report")
    include_auto_fixes: bool = Field(True, description="Include auto-fix suggestions")
    max_issues: int = Field(50, description="Maximum number of issues to return")


class ErrorPreventionResponse(BaseModel):
    """Error prevention response."""
    success: bool = Field(..., description="Request success status")
    issues: List[ErrorIssue] = Field(..., description="Detected issues")
    total_issues: int = Field(..., description="Total number of issues found")
    severity_distribution: Dict[str, int] = Field(default_factory=dict, description="Issues by severity")
    category_distribution: Dict[str, int] = Field(default_factory=dict, description="Issues by category")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    auto_fixes_available: int = Field(..., description="Number of auto-fixable issues")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class PreventionRule(BaseModel):
    """Error prevention rule."""
    name: str = Field(..., description="Rule name")
    description: str = Field(..., description="Rule description")
    category: ErrorCategory = Field(..., description="Error category")
    severity: ErrorSeverity = Field(..., description="Default severity")
    pattern: str = Field(..., description="Error pattern (regex)")
    suggestion: str = Field(..., description="Suggested fix")
    auto_fix: bool = Field(False, description="Can auto-fix")
    language: str = Field(..., description="Programming language")
    enabled: bool = Field(True, description="Rule enabled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AutoFix(BaseModel):
    """Automatic fix for an error."""
    issue_id: str = Field(..., description="ID of the issue to fix")
    original_code: str = Field(..., description="Original code")
    fixed_code: str = Field(..., description="Fixed code")
    description: str = Field(..., description="Description of the fix")
    confidence: float = Field(..., description="Confidence in the fix")
    applied: bool = Field(False, description="Whether the fix was applied")
