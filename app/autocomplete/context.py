"""Code context analysis for autocomplete."""

from __future__ import annotations

import logging
import ast
import re
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from .models import CodeContext

logger = logging.getLogger(__name__)


class CodeContextAnalyzer:
    """Analyzes code context for autocomplete suggestions."""
    
    def __init__(self) -> None:
        self.language_parsers = {
            'python': self._analyze_python_context,
            'javascript': self._analyze_javascript_context,
            'typescript': self._analyze_typescript_context,
            'java': self._analyze_java_context,
            'go': self._analyze_go_context,
            'rust': self._analyze_rust_context,
            'cpp': self._analyze_cpp_context,
            'c': self._analyze_c_context,
            'csharp': self._analyze_csharp_context,
            'php': self._analyze_php_context,
            'ruby': self._analyze_ruby_context,
            'swift': self._analyze_swift_context,
            'kotlin': self._analyze_kotlin_context,
            'dart': self._analyze_dart_context,
            'scala': self._analyze_scala_context,
        }
    
    def analyze_context(self, code: str, cursor_position: int, language: str, file_path: Optional[str] = None) -> CodeContext:
        """Analyze code context at cursor position."""
        try:
            # Extract basic context
            lines = code.split('\n')
            current_line_index = code[:cursor_position].count('\n')
            current_line = lines[current_line_index] if current_line_index < len(lines) else ""
            
            # Find cursor position in current line
            line_start = code.rfind('\n', 0, cursor_position) + 1
            cursor_in_line = cursor_position - line_start
            
            # Extract surrounding text
            preceding_text = code[:cursor_position]
            following_text = code[cursor_position:]
            
            # Get current line content before and after cursor
            line_before = current_line[:cursor_in_line]
            line_after = current_line[cursor_in_line:]
            
            # Language-specific analysis
            analyzer = self.language_parsers.get(language, self._analyze_generic_context)
            scope_info = analyzer(preceding_text, line_before, current_line)
            
            return CodeContext(
                language=language,
                file_path=file_path,
                cursor_position=cursor_position,
                current_line=current_line,
                preceding_text=preceding_text,
                following_text=following_text,
                scope=scope_info.get('scope', {}),
                imports=scope_info.get('imports', []),
                variables=scope_info.get('variables', []),
                functions=scope_info.get('functions', []),
                classes=scope_info.get('classes', [])
            )
            
        except Exception as e:
            logger.error(f"Error analyzing context: {e}")
            # Return basic context
            return CodeContext(
                language=language,
                file_path=file_path,
                cursor_position=cursor_position,
                current_line="",
                preceding_text=code[:cursor_position],
                following_text=code[cursor_position:],
                scope={},
                imports=[],
                variables=[],
                functions=[],
                classes=[]
            )
    
    def _analyze_python_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Python code context."""
        try:
            # Parse the preceding text as Python AST
            tree = ast.parse(preceding_text)
            
            scope = {
                'current_function': None,
                'current_class': None,
                'indent_level': len(line_before) - len(line_before.lstrip()),
                'in_class': False,
                'in_function': False,
                'in_import': False,
                'in_comment': False
            }
            
            imports = []
            variables = []
            functions = []
            classes = []
            
            # Walk through AST to extract context
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                    # Check if we're inside this function
                    if hasattr(node, 'end_lineno') and node.end_lineno:
                        # This would need proper line number tracking
                        pass
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        variables.append(node.id)
            
            # Check current line context
            if 'import' in line_before or 'from' in line_before:
                scope['in_import'] = True
            elif line_before.strip().startswith('#'):
                scope['in_comment'] = True
            
            # Check indentation for class/function context
            indent_level = scope['indent_level']
            if indent_level >= 4:
                scope['in_function'] = True
            if indent_level >= 8:
                scope['in_class'] = True
            
            return {
                'scope': scope,
                'imports': imports,
                'variables': variables,
                'functions': functions,
                'classes': classes
            }
            
        except SyntaxError:
            # Fallback for incomplete code
            return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_javascript_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze JavaScript code context."""
        scope = {
            'current_function': None,
            'current_class': None,
            'indent_level': len(line_before) - len(line_before.lstrip()),
            'in_function': False,
            'in_class': False,
            'in_import': False,
            'in_comment': False,
            'in_object': False
        }
        
        imports = []
        variables = []
        functions = []
        classes = []
        
        lines = preceding_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Import detection
            if line.startswith('import ') or line.startswith('const ') and 'require' in line:
                if 'from' in line:
                    imports.append(line.split('from')[1].strip().strip("';"))
                elif 'require' in line:
                    imports.append(line.split('require')[1].strip('()";'))
            
            # Function detection
            if line.startswith('function ') or 'function ' in line:
                func_match = re.search(r'function\s+(\w+)', line)
                if func_match:
                    functions.append(func_match.group(1))
            
            # Arrow function detection
            if '=>' in line:
                arrow_match = re.search(r'(\w+)\s*=', line.split('=>')[0])
                if arrow_match:
                    functions.append(arrow_match.group(1))
            
            # Class detection
            if line.startswith('class '):
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match:
                    classes.append(class_match.group(1))
            
            # Variable detection
            if line.startswith(('const ', 'let ', 'var ')):
                var_match = re.search(r'(?:const|let|var)\s+(\w+)', line)
                if var_match:
                    variables.append(var_match.group(1))
        
        # Current line context
        if 'import' in line_before or 'require' in line_before:
            scope['in_import'] = True
        elif line_before.strip().startswith('//') or line_before.strip().startswith('/*'):
            scope['in_comment'] = True
        elif '{' in line_before and '}' not in line_before:
            scope['in_object'] = True
        
        return {
            'scope': scope,
            'imports': imports,
            'variables': variables,
            'functions': functions,
            'classes': classes
        }
    
    def _analyze_typescript_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze TypeScript code context."""
        # Similar to JavaScript but with type annotations
        result = self._analyze_javascript_context(preceding_text, line_before, current_line)
        
        # Add TypeScript-specific features
        lines = preceding_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Interface detection
            if line.startswith('interface '):
                interface_match = re.search(r'interface\s+(\w+)', line)
                if interface_match:
                    result['classes'].append(interface_match.group(1))  # Treat interfaces as classes for autocomplete
            
            # Type detection
            if line.startswith('type '):
                type_match = re.search(r'type\s+(\w+)', line)
                if type_match:
                    result['variables'].append(type_match.group(1))
        
        return result
    
    def _analyze_java_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Java code context."""
        scope = {
            'current_class': None,
            'current_method': None,
            'indent_level': len(line_before) - len(line_before.lstrip()),
            'in_class': False,
            'in_method': False,
            'in_import': False,
            'in_comment': False
        }
        
        imports = []
        variables = []
        functions = []
        classes = []
        
        lines = preceding_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Import detection
            if line.startswith('import ') or line.startswith('package '):
                if line.startswith('import '):
                    imports.append(line.replace('import ', '').replace(';', ''))
            
            # Class detection
            if re.match(r'(public|private|protected)?\s*class\s+\w+', line):
                class_match = re.search(r'class\s+(\w+)', line)
                if class_match:
                    classes.append(class_match.group(1))
            
            # Method detection
            if re.match(r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', line):
                method_match = re.search(r'\w+\s+(\w+)\s*\(', line)
                if method_match:
                    functions.append(method_match.group(1))
            
            # Variable detection
            if re.match(r'(public|private|protected)?\s*(static)?\s*\w+\s+\w+', line):
                var_match = re.search(r'\w+\s+(\w+)(?=\s*[;=])', line)
                if var_match:
                    variables.append(var_match.group(1))
        
        # Current line context
        if 'import' in line_before:
            scope['in_import'] = True
        elif line_before.strip().startswith('//') or line_before.strip().startswith('/*'):
            scope['in_comment'] = True
        
        return {
            'scope': scope,
            'imports': imports,
            'variables': variables,
            'functions': functions,
            'classes': classes
        }
    
    def _analyze_go_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Go code context."""
        scope = {
            'current_function': None,
            'current_package': None,
            'indent_level': len(line_before) - len(line_before.lstrip()),
            'in_function': False,
            'in_import': False,
            'in_comment': False
        }
        
        imports = []
        variables = []
        functions = []
        classes = []  # Go uses structs, but we'll call them classes for consistency
        
        lines = preceding_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Import detection
            if line.startswith('import '):
                imports.append(line.replace('import ', '').replace('"', ''))
            
            # Function detection
            if line.startswith('func '):
                func_match = re.search(r'func\s+(\w+)', line)
                if func_match:
                    functions.append(func_match.group(1))
            
            # Struct detection
            if line.startswith('type '):
                struct_match = re.search(r'type\s+(\w+)\s+struct', line)
                if struct_match:
                    classes.append(struct_match.group(1))
            
            # Variable detection
            if line.startswith('var ') or ':=' in line:
                if line.startswith('var '):
                    var_match = re.search(r'var\s+(\w+)', line)
                    if var_match:
                        variables.append(var_match.group(1))
                elif ':=' in line:
                    var_match = re.search(r'(\w+)\s*:=', line)
                    if var_match:
                        variables.append(var_match.group(1))
        
        return {
            'scope': scope,
            'imports': imports,
            'variables': variables,
            'functions': functions,
            'classes': classes
        }
    
    def _analyze_generic_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Generic context analysis for unknown languages."""
        scope = {
            'indent_level': len(line_before) - len(line_before.lstrip()),
            'in_comment': line_before.strip().startswith('#') or line_before.strip().startswith('//')
        }
        
        # Basic pattern matching
        imports = []
        variables = []
        functions = []
        classes = []
        
        lines = preceding_text.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Generic import detection
            if 'import' in line.lower():
                imports.append(line)
            
            # Generic function detection
            if 'function' in line.lower() or 'def' in line.lower():
                func_match = re.search(r'(?:function|def)\s+(\w+)', line, re.IGNORECASE)
                if func_match:
                    functions.append(func_match.group(1))
            
            # Generic class detection
            if 'class' in line.lower():
                class_match = re.search(r'class\s+(\w+)', line, re.IGNORECASE)
                if class_match:
                    classes.append(class_match.group(1))
        
        return {
            'scope': scope,
            'imports': imports,
            'variables': variables,
            'functions': functions,
            'classes': classes
        }
    
    # Placeholder methods for other languages
    def _analyze_rust_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Rust code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_cpp_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze C++ code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_c_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze C code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_csharp_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze C# code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_php_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze PHP code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_ruby_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Ruby code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_swift_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Swift code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_kotlin_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Kotlin code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_dart_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Dart code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
    
    def _analyze_scala_context(self, preceding_text: str, line_before: str, current_line: str) -> Dict[str, Any]:
        """Analyze Scala code context."""
        return self._analyze_generic_context(preceding_text, line_before, current_line)
