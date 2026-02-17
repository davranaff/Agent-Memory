"""Parser registry for managing language parsers."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class ParserRegistry:
    """Registry for managing language parsers."""

    def __init__(self) -> None:
        self._parsers: Dict[str, BaseParser] = {}
        self._extension_map: Dict[str, str] = {}

    def register(self, parser: BaseParser) -> None:
        """Register a parser for a language."""
        self._parsers[parser.language] = parser
        
        # Map file extensions to parsers
        for ext in parser.file_extensions:
            self._extension_map[ext.lower()] = parser.language

    def get_parser(self, language: str) -> Optional[BaseParser]:
        """Get parser by language name."""
        return self._parsers.get(language)

    def get_parser_by_file(self, file_path: str) -> Optional[BaseParser]:
        """Get parser by file extension."""
        ext = Path(file_path).suffix.lower()
        language = self._extension_map.get(ext)
        if language:
            return self._parsers.get(language)
        return None

    def can_parse(self, file_path: str) -> bool:
        """Check if any parser can handle the file."""
        return self.get_parser_by_file(file_path) is not None

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return list(self._parsers.keys())

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return list(self._extension_map.keys())

    async def parse_file(self, file_path: str) -> ParseResult:
        """Parse a file using the appropriate parser."""
        parser = self.get_parser_by_file(file_path)
        if not parser:
            return ParseResult(
                file_path=file_path,
                language="unknown",
                success=False,
                error_message=f"No parser found for file: {file_path}"
            )
        
        try:
            return await parser.parse_file(file_path)
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return ParseResult(
                file_path=file_path,
                language=parser.language,
                success=False,
                error_message=str(e)
            )

    async def parse_content(self, content: str, file_path: str) -> ParseResult:
        """Parse content using the appropriate parser."""
        parser = self.get_parser_by_file(file_path)
        if not parser:
            return ParseResult(
                file_path=file_path,
                language="unknown",
                success=False,
                error_message=f"No parser found for file: {file_path}"
            )
        
        try:
            return await parser.parse_content(content, file_path)
        except Exception as e:
            logger.error(f"Error parsing content for {file_path}: {e}")
            return ParseResult(
                file_path=file_path,
                language=parser.language,
                success=False,
                error_message=str(e)
            )


# Global registry instance
_registry = ParserRegistry()


def get_registry() -> ParserRegistry:
    """Get the global parser registry."""
    return _registry


def register_parser(parser: BaseParser) -> None:
    """Register a parser with the global registry."""
    _registry.register(parser)


def get_parser(language: str) -> Optional[BaseParser]:
    """Get parser by language from global registry."""
    return _registry.get_parser(language)


def get_parser_by_file(file_path: str) -> Optional[BaseParser]:
    """Get parser by file extension from global registry."""
    return _registry.get_parser_by_file(file_path)


async def parse_file(file_path: str) -> ParseResult:
    """Parse a file using the global registry."""
    return await _registry.parse_file(file_path)


async def parse_content(content: str, file_path: str) -> ParseResult:
    """Parse content using the global registry."""
    return await _registry.parse_content(content, file_path)
