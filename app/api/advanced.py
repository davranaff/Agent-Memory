"""Advanced API endpoints for Phase 4 features."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.autocomplete import AutocompleteEngine
from app.autocomplete.models import AutocompleteRequest, AutocompleteResponse
from app.error_prevention import ErrorPreventionEngine
from app.error_prevention.models import ErrorPreventionRequest, ErrorPreventionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/advanced", tags=["advanced"])

# Global instances
_autocomplete_engine = None
_error_prevention_engine = None

def get_autocomplete_engine():
    """Get autocomplete engine instance."""
    global _autocomplete_engine
    if _autocomplete_engine is None:
        _autocomplete_engine = AutocompleteEngine()
    return _autocomplete_engine

def get_error_prevention_engine():
    """Get error prevention engine instance."""
    global _error_prevention_engine
    if _error_prevention_engine is None:
        _error_prevention_engine = ErrorPreventionEngine()
    return _error_prevention_engine

# Autocomplete endpoints

@router.post("/autocomplete/suggestions")
async def get_autocomplete_suggestions(
    request: AutocompleteRequest,
    db: AsyncSession = Depends(get_db)
) -> AutocompleteResponse:
    """Get context-aware autocomplete suggestions."""
    try:
        engine = get_autocomplete_engine()
        response = await engine.get_suggestions(request)
        return response
    except Exception as e:
        logger.error(f"Error in autocomplete suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/autocomplete/context")
async def analyze_code_context(
    code: str = Body(..., description="Code to analyze"),
    cursor_position: int = Body(..., description="Cursor position in code"),
    language: str = Body(..., description="Programming language"),
    file_path: Optional[str] = Body(None, description="File path for context"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze code context for autocomplete."""
    try:
        engine = get_autocomplete_engine()
        context = await engine.get_context(code, cursor_position, language, file_path)
        
        return {
            "success": True,
            "context": {
                "language": context.language,
                "file_path": context.file_path,
                "cursor_position": context.cursor_position,
                "current_line": context.current_line,
                "scope": context.scope,
                "imports": context.imports,
                "variables": context.variables,
                "functions": context.functions,
                "classes": context.classes
            }
        }
    except Exception as e:
        logger.error(f"Error analyzing code context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/autocomplete/cache/stats")
async def get_autocomplete_cache_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get autocomplete cache statistics."""
    try:
        engine = get_autocomplete_engine()
        stats = engine.get_cache_stats()
        return {
            "success": True,
            "cache_stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/autocomplete/cache/clear")
async def clear_autocomplete_cache(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Clear autocomplete cache."""
    try:
        engine = get_autocomplete_engine()
        engine.clear_cache()
        return {"message": "Autocomplete cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Error Prevention endpoints

@router.post("/error-prevention/analyze")
async def analyze_code_for_errors(
    request: ErrorPreventionRequest,
    db: AsyncSession = Depends(get_db)
) -> ErrorPreventionResponse:
    """Analyze code for potential errors."""
    try:
        engine = get_error_prevention_engine()
        response = await engine.analyze_code(request)
        return response
    except Exception as e:
        logger.error(f"Error in error prevention analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/error-prevention/rules")
async def get_error_prevention_rules(
    language: Optional[str] = Query(None, description="Filter by programming language"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get available error prevention rules."""
    try:
        engine = get_error_prevention_engine()
        rules = engine.get_available_rules(language)
        
        return {
            "success": True,
            "rules": rules,
            "total_count": len(rules)
        }
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/error-prevention/rules/enable")
async def enable_error_prevention_rule(
    rule_name: str = Body(..., description="Name of the rule to enable"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Enable an error prevention rule."""
    try:
        engine = get_error_prevention_engine()
        success = engine.enable_rule(rule_name)
        
        if success:
            return {"message": f"Rule '{rule_name}' enabled successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/error-prevention/rules/disable")
async def disable_error_prevention_rule(
    rule_name: str = Body(..., description="Name of the rule to disable"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Disable an error prevention rule."""
    try:
        engine = get_error_prevention_engine()
        success = engine.disable_rule(rule_name)
        
        if success:
            return {"message": f"Rule '{rule_name}' disabled successfully"}
        else:
            raise HTTPException(status_code=404, detail=f"Rule '{rule_name}' not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/error-prevention/rules/statistics")
async def get_error_prevention_statistics(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get error prevention rule statistics."""
    try:
        engine = get_error_prevention_engine()
        stats = engine.get_rule_statistics()
        
        return {
            "success": True,
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/error-prevention/autofix")
async def apply_auto_fixes(
    issue_ids: List[str] = Body(..., description="List of issue IDs to fix"),
    code: str = Body(..., description="Original code"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Apply automatic fixes to code issues."""
    try:
        engine = get_error_prevention_engine()
        fixes = await engine.apply_auto_fixes(issue_ids, code)
        
        return {
            "success": True,
            "fixes": [
                {
                    "issue_id": fix.issue_id,
                    "description": fix.description,
                    "confidence": fix.confidence,
                    "applied": fix.applied
                }
                for fix in fixes
            ],
            "total_fixes": len(fixes)
        }
    except Exception as e:
        logger.error(f"Error applying auto-fixes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Combined analysis endpoint

@router.post("/code/analysis")
async def comprehensive_code_analysis(
    code: str = Body(..., description="Code to analyze"),
    language: str = Body(..., description="Programming language"),
    cursor_position: Optional[int] = Body(None, description="Cursor position for autocomplete"),
    file_path: Optional[str] = Body(None, description="File path for context"),
    include_autocomplete: bool = Body(True, description="Include autocomplete suggestions"),
    include_error_prevention: bool = Body(True, description="Include error prevention"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Comprehensive code analysis combining autocomplete and error prevention."""
    try:
        results = {}
        
        # Autocomplete analysis
        if include_autocomplete and cursor_position is not None:
            autocomplete_engine = get_autocomplete_engine()
            context = await autocomplete_engine.get_context(code, cursor_position, language, file_path)
            
            autocomplete_request = AutocompleteRequest(
                context=context,
                query=code[:cursor_position].split()[-1] if cursor_position > 0 else "",
                max_results=10,
                include_snippets=True,
                include_patterns=True,
                language_specific=True
            )
            
            autocomplete_response = await autocomplete_engine.get_suggestions(autocomplete_request)
            results["autocomplete"] = {
                "success": True,
                "suggestions": [
                    {
                        "text": s.text,
                        "display_text": s.display_text,
                        "type": s.type.value,
                        "priority": s.priority.value,
                        "description": s.description,
                        "confidence": s.confidence
                    }
                    for s in autocomplete_response.suggestions
                ],
                "processing_time_ms": autocomplete_response.processing_time_ms
            }
        
        # Error prevention analysis
        if include_error_prevention:
            error_engine = get_error_prevention_engine()
            
            error_request = ErrorPreventionRequest(
                code=code,
                language=language,
                file_path=file_path,
                max_issues=20
            )
            
            error_response = await error_engine.analyze_code(error_request)
            results["error_prevention"] = {
                "success": True,
                "issues": [
                    {
                        "id": issue.id,
                        "title": issue.title,
                        "severity": issue.severity.value,
                        "category": issue.category.value,
                        "line_number": issue.line_number,
                        "description": issue.description,
                        "suggestion": issue.suggestion,
                        "auto_fix": issue.auto_fix,
                        "confidence": issue.confidence
                    }
                    for issue in error_response.issues
                ],
                "total_issues": error_response.total_issues,
                "auto_fixes_available": error_response.auto_fixes_available,
                "processing_time_ms": error_response.processing_time_ms
            }
        
        return {
            "success": True,
            "analysis": results,
            "metadata": {
                "language": language,
                "file_path": file_path,
                "code_length": len(code),
                "cursor_position": cursor_position,
                "include_autocomplete": include_autocomplete,
                "include_error_prevention": include_error_prevention
            }
        }
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))
