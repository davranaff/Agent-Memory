"""Git-related models for Agent Brain."""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PreCommitCheckRequest(BaseModel):
    """Pre-commit check request."""
    files: List[Dict[str, Any]] = Field(default_factory=list, description="Files to check")
    project_path: str = Field(..., description="Project path")
    checks: List[str] = Field(default=["quality", "patterns", "security"], description="Checks to run")
    fail_on_error: bool = Field(True, description="Fail on any error")


class CodeReviewRequest(BaseModel):
    """Code review request."""
    code: str = Field(..., description="Code to review")
    language: str = Field(..., description="Programming language")
    file_path: Optional[str] = Field(None, description="File path for context")
    review_type: str = Field("comprehensive", description="Review type: basic, comprehensive, security")
    include_suggestions: bool = Field(True, description="Include improvement suggestions")


class EnhancedProjectAnalysisRequest(BaseModel):
    """Enhanced project analysis request."""
    project_path: str = Field(..., description="Path to the project")
    include_semantic_analysis: bool = Field(True, description="Include semantic analysis")
    include_pattern_detection: bool = Field(True, description="Include pattern detection")
    include_recommendations: bool = Field(True, description="Include improvement recommendations")
    analysis_depth: str = Field("standard", description="Analysis depth: basic, standard, deep")


class CodeSearchRequest(BaseModel):
    """Enhanced code search request."""
    query: str = Field(..., description="Search query")
    language: Optional[str] = Field(None, description="Programming language filter")
    context: Optional[str] = Field(None, description="Code context")
    include_patterns: bool = Field(True, description="Include pattern matches")
    include_examples: bool = Field(True, description="Include usage examples")
    max_results: int = Field(10, description="Maximum results")
    min_confidence: float = Field(0.3, description="Minimum confidence")


class PatternSuggestionRequest(BaseModel):
    """Pattern suggestion request."""
    code_snippet: str = Field(..., description="Code snippet to analyze")
    language: str = Field(..., description="Programming language")
    context: Optional[str] = Field(None, description="Additional context")
    include_alternatives: bool = Field(True, description="Include alternative patterns")
