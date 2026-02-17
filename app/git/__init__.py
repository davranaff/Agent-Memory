"""Git integration for Agent Brain."""

from __future__ import annotations

from .hooks import PreCommitHooks
from .review import CodeReviewAssistant
from .integration import GitIntegration

__all__ = [
    "PreCommitHooks",
    "CodeReviewAssistant", 
    "GitIntegration",
]
