"""Main autocomplete engine."""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional, Any

from .models import AutocompleteRequest, AutocompleteResponse, CodeContext
from .context import CodeContextAnalyzer
from .suggestions import SuggestionEngine

logger = logging.getLogger(__name__)


class AutocompleteEngine:
    """Main autocomplete engine that coordinates context analysis and suggestion generation."""
    
    def __init__(self) -> None:
        self.context_analyzer = CodeContextAnalyzer()
        self.suggestion_engine = SuggestionEngine()
        self.cache = {}  # Simple in-memory cache
        self.cache_ttl = 300  # 5 minutes
    
    async def get_suggestions(self, request: AutocompleteRequest) -> AutocompleteResponse:
        """Get autocomplete suggestions for the given request."""
        start_time = time.time()
        
        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
            
            # Generate suggestions
            suggestions = self.suggestion_engine.generate_suggestions(request)
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create response
            response = AutocompleteResponse(
                success=True,
                suggestions=suggestions,
                context_used=bool(request.context),
                processing_time_ms=processing_time,
                metadata={
                    "suggestion_count": len(suggestions),
                    "language": request.context.language,
                    "query_length": len(request.query),
                    "cache_hit": False
                }
            )
            
            # Cache the result
            self._cache_result(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in autocomplete engine: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return AutocompleteResponse(
                success=False,
                suggestions=[],
                context_used=False,
                processing_time_ms=processing_time,
                metadata={
                    "error": str(e),
                    "cache_hit": False
                }
            )
    
    async def get_context(self, code: str, cursor_position: int, language: str, file_path: Optional[str] = None) -> CodeContext:
        """Analyze code context at the given position."""
        try:
            return self.context_analyzer.analyze_context(code, cursor_position, language, file_path)
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            # Return minimal context
            return CodeContext(
                language=language,
                file_path=file_path,
                cursor_position=cursor_position,
                current_line="",
                preceding_text=code[:cursor_position],
                following_text=code[cursor_position:],
                scope={},
                imports=[],
                variables=[],
                functions=[],
                classes=[]
            )
    
    def _generate_cache_key(self, request: AutocompleteRequest) -> str:
        """Generate cache key for the request."""
        # Create a simple hash of the request
        key_parts = [
            request.context.language,
            request.context.file_path or "",
            str(request.context.cursor_position),
            request.query,
            str(request.max_results),
            str(request.include_snippets),
            str(request.include_patterns),
            str(request.language_specific)
        ]
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[AutocompleteResponse]:
        """Get result from cache if available and not expired."""
        if cache_key in self.cache:
            cached_time, cached_result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                # Update metadata to indicate cache hit
                cached_result.metadata["cache_hit"] = True
                return cached_result
            else:
                # Remove expired entry
                del self.cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, result: AutocompleteResponse) -> None:
        """Cache the result."""
        self.cache[cache_key] = (time.time(), result)
        
        # Limit cache size
        if len(self.cache) > 1000:
            # Remove oldest entries (simple LRU)
            oldest_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k][0])[:100]
            for key in oldest_keys:
                del self.cache[key]
    
    def clear_cache(self) -> None:
        """Clear the autocomplete cache."""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cache_size": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "max_cache_size": 1000
        }
