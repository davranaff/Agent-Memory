"""Semantic Search API endpoints for Phase 2."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.embeddings import (
    CodeEmbeddingGenerator, PatternEmbeddingGenerator, 
    DocumentationEmbeddingGenerator, UsageExampleEmbeddingGenerator,
    SmartRetrievalSystem, SemanticSearchEngine
)
from app.embeddings.semantic_search import SearchRequest, SearchScope, SearchIntent
from app.memory.embeddings import OllamaEmbeddingProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/semantic", tags=["semantic"])

# Pydantic models for API
class CodeEmbeddingRequest(BaseModel):
    """Request model for code embedding generation."""
    component_id: str = Field(..., description="ID of the component")
    code: str = Field(..., description="Code content")
    language: str = Field(..., description="Programming language")
    context: Optional[List[str]] = Field(None, description="Context window")


class PatternEmbeddingRequest(BaseModel):
    """Request model for pattern embedding generation."""
    pattern_name: str = Field(..., description="Name of the pattern")


class DocumentationEmbeddingRequest(BaseModel):
    """Request model for documentation embedding generation."""
    doc_id: str = Field(..., description="ID of the document")
    content: str = Field(..., description="Document content")
    doc_type: str = Field(..., description="Type of documentation")
    file_path: Optional[str] = Field(None, description="File path")


class UsageEmbeddingRequest(BaseModel):
    """Request model for usage example embedding generation."""
    example_id: str = Field(..., description="ID of the example")
    code: str = Field(..., description="Example code")
    description: str = Field(..., description="Description of the example")
    usage_type: str = Field(..., description="Type of usage")
    context: Optional[str] = Field(None, description="Context")
    tags: Optional[List[str]] = Field(None, description="Tags")
    language: Optional[str] = Field(None, description="Programming language")


class SemanticSearchRequest(BaseModel):
    """Request model for semantic search."""
    query: str = Field(..., description="Search query")
    intent: Optional[str] = Field(None, description="Search intent")
    scope: Optional[str] = Field("all", description="Search scope")
    language: Optional[str] = Field(None, description="Programming language")
    context: Optional[str] = Field(None, description="Search context")
    max_results: int = Field(10, description="Maximum number of results")
    min_confidence: float = Field(0.3, description="Minimum confidence threshold")
    include_related: bool = Field(True, description="Include related items")
    explain_results: bool = Field(True, description="Explain search results")


class CodeSearchRequest(BaseModel):
    """Request model for code search."""
    query: str = Field(..., description="Search query")
    language: Optional[str] = Field(None, description="Programming language")
    context: Optional[str] = Field(None, description="Context")
    max_results: int = Field(10, description="Maximum number of results")


class PatternSearchRequest(BaseModel):
    """Request model for pattern search."""
    pattern_name: str = Field(..., description="Pattern name to search")
    language: Optional[str] = Field(None, description="Programming language")


class ExampleSearchRequest(BaseModel):
    """Request model for example search."""
    concept: str = Field(..., description="Concept to find examples for")
    language: Optional[str] = Field(None, description="Programming language")


# Global instances (in production, these would be properly initialized)
_embedding_provider = None
_retrieval_system = None
_search_engine = None

def get_embedding_provider():
    """Get embedding provider instance."""
    global _embedding_provider
    if _embedding_provider is None:
        from app.config.settings import get_settings
        settings = get_settings()
        _embedding_provider = OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model="nomic-embed-text",
            dim=768
        )
    return _embedding_provider

def get_retrieval_system():
    """Get retrieval system instance."""
    global _retrieval_system
    if _retrieval_system is None:
        provider = get_embedding_provider()
        _retrieval_system = SmartRetrievalSystem(provider)
    return _retrieval_system

def get_search_engine():
    """Get search engine instance."""
    global _search_engine
    if _search_engine is None:
        retrieval_system = get_retrieval_system()
        provider = get_embedding_provider()
        _search_engine = SemanticSearchEngine(retrieval_system, provider)
    return _search_engine

# API Endpoints

@router.post("/embeddings/code")
async def generate_code_embedding(
    request: CodeEmbeddingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate embedding for code."""
    try:
        provider = get_embedding_provider()
        generator = CodeEmbeddingGenerator(provider)
        
        embeddings = await generator.generate_all_embeddings(
            component_id=request.component_id,
            code=request.code,
            language=request.language,
            context=request.context
        )
        
        # Add to retrieval system
        retrieval_system = get_retrieval_system()
        for embedding in embeddings:
            await retrieval_system.add_code_embedding(embedding)
        
        return {
            "success": True,
            "embeddings_generated": len(embeddings),
            "embedding_ids": [emb.embedding_id for emb in embeddings],
            "component_id": request.component_id,
            "language": request.language
        }
        
    except Exception as e:
        logger.error(f"Error generating code embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/pattern")
async def generate_pattern_embedding(
    request: PatternEmbeddingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate embedding for a design pattern."""
    try:
        provider = get_embedding_provider()
        generator = PatternEmbeddingGenerator(provider)
        
        embedding = await generator.generate_pattern_embedding(request.pattern_name)
        
        # Add to retrieval system
        retrieval_system = get_retrieval_system()
        await retrieval_system.add_pattern_embedding(embedding)
        
        return {
            "success": True,
            "embedding_id": embedding.embedding_id,
            "pattern_name": embedding.pattern_name,
            "pattern_type": embedding.pattern_type.value,
            "description": embedding.description
        }
        
    except Exception as e:
        logger.error(f"Error generating pattern embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/documentation")
async def generate_documentation_embedding(
    request: DocumentationEmbeddingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate embedding for documentation."""
    try:
        from app.embeddings.documentation_embeddings import DocumentationType
        
        provider = get_embedding_provider()
        generator = DocumentationEmbeddingGenerator(provider)
        
        doc_type = DocumentationType(request.doc_type)
        embedding = await generator.generate_documentation_embedding(
            doc_id=request.doc_id,
            content=request.content,
            doc_type=doc_type,
            file_path=request.file_path
        )
        
        # Add to retrieval system
        retrieval_system = get_retrieval_system()
        await retrieval_system.add_documentation_embedding(embedding)
        
        return {
            "success": True,
            "embedding_id": embedding.embedding_id,
            "doc_id": embedding.doc_id,
            "doc_type": embedding.doc_type.value,
            "summary": embedding.summary,
            "section_count": len(embedding.sections)
        }
        
    except Exception as e:
        logger.error(f"Error generating documentation embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embeddings/usage")
async def generate_usage_embedding(
    request: UsageEmbeddingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Generate embedding for usage example."""
    try:
        from app.embeddings.usage_embeddings import UsageType
        
        provider = get_embedding_provider()
        generator = UsageExampleEmbeddingGenerator(provider)
        
        usage_type = UsageType(request.usage_type)
        embedding = await generator.generate_usage_embedding(
            example_id=request.example_id,
            code=request.code,
            description=request.description,
            usage_type=usage_type,
            context=request.context,
            tags=request.tags,
            language=request.language
        )
        
        # Add to retrieval system
        retrieval_system = get_retrieval_system()
        await retrieval_system.add_usage_embedding(embedding)
        
        return {
            "success": True,
            "embedding_id": embedding.embedding_id,
            "example_id": embedding.example_id,
            "usage_type": embedding.usage_type.value,
            "language": embedding.language,
            "tag_count": len(embedding.tags)
        }
        
    except Exception as e:
        logger.error(f"Error generating usage embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def semantic_search(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Perform advanced semantic search."""
    try:
        search_engine = get_search_engine()
        
        # Convert request
        search_request = SearchRequest(
            query=request.query,
            intent=SearchIntent(request.intent) if request.intent else None,
            scope=SearchScope(request.scope),
            language=request.language,
            context=request.context,
            max_results=request.max_results,
            min_confidence=request.min_confidence,
            include_related=request.include_related,
            explain_results=request.explain_results
        )
        
        # Perform search
        results = await search_engine.search(search_request)
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "snippet": result.snippet,
                "context_lines": result.context_lines,
                "related_items": result.related_items,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "suggestions": result.suggestions,
                "item_type": type(result.result.item).__name__,
                "match_type": result.result.match_type,
                "relevance_score": result.result.relevance_score
            })
        
        return {
            "success": True,
            "query": request.query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_metadata": {
                "intent": search_request.intent.value if search_request.intent else None,
                "scope": search_request.scope.value,
                "language": search_request.language
            }
        }
        
    except Exception as e:
        logger.error(f"Error performing semantic search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/code")
async def search_code(
    request: CodeSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search specifically for code."""
    try:
        search_engine = get_search_engine()
        
        results = await search_engine.search_code(
            query=request.query,
            language=request.language,
            context=request.context
        )
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "snippet": result.snippet,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "suggestions": result.suggestions,
                "component_id": result.result.item.component_id,
                "language": result.result.item.metadata.get("language"),
                "embedding_type": result.result.item.embedding_type.value
            })
        
        return {
            "success": True,
            "query": request.query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error searching code: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/pattern")
async def search_pattern(
    request: PatternSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search for design patterns."""
    try:
        search_engine = get_search_engine()
        
        results = await search_engine.find_pattern(
            pattern_name=request.pattern_name,
            language=request.language
        )
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "snippet": result.snippet,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "suggestions": result.suggestions,
                "pattern_name": result.result.item.pattern_name,
                "pattern_type": result.result.item.pattern_type.value,
                "description": result.result.item.description,
                "examples": result.result.item.examples
            })
        
        return {
            "success": True,
            "pattern_name": request.pattern_name,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error searching pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/examples")
async def search_examples(
    request: ExampleSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search for usage examples."""
    try:
        search_engine = get_search_engine()
        
        results = await search_engine.get_examples(
            concept=request.concept,
            language=request.language
        )
        
        formatted_results = []
        for result in results:
            formatted_results.append({
                "snippet": result.snippet,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "suggestions": result.suggestions,
                "example_id": result.result.item.example_id,
                "usage_type": result.result.item.usage_type.value,
                "language": result.result.item.language,
                "tags": result.result.item.tags,
                "description": result.result.item.description
            })
        
        return {
            "success": True,
            "concept": request.concept,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error searching examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/analytics")
async def get_search_analytics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get search analytics."""
    try:
        search_engine = get_search_engine()
        analytics = await search_engine.get_search_analytics()
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error getting search analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/embeddings/statistics")
async def get_embedding_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get embedding system statistics."""
    try:
        retrieval_system = get_retrieval_system()
        stats = await retrieval_system.get_statistics()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting embedding statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/detect")
async def detect_patterns_in_code(
    code: str = Body(..., embed=True),
    language: str = Body(..., embed=True),
    similarity_threshold: float = Body(0.7, embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Detect design patterns in code."""
    try:
        provider = get_embedding_provider()
        generator = PatternEmbeddingGenerator(provider)
        
        detected_patterns = await generator.detect_patterns_in_code(
            code=code,
            language=language,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "success": True,
            "detected_patterns": detected_patterns,
            "total_patterns": len(detected_patterns),
            "language": language,
            "similarity_threshold": similarity_threshold
        }
        
    except Exception as e:
        logger.error(f"Error detecting patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documentation/search")
async def search_documentation(
    query: str = Body(..., embed=True),
    doc_type: Optional[str] = Body(None, embed=True),
    language: Optional[str] = Body(None, embed=True),
    limit: int = Body(10, embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search documentation semantically."""
    try:
        provider = get_embedding_provider()
        generator = DocumentationEmbeddingGenerator(provider)
        retrieval_system = get_retrieval_system()
        
        # Get all documentation embeddings
        doc_embeddings = retrieval_system._documentation_embeddings
        
        # Filter by doc type if specified
        if doc_type:
            from app.embeddings.documentation_embeddings import DocumentationType
            doc_type_enum = DocumentationType(doc_type)
            doc_embeddings = [emb for emb in doc_embeddings if emb.doc_type == doc_type_enum]
        
        # Filter by language if specified
        if language:
            doc_embeddings = [emb for emb in doc_embeddings 
                           if emb.metadata.get("language") == language]
        
        # Search
        search_results = await generator.search_documentation(
            query=query,
            doc_embeddings=doc_embeddings,
            limit=limit
        )
        
        formatted_results = []
        for doc_emb, similarity in search_results:
            formatted_results.append({
                "doc_id": doc_emb.doc_id,
                "doc_type": doc_emb.doc_type.value,
                "summary": doc_emb.summary,
                "sections": doc_emb.sections,
                "similarity": similarity,
                "language": doc_emb.metadata.get("language"),
                "content_length": doc_emb.metadata.get("content_length")
            })
        
        return {
            "success": True,
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error searching documentation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/usage/similar")
async def find_similar_examples(
    target_code: str = Body(..., embed=True),
    language: Optional[str] = Body(None, embed=True),
    limit: int = Body(5, embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Find usage examples similar to target code."""
    try:
        provider = get_embedding_provider()
        generator = UsageExampleEmbeddingGenerator(provider)
        retrieval_system = get_retrieval_system()
        
        usage_embeddings = retrieval_system._usage_embeddings
        
        similar_examples = await generator.find_similar_examples(
            target_code=target_code,
            usage_embeddings=usage_embeddings,
            language=language,
            limit=limit
        )
        
        formatted_results = []
        for usage_emb, similarity in similar_examples:
            formatted_results.append({
                "example_id": usage_emb.example_id,
                "usage_type": usage_emb.usage_type.value,
                "description": usage_emb.description,
                "language": usage_emb.language,
                "tags": usage_emb.tags,
                "similarity": similarity,
                "code_length": usage_emb.metadata.get("code_length")
            })
        
        return {
            "success": True,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        logger.error(f"Error finding similar examples: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/embeddings/clear")
async def clear_all_embeddings(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Clear all embeddings from the system."""
    try:
        retrieval_system = get_retrieval_system()
        await retrieval_system.clear_all()
        
        return {"message": "All embeddings cleared successfully"}
        
    except Exception as e:
        logger.error(f"Error clearing embeddings: {e}")
        raise HTTPException(status_code=500, detail=str(e))
