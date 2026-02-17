"""Code-Aware Embeddings for semantic understanding."""

from __future__ import annotations

import logging
import ast
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

from app.memory.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class EmbeddingType(str, Enum):
    """Types of code embeddings."""
    STRUCTURE = "structure"      # AST structure and relationships
    FUNCTIONALITY = "functionality"  # What the code does
    CONTEXT = "context"          # Surrounding code context
    DEPENDENCIES = "dependencies"  # Import and dependency relationships
    PATTERNS = "patterns"        # Design patterns used
    SEMANTICS = "semantics"      # Semantic meaning


@dataclass
class CodeEmbedding:
    """A code embedding with metadata."""
    embedding_id: str
    component_id: str
    embedding_type: EmbeddingType
    vector: List[float]
    metadata: Dict[str, Any]
    source_text: str
    context_window: List[str]
    created_at: str


class CodeStructureEmbeddings:
    """Generate embeddings based on code structure and AST."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._ast_cache = {}
    
    async def generate_structure_embedding(self, 
                                         component_id: str,
                                         code: str,
                                         language: str,
                                         context: Optional[List[str]] = None) -> CodeEmbedding:
        """Generate structure-based embedding from AST."""
        try:
            # Parse AST
            ast_data = self._parse_ast(code, language)
            
            # Extract structural features
            structure_features = self._extract_structure_features(ast_data)
            
            # Create structural text representation
            structural_text = self._create_structural_text(structure_features, code)
            
            # Generate embedding
            vector = await self.embedding_provider.embed_text(structural_text)
            
            # Create embedding object
            embedding_id = self._generate_embedding_id(component_id, EmbeddingType.STRUCTURE, code)
            
            return CodeEmbedding(
                embedding_id=embedding_id,
                component_id=component_id,
                embedding_type=EmbeddingType.STRUCTURE,
                vector=vector,
                metadata={
                    "language": language,
                    "ast_nodes": len(ast_data.get("nodes", [])),
                    "functions": structure_features.get("functions", []),
                    "classes": structure_features.get("classes", []),
                    "imports": structure_features.get("imports", []),
                    "complexity": structure_features.get("complexity", 0)
                },
                source_text=code,
                context_window=context or [],
                created_at="2024-01-01T00:00:00Z"  # Would use actual timestamp
            )
            
        except Exception as e:
            logger.error(f"Error generating structure embedding: {e}")
            raise
    
    def _parse_ast(self, code: str, language: str) -> Dict[str, Any]:
        """Parse code into AST structure."""
        cache_key = f"{language}:{hashlib.md5(code.encode()).hexdigest()}"
        
        if cache_key in self._ast_cache:
            return self._ast_cache[cache_key]
        
        ast_data = {"nodes": [], "edges": [], "metadata": {}}
        
        try:
            if language == "python":
                ast_data = self._parse_python_ast(code)
            elif language in ["javascript", "typescript"]:
                ast_data = self._parse_javascript_ast(code)
            else:
                # Fallback to basic parsing
                ast_data = self._parse_generic_ast(code)
                
        except Exception as e:
            logger.warning(f"AST parsing failed for {language}: {e}")
            ast_data = self._parse_generic_ast(code)
        
        self._ast_cache[cache_key] = ast_data
        return ast_data
    
    def _parse_python_ast(self, code: str) -> Dict[str, Any]:
        """Parse Python AST."""
        try:
            tree = ast.parse(code)
            nodes = []
            edges = []
            
            for node in ast.walk(tree):
                node_info = {
                    "type": node.__class__.__name__,
                    "name": getattr(node, "name", None),
                    "lineno": getattr(node, "lineno", None),
                    "col_offset": getattr(node, "col_offset", None)
                }
                
                # Add specific node information
                if isinstance(node, ast.FunctionDef):
                    node_info.update({
                        "args": [arg.arg for arg in node.args.args],
                        "returns": ast.unparse(node.returns) if node.returns else None,
                        "decorators": [ast.unparse(dec) for dec in node.decorator_list]
                    })
                elif isinstance(node, ast.ClassDef):
                    node_info.update({
                        "bases": [ast.unparse(base) for base in node.bases],
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.Import):
                    node_info.update({
                        "names": [alias.name for alias in node.names]
                    })
                elif isinstance(node, ast.ImportFrom):
                    node_info.update({
                        "module": node.module,
                        "names": [alias.name for alias in node.names]
                    })
                
                nodes.append(node_info)
            
            return {"nodes": nodes, "edges": edges, "metadata": {"language": "python"}}
            
        except Exception as e:
            logger.error(f"Python AST parsing failed: {e}")
            return self._parse_generic_ast(code)
    
    def _parse_javascript_ast(self, code: str) -> Dict[str, Any]:
        """Parse JavaScript/TypeScript AST (simplified)."""
        # This would use tree-sitter in production
        # For now, use regex-based parsing
        nodes = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Function detection
            if line.startswith('function ') or 'function ' in line:
                parts = line.split('function ')
                if len(parts) > 1:
                    func_name = parts[1].split('(')[0].strip()
                    nodes.append({
                        "type": "FunctionDeclaration",
                        "name": func_name,
                        "lineno": i + 1
                    })
            
            # Class detection
            elif line.startswith('class '):
                class_name = line.split('class ')[1].split(' ')[0].strip()
                nodes.append({
                    "type": "ClassDeclaration", 
                    "name": class_name,
                    "lineno": i + 1
                })
            
            # Import detection
            elif line.startswith('import ') or line.startswith('const ') and 'require' in line:
                nodes.append({
                    "type": "ImportDeclaration",
                    "name": line,
                    "lineno": i + 1
                })
        
        return {"nodes": nodes, "edges": [], "metadata": {"language": "javascript"}}
    
    def _parse_generic_ast(self, code: str) -> Dict[str, Any]:
        """Generic AST parsing for unsupported languages."""
        nodes = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Basic pattern matching
            if any(keyword in line for keyword in ['function', 'def', 'class', 'interface']):
                nodes.append({
                    "type": "Declaration",
                    "name": line,
                    "lineno": i + 1
                })
        
        return {"nodes": nodes, "edges": [], "metadata": {"language": "generic"}}
    
    def _extract_structure_features(self, ast_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structural features from AST."""
        nodes = ast_data.get("nodes", [])
        
        features = {
            "functions": [],
            "classes": [],
            "imports": [],
            "variables": [],
            "complexity": 0
        }
        
        for node in nodes:
            node_type = node.get("type", "")
            
            if "Function" in node_type:
                features["functions"].append({
                    "name": node.get("name", "anonymous"),
                    "line": node.get("lineno"),
                    "args": node.get("args", [])
                })
                features["complexity"] += 1
            
            elif "Class" in node_type:
                features["classes"].append({
                    "name": node.get("name", "anonymous"),
                    "line": node.get("lineno"),
                    "methods": node.get("methods", [])
                })
                features["complexity"] += 2
            
            elif "Import" in node_type:
                features["imports"].append({
                    "name": node.get("name", ""),
                    "line": node.get("lineno")
                })
        
        return features
    
    def _create_structural_text(self, features: Dict[str, Any], original_code: str) -> str:
        """Create text representation of code structure for embedding."""
        structural_parts = []
        
        # Add functions
        for func in features.get("functions", []):
            structural_parts.append(f"function {func['name']} with args {func['args']}")
        
        # Add classes
        for cls in features.get("classes", []):
            methods = ", ".join(cls.get("methods", []))
            structural_parts.append(f"class {cls['name']} with methods {methods}")
        
        # Add imports
        for imp in features.get("imports", []):
            structural_parts.append(f"import {imp['name']}")
        
        # Add complexity indicator
        structural_parts.append(f"complexity {features.get('complexity', 0)}")
        
        # Add some original code context
        code_sample = original_code[:500]  # First 500 chars
        structural_parts.append(f"code: {code_sample}")
        
        return " | ".join(structural_parts)
    
    def _generate_embedding_id(self, component_id: str, embedding_type: EmbeddingType, code: str) -> str:
        """Generate unique embedding ID."""
        content = f"{component_id}:{embedding_type.value}:{hashlib.md5(code.encode()).hexdigest()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]


class CodeEmbeddingGenerator:
    """Main generator for all types of code embeddings."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self.structure_embeddings = CodeStructureEmbeddings(embedding_provider)
    
    async def generate_all_embeddings(self,
                                   component_id: str,
                                   code: str,
                                   language: str,
                                   context: Optional[List[str]] = None) -> List[CodeEmbedding]:
        """Generate all types of embeddings for a code component."""
        embeddings = []
        
        # Structure embedding
        try:
            structure_emb = await self.structure_embeddings.generate_structure_embedding(
                component_id, code, language, context
            )
            embeddings.append(structure_emb)
        except Exception as e:
            logger.error(f"Failed to generate structure embedding: {e}")
        
        # Functionality embedding
        try:
            functionality_emb = await self._generate_functionality_embedding(
                component_id, code, language, context
            )
            embeddings.append(functionality_emb)
        except Exception as e:
            logger.error(f"Failed to generate functionality embedding: {e}")
        
        # Context embedding
        try:
            context_emb = await self._generate_context_embedding(
                component_id, code, language, context
            )
            embeddings.append(context_emb)
        except Exception as e:
            logger.error(f"Failed to generate context embedding: {e}")
        
        return embeddings
    
    async def _generate_functionality_embedding(self,
                                              component_id: str,
                                              code: str,
                                              language: str,
                                              context: Optional[List[str]] = None) -> CodeEmbedding:
        """Generate functionality-based embedding."""
        # Extract functionality description
        functionality_text = self._extract_functionality_text(code, language)
        
        # Generate embedding
        vector = await self.embedding_provider.embed_text(functionality_text)
        
        embedding_id = self._generate_embedding_id(component_id, EmbeddingType.FUNCTIONALITY, code)
        
        return CodeEmbedding(
            embedding_id=embedding_id,
            component_id=component_id,
            embedding_type=EmbeddingType.FUNCTIONALITY,
            vector=vector,
            metadata={
                "language": language,
                "functionality": functionality_text[:200]  # First 200 chars
            },
            source_text=code,
            context_window=context or [],
            created_at="2024-01-01T00:00:00Z"
        )
    
    async def _generate_context_embedding(self,
                                        component_id: str,
                                        code: str,
                                        language: str,
                                        context: Optional[List[str]] = None) -> CodeEmbedding:
        """Generate context-based embedding."""
        # Combine code with context
        context_text = " | ".join(context or [])
        combined_text = f"Code: {code[:1000]} | Context: {context_text}"
        
        # Generate embedding
        vector = await self.embedding_provider.embed_text(combined_text)
        
        embedding_id = self._generate_embedding_id(component_id, EmbeddingType.CONTEXT, code)
        
        return CodeEmbedding(
            embedding_id=embedding_id,
            component_id=component_id,
            embedding_type=EmbeddingType.CONTEXT,
            vector=vector,
            metadata={
                "language": language,
                "context_length": len(context or []),
                "combined_length": len(combined_text)
            },
            source_text=code,
            context_window=context or [],
            created_at="2024-01-01T00:00:00Z"
        )
    
    def _extract_functionality_text(self, code: str, language: str) -> str:
        """Extract functionality description from code."""
        # This would use more sophisticated analysis in production
        functionality_parts = []
        
        # Extract comments and docstrings
        lines = code.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#') or line.startswith('//') or line.startswith('"""') or line.startswith("'''"):
                functionality_parts.append(line)
        
        # Extract function/class names
        if language == "python":
            import re
            functions = re.findall(r'def\s+(\w+)', code)
            classes = re.findall(r'class\s+(\w+)', code)
            functionality_parts.extend([f"function {f}" for f in functions])
            functionality_parts.extend([f"class {c}" for c in classes])
        
        return " | ".join(functionality_parts) if functionality_parts else code[:500]
    
    def _generate_embedding_id(self, component_id: str, embedding_type: EmbeddingType, code: str) -> str:
        """Generate unique embedding ID."""
        content = f"{component_id}:{embedding_type.value}:{hashlib.md5(code.encode()).hexdigest()}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
