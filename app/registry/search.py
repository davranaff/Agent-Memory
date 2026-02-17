"""Component search functionality for the registry."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from .metadata import ComponentMetadata, ComponentType, AccessLevel

logger = logging.getLogger(__name__)


class SearchType(str, Enum):
    """Types of search queries."""
    EXACT = "exact"
    FUZZY = "fuzzy"
    REGEX = "regex"
    SEMANTIC = "semantic"
    STRUCTURAL = "structural"


class SortOrder(str, Enum):
    """Sort orders for search results."""
    RELEVANCE = "relevance"
    NAME_ASC = "name_asc"
    NAME_DESC = "name_desc"
    QUALITY_DESC = "quality_desc"
    QUALITY_ASC = "quality_asc"
    COMPLEXITY_DESC = "complexity_desc"
    COMPLEXITY_ASC = "complexity_asc"
    RECENTLY_MODIFIED = "recently_modified"


@dataclass
class SearchQuery:
    """A search query for components."""
    query: str
    search_type: SearchType = SearchType.FUZZY
    filters: Dict[str, Any] = None
    sort_order: SortOrder = SortOrder.RELEVANCE
    limit: int = 50
    offset: int = 0
    
    def __post_init__(self) -> None:
        if self.filters is None:
            self.filters = {}


@dataclass
class SearchResult:
    """A single search result."""
    component: ComponentMetadata
    relevance_score: float
    match_highlights: List[str]
    match_reasons: List[str]


@dataclass
class SearchResponse:
    """Complete search response."""
    results: List[SearchResult]
    total_count: int
    query_time_ms: float
    facets: Dict[str, Dict[str, int]]
    suggestions: List[str]


class ComponentSearch:
    """Advanced search functionality for components."""
    
    def __init__(self, registry) -> None:
        self.registry = registry
        self._search_index = {}
        self._index_built = False

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Perform a search for components."""
        import time
        start_time = time.time()
        
        # Build search index if not already built
        if not self._index_built:
            await self._build_search_index()
        
        # Execute search based on type
        if query.search_type == SearchType.EXACT:
            results = await self._exact_search(query)
        elif query.search_type == SearchType.FUZZY:
            results = await self._fuzzy_search(query)
        elif query.search_type == SearchType.REGEX:
            results = await self._regex_search(query)
        elif query.search_type == SearchType.SEMANTIC:
            results = await self._semantic_search(query)
        elif query.search_type == SearchType.STRUCTURAL:
            results = await self._structural_search(query)
        else:
            results = await self._fuzzy_search(query)  # Default to fuzzy
        
        # Apply filters
        filtered_results = await self._apply_filters(results, query.filters)
        
        # Sort results
        sorted_results = self._sort_results(filtered_results, query.sort_order)
        
        # Apply pagination
        paginated_results = sorted_results[query.offset:query.offset + query.limit]
        
        # Calculate facets and suggestions
        facets = await self._calculate_facets(filtered_results)
        suggestions = await self._get_suggestions(query.query)
        
        query_time = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=paginated_results,
            total_count=len(filtered_results),
            query_time_ms=query_time,
            facets=facets,
            suggestions=suggestions
        )

    async def _build_search_index(self) -> None:
        """Build search index for fast searching."""
        logger.info("Building component search index...")
        
        # Get all components
        all_components = []
        
        # This would typically get all components from the registry
        # For now, we'll build a simple index structure
        
        self._search_index = {
            "name_index": {},
            "type_index": {},
            "language_index": {},
            "tag_index": {},
            "content_index": {}
        }
        
        self._index_built = True
        logger.info("Search index built successfully")

    async def _exact_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform exact match search."""
        results = []
        
        # Search in component names
        matching_components = await self.registry.search_components(
            query=query.query,
            limit=query.limit * 2  # Get more for filtering
        )
        
        for component in matching_components:
            relevance_score = self._calculate_exact_relevance(component, query.query)
            highlights, reasons = self._get_match_info(component, query.query, SearchType.EXACT)
            
            result = SearchResult(
                component=component,
                relevance_score=relevance_score,
                match_highlights=highlights,
                match_reasons=reasons
            )
            results.append(result)
        
        return results

    async def _fuzzy_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform fuzzy search."""
        results = []
        
        # Get more components for fuzzy matching
        matching_components = await self.registry.search_components(
            query="",  # Get all components
            limit=500
        )
        
        for component in matching_components:
            relevance_score = self._calculate_fuzzy_relevance(component, query.query)
            
            if relevance_score > 0.1:  # Threshold for fuzzy matching
                highlights, reasons = self._get_match_info(component, query.query, SearchType.FUZZY)
                
                result = SearchResult(
                    component=component,
                    relevance_score=relevance_score,
                    match_highlights=highlights,
                    match_reasons=reasons
                )
                results.append(result)
        
        return results

    async def _regex_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform regex search."""
        import re
        
        try:
            pattern = re.compile(query.query, re.IGNORECASE)
        except re.error:
            logger.error(f"Invalid regex pattern: {query.query}")
            return []
        
        results = []
        matching_components = await self.registry.search_components(limit=500)
        
        for component in matching_components:
            relevance_score = 0.0
            highlights = []
            reasons = []
            
            # Search in name
            if pattern.search(component.name):
                relevance_score += 0.5
                highlights.append(f"Name: {component.name}")
                reasons.append("Name matches pattern")
            
            # Search in file path
            if pattern.search(component.relative_path):
                relevance_score += 0.3
                highlights.append(f"Path: {component.relative_path}")
                reasons.append("Path matches pattern")
            
            # Search in tags
            for tag in component.tags:
                if pattern.search(tag):
                    relevance_score += 0.2
                    highlights.append(f"Tag: {tag}")
                    reasons.append("Tag matches pattern")
            
            # Search in categories
            for category in component.categories:
                if pattern.search(category):
                    relevance_score += 0.2
                    highlights.append(f"Category: {category}")
                    reasons.append("Category matches pattern")
            
            if relevance_score > 0:
                result = SearchResult(
                    component=component,
                    relevance_score=relevance_score,
                    match_highlights=highlights,
                    match_reasons=reasons
                )
                results.append(result)
        
        return results

    async def _semantic_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform semantic search (placeholder for future implementation)."""
        # This would use vector embeddings for semantic search
        # For now, fall back to fuzzy search
        logger.warning("Semantic search not yet implemented, falling back to fuzzy search")
        return await self._fuzzy_search(query)

    async def _structural_search(self, query: SearchQuery) -> List[SearchResult]:
        """Perform structural search based on component characteristics."""
        results = []
        matching_components = await self.registry.search_components(limit=500)
        
        # Parse structural query
        structural_criteria = self._parse_structural_query(query.query)
        
        for component in matching_components:
            relevance_score = self._calculate_structural_relevance(component, structural_criteria)
            
            if relevance_score > 0:
                highlights, reasons = self._get_structural_match_info(component, structural_criteria)
                
                result = SearchResult(
                    component=component,
                    relevance_score=relevance_score,
                    match_highlights=highlights,
                    match_reasons=reasons
                )
                results.append(result)
        
        return results

    def _parse_structural_query(self, query: str) -> Dict[str, Any]:
        """Parse structural search query."""
        criteria = {}
        
        # Simple parsing for common patterns
        query_lower = query.lower()
        
        if "class" in query_lower:
            criteria["type"] = ComponentType.CLASS
        elif "function" in query_lower:
            criteria["type"] = ComponentType.FUNCTION
        elif "interface" in query_lower:
            criteria["type"] = ComponentType.INTERFACE
        
        if "public" in query_lower:
            criteria["access_level"] = AccessLevel.PUBLIC
        elif "private" in query_lower:
            criteria["access_level"] = AccessLevel.PRIVATE
        
        if "abstract" in query_lower:
            criteria["is_abstract"] = True
        
        if "static" in query_lower:
            criteria["is_static"] = True
        
        if "async" in query_lower:
            criteria["is_async"] = True
        
        # Extract complexity requirements
        if "simple" in query_lower:
            criteria["max_complexity"] = 5
        elif "complex" in query_lower:
            criteria["min_complexity"] = 10
        
        return criteria

    def _calculate_exact_relevance(self, component: ComponentMetadata, query: str) -> float:
        """Calculate relevance score for exact match."""
        score = 0.0
        query_lower = query.lower()
        
        # Exact name match
        if component.name.lower() == query_lower:
            score += 1.0
        
        # Name starts with query
        if component.name.lower().startswith(query_lower):
            score += 0.8
        
        # Name contains query
        if query_lower in component.name.lower():
            score += 0.6
        
        # File path match
        if query_lower in component.relative_path.lower():
            score += 0.4
        
        # Tag match
        for tag in component.tags:
            if query_lower == tag.lower():
                score += 0.5
            elif query_lower in tag.lower():
                score += 0.3
        
        return min(score, 1.0)

    def _calculate_fuzzy_relevance(self, component: ComponentMetadata, query: str) -> float:
        """Calculate relevance score for fuzzy match."""
        score = 0.0
        query_lower = query.lower()
        
        # Fuzzy name matching
        name_similarity = self._string_similarity(component.name.lower(), query_lower)
        if name_similarity > 0.7:
            score += name_similarity * 0.8
        
        # Partial name matching
        if query_lower in component.name.lower():
            score += 0.6
        
        # File path matching
        path_similarity = self._string_similarity(component.relative_path.lower(), query_lower)
        if path_similarity > 0.6:
            score += path_similarity * 0.4
        
        # Tag matching
        for tag in component.tags:
            tag_similarity = self._string_similarity(tag.lower(), query_lower)
            if tag_similarity > 0.7:
                score += tag_similarity * 0.3
        
        return min(score, 1.0)

    def _calculate_structural_relevance(self, component: ComponentMetadata, criteria: Dict[str, Any]) -> float:
        """Calculate relevance score for structural search."""
        score = 0.0
        total_criteria = len(criteria)
        
        if total_criteria == 0:
            return 0.0
        
        # Type matching
        if "type" in criteria:
            if component.type == criteria["type"]:
                score += 1.0 / total_criteria
        
        # Access level matching
        if "access_level" in criteria:
            if component.access_level == criteria["access_level"]:
                score += 1.0 / total_criteria
        
        # Boolean properties
        for prop in ["is_abstract", "is_static", "is_async"]:
            if prop in criteria:
                if getattr(component, prop, False) == criteria[prop]:
                    score += 1.0 / total_criteria
        
        # Complexity constraints
        if "max_complexity" in criteria:
            if component.code_metrics.cyclomatic_complexity <= criteria["max_complexity"]:
                score += 1.0 / total_criteria
        
        if "min_complexity" in criteria:
            if component.code_metrics.cyclomatic_complexity >= criteria["min_complexity"]:
                score += 1.0 / total_criteria
        
        return score

    def _get_match_info(self, component: ComponentMetadata, query: str, search_type: SearchType) -> Tuple[List[str], List[str]]:
        """Get match highlights and reasons for a component."""
        highlights = []
        reasons = []
        query_lower = query.lower()
        
        # Name matches
        if query_lower in component.name.lower():
            highlights.append(f"Name: {component.name}")
            reasons.append("Name contains query")
        
        # Path matches
        if query_lower in component.relative_path.lower():
            highlights.append(f"Path: {component.relative_path}")
            reasons.append("Path contains query")
        
        # Tag matches
        matching_tags = [tag for tag in component.tags if query_lower in tag.lower()]
        for tag in matching_tags:
            highlights.append(f"Tag: {tag}")
            reasons.append(f"Tag '{tag}' matches query")
        
        # Category matches
        matching_categories = [cat for cat in component.categories if query_lower in cat.lower()]
        for category in matching_categories:
            highlights.append(f"Category: {category}")
            reasons.append(f"Category '{category}' matches query")
        
        return highlights, reasons

    def _get_structural_match_info(self, component: ComponentMetadata, criteria: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Get match highlights and reasons for structural search."""
        highlights = []
        reasons = []
        
        for key, value in criteria.items():
            if hasattr(component, key):
                component_value = getattr(component, key)
                if component_value == value:
                    highlights.append(f"{key}: {value}")
                    reasons.append(f"{key} matches criteria")
        
        return highlights, reasons

    async def _apply_filters(self, results: List[SearchResult], filters: Dict[str, Any]) -> List[SearchResult]:
        """Apply filters to search results."""
        if not filters:
            return results
        
        filtered_results = []
        
        for result in results:
            component = result.component
            
            # Type filter
            if "type" in filters:
                if component.type != filters["type"]:
                    continue
            
            # Language filter
            if "language" in filters:
                if component.language != filters["language"]:
                    continue
            
            # Tags filter
            if "tags" in filters:
                required_tags = set(filters["tags"])
                if not required_tags.issubset(component.tags):
                    continue
            
            # Categories filter
            if "categories" in filters:
                required_categories = set(filters["categories"])
                if not required_categories.issubset(component.categories):
                    continue
            
            # Quality score filter
            if "min_quality" in filters:
                if component.calculate_quality_score() < filters["min_quality"]:
                    continue
            
            # Complexity filter
            if "max_complexity" in filters:
                if component.code_metrics.cyclomatic_complexity > filters["max_complexity"]:
                    continue
            
            # Test coverage filter
            if "min_test_coverage" in filters:
                if component.code_metrics.test_coverage < filters["min_test_coverage"]:
                    continue
            
            filtered_results.append(result)
        
        return filtered_results

    def _sort_results(self, results: List[SearchResult], sort_order: SortOrder) -> List[SearchResult]:
        """Sort search results."""
        if sort_order == SortOrder.RELEVANCE:
            return sorted(results, key=lambda r: r.relevance_score, reverse=True)
        elif sort_order == SortOrder.NAME_ASC:
            return sorted(results, key=lambda r: r.component.name.lower())
        elif sort_order == SortOrder.NAME_DESC:
            return sorted(results, key=lambda r: r.component.name.lower(), reverse=True)
        elif sort_order == SortOrder.QUALITY_DESC:
            return sorted(results, key=lambda r: r.component.calculate_quality_score(), reverse=True)
        elif sort_order == SortOrder.QUALITY_ASC:
            return sorted(results, key=lambda r: r.component.calculate_quality_score())
        elif sort_order == SortOrder.COMPLEXITY_DESC:
            return sorted(results, key=lambda r: r.component.code_metrics.cyclomatic_complexity, reverse=True)
        elif sort_order == SortOrder.COMPLEXITY_ASC:
            return sorted(results, key=lambda r: r.component.code_metrics.cyclomatic_complexity)
        elif sort_order == SortOrder.RECENTLY_MODIFIED:
            return sorted(results, key=lambda r: r.component.last_modified, reverse=True)
        else:
            return results

    async def _calculate_facets(self, results: List[SearchResult]) -> Dict[str, Dict[str, int]]:
        """Calculate search facets."""
        facets = {
            "type": {},
            "language": {},
            "tags": {},
            "categories": {}
        }
        
        for result in results:
            component = result.component
            
            # Type facet
            type_name = component.type.value
            facets["type"][type_name] = facets["type"].get(type_name, 0) + 1
            
            # Language facet
            facets["language"][component.language] = facets["language"].get(component.language, 0) + 1
            
            # Tags facet
            for tag in component.tags:
                facets["tags"][tag] = facets["tags"].get(tag, 0) + 1
            
            # Categories facet
            for category in component.categories:
                facets["categories"][category] = facets["categories"].get(category, 0) + 1
        
        return facets

    async def _get_suggestions(self, query: str) -> List[str]:
        """Get search suggestions."""
        suggestions = []
        
        # This would typically use the search index to suggest corrections
        # For now, provide basic suggestions
        
        if len(query) < 3:
            return suggestions
        
        # Get common component names that start with the query
        all_components = await self.registry.search_components(limit=100)
        
        name_matches = set()
        for component in all_components:
            if component.name.lower().startswith(query.lower()):
                name_matches.add(component.name)
        
        suggestions.extend(sorted(name_matches)[:5])
        
        return suggestions

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Levenshtein distance."""
        if not s1 or not s2:
            return 0.0
        
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
        
        max_len = max(m, n)
        return 1 - (dp[m][n] / max_len)

    async def rebuild_index(self) -> None:
        """Rebuild the search index."""
        self._index_built = False
        await self._build_search_index()
