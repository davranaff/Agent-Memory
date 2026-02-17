"""Context-aware autocomplete system for Agent Brain."""

from __future__ import annotations

from .engine import AutocompleteEngine
from .context import CodeContext
from .suggestions import SuggestionEngine
from .models import AutocompleteRequest, AutocompleteResponse, Suggestion

__all__ = [
    "AutocompleteEngine",
    "CodeContext", 
    "SuggestionEngine",
    "AutocompleteRequest",
    "AutocompleteResponse",
    "Suggestion",
]
