"""Base parser interface and common functionality."""

from __future__ import annotations

import ast
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from pydantic import BaseModel


@dataclass
class ComponentInfo:
    """Information about a code component."""
    name: str
    type: str  # class, function, interface, enum, struct, etc.
    path: str
    line_start: int
    line_end: int
    dependencies: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    complexity_score: int = 1
    docstring: Optional[str] = None


@dataclass
class ParseResult:
    """Result of parsing a file."""
    file_path: str
    language: str
    success: bool
    error_message: Optional[str] = None
    components: List[ComponentInfo] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    line_count: int = 0
    size_bytes: int = 0
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def relative_path(self) -> str:
        """Get relative path from absolute path."""
        return str(Path(self.file_path))

    def add_component(self, component: ComponentInfo) -> None:
        """Add a component to the result."""
        self.components.append(component)

    def get_components_by_type(self, component_type: str) -> List[ComponentInfo]:
        """Get all components of a specific type."""
        return [c for c in self.components if c.type == component_type]

    def get_exported_components(self) -> List[ComponentInfo]:
        """Get all components that are exported."""
        return [c for c in self.components if c.exports]

    def calculate_complexity(self) -> int:
        """Calculate overall file complexity."""
        if not self.components:
            return 1
        return sum(c.complexity_score for c in self.components) // len(self.components)


class BaseParser(ABC):
    """Abstract base class for all language parsers."""

    def __init__(self, language: str, file_extensions: List[str]) -> None:
        self.language = language
        self.file_extensions = file_extensions

    @abstractmethod
    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a single file and return structured information."""
        ...

    @abstractmethod
    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse file content and return structured information."""
        ...

    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file."""
        path = Path(file_path)
        return path.suffix.lower() in self.file_extensions

    def calculate_file_hash(self, content: str) -> str:
        """Calculate SHA256 hash of file content."""
        return hashlib.sha256(content.encode()).hexdigest()

    def count_lines(self, content: str) -> int:
        """Count non-empty lines in content."""
        return len([line for line in content.splitlines() if line.strip()])

    def extract_imports_from_ast(self, tree: ast.AST) -> List[str]:
        """Extract imports from Python AST."""
        imports = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)
        
        return imports

    def extract_docstring(self, node: Union[ast.FunctionDef, ast.ClassDef, ast.Module]) -> Optional[str]:
        """Extract docstring from AST node."""
        if (node.body and 
            isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and 
            isinstance(node.body[0].value.value, str)):
            return node.body[0].value.value
        return None

    def calculate_complexity_from_ast(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity from AST node."""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.With, ast.AsyncWith):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity

    def get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature from AST node."""
        args = []
        
        # Regular arguments
        for arg in node.args.args:
            args.append(arg.arg)
        
        # Default arguments
        defaults = node.args.defaults
        if defaults:
            for i, default in enumerate(defaults):
                arg_index = len(node.args.args) - len(defaults) + i
                if arg_index < len(args):
                    args[arg_index] += f"=..."
        
        # *args
        if node.args.vararg:
            args.append(f"*{node.args.vararg.arg}")
        
        # **kwargs
        if node.args.kwarg:
            args.append(f"**{node.args.kwarg.arg}")
        
        return f"{node.name}({', '.join(args)})"

    def get_class_bases(self, node: ast.ClassDef) -> List[str]:
        """Get base classes from AST node."""
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(f"{base.value.id}.{base.attr}")
        return bases

    def get_decorators(self, node: Union[ast.FunctionDef, ast.ClassDef]) -> List[str]:
        """Get decorators from AST node."""
        decorators = []
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                decorators.append(decorator.id)
            elif isinstance(decorator, ast.Attribute):
                decorators.append(f"{decorator.value.id}.{decorator.attr}")
        return decorators
