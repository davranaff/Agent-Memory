"""Semantic Search Engine with advanced search capabilities."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timezone

from app.memory.embeddings import EmbeddingProvider
from .retrieval import SmartRetrievalSystem, SearchQuery, RetrievalResult, RetrievalType

logger = logging.getLogger(__name__)


class SearchScope(str, Enum):
    """Scope for semantic search."""
    CODE = "code"
    PATTERNS = "patterns"
    DOCUMENTATION = "documentation"
    EXAMPLES = "examples"
    ALL = "all"


class SearchIntent(str, Enum):
    """Intent behind the search query."""
    FIND_CODE = "find_code"
    LEARN_PATTERN = "learn_pattern"
    GET_EXAMPLE = "get_example"
    UNDERSTAND_CONCEPT = "understand_concept"
    SOLVE_PROBLEM = "solve_problem"
    COMPARE_APPROACHES = "compare_approaches"


@dataclass
class SearchResult:
    """Enhanced search result with context and recommendations."""
    result: RetrievalResult
    snippet: str
    context_lines: List[str]
    related_items: List[str]
    confidence: float
    explanation: str
    suggestions: List[str]


@dataclass
class SearchRequest:
    """Advanced search request with intent and context."""
    query: str
    intent: Optional[SearchIntent] = None
    scope: SearchScope = SearchScope.ALL
    language: Optional[str] = None
    context: Optional[str] = None
    max_results: int = 10
    min_confidence: float = 0.3
    include_related: bool = True
    explain_results: bool = True


class SemanticSearchEngine:
    """Advanced semantic search engine with intent recognition and context awareness."""
    
    def __init__(self, retrieval_system: SmartRetrievalSystem, embedding_provider: EmbeddingProvider) -> None:
        self.retrieval_system = retrieval_system
        self.embedding_provider = embedding_provider
        self._search_history = []
        self._intent_patterns = self._initialize_intent_patterns()
    
    async def search(self, request: SearchRequest) -> List[SearchResult]:
        """Perform advanced semantic search."""
        # Detect intent if not specified
        if not request.intent:
            request.intent = self._detect_intent(request.query)
        
        # Build search query
        search_query = self._build_search_query(request)
        
        # Execute search
        retrieval_results = await self.retrieval_system.search(search_query)
        
        # Enhance results
        enhanced_results = []
        for result in retrieval_results:
            enhanced_result = await self._enhance_result(result, request)
            if enhanced_result.confidence >= request.min_confidence:
                enhanced_results.append(enhanced_result)
        
        # Sort by confidence and limit results
        enhanced_results.sort(key=lambda x: x.confidence, reverse=True)
        final_results = enhanced_results[:request.max_results]
        
        # Add related items if requested
        if request.include_related:
            final_results = await self._add_related_items(final_results, request)
        
        # Record search
        self._record_search(request, len(final_results))
        
        return final_results
    
    async def search_code(self, query: str, language: Optional[str] = None, context: Optional[str] = None) -> List[SearchResult]:
        """Search specifically for code."""
        request = SearchRequest(
            query=query,
            intent=SearchIntent.FIND_CODE,
            scope=SearchScope.CODE,
            language=language,
            context=context
        )
        return await self.search(request)
    
    async def find_pattern(self, pattern_name: str, language: Optional[str] = None) -> List[SearchResult]:
        """Find specific design patterns."""
        query = f"pattern {pattern_name}"
        request = SearchRequest(
            query=query,
            intent=SearchIntent.LEARN_PATTERN,
            scope=SearchScope.PATTERNS,
            language=language
        )
        return await self.search(request)
    
    async def get_examples(self, concept: str, language: Optional[str] = None) -> List[SearchResult]:
        """Get usage examples for a concept."""
        query = f"examples of {concept}"
        request = SearchRequest(
            query=query,
            intent=SearchIntent.GET_EXAMPLE,
            scope=SearchScope.EXAMPLES,
            language=language
        )
        return await self.search(request)
    
    async def understand_concept(self, concept: str) -> List[SearchResult]:
        """Get comprehensive information about a concept."""
        query = f"explain {concept}"
        request = SearchRequest(
            query=query,
            intent=SearchIntent.UNDERSTAND_CONCEPT,
            scope=SearchScope.ALL,
            explain_results=True
        )
        return await self.search(request)
    
    async def solve_problem(self, problem_description: str, language: Optional[str] = None) -> List[SearchResult]:
        """Find solutions to a programming problem."""
        query = f"how to solve {problem_description}"
        request = SearchRequest(
            query=query,
            intent=SearchIntent.SOLVE_PROBLEM,
            scope=SearchScope.ALL,
            language=language,
            explain_results=True
        )
        return await self.search(request)
    
    async def compare_approaches(self, approaches: List[str], language: Optional[str] = None) -> List[SearchResult]:
        """Compare different approaches to a problem."""
        query = f"compare {' vs '.join(approaches)}"
        request = SearchRequest(
            query=query,
            intent=SearchIntent.COMPARE_APPROACHES,
            scope=SearchScope.ALL,
            language=language,
            explain_results=True
        )
        return await self.search(request)
    
    def _detect_intent(self, query: str) -> SearchIntent:
        """Detect user intent from query."""
        query_lower = query.lower()
        
        # Check for intent patterns
        for intent, patterns in self._intent_patterns.items():
            for pattern in patterns:
                if pattern in query_lower:
                    return SearchIntent(intent)
        
        # Default intent based on query content
        if any(word in query_lower for word in ["how to", "solve", "implement", "fix"]):
            return SearchIntent.SOLVE_PROBLEM
        elif any(word in query_lower for word in ["example", "demo", "sample", "tutorial"]):
            return SearchIntent.GET_EXAMPLE
        elif any(word in query_lower for word in ["pattern", "design", "architecture"]):
            return SearchIntent.LEARN_PATTERN
        elif any(word in query_lower for word in ["explain", "what is", "understand", "concept"]):
            return SearchIntent.UNDERSTAND_CONCEPT
        elif any(word in query_lower for word in ["compare", "difference", "vs", "versus"]):
            return SearchIntent.COMPARE_APPROACHES
        else:
            return SearchIntent.FIND_CODE
    
    def _build_search_query(self, request: SearchRequest) -> SearchQuery:
        """Build retrieval system search query."""
        # Determine retrieval type based on intent
        retrieval_type = self._map_intent_to_retrieval_type(request.intent)
        
        # Build filters
        filters = {}
        if request.scope != SearchScope.ALL:
            filters["scope"] = request.scope.value
        
        # Determine pattern types for pattern search
        pattern_types = None
        if request.intent == SearchIntent.LEARN_PATTERN:
            pattern_types = ["creational", "structural", "behavioral", "architectural"]
        
        return SearchQuery(
            query=request.query,
            retrieval_type=retrieval_type,
            filters=filters,
            context=request.context,
            language=request.language,
            pattern_types=pattern_types,
            limit=request.max_results * 2,  # Get more results for enhancement
            threshold=request.min_confidence
        )
    
    def _map_intent_to_retrieval_type(self, intent: SearchIntent) -> RetrievalType:
        """Map search intent to retrieval type."""
        mapping = {
            SearchIntent.FIND_CODE: RetrievalType.SEMANTIC_SEARCH,
            SearchIntent.LEARN_PATTERN: RetrievalType.PATTERN_MATCH,
            SearchIntent.GET_EXAMPLE: RetrievalType.CONTEXT_AWARE,
            SearchIntent.UNDERSTAND_CONCEPT: RetrievalType.HYBRID,
            SearchIntent.SOLVE_PROBLEM: RetrievalType.HYBRID,
            SearchIntent.COMPARE_APPROACHES: RetrievalType.HYBRID
        }
        return mapping.get(intent, RetrievalType.SEMANTIC_SEARCH)
    
    async def _enhance_result(self, result: RetrievalResult, request: SearchRequest) -> SearchResult:
        """Enhance retrieval result with additional context."""
        # Generate snippet
        snippet = self._generate_snippet(result.item)
        
        # Get context lines
        context_lines = self._get_context_lines(result.item, snippet)
        
        # Find related items
        related_items = []
        if request.include_related:
            related_items = await self._find_related_items(result.item)
        
        # Calculate confidence
        confidence = self._calculate_confidence(result, request)
        
        # Generate explanation
        explanation = result.explanation
        if request.explain_results:
            explanation = self._generate_detailed_explanation(result, request)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(result, request)
        
        return SearchResult(
            result=result,
            snippet=snippet,
            context_lines=context_lines,
            related_items=related_items,
            confidence=confidence,
            explanation=explanation,
            suggestions=suggestions
        )
    
    def _generate_snippet(self, item: Any) -> str:
        """Generate relevant snippet from item."""
        if hasattr(item, 'source_text'):
            # Code embedding
            text = item.source_text
        elif hasattr(item, 'description'):
            # Pattern or usage embedding
            text = item.description
        elif hasattr(item, 'content'):
            # Documentation embedding
            text = item.content
        else:
            text = str(item)
        
        # Return first 200 characters
        if len(text) > 200:
            return text[:200] + "..."
        return text
    
    def _get_context_lines(self, item: Any, snippet: str) -> List[str]:
        """Get context lines around the snippet."""
        context_lines = []
        
        if hasattr(item, 'context_window'):
            context_lines = item.context_window
        
        # Add some default context if none available
        if not context_lines:
            if hasattr(item, 'metadata'):
                metadata = item.metadata
                if 'functions' in metadata:
                    context_lines.extend([f"Functions: {', '.join(metadata['functions'][:3])}"])
                if 'classes' in metadata:
                    context_lines.extend([f"Classes: {', '.join(metadata['classes'][:3])}"])
                if 'patterns' in metadata:
                    context_lines.extend([f"Patterns: {', '.join(metadata['patterns'][:3])}"])
        
        return context_lines[:5]  # Limit to 5 context lines
    
    async def _find_related_items(self, item: Any) -> List[str]:
        """Find related items based on similarity."""
        related_items = []
        
        # Get item vector
        if hasattr(item, 'vector'):
            item_vector = item.vector
        else:
            return related_items
        
        # Search for similar items
        all_embeddings = (self.retrieval_system._code_embeddings + 
                         self.retrieval_system._pattern_embeddings +
                         self.retrieval_system._documentation_embeddings +
                         self.retrieval_system._usage_embeddings)
        
        similarities = []
        for emb in all_embeddings:
            if hasattr(emb, 'embedding_id') and emb.embedding_id != getattr(item, 'embedding_id', ''):
                similarity = self.retrieval_system._calculate_similarity(item_vector, emb.vector)
                if similarity > 0.7:  # High similarity threshold
                    similarities.append((emb, similarity))
        
        # Sort by similarity and get top related items
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        for emb, _ in similarities[:3]:
            if hasattr(emb, 'pattern_name'):
                related_items.append(f"Pattern: {emb.pattern_name}")
            elif hasattr(emb, 'component_id'):
                related_items.append(f"Component: {emb.component_id}")
            elif hasattr(emb, 'doc_id'):
                related_items.append(f"Documentation: {emb.doc_id}")
            elif hasattr(emb, 'example_id'):
                related_items.append(f"Example: {emb.example_id}")
        
        return related_items
    
    def _calculate_confidence(self, result: RetrievalResult, request: SearchRequest) -> float:
        """Calculate confidence score for the result."""
        base_confidence = result.relevance_score
        
        # Boost based on match type
        match_type_boosts = {
            "pattern_exact": 0.2,
            "hybrid_pattern": 0.15,
            "context_aware": 0.1,
            "hybrid_context": 0.1,
            "similarity": 0.05
        }
        
        boost = match_type_boosts.get(result.match_type, 0.0)
        
        # Language match boost
        if request.language and hasattr(result.item, 'language'):
            if result.item.language == request.language:
                boost += 0.1
        
        # Intent-specific boosts
        if request.intent == SearchIntent.LEARN_PATTERN and "pattern" in result.match_type:
            boost += 0.15
        elif request.intent == SearchIntent.GET_EXAMPLE and "usage" in result.match_type:
            boost += 0.15
        
        confidence = min(base_confidence + boost, 1.0)
        return confidence
    
    def _generate_detailed_explanation(self, result: RetrievalResult, request: SearchRequest) -> str:
        """Generate detailed explanation for the result."""
        explanation_parts = [result.explanation]
        
        # Add item-specific information
        if hasattr(result.item, 'pattern_name'):
            explanation_parts.append(f"Pattern: {result.item.pattern_name}")
            if hasattr(result.item, 'description'):
                explanation_parts.append(f"Description: {result.item.description[:100]}...")
        
        if hasattr(result.item, 'component_id'):
            explanation_parts.append(f"Component: {result.item.component_id}")
            if hasattr(result.item, 'embedding_type'):
                explanation_parts.append(f"Type: {result.item.embedding_type.value}")
        
        if hasattr(result.item, 'doc_type'):
            explanation_parts.append(f"Document Type: {result.item.doc_type.value}")
        
        if hasattr(result.item, 'usage_type'):
            explanation_parts.append(f"Usage Type: {result.item.usage_type.value}")
        
        # Add intent-specific explanation
        if request.intent == SearchIntent.SOLVE_PROBLEM:
            explanation_parts.append("This result provides a potential solution approach.")
        elif request.intent == SearchIntent.LEARN_PATTERN:
            explanation_parts.append("This result explains a design pattern concept.")
        elif request.intent == SearchIntent.GET_EXAMPLE:
            explanation_parts.append("This result shows a practical implementation example.")
        
        return " | ".join(explanation_parts)
    
    def _generate_suggestions(self, result: RetrievalResult, request: SearchRequest) -> List[str]:
        """Generate suggestions based on the result and intent."""
        suggestions = []
        
        # General suggestions
        suggestions.append("Review the complete implementation for full context")
        
        # Intent-specific suggestions
        if request.intent == SearchIntent.FIND_CODE:
            suggestions.append("Check for similar implementations in other languages")
            suggestions.append("Look for related patterns and best practices")
        
        elif request.intent == SearchIntent.LEARN_PATTERN:
            suggestions.append("Study the implementation details and variations")
            suggestions.append("Look for real-world usage examples")
            suggestions.append("Compare with alternative patterns")
        
        elif request.intent == SearchIntent.GET_EXAMPLE:
            suggestions.append("Try modifying the example for your specific use case")
            suggestions.append("Look for more advanced examples")
        
        elif request.intent == SearchIntent.SOLVE_PROBLEM:
            suggestions.append("Consider edge cases and error handling")
            suggestions.append("Look for alternative solutions")
            suggestions.append("Check performance implications")
        
        elif request.intent == SearchIntent.COMPARE_APPROACHES:
            suggestions.append("Analyze trade-offs and use cases")
            suggestions.append("Consider performance and maintainability")
        
        # Item-specific suggestions
        if hasattr(result.item, 'pattern_name'):
            suggestions.append(f"Study the {result.item.pattern_name} pattern in depth")
        
        if hasattr(result.item, 'metadata'):
            metadata = result.item.metadata
            if 'complexity' in metadata:
                if metadata['complexity'] == 'complex':
                    suggestions.append("This is a complex implementation - study carefully")
                elif metadata['complexity'] == 'simple':
                    suggestions.append("This is a simple implementation - good for learning")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    async def _add_related_items(self, results: List[SearchResult], request: SearchRequest) -> List[SearchResult]:
        """Add related items to search results."""
        # This is a placeholder for more sophisticated related item addition
        # In a full implementation, this would find and add related results
        return results
    
    def _record_search(self, request: SearchRequest, result_count: int) -> None:
        """Record search for analytics."""
        search_record = {
            "query": request.query,
            "intent": request.intent.value if request.intent else None,
            "scope": request.scope.value,
            "language": request.language,
            "result_count": result_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._search_history.append(search_record)
        
        # Keep only last 100 searches
        if len(self._search_history) > 100:
            self._search_history = self._search_history[-100:]
    
    def _initialize_intent_patterns(self) -> Dict[str, List[str]]:
        """Initialize intent detection patterns."""
        return {
            "find_code": ["find", "search", "locate", "get code", "show me"],
            "learn_pattern": ["pattern", "design pattern", "architecture", "learn"],
            "get_example": ["example", "demo", "sample", "tutorial", "how to"],
            "understand_concept": ["explain", "what is", "understand", "concept", "meaning"],
            "solve_problem": ["solve", "fix", "implement", "how to", "problem"],
            "compare_approaches": ["compare", "difference", "vs", "versus", "alternative"]
        }
    
    async def get_search_analytics(self) -> Dict[str, Any]:
        """Get search analytics and statistics."""
        if not self._search_history:
            return {"message": "No search history available"}
        
        # Calculate statistics
        total_searches = len(self._search_history)
        intent_counts = {}
        scope_counts = {}
        language_counts = {}
        
        for search in self._search_history:
            intent = search.get("intent", "unknown")
            scope = search.get("scope", "unknown")
            language = search.get("language", "unknown")
            
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            scope_counts[scope] = scope_counts.get(scope, 0) + 1
            language_counts[language] = language_counts.get(language, 0) + 1
        
        return {
            "total_searches": total_searches,
            "intent_distribution": intent_counts,
            "scope_distribution": scope_counts,
            "language_distribution": language_counts,
            "average_results": sum(s["result_count"] for s in self._search_history) / total_searches,
            "recent_searches": self._search_history[-10:]  # Last 10 searches
        }
