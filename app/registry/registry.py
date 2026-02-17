"""Component Registry for managing component metadata."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Any, Tuple
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, func

from app.core.models import Component, Project
from .metadata import ComponentMetadata, MetadataSchema, ComponentType, AccessLevel

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """Registry for managing component metadata and relationships."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._metadata_cache: Dict[str, ComponentMetadata] = {}
        self._cache_enabled = True
        self._cache_ttl = 3600  # 1 hour
        self._cache_timestamps: Dict[str, datetime] = {}

    async def register_component(self, metadata: ComponentMetadata) -> str:
        """Register a component with its metadata."""
        # Validate metadata
        errors = MetadataSchema.validate(metadata)
        if errors:
            raise ValueError(f"Invalid metadata: {', '.join(errors)}")
        
        # Check if component already exists
        existing = await self._get_component_by_id(metadata.component_id)
        
        if existing:
            # Update existing component
            await self._update_component_metadata(existing, metadata)
        else:
            # Create new component
            await self._create_component_metadata(metadata)
        
        # Update cache
        if self._cache_enabled:
            self._metadata_cache[metadata.component_id] = metadata
            self._cache_timestamps[metadata.component_id] = datetime.now(timezone.utc)
        
        logger.info(f"Registered component: {metadata.name} ({metadata.component_id})")
        return metadata.component_id

    async def get_component(self, component_id: str) -> Optional[ComponentMetadata]:
        """Get component metadata by ID."""
        # Check cache first
        if self._cache_enabled and component_id in self._metadata_cache:
            # Check if cache is still valid
            if component_id in self._cache_timestamps:
                age = (datetime.now(timezone.utc) - self._cache_timestamps[component_id]).total_seconds()
                if age < self._cache_ttl:
                    return self._metadata_cache[component_id]
        
        # Load from database
        component = await self._get_component_by_id(component_id)
        if not component:
            return None
        
        metadata = await self._component_to_metadata(component)
        
        # Update cache
        if self._cache_enabled:
            self._metadata_cache[component_id] = metadata
            self._cache_timestamps[component_id] = datetime.now(timezone.utc)
        
        return metadata

    async def update_component(self, component_id: str, updates: Dict[str, Any]) -> bool:
        """Update component metadata."""
        component = await self._get_component_by_id(component_id)
        if not component:
            return False
        
        # Apply updates
        for field, value in updates.items():
            if hasattr(component, field):
                setattr(component, field, value)
        
        component.last_modified = datetime.now(timezone.utc)
        
        await self.db.commit()
        
        # Invalidate cache
        if component_id in self._metadata_cache:
            del self._metadata_cache[component_id]
            del self._cache_timestamps[component_id]
        
        logger.info(f"Updated component: {component_id}")
        return True

    async def delete_component(self, component_id: str) -> bool:
        """Delete a component from the registry."""
        component = await self._get_component_by_id(component_id)
        if not component:
            return False
        
        await self.db.delete(component)
        await self.db.commit()
        
        # Remove from cache
        if component_id in self._metadata_cache:
            del self._metadata_cache[component_id]
            del self._cache_timestamps[component_id]
        
        logger.info(f"Deleted component: {component_id}")
        return True

    async def search_components(self, 
                               project_id: Optional[str] = None,
                               component_type: Optional[ComponentType] = None,
                               language: Optional[str] = None,
                               tags: Optional[Set[str]] = None,
                               categories: Optional[Set[str]] = None,
                               query: Optional[str] = None,
                               limit: int = 100,
                               offset: int = 0) -> List[ComponentMetadata]:
        """Search components with various filters."""
        # Build query
        stmt = select(Component)
        
        if project_id:
            stmt = stmt.where(Component.project_id == project_id)
        
        if component_type:
            stmt = stmt.where(Component.type == component_type.value)
        
        if language:
            stmt = stmt.where(Component.language == language)
        
        if query:
            stmt = stmt.where(
                or_(
                    Component.name.ilike(f"%{query}%"),
                    Component.relative_path.ilike(f"%{query}%")
                )
            )
        
        # Order by name for consistent results
        stmt = stmt.order_by(Component.name).limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        components = result.scalars().all()
        
        # Convert to metadata
        metadata_list = []
        for component in components:
            metadata = await self._component_to_metadata(component)
            
            # Apply additional filters that require metadata
            if tags and not tags & metadata.tags:
                continue
            
            if categories and not categories & metadata.categories:
                continue
            
            metadata_list.append(metadata)
        
        return metadata_list

    async def get_components_by_project(self, project_id: str) -> List[ComponentMetadata]:
        """Get all components for a project."""
        return await self.search_components(project_id=project_id)

    async def get_components_by_file(self, file_path: str) -> List[ComponentMetadata]:
        """Get all components in a specific file."""
        stmt = select(Component).where(Component.path == file_path)
        result = await self.db.execute(stmt)
        components = result.scalars().all()
        
        metadata_list = []
        for component in components:
            metadata = await self._component_to_metadata(component)
            metadata_list.append(metadata)
        
        return metadata_list

    async def get_component_dependencies(self, component_id: str) -> List[ComponentMetadata]:
        """Get all dependencies of a component."""
        component = await self._get_component_by_id(component_id)
        if not component:
            return []
        
        dependencies = []
        for dep_name in component.dependencies:
            # Find components by name in the same project
            stmt = select(Component).where(
                and_(
                    Component.project_id == component.project_id,
                    Component.name == dep_name
                )
            )
            result = await self.db.execute(stmt)
            dep_components = result.scalars().all()
            
            for dep_component in dep_components:
                metadata = await self._component_to_metadata(dep_component)
                dependencies.append(metadata)
        
        return dependencies

    async def get_component_dependents(self, component_id: str) -> List[ComponentMetadata]:
        """Get all components that depend on this component."""
        component = await self._get_component_by_id(component_id)
        if not component:
            return []
        
        dependents = []
        
        # Find components that have this component in their dependencies
        stmt = select(Component).where(
            and_(
                Component.project_id == component.project_id,
                Component.dependencies.any(component.name)
            )
        )
        result = await self.db.execute(stmt)
        dependent_components = result.scalars().all()
        
        for dependent_component in dependent_components:
            metadata = await self._component_to_metadata(dependent_component)
            dependents.append(metadata)
        
        return dependents

    async def get_project_statistics(self, project_id: str) -> Dict[str, Any]:
        """Get statistics for a project."""
        # Component counts by type
        type_counts = await self.db.execute(
            select(Component.type, func.count(Component.id))
            .where(Component.project_id == project_id)
            .group_by(Component.type)
        )
        
        component_types = {row[0]: row[1] for row in type_counts}
        
        # Language distribution
        lang_counts = await self.db.execute(
            select(Component.language, func.count(Component.id))
            .where(Component.project_id == project_id)
            .group_by(Component.language)
        )
        
        languages = {row[0]: row[1] for row in lang_counts}
        
        # Quality metrics
        quality_stats = await self.db.execute(
            select(
                func.avg(Component.complexity_score).label('avg_complexity'),
                func.max(Component.complexity_score).label('max_complexity'),
                func.min(Component.complexity_score).label('min_complexity'),
                func.count(Component.id).label('total_components')
            )
            .where(Component.project_id == project_id)
        )
        
        stats = quality_stats.first()
        
        return {
            "total_components": stats.total_components,
            "component_types": component_types,
            "languages": languages,
            "average_complexity": float(stats.avg_complexity) if stats.avg_complexity else 0,
            "max_complexity": float(stats.max_complexity) if stats.max_complexity else 0,
            "min_complexity": float(stats.min_complexity) if stats.min_complexity else 0
        }

    async def bulk_register_components(self, metadata_list: List[ComponentMetadata]) -> List[str]:
        """Register multiple components efficiently."""
        registered_ids = []
        
        for metadata in metadata_list:
            try:
                component_id = await self.register_component(metadata)
                registered_ids.append(component_id)
            except Exception as e:
                logger.error(f"Failed to register component {metadata.name}: {e}")
                continue
        
        return registered_ids

    async def update_relationships(self, project_id: str) -> int:
        """Update dependency relationships for all components in a project."""
        # Get all components in the project
        stmt = select(Component).where(Component.project_id == project_id)
        result = await self.db.execute(stmt)
        components = result.scalars().all()
        
        # Build name to ID mapping
        name_to_id = {comp.name: str(comp.id) for comp in components}
        
        updated_count = 0
        
        for component in components:
            # Update dependents based on other components' dependencies
            dependents = []
            for other_comp in components:
                if other_comp.id != component.id:
                    if component.name in other_comp.dependencies:
                        dependents.append(str(other_comp.id))
            
            if dependents != component.dependents:
                component.dependents = dependents
                updated_count += 1
        
        await self.db.commit()
        
        # Clear cache for this project
        if self._cache_enabled:
            for component in components:
                component_id = str(component.id)
                if component_id in self._metadata_cache:
                    del self._metadata_cache[component_id]
                    del self._cache_timestamps[component_id]
        
        logger.info(f"Updated relationships for {updated_count} components in project {project_id}")
        return updated_count

    async def get_similar_components(self, 
                                   component_id: str,
                                   similarity_threshold: float = 0.7,
                                   limit: int = 10) -> List[Tuple[ComponentMetadata, float]]:
        """Find components similar to the given component."""
        target = await self.get_component(component_id)
        if not target:
            return []
        
        # Get all components in the same project
        stmt = select(Component).where(
            and_(
                Component.project_id == target.custom_metadata.get("project_id"),
                Component.id != component_id
            )
        )
        result = await self.db.execute(stmt)
        components = result.scalars().all()
        
        similar_components = []
        
        for component in components:
            metadata = await self._component_to_metadata(component)
            similarity = self._calculate_similarity(target, metadata)
            
            if similarity >= similarity_threshold:
                similar_components.append((metadata, similarity))
        
        # Sort by similarity (descending)
        similar_components.sort(key=lambda x: x[1], reverse=True)
        
        return similar_components[:limit]

    def _calculate_similarity(self, comp1: ComponentMetadata, comp2: ComponentMetadata) -> float:
        """Calculate similarity between two components."""
        similarity_score = 0.0
        total_factors = 0
        
        # Type similarity (20%)
        if comp1.type == comp2.type:
            similarity_score += 0.2
        total_factors += 0.2
        
        # Language similarity (15%)
        if comp1.language == comp2.language:
            similarity_score += 0.15
        total_factors += 0.15
        
        # Tag similarity (25%)
        if comp1.tags and comp2.tags:
            tag_similarity = len(comp1.tags & comp2.tags) / len(comp1.tags | comp2.tags)
            similarity_score += tag_similarity * 0.25
        total_factors += 0.25
        
        # Category similarity (20%)
        if comp1.categories and comp2.categories:
            cat_similarity = len(comp1.categories & comp2.categories) / len(comp1.categories | comp2.categories)
            similarity_score += cat_similarity * 0.2
        total_factors += 0.2
        
        # Name similarity (10%)
        name_similarity = self._string_similarity(comp1.name.lower(), comp2.name.lower())
        similarity_score += name_similarity * 0.1
        total_factors += 0.1
        
        # Complexity similarity (10%)
        complexity_diff = abs(comp1.code_metrics.cyclomatic_complexity - comp2.code_metrics.cyclomatic_complexity)
        max_complexity = max(comp1.code_metrics.cyclomatic_complexity, comp2.code_metrics.cyclomatic_complexity)
        if max_complexity > 0:
            complexity_similarity = 1 - (complexity_diff / max_complexity)
            similarity_score += complexity_similarity * 0.1
        total_factors += 0.1
        
        return similarity_score / total_factors if total_factors > 0 else 0.0

    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity using Levenshtein distance."""
        if not s1 or not s2:
            return 0.0
        
        # Simple Levenshtein distance implementation
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

    async def _get_component_by_id(self, component_id: str) -> Optional[Component]:
        """Get component from database by ID."""
        stmt = select(Component).where(Component.id == component_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_component_metadata(self, metadata: ComponentMetadata) -> Component:
        """Create new component in database."""
        component = Component(
            id=metadata.component_id,
            project_id=metadata.custom_metadata.get("project_id"),
            name=metadata.name,
            type=metadata.type.value,
            path=metadata.file_path,
            relative_path=metadata.relative_path,
            language=metadata.language,
            file_extension=Path(metadata.file_path).suffix,
            line_start=metadata.line_start,
            line_end=metadata.line_end,
            dependencies=metadata.dependencies,
            dependents=metadata.dependents,
            exports=metadata.exports,
            complexity_score=metadata.code_metrics.cyclomatic_complexity,
            line_count=metadata.code_metrics.lines_of_code,
            metadata_=metadata.to_dict()
        )
        
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        
        return component

    async def _update_component_metadata(self, component: Component, metadata: ComponentMetadata) -> None:
        """Update existing component in database."""
        component.name = metadata.name
        component.type = metadata.type.value
        component.path = metadata.file_path
        component.relative_path = metadata.relative_path
        component.language = metadata.language
        component.line_start = metadata.line_start
        component.line_end = metadata.line_end
        component.dependencies = metadata.dependencies
        component.dependents = metadata.dependents
        component.exports = metadata.exports
        component.complexity_score = metadata.code_metrics.cyclomatic_complexity
        component.line_count = metadata.code_metrics.lines_of_code
        component.metadata_ = metadata.to_dict()
        
        await self.db.commit()

    async def _component_to_metadata(self, component: Component) -> ComponentMetadata:
        """Convert database component to metadata object."""
        # Extract metadata from JSON field
        metadata_dict = component.metadata_ or {}
        
        # Create ComponentMetadata with basic info from database
        metadata = ComponentMetadata(
            component_id=str(component.id),
            name=component.name,
            type=ComponentType(component.type),
            language=component.language,
            file_path=component.path,
            relative_path=component.relative_path,
            line_start=component.line_start or 0,
            line_end=component.line_end or 0,
            dependencies=component.dependencies or [],
            dependents=component.dependents or [],
            exports=component.exports or []
        )
        
        # Update with stored metadata
        for key, value in metadata_dict.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        return metadata

    def clear_cache(self) -> None:
        """Clear the metadata cache."""
        self._metadata_cache.clear()
        self._cache_timestamps.clear()
        logger.info("Component registry cache cleared")

    def enable_cache(self, enabled: bool = True) -> None:
        """Enable or disable caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
        logger.info(f"Component registry cache {'enabled' if enabled else 'disabled'}")
