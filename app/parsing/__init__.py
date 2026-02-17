"""Universal Code Parsing System for Agent Brain."""

from __future__ import annotations

from .base import BaseParser, ParseResult, ComponentInfo
from .registry import ParserRegistry, get_registry, register_parser, get_parser, get_parser_by_file, parse_file, parse_content
from .languages import (
    PythonParser,
    JavaScriptParser,
    TypeScriptParser,
    JavaParser,
    GoParser,
    RustParser,
    CSharpParser,
    CppParser,
    PhpParser,
    RubyParser,
    SwiftParser,
    KotlinParser,
    DartParser,
    ScalaParser,
    LuaParser,
)

# Auto-register all parsers
def _register_all_parsers() -> None:
    """Register all built-in parsers."""
    parsers = [
        PythonParser(),
        JavaScriptParser(),
        TypeScriptParser(),
        JavaParser(),
        GoParser(),
        RustParser(),
        CSharpParser(),
        CppParser(),
        PhpParser(),
        RubyParser(),
        SwiftParser(),
        KotlinParser(),
        DartParser(),
        ScalaParser(),
        LuaParser(),
    ]
    
    registry = get_registry()
    for parser in parsers:
        register_parser(parser)

# Register parsers on import
_register_all_parsers()

__all__ = [
    "BaseParser",
    "ParseResult",
    "ComponentInfo",
    "ParserRegistry",
    "get_registry",
    "register_parser",
    "get_parser",
    "get_parser_by_file",
    "parse_file",
    "parse_content",
    "PythonParser",
    "JavaScriptParser",
    "TypeScriptParser",
    "JavaParser",
    "GoParser",
    "RustParser",
    "CSharpParser",
    "CppParser",
    "PhpParser",
    "RubyParser",
    "SwiftParser",
    "KotlinParser",
    "DartParser",
    "ScalaParser",
    "LuaParser",
]
