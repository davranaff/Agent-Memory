"""Models for context-aware autocomplete system."""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class SuggestionType(str, Enum):
    """Types of autocomplete suggestions."""
    FUNCTION = "function"
    VARIABLE = "variable"
    CLASS = "class"
    METHOD = "method"
    IMPORT = "import"
    KEYWORD = "keyword"
    SNIPPET = "snippet"
    PATTERN = "pattern"
    CUSTOM = "custom"


class SuggestionPriority(str, Enum):
    """Priority levels for suggestions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CodeContext(BaseModel):
    """Code context for autocomplete."""
    language: str = Field(..., description="Programming language")
    file_path: Optional[str] = Field(None, description="File path")
    cursor_position: int = Field(..., description="Cursor position in code")
    current_line: str = Field(..., description="Current line content")
    preceding_text: str = Field(..., description="Text before cursor")
    following_text: str = Field(..., description="Text after cursor")
    scope: Dict[str, Any] = Field(default_factory=dict, description="Current scope information")
    imports: List[str] = Field(default_factory=list, description="Available imports")
    variables: List[str] = Field(default_factory=list, description="Available variables")
    functions: List[str] = Field(default_factory=list, description="Available functions")
    classes: List[str] = Field(default_factory=list, description="Available classes")


class Suggestion(BaseModel):
    """Autocomplete suggestion."""
    text: str = Field(..., description="Suggestion text")
    display_text: str = Field(..., description="Text to display")
    type: SuggestionType = Field(..., description="Type of suggestion")
    priority: SuggestionPriority = Field(..., description="Priority level")
    description: Optional[str] = Field(None, description="Description of suggestion")
    documentation: Optional[str] = Field(None, description="Full documentation")
    insert_text: Optional[str] = Field(None, description="Text to insert")
    confidence: float = Field(..., description="Confidence score (0-1)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class AutocompleteRequest(BaseModel):
    """Autocomplete request."""
    context: CodeContext = Field(..., description="Code context")
    query: str = Field(..., description="Current query/prefix")
    max_results: int = Field(10, description="Maximum number of results")
    include_snippets: bool = Field(True, description="Include code snippets")
    include_patterns: bool = Field(True, description="Include pattern suggestions")
    language_specific: bool = Field(True, description="Language-specific suggestions")


class AutocompleteResponse(BaseModel):
    """Autocomplete response."""
    success: bool = Field(..., description="Request success status")
    suggestions: List[Suggestion] = Field(..., description="Autocomplete suggestions")
    context_used: bool = Field(..., description="Whether context was used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")


class CompletionPattern(BaseModel):
    """Code completion pattern."""
    name: str = Field(..., description="Pattern name")
    trigger: str = Field(..., description="Trigger string")
    description: str = Field(..., description="Pattern description")
    template: str = Field(..., description="Code template")
    language: str = Field(..., description="Programming language")
    category: str = Field(..., description="Pattern category")
    variables: List[str] = Field(default_factory=list, description="Template variables")


class ErrorPreventionRule(BaseModel):
    """Error prevention rule."""
    name: str = Field(..., description="Rule name")
    pattern: str = Field(..., description="Error pattern")
    suggestion: str = Field(..., description="Prevention suggestion")
    severity: Literal["low", "medium", "high", "critical"] = Field(..., description="Severity level")
    language: str = Field(..., description="Programming language")
    auto_fix: bool = Field(False, description="Can auto-fix the error")
