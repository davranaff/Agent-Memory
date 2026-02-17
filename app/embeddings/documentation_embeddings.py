"""Documentation Embeddings for README, API docs, and other documentation."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

from app.memory.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class DocumentationType(str, Enum):
    """Types of documentation."""
    README = "readme"
    API_DOCS = "api_docs"
    CODE_COMMENTS = "code_comments"
    INLINE_DOCS = "inline_docs"
    TUTORIAL = "tutorial"
    GUIDE = "guide"
    REFERENCE = "reference"
    EXAMPLE = "example"


@dataclass
class DocumentationEmbedding:
    """Embedding for documentation content."""
    embedding_id: str
    doc_id: str
    doc_type: DocumentationType
    vector: List[float]
    metadata: Dict[str, Any]
    content: str
    summary: str
    sections: List[str]
    code_examples: List[str]
    created_at: str


class DocumentationEmbeddingGenerator:
    """Generate embeddings for documentation content."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._section_patterns = self._initialize_section_patterns()
    
    async def generate_documentation_embedding(self,
                                             doc_id: str,
                                             content: str,
                                             doc_type: DocumentationType,
                                             file_path: Optional[str] = None) -> DocumentationEmbedding:
        """Generate embedding for documentation content."""
        try:
            # Extract structured information
            sections = self._extract_sections(content)
            code_examples = self._extract_code_examples(content)
            summary = self._generate_summary(content)
            
            # Create enhanced text for embedding
            enhanced_text = self._create_enhanced_text(content, sections, code_examples, summary)
            
            # Generate embedding
            vector = await self.embedding_provider.embed_text(enhanced_text)
            
            # Create embedding object
            embedding_id = self._generate_embedding_id(doc_id, doc_type, content)
            
            return DocumentationEmbedding(
                embedding_id=embedding_id,
                doc_id=doc_id,
                doc_type=doc_type,
                vector=vector,
                metadata={
                    "file_path": file_path,
                    "content_length": len(content),
                    "section_count": len(sections),
                    "code_example_count": len(code_examples),
                    "language": self._detect_language(content),
                    "complexity": self._calculate_complexity(content)
                },
                content=content,
                summary=summary,
                sections=sections,
                code_examples=code_examples,
                created_at="2024-01-01T00:00:00Z"
            )
            
        except Exception as e:
            logger.error(f"Error generating documentation embedding: {e}")
            raise
    
    async def search_documentation(self,
                                 query: str,
                                 doc_embeddings: List[DocumentationEmbedding],
                                 limit: int = 10) -> List[Tuple[DocumentationEmbedding, float]]:
        """Search documentation by semantic similarity."""
        # Generate embedding for query
        query_vector = await self.embedding_provider.embed_text(query)
        
        # Calculate similarities
        similarities = []
        for doc_emb in doc_embeddings:
            similarity = self._calculate_similarity(query_vector, doc_emb.vector)
            similarities.append((doc_emb, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:limit]
    
    async def find_relevant_documentation(self,
                                         code_context: str,
                                         doc_embeddings: List[DocumentationEmbedding],
                                         doc_type: Optional[DocumentationType] = None) -> List[Tuple[DocumentationEmbedding, float]]:
        """Find documentation relevant to code context."""
        # Filter by doc type if specified
        if doc_type:
            filtered_embeddings = [emb for emb in doc_embeddings if emb.doc_type == doc_type]
        else:
            filtered_embeddings = doc_embeddings
        
        # Generate embedding for code context
        context_vector = await self.embedding_provider.embed_text(code_context)
        
        # Calculate similarities
        similarities = []
        for doc_emb in filtered_embeddings:
            similarity = self._calculate_similarity(context_vector, doc_emb.vector)
            similarities.append((doc_emb, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:5]  # Return top 5 most relevant
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract section headings from documentation."""
        sections = []
        
        # Common section patterns
        patterns = [
            r'^#+\s+(.+)$',  # Markdown headers
            r'^[A-Z][A-Z\s]+:$',  # ALL CAPS headers
            r'^\d+\.\s+(.+)$',  # Numbered sections
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*:$',  # Title Case headers
        ]
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in patterns:
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    section = match.group(1) if match.groups() else line
                    sections.append(section)
                    break
        
        return sections
    
    def _extract_code_examples(self, content: str) -> List[str]:
        """Extract code examples from documentation."""
        code_examples = []
        
        # Markdown code blocks
        code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
        code_examples.extend(code_blocks)
        
        # Inline code
        inline_code = re.findall(r'`([^`]+)`', content)
        code_examples.extend([code for code in inline_code if len(code.split('\n')) == 1])
        
        # Indented code blocks
        indented_blocks = re.findall(r'^(?: {4}|\t)(.+)$', content, re.MULTILINE)
        if indented_blocks:
            # Group consecutive indented lines
            current_block = []
            for line in indented_blocks:
                if line.strip():
                    current_block.append(line)
                else:
                    if current_block:
                        code_examples.append('\n'.join(current_block))
                        current_block = []
            if current_block:
                code_examples.append('\n'.join(current_block))
        
        return code_examples
    
    def _generate_summary(self, content: str) -> str:
        """Generate a summary of the documentation content."""
        # Take first paragraph or first few lines
        lines = content.split('\n')
        summary_lines = []
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                summary_lines.append(line)
                if len(summary_lines) >= 3:  # Take first 3 non-header lines
                    break
        
        if summary_lines:
            summary = ' '.join(summary_lines)
            # Truncate if too long
            if len(summary) > 200:
                summary = summary[:200] + '...'
            return summary
        
        # Fallback to first 200 characters
        return content[:200] + '...' if len(content) > 200 else content
    
    def _create_enhanced_text(self,
                            content: str,
                            sections: List[str],
                            code_examples: List[str],
                            summary: str) -> str:
        """Create enhanced text representation for embedding."""
        text_parts = []
        
        # Add summary
        if summary:
            text_parts.append(f"Summary: {summary}")
        
        # Add sections
        if sections:
            sections_text = " | ".join(sections[:10])  # Limit to first 10
            text_parts.append(f"Sections: {sections_text}")
        
        # Add code examples (brief)
        if code_examples:
            # Take first few examples and truncate them
            example_snippets = []
            for example in code_examples[:3]:
                snippet = example[:100] + '...' if len(example) > 100 else example
                example_snippets.append(snippet)
            text_parts.append(f"Code examples: {' | '.join(example_snippets)}")
        
        # Add content sample
        content_sample = content[:500]
        text_parts.append(f"Content: {content_sample}")
        
        return " | ".join(text_parts)
    
    def _detect_language(self, content: str) -> str:
        """Detect the primary language of the documentation."""
        # Look for language indicators
        language_patterns = {
            'python': [r'python', r'py\s+', r'def\s+', r'import\s+', r'from\s+'],
            'javascript': [r'javascript', r'js\s+', r'function\s+', r'const\s+', r'let\s+'],
            'typescript': [r'typescript', r'ts\s+', r'interface\s+', r'type\s+'],
            'java': [r'java', r'public\s+class', r'private\s+', r'protected\s+'],
            'go': [r'go\s+', r'func\s+', r'package\s+', r'import\s+'],
            'rust': [r'rust', r'fn\s+', r'let\s+mut', r'use\s+'],
            'csharp': [r'c#', r'csharp', r'public\s+class', r'namespace\s+'],
            'cpp': [r'c\+\+', r'cpp', r'#include', r'std::'],
            'php': [r'php', r'\$\w+', r'function\s+\w+\s*\(', r'class\s+\w+'],
            'ruby': [r'ruby', r'def\s+', r'class\s+', r'module\s+'],
        }
        
        content_lower = content.lower()
        scores = {}
        
        for lang, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower))
                score += matches
            scores[lang] = score
        
        if scores:
            best_lang = max(scores, key=scores.get)
            if scores[best_lang] > 0:
                return best_lang
        
        return 'unknown'
    
    def _calculate_complexity(self, content: str) -> str:
        """Calculate complexity of documentation."""
        # Simple complexity metrics
        length_score = min(len(content) / 5000, 1.0)  # Normalize to 0-1
        section_score = min(len(self._extract_sections(content)) / 20, 1.0)
        code_score = min(len(self._extract_code_examples(content)) / 10, 1.0)
        
        overall_score = (length_score + section_score + code_score) / 3
        
        if overall_score < 0.3:
            return 'simple'
        elif overall_score < 0.7:
            return 'moderate'
        else:
            return 'complex'
    
    def _initialize_section_patterns(self) -> Dict[str, List[str]]:
        """Initialize common section patterns for different doc types."""
        return {
            'readme': [
                'installation', 'usage', 'examples', 'contributing', 'license',
                'getting started', 'quick start', 'documentation', 'api',
                'features', 'requirements', 'setup', 'configuration'
            ],
            'api_docs': [
                'endpoints', 'parameters', 'responses', 'authentication',
                'errors', 'examples', 'overview', 'reference', 'methods',
                'request', 'response', 'status codes', 'headers'
            ],
            'tutorial': [
                'introduction', 'prerequisites', 'step 1', 'step 2', 'step 3',
                'conclusion', 'next steps', 'exercises', 'summary',
                'getting started', 'what you will learn'
            ],
            'guide': [
                'overview', 'concepts', 'implementation', 'best practices',
                'troubleshooting', 'faq', 'advanced topics', 'examples',
                'configuration', 'deployment'
            ]
        }
    
    def _calculate_similarity(self, vector1: List[float], vector2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        import math
        
        if len(vector1) != len(vector2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _generate_embedding_id(self, doc_id: str, doc_type: DocumentationType, content: str) -> str:
        """Generate unique embedding ID."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        return hashlib.sha256(f"{doc_id}:{doc_type.value}:{content_hash}".encode()).hexdigest()[:32]
