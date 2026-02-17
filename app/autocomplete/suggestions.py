"""Suggestion engine for context-aware autocomplete."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .models import Suggestion, SuggestionType, SuggestionPriority, CodeContext, CompletionPattern
from .context import CodeContextAnalyzer

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """Generates context-aware autocomplete suggestions."""
    
    def __init__(self) -> None:
        self.context_analyzer = CodeContextAnalyzer()
        self.patterns = self._load_completion_patterns()
        self.language_keywords = self._load_language_keywords()
        self.standard_libraries = self._load_standard_libraries()
    
    def generate_suggestions(self, request: AutocompleteRequest) -> List[Suggestion]:
        """Generate autocomplete suggestions based on context and query."""
        try:
            suggestions = []
            
            # Analyze context if not provided
            context = request.context
            
            # Extract current prefix from query
            prefix = request.query.lower()
            
            # Generate different types of suggestions
            suggestions.extend(self._generate_keyword_suggestions(context, prefix))
            suggestions.extend(self._generate_variable_suggestions(context, prefix))
            suggestions.extend(self._generate_function_suggestions(context, prefix))
            suggestions.extend(self._generate_class_suggestions(context, prefix))
            suggestions.extend(self._generate_import_suggestions(context, prefix))
            
            if request.include_snippets:
                suggestions.extend(self._generate_snippet_suggestions(context, prefix))
            
            if request.include_patterns:
                suggestions.extend(self._generate_pattern_suggestions(context, prefix))
            
            if request.language_specific:
                suggestions.extend(self._generate_language_specific_suggestions(context, prefix))
            
            # Sort by priority and confidence
            suggestions.sort(key=lambda x: (self._priority_score(x.priority), x.confidence), reverse=True)
            
            # Limit results
            return suggestions[:request.max_results]
            
        except Exception as e:
            logger.error(f"Error generating suggestions: {e}")
            return []
    
    def _generate_keyword_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate keyword suggestions."""
        suggestions = []
        keywords = self.language_keywords.get(context.language, [])
        
        for keyword in keywords:
            if keyword.lower().startswith(prefix):
                suggestions.append(Suggestion(
                    text=keyword,
                    display_text=keyword,
                    type=SuggestionType.KEYWORD,
                    priority=SuggestionPriority.HIGH,
                    description=f"Python keyword: {keyword}",
                    confidence=0.9,
                    metadata={"category": "keyword"}
                ))
        
        return suggestions
    
    def _generate_variable_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate variable suggestions."""
        suggestions = []
        
        for var in context.variables:
            if var.lower().startswith(prefix):
                suggestions.append(Suggestion(
                    text=var,
                    display_text=var,
                    type=SuggestionType.VARIABLE,
                    priority=SuggestionPriority.MEDIUM,
                    description=f"Variable: {var}",
                    confidence=0.8,
                    metadata={"category": "variable"}
                ))
        
        return suggestions
    
    def _generate_function_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate function suggestions."""
        suggestions = []
        
        for func in context.functions:
            if func.lower().startswith(prefix):
                suggestions.append(Suggestion(
                    text=func,
                    display_text=f"{func}()",
                    type=SuggestionType.FUNCTION,
                    priority=SuggestionPriority.HIGH,
                    description=f"Function: {func}",
                    insert_text=f"{func}()",
                    confidence=0.85,
                    metadata={"category": "function"}
                ))
        
        return suggestions
    
    def _generate_class_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate class suggestions."""
        suggestions = []
        
        for cls in context.classes:
            if cls.lower().startswith(prefix):
                suggestions.append(Suggestion(
                    text=cls,
                    display_text=cls,
                    type=SuggestionType.CLASS,
                    priority=SuggestionPriority.HIGH,
                    description=f"Class: {cls}",
                    confidence=0.85,
                    metadata={"category": "class"}
                ))
        
        return suggestions
    
    def _generate_import_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate import suggestions."""
        suggestions = []
        
        # Check if we're in an import statement
        if context.scope.get('in_import', False):
            libraries = self.standard_libraries.get(context.language, [])
            
            for lib in libraries:
                if lib.lower().startswith(prefix):
                    suggestions.append(Suggestion(
                        text=lib,
                        display_text=lib,
                        type=SuggestionType.IMPORT,
                        priority=SuggestionPriority.MEDIUM,
                        description=f"Import library: {lib}",
                        confidence=0.7,
                        metadata={"category": "import"}
                    ))
        
        return suggestions
    
    def _generate_snippet_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate code snippet suggestions."""
        suggestions = []
        
        # Language-specific snippets
        if context.language == 'python':
            snippets = {
                'def': 'def ${1:function_name}(${2:args}):\n    ${3:pass}',
                'class': 'class ${1:ClassName}:\n    def __init__(self${2:, args}):\n        ${3:pass}',
                'if': 'if ${1:condition}:\n    ${2:pass}',
                'for': 'for ${1:item} in ${2:iterable}:\n    ${3:pass}',
                'try': 'try:\n    ${1:pass}\nexcept ${2:Exception}:\n    ${3:pass}',
                'with': 'with ${1:context} as ${2:variable}:\n    ${3:pass}',
                'lambda': 'lambda ${1:args}: ${2:expression}',
                'list': '[${1:item} for ${2:item} in ${3:iterable}]',
                'dict': '{${1:key}: ${2:value} for ${3:key}, ${4:value} in ${5:iterable}}'
            }
        elif context.language == 'javascript':
            snippets = {
                'function': 'function ${1:functionName}(${2:args}) {\n    ${3:// body}\n}',
                'arrow': 'const ${1:functionName} = (${2:args}) => {\n    ${3:// body}\n}',
                'class': 'class ${1:ClassName} {\n    constructor(${2:args}) {\n        ${3:// body}\n    }\n}',
                'if': 'if (${1:condition}) {\n    ${2:// body}\n}',
                'for': 'for (let ${1:item} of ${2:iterable}) {\n    ${3:// body}\n}',
                'try': 'try {\n    ${1:// body}\n} catch (${2:error}) {\n    ${3:// handle error}\n}',
                'async': 'async function ${1:functionName}(${2:args}) {\n    ${3:// body}\n}'
            }
        else:
            snippets = {}
        
        for trigger, template in snippets.items():
            if trigger.startswith(prefix):
                suggestions.append(Suggestion(
                    text=trigger,
                    display_text=trigger,
                    type=SuggestionType.SNIPPET,
                    priority=SuggestionPriority.MEDIUM,
                    description=f"Code snippet: {trigger}",
                    insert_text=template,
                    confidence=0.6,
                    metadata={"category": "snippet", "template": template}
                ))
        
        return suggestions
    
    def _generate_pattern_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate design pattern suggestions."""
        suggestions = []
        
        # Filter patterns by language
        language_patterns = [p for p in self.patterns if p.language == context.language or p.language == 'all']
        
        for pattern in language_patterns:
            if pattern.trigger.lower().startswith(prefix):
                suggestions.append(Suggestion(
                    text=pattern.name,
                    display_text=pattern.name,
                    type=SuggestionType.PATTERN,
                    priority=SuggestionPriority.LOW,
                    description=pattern.description,
                    insert_text=pattern.template,
                    confidence=0.5,
                    metadata={
                        "category": "pattern",
                        "template": pattern.template,
                        "variables": pattern.variables
                    }
                ))
        
        return suggestions
    
    def _generate_language_specific_suggestions(self, context: CodeContext, prefix: str) -> List[Suggestion]:
        """Generate language-specific suggestions."""
        suggestions = []
        
        if context.language == 'python':
            # Python-specific suggestions
            python_builtins = ['print', 'len', 'str', 'int', 'float', 'list', 'dict', 'set', 'tuple', 'range', 'enumerate', 'zip', 'map', 'filter', 'sorted', 'sum', 'max', 'min', 'abs', 'round']
            
            for builtin in python_builtins:
                if builtin.lower().startswith(prefix):
                    suggestions.append(Suggestion(
                        text=builtin,
                        display_text=f"{builtin}()",
                        type=SuggestionType.FUNCTION,
                        priority=SuggestionPriority.HIGH,
                        description=f"Python built-in: {builtin}",
                        insert_text=f"{builtin}()",
                        confidence=0.9,
                        metadata={"category": "builtin"}
                    ))
            
            # Common modules
            common_modules = ['os', 'sys', 'json', 'datetime', 'math', 'random', 'collections', 'itertools', 'functools', 'pathlib', 're', 'urllib', 'http', 'sqlite3']
            
            for module in common_modules:
                if module.lower().startswith(prefix):
                    suggestions.append(Suggestion(
                        text=module,
                        display_text=module,
                        type=SuggestionType.IMPORT,
                        priority=SuggestionPriority.MEDIUM,
                        description=f"Python module: {module}",
                        confidence=0.7,
                        metadata={"category": "module"}
                    ))
        
        elif context.language == 'javascript':
            # JavaScript-specific suggestions
            js_builtins = ['console', 'document', 'window', 'Array', 'Object', 'String', 'Number', 'Boolean', 'Date', 'Math', 'JSON', 'Promise', 'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval']
            
            for builtin in js_builtins:
                if builtin.lower().startswith(prefix):
                    suggestions.append(Suggestion(
                        text=builtin,
                        display_text=builtin,
                        type=SuggestionType.VARIABLE,
                        priority=SuggestionPriority.HIGH,
                        description=f"JavaScript built-in: {builtin}",
                        confidence=0.9,
                        metadata={"category": "builtin"}
                    ))
        
        return suggestions
    
    def _priority_score(self, priority: SuggestionPriority) -> int:
        """Get numeric score for priority."""
        scores = {
            SuggestionPriority.HIGH: 3,
            SuggestionPriority.MEDIUM: 2,
            SuggestionPriority.LOW: 1
        }
        return scores.get(priority, 1)
    
    def _load_completion_patterns(self) -> List[CompletionPattern]:
        """Load code completion patterns."""
        patterns = [
            # Python patterns
            CompletionPattern(
                name="Singleton Pattern",
                trigger="singleton",
                description="Singleton design pattern implementation",
                template="class ${1:ClassName}:\n    _instance = None\n    \n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance",
                language="python",
                category="creational",
                variables=["ClassName"]
            ),
            CompletionPattern(
                name="Factory Pattern",
                trigger="factory",
                description="Factory design pattern implementation",
                template="class ${1:ProductFactory}:\n    @staticmethod\n    def create_${2:product_type}():\n        return ${2:ProductType}()",
                language="python",
                category="creational",
                variables=["ProductFactory", "product_type", "ProductType"]
            ),
            # JavaScript patterns
            CompletionPattern(
                name="Module Pattern",
                trigger="module",
                description="JavaScript module pattern",
                template="const ${1:ModuleName} = (function() {\n    'use strict';\n    \n    // Private variables\n    let ${2:privateVar} = null;\n    \n    // Public API\n    return {\n        ${3:publicMethod}: function() {\n            // implementation\n        }\n    };\n})();",
                language="javascript",
                category="structural",
                variables=["ModuleName", "privateVar", "publicMethod"]
            ),
            # Generic patterns
            CompletionPattern(
                name="Error Handling",
                trigger="error",
                description="Standard error handling pattern",
                template="try:\n    ${1:// risky code}\nexcept ${2:Exception} as e:\n    ${3:// handle error}\nfinally:\n    ${4:// cleanup}",
                language="all",
                category="error_handling",
                variables=[]
            )
        ]
        
        return patterns
    
    def _load_language_keywords(self) -> Dict[str, List[str]]:
        """Load language keywords."""
        return {
            'python': [
                'and', 'as', 'assert', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
                'except', 'exec', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
                'lambda', 'not', 'or', 'pass', 'print', 'raise', 'return', 'try', 'while', 'with',
                'yield', 'async', 'await', 'nonlocal'
            ],
            'javascript': [
                'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
                'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function',
                'if', 'import', 'in', 'instanceof', 'let', 'new', 'return', 'super', 'switch',
                'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'async', 'await'
            ],
            'typescript': [
                'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default',
                'delete', 'do', 'else', 'export', 'extends', 'finally', 'for', 'function',
                'if', 'import', 'in', 'instanceof', 'let', 'new', 'return', 'super', 'switch',
                'this', 'throw', 'try', 'typeof', 'var', 'void', 'while', 'with', 'yield', 'async',
                'await', 'type', 'interface', 'implements', 'declare', 'module', 'namespace'
            ],
            'java': [
                'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char', 'class',
                'const', 'continue', 'default', 'do', 'double', 'else', 'enum', 'extends', 'final',
                'finally', 'float', 'for', 'goto', 'if', 'implements', 'import', 'instanceof',
                'int', 'interface', 'long', 'native', 'new', 'package', 'private', 'protected',
                'public', 'return', 'short', 'static', 'strictfp', 'super', 'switch', 'synchronized',
                'this', 'throw', 'throws', 'transient', 'try', 'void', 'volatile', 'while'
            ],
            'go': [
                'break', 'case', 'chan', 'const', 'continue', 'default', 'defer', 'else', 'fallthrough',
                'for', 'func', 'go', 'goto', 'if', 'import', 'interface', 'map', 'package', 'range',
                'return', 'select', 'struct', 'switch', 'type', 'var'
            ]
        }
    
    def _load_standard_libraries(self) -> Dict[str, List[str]]:
        """Load standard libraries for different languages."""
        return {
            'python': [
                'os', 'sys', 'json', 'datetime', 'math', 'random', 'collections', 'itertools',
                'functools', 'pathlib', 're', 'urllib', 'http', 'sqlite3', 'csv', 'xml', 'html',
                'email', 'socket', 'ssl', 'hashlib', 'hmac', 'secrets', 'uuid', 'base64',
                'pickle', 'gzip', 'zipfile', 'tarfile', 'shutil', 'tempfile', 'glob', 'fnmatch',
                'time', 'calendar', 'locale', 'decimal', 'fractions', 'statistics', 'string',
                'textwrap', 'unicodedata', 'codecs', 'io', 'argparse', 'configparser', 'logging'
            ],
            'javascript': [
                'fs', 'path', 'http', 'https', 'url', 'querystring', 'util', 'events', 'stream',
                'buffer', 'child_process', 'cluster', 'os', 'crypto', 'tls', 'net', 'dgram', 'dns',
                'readline', 'repl', 'vm', 'v8', 'zlib', 'console', 'timers', 'process', 'global'
            ],
            'java': [
                'java.lang', 'java.util', 'java.io', 'java.net', 'java.nio', 'java.time', 'java.math',
                'java.text', 'java.sql', 'javax.sql', 'org.json', 'org.apache.commons', 'com.google.gson'
            ],
            'go': [
                'fmt', 'os', 'io', 'bufio', 'strings', 'strconv', 'time', 'math', 'math/rand',
                'net/http', 'net/url', 'encoding/json', 'encoding/xml', 'path/filepath', 'log'
            ]
        }
