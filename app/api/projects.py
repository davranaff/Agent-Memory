"""Project analysis API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel, Field

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.indexing import ProjectIndexer
from app.dependencies import GraphDependencyService
from app.profiling import TechnologyStackProfiler
from app.patterns import ArchitecturePatternDetector
from app.registry import ComponentRegistry, ComponentSearch, ComponentAnalytics
from app.parsing import parse_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_graph_dependency_service(
    db: AsyncSession = Depends(get_db),
) -> GraphDependencyService:
    return GraphDependencyService(db)


# Pydantic models for API
class ProjectAnalysisRequest(BaseModel):
    """Request model for project analysis."""
    project_path: str = Field(..., description="Path to the project directory")
    project_name: Optional[str] = Field(None, description="Name for the project")
    force_reindex: bool = Field(False, description="Force reindexing even if already analyzed")
    analysis_options: Dict[str, Any] = Field(default_factory=dict, description="Analysis options")


class ProjectAnalysisResponse(BaseModel):
    """Response model for project analysis."""
    project_id: str
    project_name: str
    analysis_status: str
    analysis_timestamp: str
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


class ComponentSearchRequest(BaseModel):
    """Request model for component search."""
    query: str = Field(..., description="Search query")
    search_type: str = Field("fuzzy", description="Type of search")
    filters: Dict[str, Any] = Field(default_factory=dict, description="Search filters")
    limit: int = Field(50, description="Maximum number of results")
    offset: int = Field(0, description="Offset for pagination")


class ComponentAnalysisRequest(BaseModel):
    """Request model for component analysis."""
    component_id: str = Field(..., description="ID of the component to analyze")
    include_comparisons: bool = Field(True, description="Include similar components comparison")
    include_recommendations: bool = Field(True, description="Include improvement recommendations")


class DependencyAnalysisRequest(BaseModel):
    """Request model for dependency analysis."""
    project_id: str = Field(..., description="ID of the project")
    include_impact_analysis: bool = Field(True, description="Include change impact analysis")
    component_id: Optional[str] = Field(None, description="Specific component for impact analysis")


class TechnologyStackRequest(BaseModel):
    """Request model for technology stack analysis."""
    project_id: str = Field(..., description="ID of the project")
    include_recommendations: bool = Field(True, description="Include improvement recommendations")
    export_format: str = Field("json", description="Export format")


class GraphSyncRequest(BaseModel):
    """Request model for dependency graph synchronization."""

    project_id: str = Field(..., description="ID of the project to sync into graph backend")
    changed_files: List[str] = Field(
        default_factory=list,
        description="Optional changed file paths for incremental graph sync",
    )


# API Endpoints

@router.post("/analyze", response_model=ProjectAnalysisResponse)
async def analyze_project(
    request: ProjectAnalysisRequest,
    db: AsyncSession = Depends(get_db)
) -> ProjectAnalysisResponse:
    """Analyze a project and extract comprehensive information."""
    try:
        # Initialize indexer
        indexer = ProjectIndexer(db)
        
        # Perform project analysis
        project = await indexer.index_project(
            project_path=request.project_path,
            project_name=request.project_name,
            force_reindex=request.force_reindex
        )
        
        # Get project summary
        summary = await indexer.get_project_summary(str(project.id))
        
        return ProjectAnalysisResponse(
            project_id=str(project.id),
            project_name=project.name,
            analysis_status=project.analysis_status,
            analysis_timestamp=project.last_analyzed.isoformat() if project.last_analyzed else "",
            summary=summary,
            metadata={
                "total_files": project.total_files,
                "total_lines": project.total_lines,
                "architecture_type": project.architecture_type,
                "tech_stack": project.tech_stack,
                "frameworks": project.frameworks,
                "languages": project.languages,
                "databases": project.databases,
                "build_tools": project.build_tools
            }
        )
        
    except Exception as e:
        logger.error(f"Error analyzing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/summary")
async def get_project_summary(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive summary of a project."""
    try:
        indexer = ProjectIndexer(db)
        summary = await indexer.get_project_summary(project_id)
        return summary
    except Exception as e:
        logger.error(f"Error getting project summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/components")
async def get_project_components(
    project_id: str,
    component_type: Optional[str] = Query(None, description="Filter by component type"),
    language: Optional[str] = Query(None, description="Filter by language"),
    limit: int = Query(100, description="Maximum number of components"),
    offset: int = Query(0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Get all components for a project with optional filtering."""
    try:
        indexer = ProjectIndexer(db)
        
        # Convert component type string to enum if provided
        from app.parsing.base import ComponentInfo
        component_type_enum = None
        if component_type:
            try:
                component_type_enum = component_type  # Use as string for now
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid component type: {component_type}")
        
        components = await indexer.search_components(
            project_id=project_id,
            component_type=component_type_enum,
            language=language,
            limit=limit,
            offset=offset
        )
        
        return [
            {
                "id": str(comp.id),
                "name": comp.name,
                "type": comp.type,
                "path": comp.relative_path,
                "language": comp.language,
                "line_count": comp.line_count,
                "complexity_score": comp.complexity_score,
                "dependencies": comp.dependencies,
                "exports": comp.exports
            }
            for comp in components
        ]
        
    except Exception as e:
        logger.error(f"Error getting project components: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/components/search")
async def search_components(
    request: ComponentSearchRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Search for components across all projects."""
    try:
        registry = ComponentRegistry(db)
        search = ComponentSearch(registry)
        
        # Convert search type string to enum
        from app.registry.search import SearchType
        try:
            search_type_enum = SearchType(request.search_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid search type: {request.search_type}")
        
        # Create search query
        from app.registry.search import SearchQuery
        search_query = SearchQuery(
            query=request.query,
            search_type=search_type_enum,
            filters=request.filters,
            limit=request.limit,
            offset=request.offset
        )
        
        # Perform search
        response = await search.search(search_query)
        
        return {
            "results": [
                {
                    "component": {
                        "id": result.component.component_id,
                        "name": result.component.name,
                        "type": result.component.type.value,
                        "language": result.component.language,
                        "path": result.component.relative_path,
                        "summary": result.component.get_summary()
                    },
                    "relevance_score": result.relevance_score,
                    "match_highlights": result.match_highlights,
                    "match_reasons": result.match_reasons
                }
                for result in response.results
            ],
            "total_count": response.total_count,
            "query_time_ms": response.query_time_ms,
            "facets": response.facets,
            "suggestions": response.suggestions
        }
        
    except Exception as e:
        logger.error(f"Error searching components: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/components/analyze", response_model=Dict[str, Any])
async def analyze_component(
    request: ComponentAnalysisRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Perform detailed analysis of a specific component."""
    try:
        registry = ComponentRegistry(db)
        analytics = ComponentAnalytics(registry)
        
        # Get component
        component = await registry.get_component(request.component_id)
        if not component:
            raise HTTPException(status_code=404, detail="Component not found")
        
        # Perform analysis
        analysis = await analytics.analyze_component(request.component_id)
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing component: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dependencies/analyze", response_model=Dict[str, Any])
async def analyze_dependencies(
    request: DependencyAnalysisRequest,
    svc: GraphDependencyService = Depends(_get_graph_dependency_service),
) -> Dict[str, Any]:
    """Analyze dependencies and build dependency graphs."""
    try:
        return await svc.dependencies_analyze_compat(
            project_id=request.project_id,
            include_impact_analysis=request.include_impact_analysis,
            component_id=request.component_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing dependencies: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dependencies/sync", response_model=Dict[str, Any])
async def sync_dependencies_graph(
    request: GraphSyncRequest,
    svc: GraphDependencyService = Depends(_get_graph_dependency_service),
) -> Dict[str, Any]:
    """Build and sync project dependency graph into configured graph backend."""
    try:
        return await svc.sync_project_graph(
            project_id=request.project_id,
            changed_files=request.changed_files,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing dependency graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/graph/impact", response_model=Dict[str, Any])
async def get_graph_impact(
    project_id: str,
    component_id: str = Query(..., description="Component ID to analyze"),
    svc: GraphDependencyService = Depends(_get_graph_dependency_service),
) -> Dict[str, Any]:
    """Get dependency impact analysis from graph backend."""
    try:
        return await svc.graph_impact(project_id=project_id, component_id=component_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting graph impact: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/graph/path", response_model=Dict[str, Any])
async def get_graph_path(
    project_id: str,
    from_component_id: str = Query(..., description="Source component ID"),
    to_component_id: str = Query(..., description="Target component ID"),
    max_depth: int = Query(15, description="Maximum traversal depth"),
    svc: GraphDependencyService = Depends(_get_graph_dependency_service),
) -> Dict[str, Any]:
    """Find a path between two components in graph backend."""
    try:
        return await svc.graph_path(
            project_id=project_id,
            from_component_id=from_component_id,
            to_component_id=to_component_id,
            max_depth=max_depth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting graph path: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/graph/neighbors", response_model=Dict[str, Any])
async def get_graph_neighbors(
    project_id: str,
    component_id: str = Query(..., description="Component ID"),
    depth: int = Query(1, description="Traversal depth"),
    svc: GraphDependencyService = Depends(_get_graph_dependency_service),
) -> Dict[str, Any]:
    """Get neighborhood around a component in graph backend."""
    try:
        return await svc.graph_neighbors(
            project_id=project_id,
            component_id=component_id,
            depth=depth,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting graph neighbors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/technology/analyze", response_model=Dict[str, Any])
async def analyze_technology_stack(
    request: TechnologyStackRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Analyze the technology stack of a project."""
    try:
        profiler = TechnologyStackProfiler(db)
        
        # Profile the project
        stack = await profiler.profile_project(request.project_id)
        
        result = {
            "stack_summary": stack.get_stack_summary(),
            "technologies": {
                "languages": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.languages],
                "frameworks": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.frameworks],
                "databases": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.databases],
                "build_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.build_tools],
                "testing_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.testing_tools],
                "deployment_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.deployment_tools],
                "monitoring_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.monitoring_tools],
                "security_tools": [{"name": t.name, "version": t.version, "confidence": t.confidence} for t in stack.security_tools]
            },
            "analysis": {
                "confidence_score": stack.confidence_score,
                "complexity_score": stack.complexity_score,
                "modernization_score": stack.modernization_score,
                "architecture_type": stack.architecture_pattern,
                "deployment_pattern": stack.deployment_pattern
            }
        }
        
        # Add recommendations if requested
        if request.include_recommendations:
            recommendations = await profiler.get_stack_recommendations(request.project_id)
            result["recommendations"] = recommendations
        
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing technology stack: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patterns/detect", response_model=Dict[str, Any])
async def detect_architecture_patterns(
    project_id: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Detect architecture patterns in a project."""
    try:
        from app.patterns import ArchitecturePatternDetector
        
        # Get project data
        indexer = ProjectIndexer(db)
        components = await indexer.search_components(project_id=project_id, query="")
        
        # Prepare project data for pattern detection
        project_data = {
            "components": [
                {
                    "name": comp.name,
                    "type": comp.type,
                    "path": comp.relative_path,
                    "dependencies": comp.dependencies,
                    "exports": comp.exports
                }
                for comp in components
            ],
            "file_paths": [comp.path for comp in components],
            "directory_structure": list(set(comp.relative_path.split('/')[0] for comp in components if '/' in comp.relative_path))
        }
        
        # Detect patterns
        detector = ArchitecturePatternDetector()
        detected_patterns = await detector.detect_patterns(project_data)
        
        return {
            "project_id": project_id,
            "detected_patterns": detected_patterns,
            "total_patterns_detected": len(detected_patterns),
            "analysis_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error detecting architecture patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/analytics", response_model=Dict[str, Any])
async def get_project_analytics(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get comprehensive analytics for a project."""
    try:
        registry = ComponentRegistry(db)
        analytics = ComponentAnalytics(registry)
        
        # Perform project analysis
        analysis = await analytics.analyze_project(project_id)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error getting project analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/parse", response_model=Dict[str, Any])
async def parse_file_endpoint(
    file_path: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Parse a single file and extract components."""
    try:
        # Parse the file
        parse_result = await parse_file(file_path)
        
        if not parse_result.success:
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {parse_result.error_message}")
        
        return {
            "success": True,
            "file_path": file_path,
            "language": parse_result.language,
            "line_count": parse_result.line_count,
            "components": [
                {
                    "name": comp.name,
                    "type": comp.type,
                    "line_start": comp.line_start,
                    "line_end": comp.line_end,
                    "dependencies": comp.dependencies,
                    "exports": comp.exports,
                    "metadata": comp.metadata
                }
                for comp in parse_result.components
            ],
            "imports": parse_result.imports,
            "exports": parse_result.exports,
            "metadata": parse_result.metadata
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error parsing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}/health")
async def get_project_health(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Get health metrics for a project."""
    try:
        registry = ComponentRegistry(db)
        analytics = ComponentAnalytics(registry)
        
        # Get project components
        components = await registry.search_components(project_id=project_id)
        
        if not components:
            raise HTTPException(status_code=404, detail="Project not found or has no components")
        
        # Calculate health metrics
        health_metrics = {
            "overall_health": sum(comp.calculate_health_score() for comp in components) / len(components),
            "health_distribution": analytics._calculate_health_distribution(components),
            "quality_metrics": analytics._calculate_project_metrics(components)["quality_metrics"],
            "risk_factors": [],
            "recommendations": []
        }
        
        # Identify risk factors
        avg_complexity = sum(comp.code_metrics.cyclomatic_complexity for comp in components) / len(components)
        if avg_complexity > 10:
            health_metrics["risk_factors"].append("High average complexity")
        
        avg_coverage = sum(comp.code_metrics.test_coverage for comp in components) / len(components)
        if avg_coverage < 50:
            health_metrics["risk_factors"].append("Low test coverage")
        
        low_quality_count = len([c for c in components if c.calculate_quality_score() < 50])
        if low_quality_count > len(components) * 0.2:
            health_metrics["risk_factors"].append("Many low-quality components")
        
        return health_metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=Dict[str, Any])
async def compare_projects(
    project1_id: str = Body(..., embed=True),
    project2_id: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """Compare two projects."""
    try:
        profiler = TechnologyStackProfiler(db)
        
        # Compare stacks
        comparison = await profiler.compare_stacks(project1_id, project2_id)
        
        return comparison
        
    except Exception as e:
        logger.error(f"Error comparing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Dict[str, Any]])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, description="Maximum number of projects"),
    offset: int = Query(0, description="Offset for pagination")
) -> List[Dict[str, Any]]:
    """List all analyzed projects."""
    try:
        from sqlalchemy import select
        from app.core.models import Project
        
        stmt = select(Project).limit(limit).offset(offset)
        result = await db.execute(stmt)
        projects = result.scalars().all()
        
        return [
            {
                "id": str(project.id),
                "name": project.name,
                "path": project.path,
                "analysis_status": project.analysis_status,
                "last_analyzed": project.last_analyzed.isoformat() if project.last_analyzed else None,
                "total_files": project.total_files,
                "total_lines": project.total_lines,
                "architecture_type": project.architecture_type,
                "languages": project.languages,
                "frameworks": project.frameworks
            }
            for project in projects
        ]
        
    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """Delete a project and all its data."""
    try:
        from sqlalchemy import delete
        from app.core.models import Project, Component, Documentation, CodePattern
        
        # Delete in order to respect foreign key constraints
        await db.execute(delete(Documentation).where(Documentation.project_id == project_id))
        await db.execute(delete(CodePattern).where(CodePattern.project_id == project_id))
        await db.execute(delete(Component).where(Component.project_id == project_id))
        await db.execute(delete(Project).where(Project.id == project_id))
        
        await db.commit()
        
        return {"message": f"Project {project_id} deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
