"""Language-specific parsers."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .base import BaseParser, ComponentInfo, ParseResult


class PythonParser(BaseParser):
    """Python language parser using AST."""

    def __init__(self) -> None:
        super().__init__("python", [".py", ".pyi", ".pyw"])

    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse Python content."""
        try:
            tree = ast.parse(content)
            
            result = ParseResult(
                file_path=file_path,
                language=self.language,
                success=True,
                line_count=self.count_lines(content),
                size_bytes=len(content.encode()),
                file_hash=self.calculate_file_hash(content),
                imports=self.extract_imports_from_ast(tree)
            )

            # Extract components
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    component = self._extract_class_info(node, file_path)
                    result.add_component(component)
                elif isinstance(node, ast.FunctionDef):
                    component = self._extract_function_info(node, file_path)
                    result.add_component(component)
                elif isinstance(node, ast.AsyncFunctionDef):
                    component = self._extract_function_info(node, file_path, is_async=True)
                    result.add_component(component)

            return result

        except SyntaxError as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=f"Syntax error: {e}"
            )
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    def _extract_class_info(self, node: ast.ClassDef, file_path: str) -> ComponentInfo:
        """Extract information about a class."""
        methods = []
        properties = []
        
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(child.name)
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        properties.append(target.id)

        return ComponentInfo(
            name=node.name,
            type="class",
            path=file_path,
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            dependencies=self._extract_class_dependencies(node),
            exports=[node.name],  # Classes are exported by default
            metadata={
                "bases": self.get_class_bases(node),
                "methods": methods,
                "properties": properties,
                "decorators": self.get_decorators(node),
                "docstring": self.extract_docstring(node)
            },
            complexity_score=self.calculate_complexity_from_ast(node),
            docstring=self.extract_docstring(node)
        )

    def _extract_function_info(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], 
                            file_path: str, is_async: bool = False) -> ComponentInfo:
        """Extract information about a function."""
        signature = self.get_function_signature(node)
        
        return ComponentInfo(
            name=node.name,
            type="async_function" if is_async else "function",
            path=file_path,
            line_start=node.lineno,
            line_end=getattr(node, 'end_lineno', node.lineno),
            dependencies=self._extract_function_dependencies(node),
            exports=[node.name] if not node.name.startswith('_') else [],
            metadata={
                "signature": signature,
                "args": [arg.arg for arg in node.args.args],
                "returns": ast.unparse(node.returns) if node.returns else None,
                "decorators": self.get_decorators(node),
                "docstring": self.extract_docstring(node)
            },
            complexity_score=self.calculate_complexity_from_ast(node),
            docstring=self.extract_docstring(node)
        )

    def _extract_class_dependencies(self, node: ast.ClassDef) -> List[str]:
        """Extract dependencies from a class."""
        deps = []
        
        # Base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                deps.append(base.id)
        
        # Method dependencies
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                deps.extend(self._extract_function_dependencies(child))
        
        return list(set(deps))

    def _extract_function_dependencies(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> List[str]:
        """Extract dependencies from a function."""
        deps = []
        
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                # Skip function arguments and local variables
                if not self._is_local_variable(child.id, node):
                    deps.append(child.id)
            elif isinstance(child, ast.Attribute):
                if isinstance(child.value, ast.Name):
                    deps.append(child.value.id)
        
        return list(set(deps))

    def _is_local_variable(self, name: str, node: ast.FunctionDef) -> bool:
        """Check if a name is a local variable."""
        # Function arguments
        arg_names = {arg.arg for arg in node.args.args}
        if name in arg_names:
            return True
        
        # Local assignments
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return True
        
        return False


class JavaScriptParser(BaseParser):
    """JavaScript language parser using Tree-sitter."""

    def __init__(self) -> None:
        super().__init__("javascript", [".js", ".jsx", ".mjs"])
        self._parser = None
        self._language = None

    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a JavaScript file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse JavaScript content."""
        try:
            # For now, use regex-based parsing as fallback
            return await self._parse_with_regex(content, file_path)
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    async def _parse_with_regex(self, content: str, file_path: str) -> ParseResult:
        """Parse JavaScript using regex patterns."""
        result = ParseResult(
            file_path=file_path,
            language=self.language,
            success=True,
            line_count=self.count_lines(content),
            size_bytes=len(content.encode()),
            file_hash=self.calculate_file_hash(content)
        )

        # Extract imports
        import_patterns = [
            r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',
            r'const\s+.*?=\s*require\([\'"]([^\'"]+)[\'"]',
            r'import\s+[\'"]([^\'"]+)[\'"]'
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            result.imports.extend(matches)

        # Extract functions
        function_pattern = r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>|(\w+)\s*:\s*function)'
        for match in re.finditer(function_pattern, content):
            func_name = next(m for m in match if m)
            if func_name:
                line_num = content[:match.start()].count('\n') + 1
                component = ComponentInfo(
                    name=func_name,
                    type="function",
                    path=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    exports=[func_name] if not func_name.startswith('_') else [],
                    metadata={"detected_by": "regex"}
                )
                result.add_component(component)

        # Extract classes
        class_pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            base_class = match.group(2)
            line_num = content[:match.start()].count('\n') + 1
            
            component = ComponentInfo(
                name=class_name,
                type="class",
                path=file_path,
                line_start=line_num,
                line_end=line_num,
                dependencies=[base_class] if base_class else [],
                exports=[class_name],
                metadata={"base_class": base_class, "detected_by": "regex"}
            )
            result.add_component(component)

        return result


class TypeScriptParser(BaseParser):
    """TypeScript language parser."""

    def __init__(self) -> None:
        super().__init__("typescript", [".ts", ".tsx"])

    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a TypeScript file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse TypeScript content."""
        # Similar to JavaScript but with TypeScript-specific patterns
        js_parser = JavaScriptParser()
        js_parser.language = "typescript"
        return await js_parser._parse_with_regex(content, file_path)


class JavaParser(BaseParser):
    """Java language parser."""

    def __init__(self) -> None:
        super().__init__("java", [".java"])

    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a Java file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(
                file_path=file_path,
                language=self.language,
                success=False,
                error_message=str(e)
            )

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse Java content."""
        result = ParseResult(
            file_path=file_path,
            language=self.language,
            success=True,
            line_count=self.count_lines(content),
            size_bytes=len(content.encode()),
            file_hash=self.calculate_file_hash(content)
        )

        # Extract package and imports
        package_match = re.search(r'package\s+([^;]+);', content)
        if package_match:
            result.metadata["package"] = package_match.group(1).strip()

        import_matches = re.findall(r'import\s+([^;]+);', content)
        result.imports.extend(import_matches)

        # Extract classes
        class_pattern = r'(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{\s]+))?'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            extends = match.group(2)
            implements = match.group(3)
            line_num = content[:match.start()].count('\n') + 1
            
            dependencies = []
            if extends:
                dependencies.append(extends)
            if implements:
                dependencies.extend([imp.strip() for imp in implements.split(',')])

            component = ComponentInfo(
                name=class_name,
                type="class",
                path=file_path,
                line_start=line_num,
                line_end=line_num,
                dependencies=dependencies,
                exports=[class_name],
                metadata={
                    "extends": extends,
                    "implements": implements.split(',') if implements else [],
                    "detected_by": "regex"
                }
            )
            result.add_component(component)

        # Extract methods
        method_pattern = r'(?:public\s+|private\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?(?:\w+\s+)?(\w+)\s*\([^)]*\)\s*(?:throws\s+[^{]+)?\s*[{;]'
        for match in re.finditer(method_pattern, content):
            method_name = match.group(1)
            if method_name not in ['class', 'interface', 'enum']:  # Filter out keywords
                line_num = content[:match.start()].count('\n') + 1
                component = ComponentInfo(
                    name=method_name,
                    type="method",
                    path=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    exports=[method_name],
                    metadata={"detected_by": "regex"}
                )
                result.add_component(component)

        return result


# Add more parsers for other languages
class GoParser(BaseParser):
    """Go language parser."""
    
    def __init__(self) -> None:
        super().__init__("go", [".go"])

    async def parse_file(self, file_path: str) -> ParseResult:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(file_path=file_path, language=self.language, success=False, error_message=str(e))

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        result = ParseResult(
            file_path=file_path, language=self.language, success=True,
            line_count=self.count_lines(content), size_bytes=len(content.encode()),
            file_hash=self.calculate_file_hash(content)
        )

        # Extract imports
        import_matches = re.findall(r'"([^"]+)"', re.search(r'import\s*\((.*?)\)', content, re.DOTALL).group(1) if re.search(r'import\s*\((.*?)\)', content, re.DOTALL) else "")
        result.imports.extend(import_matches)

        # Extract functions
        func_pattern = r'func\s+(?:\([^)]*\)\s+)?(\w+)\s*\([^)]*\)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            component = ComponentInfo(
                name=func_name, type="function", path=file_path,
                line_start=line_num, line_end=line_num,
                exports=[func_name] if func_name[0].isupper() else [],
                metadata={"detected_by": "regex"}
            )
            result.add_component(component)

        return result


class RustParser(BaseParser):
    """Rust language parser."""
    
    def __init__(self) -> None:
        super().__init__("rust", [".rs"])

    async def parse_file(self, file_path: str) -> ParseResult:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return await self.parse_content(content, file_path)
        except Exception as e:
            return ParseResult(file_path=file_path, language=self.language, success=False, error_message=str(e))

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        result = ParseResult(
            file_path=file_path, language=self.language, success=True,
            line_count=self.count_lines(content), size_bytes=len(content.encode()),
            file_hash=self.calculate_file_hash(content)
        )

        # Extract use statements
        use_matches = re.findall(r'use\s+([^;]+);', content)
        result.imports.extend(use_matches)

        # Extract functions
        func_pattern = r'(?:pub\s+)?(?:async\s+)?(?:unsafe\s+)?fn\s+(\w+)\s*\([^)]*\)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            component = ComponentInfo(
                name=func_name, type="function", path=file_path,
                line_start=line_num, line_end=line_num,
                exports=[func_name],
                metadata={"detected_by": "regex"}
            )
            result.add_component(component)

        # Extract structs
        struct_pattern = r'(?:pub\s+)?struct\s+(\w+)'
        for match in re.finditer(struct_pattern, content):
            struct_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            component = ComponentInfo(
                name=struct_name, type="struct", path=file_path,
                line_start=line_num, line_end=line_num,
                exports=[struct_name],
                metadata={"detected_by": "regex"}
            )
            result.add_component(component)

        return result


# Add stub parsers for remaining languages
class CSharpParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("csharp", [".cs"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class CppParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("cpp", [".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++", ".h"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class PhpParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("php", [".php", ".phtml", ".php3", ".php4", ".php5", ".phps"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class RubyParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("ruby", [".rb", ".rbw"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class SwiftParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("swift", [".swift"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class KotlinParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("kotlin", [".kt", ".kts"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class DartParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("dart", [".dart"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class ScalaParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("scala", [".scala", ".sc"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)


class LuaParser(BaseParser):
    def __init__(self) -> None:
        super().__init__("lua", [".lua", ".wlua"])

    async def parse_file(self, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        return ParseResult(file_path=file_path, language=self.language, success=True)
