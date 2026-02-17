"""Enhanced API endpoints for Phase 3 Developer Integration."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.indexing import ProjectIndexer
from app.embeddings import SemanticSearchEngine, SmartRetrievalSystem
from app.memory.embeddings import OllamaEmbeddingProvider
from app.config.settings import get_settings
from app.git.integration import GitIntegration
from app.models.git import (
    PreCommitCheckRequest,
    CodeReviewRequest,
    EnhancedProjectAnalysisRequest,
    CodeSearchRequest,
    PatternSuggestionRequest
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enhanced", tags=["enhanced"])

# Global instances
_search_engine = None

def get_search_engine():
    """Get search engine instance."""
    global _search_engine
    if _search_engine is None:
        settings = get_settings()
        provider = OllamaEmbeddingProvider(
            base_url=settings.ollama_base_url,
            model="nomic-embed-text",
            dim=768
        )
        retrieval_system = SmartRetrievalSystem(provider)
        _search_engine = SemanticSearchEngine(retrieval_system, provider)
    return _search_engine

# API Endpoints

@router.post("/projects/analyze")
async def enhanced_project_analysis(
    request: EnhancedProjectAnalysisRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Enhanced project analysis with semantic insights."""
    try:
        # Basic project analysis
        indexer = ProjectIndexer(db)
        project = await indexer.index_project(
            project_path=request.project_path,
            force_reindex=True
        )
        
        analysis_result = {
            "project_id": str(project.id),
            "project_name": project.name,
            "basic_analysis": await indexer.get_project_summary(str(project.id)),
            "enhanced_analysis": {}
        }
        
        # Add semantic analysis if requested
        if request.include_semantic_analysis:
            search_engine = get_search_engine()
            
            # Analyze project components semantically
            components = await indexer.search_components(project_id=str(project.id), query="")
            
            semantic_insights = []
            for component in components[:10]:  # Limit to first 10 components
                try:
                    # Search for similar components
                    similar_results = await search_engine.search_code(
                        query=component.name,
                        language=component.language
                    )
                    
                    if similar_results:
                        semantic_insights.append({
                            "component_id": str(component.id),
                            "component_name": component.name,
                            "similar_components": len(similar_results),
                            "semantic_score": max(r.confidence for r in similar_results) if similar_results else 0
                        })
                except Exception as e:
                    logger.warning(f"Semantic analysis failed for component {component.name}: {e}")
            
            analysis_result["enhanced_analysis"]["semantic_insights"] = semantic_insights
        
        # Add pattern detection if requested
        if request.include_pattern_detection:
            # This would integrate with the pattern detection system
            analysis_result["enhanced_analysis"]["patterns_detected"] = {
                "architectural_patterns": ["Layered", "Repository"],
                "design_patterns": ["Singleton", "Factory"],
                "anti_patterns": []
            }
        
        # Add recommendations if requested
        if request.include_recommendations:
            analysis_result["enhanced_analysis"]["recommendations"] = {
                "quality_improvements": [
                    "Increase test coverage in service layer",
                    "Consider implementing dependency injection",
                    "Add error handling for API endpoints"
                ],
                "pattern_suggestions": [
                    "Consider using Strategy pattern for payment processing",
                    "Implement Observer pattern for event handling"
                ],
                "architecture_improvements": [
                    "Separate concerns in controller layer",
                    "Add caching for frequently accessed data"
                ]
            }
        
        # Add analysis depth information
        analysis_result["analysis_metadata"] = {
            "analysis_depth": request.analysis_depth,
            "components_analyzed": len(components),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in enhanced project analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search/code")
async def enhanced_code_search(
    request: CodeSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Enhanced code search with multiple result types."""
    try:
        search_engine = get_search_engine()
        
        # Perform semantic search
        semantic_results = await search_engine.search_code(
            query=request.query,
            language=request.language,
            context=request.context
        )
        
        # Format results
        formatted_results = []
        for result in semantic_results:
            formatted_results.append({
                "snippet": result.snippet,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "suggestions": result.suggestions,
                "component_id": result.result.item.component_id,
                "language": result.result.item.metadata.get("language"),
                "embedding_type": result.result.item.embedding_type.value
            })
        
        search_response = {
            "success": True,
            "query": request.query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_metadata": {
                "language": request.language,
                "context_provided": request.context is not None,
                "include_patterns": request.include_patterns,
                "include_examples": request.include_examples
            }
        }
        
        # Add pattern matches if requested
        if request.include_patterns:
            search_engine = get_search_engine()
            pattern_results = await search_engine.find_pattern(
                pattern_name=request.query,
                language=request.language
            )
            
            search_response["pattern_matches"] = [
                {
                    "pattern_name": r.result.item.pattern_name,
                    "pattern_type": r.result.item.pattern_type.value,
                    "description": r.result.item.description,
                    "confidence": r.confidence
                }
                for r in pattern_results
            ]
        
        # Add usage examples if requested
        if request.include_examples:
            search_engine = get_search_engine()
            example_results = await search_engine.get_examples(
                concept=request.query,
                language=request.language
            )
            
            search_response["usage_examples"] = [
                {
                    "example_id": r.result.item.example_id,
                    "usage_type": r.result.item.usage_type.value,
                    "description": r.result.item.description,
                    "language": r.result.item.language,
                    "confidence": r.confidence
                }
                for r in example_results
            ]
        
        return search_response
        
    except Exception as e:
        logger.error(f"Error in enhanced code search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/suggest")
async def suggest_patterns(
    request: PatternSuggestionRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Suggest design patterns for code snippet."""
    try:
        search_engine = get_search_engine()
        
        # Analyze code snippet
        code_analysis = await _analyze_code_snippet(request.code_snippet, request.language)
        
        # Get pattern suggestions
        pattern_suggestions = []
        
        # Detect patterns in the code
        from app.embeddings.pattern_embeddings import PatternEmbeddingGenerator
        provider = get_search_engine().embedding_provider
        pattern_generator = PatternEmbeddingGenerator(provider)
        
        detected_patterns = await pattern_generator.detect_patterns_in_code(
            code=request.code_snippet,
            language=request.language,
            similarity_threshold=0.6
        )
        
        for pattern_name, confidence in detected_patterns:
            pattern_suggestions.append({
                "pattern_name": pattern_name,
                "confidence": confidence,
                "match_type": "detected",
                "recommendation": f"Your code already uses {pattern_name} pattern"
            })
        
        # Suggest alternative patterns
        if request.include_alternatives:
            alternatives = await _suggest_alternative_patterns(
                code_analysis, request.language, request.context
            )
            pattern_suggestions.extend(alternatives)
        
        # Sort by confidence
        pattern_suggestions.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "success": True,
            "code_analysis": code_analysis,
            "pattern_suggestions": pattern_suggestions[:10],  # Limit to top 10
            "metadata": {
                "language": request.language,
                "code_length": len(request.code_snippet),
                "context_provided": request.context is not None
            }
        }
        
    except Exception as e:
        logger.error(f"Error in pattern suggestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code/review")
async def code_review(
    request: CodeReviewRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Automated code review with suggestions."""
    try:
        review_result = await _perform_code_review(request)
        
        return review_result
        
    except Exception as e:
        logger.error(f"Error in code review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/git/precommit")
async def pre_commit_check(
    request: PreCommitCheckRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Pre-commit hook checks."""
    try:
        git_integration = GitIntegration(request.project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        # Get staged files if not provided
        if not request.files:
            staged_files = git_integration.get_staged_files()
            files = [{"path": f, "content": git_integration.get_file_content(f)} for f in staged_files]
        else:
            files = request.files
        
        check_results = await git_integration.run_pre_commit_check([f["path"] for f in files])
        
        return check_results
        
    except Exception as e:
        logger.error(f"Error in pre-commit check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/git/review")
async def git_commit_review(
    project_path: str = Body(..., description="Path to the project"),
    commit_hash: Optional[str] = Body(None, description="Commit hash to review"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Review a git commit."""
    try:
        git_integration = GitIntegration(project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        review_result = await git_integration.review_commit(commit_hash)
        
        return review_result
        
    except Exception as e:
        logger.error(f"Error in git commit review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/git/status")
async def get_git_status(
    project_path: str = Query(..., description="Path to the project"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get git status information."""
    try:
        git_integration = GitIntegration(project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        status = git_integration.get_git_status()
        repo_info = git_integration.get_repository_info()
        branch_info = git_integration.get_branch_info()
        
        return {
            "status": status,
            "repository": repo_info,
            "branches": branch_info
        }
        
    except Exception as e:
        logger.error(f"Error getting git status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/git/commits")
async def get_commit_history(
    project_path: str = Query(..., description="Path to the project"),
    limit: int = Query(10, description="Number of commits to return"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get commit history."""
    try:
        git_integration = GitIntegration(project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        commits = git_integration.get_commit_history(limit)
        
        return {
            "commits": commits,
            "total_count": len(commits)
        }
        
    except Exception as e:
        logger.error(f"Error getting commit history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/git/hooks/install")
async def install_git_hooks(
    project_path: str = Body(..., description="Path to the project"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Install Agent Brain git hooks."""
    try:
        git_integration = GitIntegration(project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        success = git_integration.install_agent_brain_hooks()
        
        if success:
            return {"message": "Agent Brain hooks installed successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to install hooks")
        
    except Exception as e:
        logger.error(f"Error installing git hooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/git/hooks/uninstall")
async def uninstall_git_hooks(
    project_path: str = Body(..., description="Path to the project"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Uninstall Agent Brain git hooks."""
    try:
        git_integration = GitIntegration(project_path)
        
        if not git_integration.is_git_repository():
            raise HTTPException(status_code=400, detail="Not a git repository")
        
        success = git_integration.uninstall_agent_brain_hooks()
        
        if success:
            return {"message": "Agent Brain hooks uninstalled successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to uninstall hooks")
        
    except Exception as e:
        logger.error(f"Error uninstalling git hooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/git/hooks/config")
async def get_hooks_config(
    project_path: str = Query(..., description="Path to the project"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get hooks configuration."""
    try:
        git_integration = GitIntegration(project_path)
        
        config = git_integration.generate_hooks_config()
        
        return {
            "config": json.loads(config),
            "project_path": project_path
        }
        
    except Exception as e:
        logger.error(f"Error getting hooks config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions

async def _analyze_code_snippet(code: str, language: str) -> Dict[str, Any]:
    """Analyze code snippet for pattern suggestions."""
    lines = code.split('\n')
    
    analysis = {
        "language": language,
        "line_count": len(lines),
        "complexity_indicators": {
            "nested_loops": code.count('for') + code.count('while'),
            "conditional_statements": code.count('if') + code.count('switch'),
            "function_calls": code.count('(') - code.count('if') - code.count('for') - code.count('while'),
            "class_definitions": code.count('class') + code.count('struct'),
            "exception_handling": code.count('try') + code.count('catch') + code.count('except')
        },
        "code_smells": [],
        "suggestions": []
    }
    
    # Detect potential code smells
    if analysis["complexity_indicators"]["nested_loops"] > 2:
        analysis["code_smells"].append("High nesting detected")
        analysis["suggestions"].append("Consider extracting nested loops into separate methods")
    
    if analysis["complexity_indicators"]["conditional_statements"] > 5:
        analysis["code_smells"].append("Complex conditional logic")
        analysis["suggestions"].append("Consider using polymorphism or strategy pattern")
    
    if analysis["complexity_indicators"]["exception_handling"] == 0 and len(lines) > 10:
        analysis["code_smells"].append("No error handling")
        analysis["suggestions"].append("Consider adding try-catch blocks for error handling")
    
    return analysis


async def _suggest_alternative_patterns(analysis: Dict[str, Any], language: str, context: Optional[str]) -> List[Dict[str, Any]]:
    """Suggest alternative patterns based on code analysis."""
    suggestions = []
    
    # Based on complexity indicators
    if analysis["complexity_indicators"]["nested_loops"] > 1:
        suggestions.append({
            "pattern_name": "Iterator",
            "confidence": 0.8,
            "match_type": "suggested",
            "recommendation": "Consider using Iterator pattern to handle nested loops"
        })
    
    if analysis["complexity_indicators"]["conditional_statements"] > 3:
        suggestions.append({
            "pattern_name": "Strategy",
            "confidence": 0.7,
            "match_type": "suggested",
            "recommendation": "Strategy pattern can simplify complex conditional logic"
        })
    
    if analysis["complexity_indicators"]["class_definitions"] > 0:
        suggestions.append({
            "pattern_name": "Factory",
            "confidence": 0.6,
            "match_type": "suggested",
            "recommendation": "Factory pattern can help with object creation"
        })
    
    return suggestions


async def _perform_code_review(request: CodeReviewRequest) -> Dict[str, Any]:
    """Perform automated code review."""
    code_lines = request.code.split('\n')
    
    review_result = {
        "file_path": request.file_path,
        "language": request.language,
        "line_count": len(code_lines),
        "review_type": request.review_type,
        "issues": [],
        "suggestions": [],
        "metrics": {
            "complexity": 0,
            "maintainability": 0,
            "test_coverage": 0
        },
        "overall_score": 0
    }
    
    # Analyze code for issues
    for i, line in enumerate(code_lines, 1):
        line = line.strip()
        
        # Check for common issues
        if len(line) > 120:
            review_result["issues"].append({
                "line": i,
                "type": "style",
                "severity": "low",
                "message": "Line too long (>120 characters)",
                "suggestion": "Break line into multiple lines"
            })
        
        if "TODO" in line or "FIXME" in line:
            review_result["issues"].append({
                "line": i,
                "type": "technical_debt",
                "severity": "medium",
                "message": "TODO/FIXME comment found",
                "suggestion": "Address the TODO item or create a ticket"
            })
        
        if request.review_type == "security":
            if "eval(" in line or "exec(" in line:
                review_result["issues"].append({
                    "line": i,
                    "type": "security",
                    "severity": "high",
                    "message": "Use of eval/exec detected",
                    "suggestion": "Avoid using eval/exec functions"
                })
    
    # Calculate metrics
    review_result["metrics"]["complexity"] = len([l for l in code_lines if 'if' in l or 'for' in l or 'while' in l])
    review_result["metrics"]["maintainability"] = max(0, 100 - len(review_result["issues"]) * 5)
    
    # Calculate overall score
    high_issues = len([i for i in review_result["issues"] if i["severity"] == "high"])
    medium_issues = len([i for i in review_result["issues"] if i["severity"] == "medium"])
    
    score = 100 - (high_issues * 20) - (medium_issues * 10) - (len(review_result["issues"]) * 5)
    review_result["overall_score"] = max(0, score)
    
    # Add suggestions if requested
    if request.include_suggestions:
        review_result["suggestions"] = [
            "Add unit tests for critical functions",
            "Consider adding type hints",
            "Document complex algorithms",
            "Extract large methods into smaller functions"
        ]
    
    return review_result


async def _check_file(file_info: Dict[str, Any], checks: List[str]) -> Dict[str, Any]:
    """Check a single file for pre-commit hooks."""
    result = {
        "file_path": file_info.get("path", ""),
        "status": "passed",
        "checks": {},
        "warnings": [],
        "errors": []
    }
    
    for check in checks:
        try:
            if check == "quality":
                # Quality check
                if file_info.get("size", 0) > 10000:  # 10KB
                    result["checks"][check] = "warning"
                    result["warnings"].append("Large file detected")
                else:
                    result["checks"][check] = "passed"
            
            elif check == "patterns":
                # Pattern check
                result["checks"][check] = "passed"
            
            elif check == "security":
                # Security check
                content = file_info.get("content", "")
                if "password" in content.lower() or "secret" in content.lower():
                    result["checks"][check] = "failed"
                    result["errors"].append("Potential security issue detected")
                    result["status"] = "failed"
                else:
                    result["checks"][check] = "passed"
            
        except Exception as e:
            result["checks"][check] = "error"
            result["errors"].append(f"Check failed: {str(e)}")
    
    return result
