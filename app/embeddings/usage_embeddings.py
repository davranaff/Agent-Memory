"""Usage Example Embeddings for real code examples and patterns."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

from app.memory.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class UsageType(str, Enum):
    """Types of usage examples."""
    CODE_SAMPLE = "code_sample"
    TUTORIAL = "tutorial"
    API_EXAMPLE = "api_example"
    CONFIGURATION = "configuration"
    TEST_CASE = "test_case"
    PATTERN_EXAMPLE = "pattern_example"
    BEST_PRACTICE = "best_practice"
    ANTI_PATTERN = "anti_pattern"


@dataclass
class UsageExampleEmbedding:
    """Embedding for usage examples."""
    embedding_id: str
    example_id: str
    usage_type: UsageType
    vector: List[float]
    metadata: Dict[str, Any]
    code: str
    description: str
    context: str
    tags: List[str]
    language: str
    created_at: str


class UsageExampleEmbeddingGenerator:
    """Generate embeddings for usage examples."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._code_patterns = self._initialize_code_patterns()
    
    async def generate_usage_embedding(self,
                                     example_id: str,
                                     code: str,
                                     description: str,
                                     usage_type: UsageType,
                                     context: Optional[str] = None,
                                     tags: Optional[List[str]] = None,
                                     language: Optional[str] = None) -> UsageExampleEmbedding:
        """Generate embedding for a usage example."""
        try:
            # Detect language if not provided
            if not language:
                language = self._detect_language(code)
            
            # Extract features from code
            code_features = self._extract_code_features(code, language)
            
            # Create enhanced text for embedding
            enhanced_text = self._create_enhanced_text(
                code, description, context, tags, code_features, usage_type
            )
            
            # Generate embedding
            vector = await self.embedding_provider.embed_text(enhanced_text)
            
            # Create embedding object
            embedding_id = self._generate_embedding_id(example_id, usage_type, code)
            
            return UsageExampleEmbedding(
                embedding_id=embedding_id,
                example_id=example_id,
                usage_type=usage_type,
                vector=vector,
                metadata={
                    "language": language,
                    "code_length": len(code),
                    "line_count": len(code.split('\n')),
                    "complexity": code_features.get("complexity", "simple"),
                    "patterns_found": code_features.get("patterns", []),
                    "functions": code_features.get("functions", []),
                    "classes": code_features.get("classes", []),
                    "imports": code_features.get("imports", [])
                },
                code=code,
                description=description,
                context=context or "",
                tags=tags or [],
                language=language,
                created_at="2024-01-01T00:00:00Z"
            )
            
        except Exception as e:
            logger.error(f"Error generating usage embedding: {e}")
            raise
    
    async def search_usage_examples(self,
                                  query: str,
                                  usage_embeddings: List[UsageExampleEmbedding],
                                  usage_type: Optional[UsageType] = None,
                                  language: Optional[str] = None,
                                  limit: int = 10) -> List[Tuple[UsageExampleEmbedding, float]]:
        """Search usage examples by semantic similarity."""
        # Filter embeddings
        filtered_embeddings = usage_embeddings
        
        if usage_type:
            filtered_embeddings = [emb for emb in filtered_embeddings if emb.usage_type == usage_type]
        
        if language:
            filtered_embeddings = [emb for emb in filtered_embeddings if emb.language == language]
        
        # Generate embedding for query
        query_vector = await self.embedding_provider.embed_text(query)
        
        # Calculate similarities
        similarities = []
        for usage_emb in filtered_embeddings:
            similarity = self._calculate_similarity(query_vector, usage_emb.vector)
            similarities.append((usage_emb, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:limit]
    
    async def find_similar_examples(self,
                                  target_code: str,
                                  usage_embeddings: List[UsageExampleEmbedding],
                                  language: Optional[str] = None,
                                  limit: int = 5) -> List[Tuple[UsageExampleEmbedding, float]]:
        """Find usage examples similar to target code."""
        # Filter by language if specified
        if language:
            filtered_embeddings = [emb for emb in usage_embeddings if emb.language == language]
        else:
            filtered_embeddings = usage_embeddings
        
        # Generate embedding for target code
        target_vector = await self.embedding_provider.embed_text(target_code)
        
        # Calculate similarities
        similarities = []
        for usage_emb in filtered_embeddings:
            similarity = self._calculate_similarity(target_vector, usage_emb.vector)
            similarities.append((usage_emb, similarity))
        
        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:limit]
    
    async def get_examples_by_pattern(self,
                                    pattern_name: str,
                                    usage_embeddings: List[UsageExampleEmbedding]) -> List[UsageExampleEmbedding]:
        """Get usage examples that demonstrate a specific pattern."""
        matching_examples = []
        
        for usage_emb in usage_embeddings:
            # Check if pattern is in metadata or tags
            patterns = usage_emb.metadata.get("patterns_found", [])
            if pattern_name in patterns or pattern_name in usage_emb.tags:
                matching_examples.append(usage_emb)
        
        return matching_examples
    
    def _extract_code_features(self, code: str, language: str) -> Dict[str, Any]:
        """Extract features from code for embedding enhancement."""
        features = {
            "complexity": "simple",
            "patterns": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "keywords": []
        }
        
        lines = code.split('\n')
        line_count = len(lines)
        
        # Calculate complexity
        if line_count > 50:
            features["complexity"] = "complex"
        elif line_count > 20:
            features["complexity"] = "moderate"
        
        # Language-specific feature extraction
        if language == "python":
            features.update(self._extract_python_features(code))
        elif language in ["javascript", "typescript"]:
            features.update(self._extract_js_features(code))
        elif language == "java":
            features.update(self._extract_java_features(code))
        else:
            features.update(self._extract_generic_features(code))
        
        return features
    
    def _extract_python_features(self, code: str) -> Dict[str, Any]:
        """Extract features from Python code."""
        features = {
            "patterns": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "keywords": []
        }
        
        # Extract functions
        func_matches = re.findall(r'def\s+(\w+)\s*\(', code)
        features["functions"] = func_matches
        
        # Extract classes
        class_matches = re.findall(r'class\s+(\w+)', code)
        features["classes"] = class_matches
        
        # Extract imports
        import_matches = re.findall(r'import\s+(\w+)', code)
        from_matches = re.findall(r'from\s+(\w+)', code)
        features["imports"] = list(set(import_matches + from_matches))
        
        # Detect patterns
        if "class " in code and "__init__" in code:
            features["patterns"].append("class")
        if "def " in code and "self" in code:
            features["patterns"].append("method")
        if "import " in code and "from " in code:
            features["patterns"].append("import")
        if "try:" in code and "except" in code:
            features["patterns"].append("exception_handling")
        if "with " in code:
            features["patterns"].append("context_manager")
        if "def " in code and "yield" in code:
            features["patterns"].append("generator")
        if "@" in code and "def " in code:
            features["patterns"].append("decorator")
        
        # Extract keywords
        python_keywords = ["def", "class", "import", "from", "try", "except", "with", "if", "else", "for", "while"]
        for keyword in python_keywords:
            if keyword in code:
                features["keywords"].append(keyword)
        
        return features
    
    def _extract_js_features(self, code: str) -> Dict[str, Any]:
        """Extract features from JavaScript/TypeScript code."""
        features = {
            "patterns": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "keywords": []
        }
        
        # Extract functions
        func_matches = re.findall(r'function\s+(\w+)', code)
        arrow_matches = re.findall(r'const\s+(\w+)\s*=\s*\(', code)
        features["functions"] = list(set(func_matches + arrow_matches))
        
        # Extract classes
        class_matches = re.findall(r'class\s+(\w+)', code)
        features["classes"] = class_matches
        
        # Extract imports
        import_matches = re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', code)
        require_matches = re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', code)
        features["imports"] = list(set(import_matches + require_matches))
        
        # Detect patterns
        if "class " in code and "constructor" in code:
            features["patterns"].append("class")
        if "function " in code or "=> " in code:
            features["patterns"].append("function")
        if "async " in code and "await " in code:
            features["patterns"].append("async")
        if "try {" in code and "catch" in code:
            features["patterns"].append("exception_handling")
        if "Promise" in code:
            features["patterns"].append("promise")
        if "fetch(" in code:
            features["patterns"].append("api_call")
        
        # Extract keywords
        js_keywords = ["function", "class", "const", "let", "var", "if", "else", "for", "while", "try", "catch"]
        for keyword in js_keywords:
            if keyword in code:
                features["keywords"].append(keyword)
        
        return features
    
    def _extract_java_features(self, code: str) -> Dict[str, Any]:
        """Extract features from Java code."""
        features = {
            "patterns": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "keywords": []
        }
        
        # Extract classes
        class_matches = re.findall(r'public\s+class\s+(\w+)', code)
        features["classes"] = class_matches
        
        # Extract methods
        method_matches = re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', code)
        features["functions"] = method_matches
        
        # Extract imports
        import_matches = re.findall(r'import\s+([^;]+);', code)
        features["imports"] = import_matches
        
        # Detect patterns
        if "public class " in code:
            features["patterns"].append("class")
        if "interface " in code:
            features["patterns"].append("interface")
        if "extends " in code:
            features["patterns"].append("inheritance")
        if "implements " in code:
            features["patterns"].append("implementation")
        
        return features
    
    def _extract_generic_features(self, code: str) -> Dict[str, Any]:
        """Extract generic features for unknown languages."""
        features = {
            "patterns": [],
            "functions": [],
            "classes": [],
            "imports": [],
            "keywords": []
        }
        
        # Generic pattern detection
        if "function" in code or "def" in code or "func" in code:
            features["patterns"].append("function")
        if "class" in code:
            features["patterns"].append("class")
        if "import" in code or "include" in code:
            features["patterns"].append("import")
        if "try" in code and "catch" in code:
            features["patterns"].append("exception_handling")
        
        return features
    
    def _detect_language(self, code: str) -> str:
        """Detect programming language from code."""
        language_patterns = {
            'python': [r'def\s+\w+\s*\(', r'import\s+\w+', r'from\s+\w+\s+import', r'print\s*\('],
            'javascript': [r'function\s+\w+', r'const\s+\w+\s*=', r'let\s+\w+\s*=', r'console\.log'],
            'typescript': [r'interface\s+\w+', r'type\s+\w+', r':\s*\w+', r'as\s+\w+'],
            'java': [r'public\s+class\s+\w+', r'public\s+static\s+void\s+main', r'import\s+[^;]+;'],
            'go': [r'func\s+\w+', r'package\s+\w+', r'import\s+\(', r'go\s+\w+'],
            'rust': [r'fn\s+\w+', r'use\s+\w+', r'let\s+mut', r'impl\s+\w+'],
            'csharp': [r'public\s+class\s+\w+', r'using\s+[^;]+;', r'namespace\s+\w+'],
            'cpp': [r'#include\s+<[^>]+>', r'std::', r'cout\s*<<', r'int\s+main'],
            'php': [r'\$\w+', r'function\s+\w+', r'<?php', r'echo\s+'],
            'ruby': [r'def\s+\w+', r'class\s+\w+', r'require\s+', r'puts\s+'],
        }
        
        code_lower = code.lower()
        scores = {}
        
        for lang, patterns in language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code_lower))
                score += matches
            scores[lang] = score
        
        if scores:
            best_lang = max(scores, key=scores.get)
            if scores[best_lang] > 0:
                return best_lang
        
        return 'unknown'
    
    def _create_enhanced_text(self,
                           code: str,
                           description: str,
                           context: str,
                           tags: List[str],
                           features: Dict[str, Any],
                           usage_type: UsageType) -> str:
        """Create enhanced text representation for embedding."""
        text_parts = []
        
        # Add description
        if description:
            text_parts.append(f"Description: {description}")
        
        # Add usage type
        text_parts.append(f"Type: {usage_type.value}")
        
        # Add context
        if context:
            text_parts.append(f"Context: {context}")
        
        # Add tags
        if tags:
            tags_text = " | ".join(tags)
            text_parts.append(f"Tags: {tags_text}")
        
        # Add features
        if features.get("patterns"):
            patterns_text = " | ".join(features["patterns"])
            text_parts.append(f"Patterns: {patterns_text}")
        
        if features.get("functions"):
            functions_text = " | ".join(features["functions"][:5])  # Limit to first 5
            text_parts.append(f"Functions: {functions_text}")
        
        if features.get("classes"):
            classes_text = " | ".join(features["classes"][:3])  # Limit to first 3
            text_parts.append(f"Classes: {classes_text}")
        
        if features.get("imports"):
            imports_text = " | ".join(features["imports"][:3])  # Limit to first 3
            text_parts.append(f"Imports: {imports_text}")
        
        # Add code sample (truncated)
        code_sample = code[:300]
        text_parts.append(f"Code: {code_sample}")
        
        return " | ".join(text_parts)
    
    def _initialize_code_patterns(self) -> Dict[str, List[str]]:
        """Initialize common code patterns."""
        return {
            'creational': ['singleton', 'factory', 'builder', 'prototype'],
            'structural': ['adapter', 'decorator', 'proxy', 'composite'],
            'behavioral': ['observer', 'strategy', 'command', 'iterator'],
            'architectural': ['mvc', 'repository', 'service', 'controller'],
            'concurrency': ['thread', 'async', 'await', 'lock', 'mutex'],
            'error_handling': ['try', 'catch', 'except', 'finally', 'throw'],
            'data_structures': ['list', 'dict', 'map', 'array', 'set'],
            'algorithms': ['sort', 'search', 'filter', 'map', 'reduce']
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
    
    def _generate_embedding_id(self, example_id: str, usage_type: UsageType, code: str) -> str:
        """Generate unique embedding ID."""
        code_hash = hashlib.md5(code.encode()).hexdigest()
        return hashlib.sha256(f"{example_id}:{usage_type.value}:{code_hash}".encode()).hexdigest()[:32]
