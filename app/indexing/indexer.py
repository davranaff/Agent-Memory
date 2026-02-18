"""Main project indexer that coordinates scanning and analysis."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models import Project, Component, Documentation, CodePattern
from app.paths import resolve_project_path
from app.config.settings import get_settings
from .scanner import ProjectScanner, FileInfo, DirectoryInfo
from .analyzer import ProjectAnalyzer
from app.parsing import parse_file

logger = logging.getLogger(__name__)


class ProjectIndexer:
    """Main indexer that coordinates project scanning, parsing, and analysis."""

    def __init__(self, 
                 db: AsyncSession,
                 ignore_patterns: Optional[List[str]] = None,
                 max_file_size_mb: int = 10) -> None:
        self.db = db
        self.scanner = ProjectScanner(
            ignore_patterns=ignore_patterns,
            max_file_size_mb=max_file_size_mb
        )
        self.analyzer = ProjectAnalyzer()

    async def index_project(self, 
                           project_path: str, 
                           project_name: Optional[str] = None,
                           force_reindex: bool = False) -> Project:
        """Index a project from scratch or update existing."""
        requested_project_path = project_path
        resolved_path = resolve_project_path(project_path)
        project_path = str(resolved_path.resolved_path)

        if resolved_path.used_mapping:
            logger.info(
                "Resolved project path via PROJECT_PATH_MAPPINGS: %s -> %s",
                requested_project_path,
                project_path,
            )

        if not resolved_path.resolved_path.exists() or not resolved_path.resolved_path.is_dir():
            mapping_hint = ""
            project_path_mappings = get_settings().project_path_mappings
            if project_path_mappings:
                mapping_hint = (
                    f" Current PROJECT_PATH_MAPPINGS='{project_path_mappings}'."
                )
            raise ValueError(
                "Invalid project path: "
                f"{requested_project_path}. Ensure the directory is mounted into the backend container "
                f"and configure PROJECT_PATH_MAPPINGS for host->container translation.{mapping_hint}"
            )
        
        # Check if project already exists
        existing_project = await self._get_project_by_path(project_path)
        
        if existing_project and not force_reindex:
            logger.info(f"Project {project_name or project_path} already indexed")
            return existing_project
        
        # Create or update project record
        if existing_project:
            project = existing_project
            project.analysis_status = "analyzing"
            project.analysis_error = None
        else:
            project = Project(
                name=project_name or Path(project_path).name,
                path=project_path,
                analysis_status="analyzing"
            )
            self.db.add(project)
            await self.db.flush()

        try:
            # Scan project structure
            logger.info(f"Scanning project: {project_path}")
            files, directories = self.scanner.scan_project(project_path)
            
            # Analyze project
            logger.info("Analyzing project structure")
            tech_stack = self.analyzer.detect_technology_stack(files)
            architecture_type = self.analyzer.detect_architecture_type(files, directories)
            complexity = self.analyzer.analyze_project_complexity(files, directories)
            metadata = self.analyzer.extract_project_metadata(files)

            # Update project with analysis results
            project.tech_stack = tech_stack.get("languages", [])
            project.frameworks = tech_stack.get("frameworks", [])
            project.languages = tech_stack.get("languages", [])
            project.databases = tech_stack.get("databases", [])
            project.build_tools = tech_stack.get("build_tools", [])
            project.architecture_type = architecture_type
            project.total_files = len(files)
            project.total_lines = 0  # Will be updated after parsing
            project.metadata_ = {
                **metadata,
                "complexity": complexity,
                "testing_tools": tech_stack.get("testing_tools", []),
                "package_managers": tech_stack.get("package_managers", [])
            }

            # Clear existing components if reindexing
            if force_reindex and existing_project:
                await self._clear_project_components(project.id)

            # Parse source files and create components
            logger.info("Parsing source files")
            total_lines = 0
            source_files = [f for f in files if f.language and not f.is_binary and not f.is_generated]
            
            # Process files in batches to avoid memory issues
            batch_size = 50
            for i in range(0, len(source_files), batch_size):
                batch = source_files[i:i + batch_size]
                await self._process_file_batch(batch, project.id)
                total_lines += sum(await self._count_lines_in_files(batch))
                
                # Commit batch to avoid long transactions
                await self.db.commit()
                await self.db.refresh(project)

            project.total_lines = total_lines
            project.last_analyzed = datetime.now(timezone.utc)
            project.analysis_status = "completed"
            
            await self.db.commit()
            logger.info(f"Successfully indexed project: {project.name}")
            
            return project

        except Exception as e:
            project.analysis_status = "error"
            project.analysis_error = str(e)
            await self.db.commit()
            logger.error(f"Failed to index project {project_path}: {e}")
            raise

    async def _get_project_by_path(self, project_path: str) -> Optional[Project]:
        """Get existing project by path."""
        from sqlalchemy import select
        
        stmt = select(Project).where(Project.path == project_path)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _clear_project_components(self, project_id: str) -> None:
        """Clear existing components for a project."""
        from sqlalchemy import delete
        
        # Delete in order to respect foreign key constraints
        await self.db.execute(delete(Documentation).where(Documentation.project_id == project_id))
        await self.db.execute(delete(CodePattern).where(CodePattern.project_id == project_id))
        await self.db.execute(delete(Component).where(Component.project_id == project_id))

    async def _process_file_batch(self, files: List[FileInfo], project_id: str) -> None:
        """Process a batch of files and create components."""
        tasks = []
        
        for file_info in files:
            task = self._process_single_file(file_info, project_id)
            tasks.append(task)
        
        # Process files concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing file {files[i].path}: {result}")

    async def _process_single_file(self, file_info: FileInfo, project_id: str) -> None:
        """Process a single file and create components."""
        try:
            # Parse file
            parse_result = await parse_file(file_info.path)
            
            if not parse_result.success:
                logger.warning(f"Failed to parse {file_info.path}: {parse_result.error_message}")
                return

            # Create file component
            file_component = Component(
                project_id=project_id,
                name=Path(file_info.path).stem,
                type="file",
                path=file_info.path,
                relative_path=file_info.relative_path,
                language=file_info.language,
                file_extension=file_info.extension,
                size_bytes=file_info.size_bytes,
                line_count=parse_result.line_count,
                dependencies=parse_result.imports,
                exports=parse_result.exports,
                metadata_={
                    "is_test": file_info.is_test,
                    "is_config": file_info.is_config,
                    "is_documentation": file_info.is_documentation,
                    "parse_metadata": parse_result.metadata
                }
            )
            self.db.add(file_component)
            await self.db.flush()

            # Create components for parsed structures
            for comp_info in parse_result.components:
                component = Component(
                    project_id=project_id,
                    name=comp_info.name,
                    type=comp_info.type,
                    path=file_info.path,
                    relative_path=file_info.relative_path,
                    language=file_info.language,
                    file_extension=file_info.extension,
                    line_start=comp_info.line_start,
                    line_end=comp_info.line_end,
                    dependencies=comp_info.dependencies,
                    dependents=[],  # Will be calculated later
                    exports=comp_info.exports,
                    complexity_score=comp_info.complexity_score,
                    metadata_=comp_info.metadata
                )
                self.db.add(component)

            # Create documentation if applicable
            if file_info.is_documentation:
                await self._create_documentation(file_info, project_id)

        except Exception as e:
            logger.error(f"Error processing file {file_info.path}: {e}")
            raise

    async def _create_documentation(self, file_info: FileInfo, project_id: str) -> None:
        """Create documentation record."""
        try:
            with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Determine documentation type
            doc_type = "readme"
            if "api" in file_info.path.lower():
                doc_type = "api"
            elif "guide" in file_info.path.lower():
                doc_type = "guide"
            elif "tutorial" in file_info.path.lower():
                doc_type = "tutorial"
            elif "license" in file_info.path.lower():
                doc_type = "license"
            elif "changelog" in file_info.path.lower():
                doc_type = "changelog"

            documentation = Documentation(
                project_id=project_id,
                title=Path(file_info.path).stem,
                type=doc_type,
                path=file_info.path,
                relative_path=file_info.relative_path,
                content=content,
                language="markdown" if file_info.extension == ".md" else "text",
                format=file_info.extension[1:] if file_info.extension else "txt",
                size_bytes=file_info.size_bytes,
                word_count=len(content.split()),
                metadata_={
                    "file_type": file_info.extension,
                    "is_generated": file_info.is_generated
                }
            )
            self.db.add(documentation)

        except Exception as e:
            logger.error(f"Error creating documentation for {file_info.path}: {e}")

    async def _count_lines_in_files(self, files: List[FileInfo]) -> int:
        """Count total lines in a batch of files."""
        total_lines = 0
        
        for file_info in files:
            try:
                with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                    total_lines += sum(1 for _ in f)
            except (IOError, UnicodeDecodeError):
                continue
        
        return total_lines

    async def update_project_dependencies(self, project_id: str) -> None:
        """Update dependency relationships between components."""
        from sqlalchemy import select
        
        # Get all components for the project
        stmt = select(Component).where(Component.project_id == project_id)
        result = await self.db.execute(stmt)
        components = result.scalars().all()
        
        # Build dependency map
        component_map = {comp.name: comp for comp in components}
        
        # Update dependents for each component
        for component in components:
            dependents = []
            
            for other_comp in components:
                if other_comp.id == component.id:
                    continue
                
                # Check if other component depends on this one
                if component.name in other_comp.dependencies:
                    dependents.append(other_comp.name)
            
            component.dependents = dependents
        
        await self.db.commit()

    async def get_project_summary(self, project_id: str) -> Dict:
        """Get summary statistics for a project."""
        from sqlalchemy import select, func
        
        # Get project
        stmt = select(Project).where(Project.id == project_id)
        result = await self.db.execute(stmt)
        project = result.scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
        
        # Get component statistics
        component_stats = await self.db.execute(
            select(
                Component.type,
                func.count(Component.id).label('count'),
                func.avg(Component.complexity_score).label('avg_complexity')
            )
            .where(Component.project_id == project_id)
            .group_by(Component.type)
        )
        
        component_breakdown = {
            row.type: {
                "count": row.count,
                "avg_complexity": float(row.avg_complexity) if row.avg_complexity else 0
            }
            for row in component_stats
        }
        
        # Get documentation count
        doc_count = await self.db.execute(
            select(func.count(Documentation.id))
            .where(Documentation.project_id == project_id)
        )
        
        return {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "path": project.path,
                "architecture_type": project.architecture_type,
                "tech_stack": project.tech_stack,
                "frameworks": project.frameworks,
                "languages": project.languages,
                "databases": project.databases,
                "build_tools": project.build_tools,
                "total_files": project.total_files,
                "total_lines": project.total_lines,
                "last_analyzed": project.last_analyzed.isoformat() if project.last_analyzed else None,
                "analysis_status": project.analysis_status
            },
            "components": component_breakdown,
            "documentation_count": doc_count.scalar(),
            "metadata": project.metadata_
        }

    async def search_components(self, 
                               project_id: str, 
                               query: str, 
                               component_type: Optional[str] = None,
                               language: Optional[str] = None,
                               limit: int = 100,
                               offset: int = 0) -> List[Component]:
        """Search components within a project."""
        from sqlalchemy import select, or_
        
        stmt = select(Component).where(Component.project_id == project_id)
        
        # Add type filter
        if component_type:
            stmt = stmt.where(Component.type == component_type)
        
        # Add language filter
        if language:
            stmt = stmt.where(Component.language == language)
        
        # Add text search
        search_filter = or_(
            Component.name.ilike(f"%{query}%"),
            Component.relative_path.ilike(f"%{query}%")
        )
        stmt = stmt.where(search_filter)
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return result.scalars().all()
