"""Smart Retrieval System for semantic code search and pattern matching."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import asyncio
from collections import defaultdict

from app.memory.embeddings import EmbeddingProvider
from .code_embeddings import CodeEmbedding, EmbeddingType
from .pattern_embeddings import PatternEmbedding, PatternType
from .documentation_embeddings import DocumentationEmbedding, DocumentationType
from .usage_embeddings import UsageExampleEmbedding, UsageType

logger = logging.getLogger(__name__)


class RetrievalType(str, Enum):
    """Types of retrieval operations."""
    SEMANTIC_SEARCH = "semantic_search"
    PATTERN_MATCH = "pattern_match"
    SIMILARITY_SEARCH = "similarity_search"
    CONTEXT_AWARE = "context_aware"
    HYBRID = "hybrid"


@dataclass
class RetrievalResult:
    """Result from retrieval operation."""
    item: Union[CodeEmbedding, PatternEmbedding, DocumentationEmbedding, UsageExampleEmbedding]
    relevance_score: float
    match_type: str
    explanation: str
    context: Optional[str] = None


@dataclass
class SearchQuery:
    """Enhanced search query with context and filters."""
    query: str
    retrieval_type: RetrievalType = RetrievalType.SEMANTIC_SEARCH
    filters: Dict[str, Any] = None
    context: Optional[str] = None
    language: Optional[str] = None
    pattern_types: Optional[List[str]] = None
    limit: int = 10
    threshold: float = 0.5


class SmartRetrievalSystem:
    """Intelligent retrieval system for code, patterns, and documentation."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._code_embeddings: List[CodeEmbedding] = []
        self._pattern_embeddings: List[PatternEmbedding] = []
        self._documentation_embeddings: List[DocumentationEmbedding] = []
        self._usage_embeddings: List[UsageExampleEmbedding] = []
        self._embedding_index = defaultdict(list)  # Type -> embeddings
        self._language_index = defaultdict(list)  # Language -> embeddings
        self._pattern_index = defaultdict(list)    # Pattern -> embeddings
    
    async def add_code_embedding(self, embedding: CodeEmbedding) -> None:
        """Add a code embedding to the retrieval system."""
        self._code_embeddings.append(embedding)
        self._embedding_index["code"].append(embedding)
        
        # Index by language
        language = embedding.metadata.get("language", "unknown")
        self._language_index[language].append(embedding)
        
        # Index by embedding type
        self._embedding_index[embedding.embedding_type.value].append(embedding)
    
    async def add_pattern_embedding(self, embedding: PatternEmbedding) -> None:
        """Add a pattern embedding to the retrieval system."""
        self._pattern_embeddings.append(embedding)
        self._embedding_index["pattern"].append(embedding)
        
        # Index by pattern type
        self._embedding_index[embedding.pattern_type.value].append(embedding)
        self._pattern_index[embedding.pattern_name].append(embedding)
    
    async def add_documentation_embedding(self, embedding: DocumentationEmbedding) -> None:
        """Add a documentation embedding to the retrieval system."""
        self._documentation_embeddings.append(embedding)
        self._embedding_index["documentation"].append(embedding)
        
        # Index by doc type
        self._embedding_index[embedding.doc_type.value].append(embedding)
        
        # Index by language
        language = embedding.metadata.get("language", "unknown")
        self._language_index[language].append(embedding)
    
    async def add_usage_embedding(self, embedding: UsageExampleEmbedding) -> None:
        """Add a usage example embedding to the retrieval system."""
        self._usage_embeddings.append(embedding)
        self._embedding_index["usage"].append(embedding)
        
        # Index by usage type
        self._embedding_index[embedding.usage_type.value].append(embedding)
        
        # Index by language
        self._language_index[embedding.language].append(embedding)
    
    async def search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Perform intelligent search across all embedding types."""
        results = []
        
        if query.retrieval_type == RetrievalType.SEMANTIC_SEARCH:
            results = await self._semantic_search(query)
        elif query.retrieval_type == RetrievalType.PATTERN_MATCH:
            results = await self._pattern_match_search(query)
        elif query.retrieval_type == RetrievalType.SIMILARITY_SEARCH:
            results = await self._similarity_search(query)
        elif query.retrieval_type == RetrievalType.CONTEXT_AWARE:
            results = await self._context_aware_search(query)
        elif query.retrieval_type == RetrievalType.HYBRID:
            results = await self._hybrid_search(query)
        else:
            results = await self._semantic_search(query)  # Default
        
        # Apply filters
        filtered_results = self._apply_filters(results, query.filters)
        
        # Sort by relevance and limit
        filtered_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return filtered_results[:query.limit]
    
    async def _semantic_search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Perform semantic search across all embeddings."""
        results = []
        query_vector = await self.embedding_provider.embed_text(query.query)
        
        # Search in code embeddings
        if not query.filters or query.filters.get("include_code", True):
            code_results = await self._search_code_embeddings(query_vector, query)
            results.extend(code_results)
        
        # Search in pattern embeddings
        if not query.filters or query.filters.get("include_patterns", True):
            pattern_results = await self._search_pattern_embeddings(query_vector, query)
            results.extend(pattern_results)
        
        # Search in documentation embeddings
        if not query.filters or query.filters.get("include_docs", True):
            doc_results = await self._search_documentation_embeddings(query_vector, query)
            results.extend(doc_results)
        
        # Search in usage embeddings
        if not query.filters or query.filters.get("include_examples", True):
            usage_results = await self._search_usage_embeddings(query_vector, query)
            results.extend(usage_results)
        
        return results
    
    async def _pattern_match_search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Search for specific patterns."""
        results = []
        
        # Extract pattern names from query
        pattern_names = self._extract_pattern_names(query.query)
        
        for pattern_name in pattern_names:
            if pattern_name in self._pattern_index:
                pattern_embs = self._pattern_index[pattern_name]
                for emb in pattern_embs:
                    results.append(RetrievalResult(
                        item=emb,
                        relevance_score=1.0,  # Exact match
                        match_type="pattern_exact",
                        explanation=f"Exact pattern match for '{pattern_name}'"
                    ))
        
        return results
    
    async def _similarity_search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Search by similarity to provided context."""
        if not query.context:
            return await self._semantic_search(query)
        
        results = []
        context_vector = await self.embedding_provider.embed_text(query.context)
        
        # Search across all embedding types
        all_embeddings = (self._code_embeddings + self._pattern_embeddings + 
                          self._documentation_embeddings + self._usage_embeddings)
        
        for emb in all_embeddings:
            similarity = self._calculate_similarity(context_vector, emb.vector)
            if similarity >= query.threshold:
                results.append(RetrievalResult(
                    item=emb,
                    relevance_score=similarity,
                    match_type="similarity",
                    explanation=f"Similarity match: {similarity:.3f}",
                    context=query.context
                ))
        
        return results
    
    async def _context_aware_search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Search with context awareness."""
        results = []
        
        # Combine query and context
        combined_query = query.query
        if query.context:
            combined_query = f"{query.query} | Context: {query.context}"
        
        # Generate enhanced query vector
        query_vector = await self.embedding_provider.embed_text(combined_query)
        
        # Search with language preference
        if query.language:
            language_embs = self._language_index.get(query.language, [])
            for emb in language_embs:
                similarity = self._calculate_similarity(query_vector, emb.vector)
                if similarity >= query.threshold:
                    results.append(RetrievalResult(
                        item=emb,
                        relevance_score=similarity * 1.1,  # Boost for language match
                        match_type="context_aware",
                        explanation=f"Context-aware match in {query.language}",
                        context=query.context
                    ))
        else:
            # Search across all embeddings
            results = await self._semantic_search(SearchQuery(
                query=combined_query,
                retrieval_type=RetrievalType.SEMANTIC_SEARCH,
                threshold=query.threshold,
                limit=query.limit
            ))
        
        return results
    
    async def _hybrid_search(self, query: SearchQuery) -> List[RetrievalResult]:
        """Hybrid search combining multiple strategies."""
        all_results = []
        
        # Semantic search
        semantic_results = await self._semantic_search(query)
        for result in semantic_results:
            result.relevance_score *= 0.6  # Weight for semantic
            result.match_type = "hybrid_semantic"
            all_results.append(result)
        
        # Pattern match search
        pattern_results = await self._pattern_match_search(query)
        for result in pattern_results:
            result.relevance_score *= 0.8  # Weight for pattern match
            result.match_type = "hybrid_pattern"
            all_results.append(result)
        
        # Context-aware search if context provided
        if query.context:
            context_results = await self._context_aware_search(query)
            for result in context_results:
                result.relevance_score *= 0.7  # Weight for context
                result.match_type = "hybrid_context"
                all_results.append(result)
        
        # Merge and deduplicate results
        merged_results = self._merge_results(all_results)
        
        return merged_results
    
    async def _search_code_embeddings(self, query_vector: List[float], query: SearchQuery) -> List[RetrievalResult]:
        """Search in code embeddings."""
        results = []
        
        # Filter by language if specified
        embeddings = self._code_embeddings
        if query.language:
            embeddings = [emb for emb in embeddings 
                          if emb.metadata.get("language") == query.language]
        
        for emb in embeddings:
            similarity = self._calculate_similarity(query_vector, emb.vector)
            if similarity >= query.threshold:
                results.append(RetrievalResult(
                    item=emb,
                    relevance_score=similarity,
                    match_type="code_semantic",
                    explanation=f"Code semantic match: {similarity:.3f}"
                ))
        
        return results
    
    async def _search_pattern_embeddings(self, query_vector: List[float], query: SearchQuery) -> List[RetrievalResult]:
        """Search in pattern embeddings."""
        results = []
        
        # Filter by pattern types if specified
        embeddings = self._pattern_embeddings
        if query.pattern_types:
            embeddings = [emb for emb in embeddings 
                         if emb.pattern_type.value in query.pattern_types]
        
        for emb in embeddings:
            similarity = self._calculate_similarity(query_vector, emb.vector)
            if similarity >= query.threshold:
                results.append(RetrievalResult(
                    item=emb,
                    relevance_score=similarity,
                    match_type="pattern_semantic",
                    explanation=f"Pattern semantic match: {similarity:.3f}"
                ))
        
        return results
    
    async def _search_documentation_embeddings(self, query_vector: List[float], query: SearchQuery) -> List[RetrievalResult]:
        """Search in documentation embeddings."""
        results = []
        
        for emb in self._documentation_embeddings:
            similarity = self._calculate_similarity(query_vector, emb.vector)
            if similarity >= query.threshold:
                results.append(RetrievalResult(
                    item=emb,
                    relevance_score=similarity,
                    match_type="documentation_semantic",
                    explanation=f"Documentation semantic match: {similarity:.3f}"
                ))
        
        return results
    
    async def _search_usage_embeddings(self, query_vector: List[float], query: SearchQuery) -> List[RetrievalResult]:
        """Search in usage example embeddings."""
        results = []
        
        # Filter by usage type if specified
        embeddings = self._usage_embeddings
        usage_type_filter = query.filters.get("usage_type") if query.filters else None
        if usage_type_filter:
            embeddings = [emb for emb in embeddings 
                         if emb.usage_type.value == usage_type_filter]
        
        for emb in embeddings:
            similarity = self._calculate_similarity(query_vector, emb.vector)
            if similarity >= query.threshold:
                results.append(RetrievalResult(
                    item=emb,
                    relevance_score=similarity,
                    match_type="usage_semantic",
                    explanation=f"Usage example semantic match: {similarity:.3f}"
                ))
        
        return results
    
    def _apply_filters(self, results: List[RetrievalResult], filters: Optional[Dict[str, Any]]) -> List[RetrievalResult]:
        """Apply filters to search results."""
        if not filters:
            return results
        
        filtered_results = []
        
        for result in results:
            # Language filter
            if "language" in filters:
                item_lang = getattr(result.item, "language", None)
                if not item_lang or item_lang != filters["language"]:
                    continue
            
            # Type filter
            if "type" in filters:
                if not hasattr(result.item, filters["type"]):
                    continue
            
            # Score filter
            if "min_score" in filters:
                if result.relevance_score < filters["min_score"]:
                    continue
            
            filtered_results.append(result)
        
        return filtered_results
    
    def _merge_results(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """Merge and deduplicate results."""
        seen = set()
        merged = []
        
        for result in results:
            # Create a unique key for the item
            if hasattr(result.item, 'embedding_id'):
                key = result.item.embedding_id
            elif hasattr(result.item, 'pattern_name'):
                key = result.item.pattern_name
            elif hasattr(result.item, 'doc_id'):
                key = result.item.doc_id
            else:
                key = str(id(result.item))
            
            if key not in seen:
                seen.add(key)
                merged.append(result)
            else:
                # Update existing result if higher score
                for existing in merged:
                    if (hasattr(existing.item, 'embedding_id') and 
                        existing.item.embedding_id == key and
                        result.relevance_score > existing.relevance_score):
                        existing.relevance_score = result.relevance_score
                        existing.match_type = result.match_type
                        existing.explanation = result.explanation
                        break
        
        return merged
    
    def _extract_pattern_names(self, query: str) -> List[str]:
        """Extract pattern names from query."""
        # Common pattern names
        pattern_names = [
            "singleton", "factory", "builder", "prototype", "adapter", "decorator",
            "proxy", "composite", "flyweight", "facade", "bridge", "observer",
            "strategy", "command", "iterator", "mediator", "memento", "state",
            "template", "visitor", "chain", "repository", "mvc", "microservices",
            "cqrs", "event-driven", "saga", "circuit-breaker", "api-gateway"
        ]
        
        found_patterns = []
        query_lower = query.lower()
        
        for pattern in pattern_names:
            if pattern in query_lower:
                found_patterns.append(pattern)
        
        return found_patterns
    
    def _calculate_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if len(vector1) != len(vector2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get retrieval system statistics."""
        return {
            "total_embeddings": len(self._code_embeddings) + len(self._pattern_embeddings) + 
                              len(self._documentation_embeddings) + len(self._usage_embeddings),
            "code_embeddings": len(self._code_embeddings),
            "pattern_embeddings": len(self._pattern_embeddings),
            "documentation_embeddings": len(self._documentation_embeddings),
            "usage_embeddings": len(self._usage_embeddings),
            "languages": list(self._language_index.keys()),
            "pattern_types": list(set(emb.pattern_type.value for emb in self._pattern_embeddings)),
            "embedding_types": list(self._embedding_index.keys())
        }
    
    async def clear_all(self) -> None:
        """Clear all embeddings from the retrieval system."""
        self._code_embeddings.clear()
        self._pattern_embeddings.clear()
        self._documentation_embeddings.clear()
        self._usage_embeddings.clear()
        self._embedding_index.clear()
        self._language_index.clear()
        self._pattern_index.clear()
        
        logger.info("Cleared all embeddings from retrieval system")
