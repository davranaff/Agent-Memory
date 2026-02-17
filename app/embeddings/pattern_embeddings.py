"""Pattern Embeddings for design patterns and architectural patterns."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib

from app.memory.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of design patterns."""
    CREATIONAL = "creational"
    STRUCTURAL = "structural"
    BEHAVIORAL = "behavioral"
    ARCHITECTURAL = "architectural"
    CONCURRENCY = "concurrency"
    DATA = "data"


@dataclass
class PatternEmbedding:
    """Embedding for a design pattern."""
    embedding_id: str
    pattern_name: str
    pattern_type: PatternType
    vector: List[float]
    metadata: Dict[str, Any]
    description: str
    examples: List[str]
    implementations: List[str]
    created_at: str


class PatternEmbeddingGenerator:
    """Generate embeddings for design patterns."""
    
    def __init__(self, embedding_provider: EmbeddingProvider) -> None:
        self.embedding_provider = embedding_provider
        self._pattern_library = self._initialize_pattern_library()
    
    async def generate_pattern_embedding(self, pattern_name: str) -> PatternEmbedding:
        """Generate embedding for a specific pattern."""
        if pattern_name not in self._pattern_library:
            raise ValueError(f"Pattern '{pattern_name}' not found in library")
        
        pattern_info = self._pattern_library[pattern_name]
        
        # Create pattern text for embedding
        pattern_text = self._create_pattern_text(pattern_info)
        
        # Generate embedding
        vector = await self.embedding_provider.embed_text(pattern_text)
        
        # Create embedding object
        embedding_id = self._generate_embedding_id(pattern_name)
        
        return PatternEmbedding(
            embedding_id=embedding_id,
            pattern_name=pattern_name,
            pattern_type=pattern_info["type"],
            vector=vector,
            metadata={
                "category": pattern_info["category"],
                "intent": pattern_info["intent"],
                "motivation": pattern_info["motivation"],
                "applicability": pattern_info["applicability"],
                "consequences": pattern_info["consequences"],
                "related_patterns": pattern_info["related_patterns"]
            },
            description=pattern_info["description"],
            examples=pattern_info["examples"],
            implementations=pattern_info["implementations"],
            created_at="2024-01-01T00:00:00Z"
        )
    
    async def generate_all_pattern_embeddings(self) -> List[PatternEmbedding]:
        """Generate embeddings for all patterns in the library."""
        embeddings = []
        
        for pattern_name in self._pattern_library:
            try:
                embedding = await self.generate_pattern_embedding(pattern_name)
                embeddings.append(embedding)
            except Exception as e:
                logger.error(f"Failed to generate embedding for pattern {pattern_name}: {e}")
        
        return embeddings
    
    async def detect_patterns_in_code(self, 
                                    code: str, 
                                    language: str,
                                    similarity_threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Detect patterns in code using similarity matching."""
        detected_patterns = []
        
        # Generate embedding for the code
        code_vector = await self.embedding_provider.embed_text(code)
        
        # Compare with all pattern embeddings
        for pattern_name in self._pattern_library:
            pattern_info = self._pattern_library[pattern_name]
            pattern_text = self._create_pattern_text(pattern_info)
            pattern_vector = await self.embedding_provider.embed_text(pattern_text)
            
            # Calculate similarity
            similarity = self._calculate_similarity(code_vector, pattern_vector)
            
            if similarity >= similarity_threshold:
                detected_patterns.append((pattern_name, similarity))
        
        # Sort by similarity (descending)
        detected_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return detected_patterns
    
    def _initialize_pattern_library(self) -> Dict[str, Dict[str, Any]]:
        """Initialize the pattern library with common design patterns."""
        return {
            # Creational Patterns
            "Singleton": {
                "type": PatternType.CREATIONAL,
                "category": "Creational",
                "description": "Ensure a class has only one instance and provide global access to it.",
                "intent": "Control object creation and limit instances to one.",
                "motivation": "Some objects need exactly one instance (database connection, logging).",
                "applicability": "When exactly one instance of a class is needed globally.",
                "consequences": "Controlled access, reduced memory, global state.",
                "examples": [
                    "Database connection manager",
                    "Logger instance",
                    "Configuration manager",
                    "Cache manager"
                ],
                "implementations": [
                    "class Singleton:\n    _instance = None\n    def __new__(cls):\n        if cls._instance is None:\n            cls._instance = super().__new__(cls)\n        return cls._instance"
                ],
                "related_patterns": ["Abstract Factory", "Prototype"]
            },
            
            "Factory Method": {
                "type": PatternType.CREATIONAL,
                "category": "Creational",
                "description": "Define an interface for creating objects but let subclasses decide which class to instantiate.",
                "intent": "Let a class defer instantiation to subclasses.",
                "motivation": "Framework needs to instantiate classes but doesn't know which ones.",
                "applicability": "When a class cannot anticipate the class of objects it must create.",
                "consequences": "Flexible object creation, decoupled client code.",
                "examples": [
                    "Document creation in editors",
                    "UI component factories",
                    "Database connection factories",
                    "API client factories"
                ],
                "implementations": [
                    "class DocumentFactory:\n    def create_document(self, doc_type):\n        if doc_type == 'pdf':\n            return PDFDocument()\n        elif doc_type == 'word':\n            return WordDocument()"
                ],
                "related_patterns": ["Abstract Factory", "Prototype", "Template Method"]
            },
            
            "Abstract Factory": {
                "type": PatternType.CREATIONAL,
                "category": "Creational", 
                "description": "Provide an interface for creating families of related objects without specifying their concrete classes.",
                "intent": "Create families of related objects without specifying concrete classes.",
                "motivation": "Need to create objects that work together for different systems.",
                "applicability": "When system needs to be independent of how products are created.",
                "consequences": "Isolated concrete classes, easy product family switching.",
                "examples": [
                    "UI toolkit factories (Windows/Mac/Linux)",
                    "Database access layer factories",
                    "Theme factories (light/dark mode)",
                    "Protocol factories (HTTP/HTTPS/WebSocket)"
                ],
                "implementations": [
                    "class GUIFactory:\n    def create_button(self): pass\n    def create_window(self): pass\n\nclass WindowsFactory(GUIFactory):\n    def create_button(self): return WindowsButton()"
                ],
                "related_patterns": ["Factory Method", "Singleton", "Prototype"]
            },
            
            "Builder": {
                "type": PatternType.CREATIONAL,
                "category": "Creational",
                "description": "Separate the construction of a complex object from its representation.",
                "intent": "Construct complex objects step by step.",
                "motivation": "Complex objects need flexible construction processes.",
                "applicability": "When algorithm for creating complex object should be independent of parts.",
                "consequences": "Fine control over construction, different representations.",
                "examples": [
                    "SQL query builders",
                    "JSON/XML document builders",
                    "Configuration object builders",
                    "HTTP request builders"
                ],
                "implementations": [
                    "class SQLBuilder:\n    def select(self, columns): return self\n    def from_table(self, table): return self\n    def where(self, condition): return self\n    def build(self): return self.query"
                ],
                "related_patterns": ["Abstract Factory", "Composite", "Template Method"]
            },
            
            "Prototype": {
                "type": PatternType.CREATIONAL,
                "category": "Creational",
                "description": "Create new objects by copying an existing object.",
                "intent": "Create objects by cloning existing ones.",
                "motivation": "Creating objects is expensive or complex.",
                "applicability": "When classes are instantiated at runtime or have many configurations.",
                "consequences": "Hidden creation complexities, dynamic object addition.",
                "examples": [
                    "Game object cloning",
                    "Document template copying",
                    "Configuration profile duplication",
                    "Graph node copying"
                ],
                "implementations": [
                    "class Prototype:\n    def clone(self): return copy.deepcopy(self)"
                ],
                "related_patterns": ["Abstract Factory", "Composite", "Decorator"]
            },
            
            # Structural Patterns
            "Adapter": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Convert the interface of a class into another interface clients expect.",
                "intent": "Make incompatible interfaces work together.",
                "motivation": "Need to use existing class with incompatible interface.",
                "applicability": "When you want to use existing class but interface doesn't match.",
                "consequences": "Allows incompatible classes to work together.",
                "examples": [
                    "Legacy system adapters",
                    "Third-party library adapters",
                    "Database driver adapters",
                    "API version adapters"
                ],
                "implementations": [
                    "class Adapter:\n    def __init__(self, adaptee):\n        self.adaptee = adaptee\n    def request(self): return self.adaptee.specific_request()"
                ],
                "related_patterns": ["Bridge", "Decorator", "Proxy"]
            },
            
            "Bridge": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Decouple an abstraction from its implementation so that the two can vary independently.",
                "intent": "Separate abstraction from implementation.",
                "motivation": "Abstraction and implementation should vary independently.",
                "applicability": "When you want to avoid permanent binding between abstraction and implementation.",
                "consequences": "Independent extensibility, hidden implementation details.",
                "examples": [
                    "Platform-specific UI implementations",
                    "Database driver abstractions",
                    "Communication protocol implementations",
                    "Rendering engine abstractions"
                ],
                "implementations": [
                    "class Abstraction:\n    def __init__(self, implementation):\n        self.implementation = implementation\n    def operation(self): return self.implementation.operation_impl()"
                ],
                "related_patterns": ["Adapter", "Abstract Factory", "Template Method"]
            },
            
            "Composite": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Compose objects into tree structures to represent part-whole hierarchies.",
                "intent": "Compose objects into tree structures.",
                "motivation": "Need to treat individual objects and compositions uniformly.",
                "applicability": "When you want to represent part-whole hierarchies of objects.",
                "consequences": "Defines class hierarchies, simplifies client code.",
                "examples": [
                    "File system structures",
                    "GUI component hierarchies",
                    "Organization structures",
                    "Mathematical expressions"
                ],
                "implementations": [
                    "class Component:\n    def add(self, component): pass\n    def remove(self, component): pass\n\nclass Composite(Component):\n    def __init__(self): self.children = []"
                ],
                "related_patterns": ["Iterator", "Visitor", "Chain of Responsibility"]
            },
            
            "Decorator": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Attach additional responsibilities to an object dynamically.",
                "intent": "Add responsibilities to objects dynamically.",
                "motivation": "Need to add functionality to objects without subclassing.",
                "applicability": "When you want to add responsibilities to individual objects dynamically.",
                "consequences": "Flexible object extension, more functionality than inheritance.",
                "examples": [
                    "UI component decorators",
                    "Stream decorators (compression/encryption)",
                    "HTTP middleware decorators",
                    "Logging decorators"
                ],
                "implementations": [
                    "class Decorator:\n    def __init__(self, component):\n        self.component = component\n    def operation(self): return self.component.operation()"
                ],
                "related_patterns": ["Adapter", "Composite", "Strategy"]
            },
            
            "Facade": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Provide a unified interface to a set of interfaces in a subsystem.",
                "intent": "Provide simplified interface to complex subsystem.",
                "motivation": "Complex subsystem needs simplified interface.",
                "applicability": "When you want to provide simple interface to complex system.",
                "consequences": "Shields clients from subsystem complexity, loose coupling.",
                "examples": [
                    "Database connection facades",
                    "API client facades",
                    "Configuration system facades",
                    "Payment processing facades"
                ],
                "implementations": [
                    "class Facade:\n    def __init__(self):\n        self.subsystem1 = Subsystem1()\n        self.subsystem2 = Subsystem2()\n    def operation(self): return self.subsystem1.op1() + self.subsystem2.op2()"
                ],
                "related_patterns": ["Abstract Factory", "Mediator", "Singleton"]
            },
            
            "Flyweight": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Use sharing to support large numbers of fine-grained objects efficiently.",
                "intent": "Use sharing to support large numbers of objects efficiently.",
                "motivation": "Too many objects cause memory problems.",
                "applicability": "When application uses many similar objects.",
                "consequences": "Reduces memory usage, shared intrinsic state.",
                "examples": [
                    "Text character objects in editors",
                    "Game object instances",
                    "Icon/image caching",
                    "String interning"
                ],
                "implementations": [
                    "class FlyweightFactory:\n    def __init__(self): self.flyweights = {}\n    def get_flyweight(self, key):\n        if key not in self.flyweights:\n            self.flyweights[key] = Flyweight(key)\n        return self.flyweights[key]"
                ],
                "related_patterns": ["Composite", "Strategy", "State"]
            },
            
            "Proxy": {
                "type": PatternType.STRUCTURAL,
                "category": "Structural",
                "description": "Provide a surrogate or placeholder for another object to control access to it.",
                "intent": "Control access to another object.",
                "motivation": "Need controlled access to object.",
                "applicability": "When you need controlled access, lazy initialization, or access protection.",
                "consequences": "Transparent object access, additional level of indirection.",
                "examples": [
                    "Database connection proxies",
                    "Remote service proxies",
                    "Caching proxies",
                    "Security proxies"
                ],
                "implementations": [
                    "class Proxy:\n    def __init__(self, real_subject):\n        self.real_subject = real_subject\n    def request(self): return self.real_subject.request()"
                ],
                "related_patterns": ["Adapter", "Decorator", "Facade"]
            },
            
            # Behavioral Patterns
            "Chain of Responsibility": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Avoid coupling the sender of a request to its receiver by giving multiple objects a chance to handle the request.",
                "intent": "Chain receiving objects until one handles request.",
                "motivation": "Multiple objects can handle request without specifying handler explicitly.",
                "applicability": "When more than one object may handle request.",
                "consequences": "Reduced coupling, added flexibility in assigning responsibilities.",
                "examples": [
                    "HTTP middleware chains",
                    "Event handling systems",
                    "Validation chains",
                    "Logging systems"
                ],
                "implementations": [
                    "class Handler:\n    def __init__(self): self.next_handler = None\n    def set_next(self, handler): self.next_handler = handler\n    def handle(self, request):\n        if self.can_handle(request): return self.handle_request(request)\n        elif self.next_handler: return self.next_handler.handle(request)"
                ],
                "related_patterns": ["Composite", "Decorator", "Mediator"]
            },
            
            "Command": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Encapsulate a request as an object.",
                "intent": "Encapsulate request as object.",
                "motivation": "Need to parameterize objects with actions.",
                "applicability": "When you want to parameterize objects with actions.",
                "consequences": "Decouples invoker from receiver, supports undo/redo.",
                "examples": [
                    "GUI menu commands",
                    "Database transactions",
                    "Macro recording",
                    "Remote procedure calls"
                ],
                "implementations": [
                    "class Command:\n    def __init__(self, receiver):\n        self.receiver = receiver\n    def execute(self): self.receiver.action()"
                ],
                "related_patterns": ["Memento", "Composite", "Prototype"]
            },
            
            "Iterator": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Provide a way to access the elements of an aggregate object sequentially without exposing its underlying representation.",
                "intent": "Access elements sequentially without exposing representation.",
                "motivation": "Need to traverse aggregate objects in different ways.",
                "applicability": "When you want to access aggregate object contents without exposing representation.",
                "consequences": "Supports variations in traversal, simplified aggregate interface.",
                "examples": [
                    "Collection iterators",
                    "Tree traversals",
                    "Database result iterators",
                    "File system iterators"
                ],
                "implementations": [
                    "class Iterator:\n    def __init__(self, collection): self.collection = collection\n    def has_next(self): return self.index < len(self.collection)\n    def next(self): item = self.collection[self.index]; self.index += 1; return item"
                ],
                "related_patterns": ["Composite", "Memento", "Factory Method"]
            },
            
            "Mediator": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Define an object that encapsulates how a set of objects interact.",
                "intent": "Centralize complex communications and control.",
                "motivation": "Objects communicate in complex ways.",
                "applicability": "When set of objects communicate in well-defined but complex ways.",
                "consequences": "Centralized control, reduced subclassing, improved maintainability.",
                "examples": [
                    "Chat room systems",
                    "GUI component coordination",
                    "Air traffic control",
                    "Database transaction coordination"
                ],
                "implementations": [
                    "class Mediator:\n    def __init__(self): self.colleagues = []\n    def send(self, message, colleague): \n        for c in self.colleagues:\n            if c != colleague: c.receive(message)"
                ],
                "related_patterns": ["Observer", "Facade", "Singleton"]
            },
            
            "Memento": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Capture and restore an object's internal state.",
                "intent": "Capture and restore object state without violating encapsulation.",
                "motivation": "Need to checkpoint objects and restore to previous state.",
                "applicability": "When you need to save and restore state.",
                "consequences": "Preserves encapsulation boundaries, simplifies originator.",
                "examples": [
                    "Undo/redo systems",
                    "Game save states",
                    "Database transactions",
                    "Text editor history"
                ],
                "implementations": [
                    "class Memento:\n    def __init__(self, state): self.state = state\n\nclass Originator:\n    def create_memento(self): return Memento(self.state)\n    def restore(self, memento): self.state = memento.state"
                ],
                "related_patterns": ["Command", "Iterator", "Prototype"]
            },
            
            "Observer": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Define a one-to-many dependency between objects so that when one object changes state, all dependents are notified automatically.",
                "intent": "Define one-to-many dependency between objects.",
                "motivation": "When one object changes state, others need to be updated.",
                "applicability": "When change in one object requires change in others.",
                "consequences": "Abstract coupling between subject and observer, broadcast communication.",
                "examples": [
                    "Event systems",
                    "Model-View-Controller",
                    "Stock price monitoring",
                    "Social media notifications"
                ],
                "implementations": [
                    "class Subject:\n    def __init__(self): self.observers = []\n    def attach(self, observer): self.observers.append(observer)\n    def notify(self): for o in self.observers: o.update()"
                ],
                "related_patterns": ["Mediator", "Singleton", "State"]
            },
            
            "State": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Allow an object to alter its behavior when its internal state changes.",
                "intent": "Allow object to change behavior when state changes.",
                "motivation": "Object behavior depends on state and must change at runtime.",
                "applicability": "When object behavior depends on its state.",
                "consequences": "State-specific behavior, clean state transitions.",
                "examples": [
                    "Game character states",
                    "Connection states",
                    "Audio player states",
                    "Order processing states"
                ],
                "implementations": [
                    "class State:\n    def handle(self, context): pass\n\nclass Context:\n    def __init__(self): self.state = None\n    def set_state(self, state): self.state = state\n    def request(self): self.state.handle(self)"
                ],
                "related_patterns": ["Flyweight", "Singleton", "Strategy"]
            },
            
            "Strategy": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Define a family of algorithms, encapsulate each one, and make them interchangeable.",
                "intent": "Define family of algorithms and make them interchangeable.",
                "motivation": "Need to use different algorithms interchangeably.",
                "applicability": "When you have multiple algorithms for a task.",
                "consequences": "Alternative algorithms, eliminates conditional statements.",
                "examples": [
                    "Sorting algorithms",
                    "Payment methods",
                    "Compression algorithms",
                    "Routing strategies"
                ],
                "implementations": [
                    "class Strategy:\n    def algorithm(self): pass\n\nclass Context:\n    def __init__(self, strategy): self.strategy = strategy\n    def execute(self): return self.strategy.algorithm()"
                ],
                "related_patterns": ["State", "Template Method", "Flyweight"]
            },
            
            "Template Method": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Define the skeleton of an algorithm in an operation, deferring some steps to subclasses.",
                "intent": "Define algorithm skeleton, defer steps to subclasses.",
                "motivation": "Algorithm structure is fixed but some steps vary.",
                "applicability": "When you have fixed algorithm structure with variable steps.",
                "consequences": "Code reuse, inverted control structure.",
                "examples": [
                    "Data processing pipelines",
                    "Report generation",
                    "Game frameworks",
                    "Web request handling"
                ],
                "implementations": [
                    "class AbstractClass:\n    def template_method(self):\n        self.step1()\n        self.step2()\n        self.step3()\n    def step1(self): pass\n    def step2(self): pass\n    def step3(self): pass"
                ],
                "related_patterns": ["Strategy", "Factory Method", "Builder"]
            },
            
            "Visitor": {
                "type": PatternType.BEHAVIORAL,
                "category": "Behavioral",
                "description": "Represent an operation to be performed on elements of an object structure.",
                "intent": "Represent operation on elements of object structure.",
                "motivation": "Need to perform operations on object structure without changing classes.",
                "applicability": "When structure has many unrelated operations.",
                "consequences": "Related behavior grouped, easy to add new operations.",
                "examples": [
                    "Compiler operations",
                    "Document processing",
                    "Code analysis tools",
                    "UI component operations"
                ],
                "implementations": [
                    "class Visitor:\n    def visit_element_a(self, element): pass\n    def visit_element_b(self, element): pass\n\nclass Element:\n    def accept(self, visitor): visitor.visit_element(self)"
                ],
                "related_patterns": ["Composite", "Iterator", "Interpreter"]
            },
            
            # Architectural Patterns
            "Microservices": {
                "type": PatternType.ARCHITECTURAL,
                "category": "Architectural",
                "description": "Decompose application into small, independent services.",
                "intent": "Build application as collection of loosely coupled services.",
                "motivation": "Monolithic applications are hard to scale and maintain.",
                "applicability": "Large applications requiring independent scaling and deployment.",
                "consequences": "Independent deployment, technology diversity, operational complexity.",
                "examples": [
                    "E-commerce platforms",
                    "Streaming services",
                    "Financial systems",
                    "Social media platforms"
                ],
                "implementations": [
                    "# Service decomposition by business capability\n# Each service owns its data\n# Services communicate via APIs/events\n# Independent deployment and scaling"
                ],
                "related_patterns": ["API Gateway", "Event-Driven", "Database per Service"]
            },
            
            "Repository": {
                "type": PatternType.ARCHITECTURAL,
                "category": "Architectural",
                "description": "Mediate between domain and data mapping layers using collection-like interface.",
                "intent": "Encapsulate data access logic.",
                "motivation": "Need clean separation between business logic and data access.",
                "applicability": "When you need to isolate data access from business logic.",
                "consequences": "Testable business logic, centralized data access, reduced duplication.",
                "examples": [
                    "User repositories",
                    "Product repositories",
                    "Order repositories",
                    "Document repositories"
                ],
                "implementations": [
                    "class Repository:\n    def find_by_id(self, id): pass\n    def find_all(self): pass\n    def save(self, entity): pass\n    def delete(self, entity): pass"
                ],
                "related_patterns": ["Unit of Work", "Data Mapper", "Specification"]
            },
            
            "CQRS": {
                "type": PatternType.ARCHITECTURAL,
                "category": "Architectural",
                "description": "Separate read and write operations for data stores.",
                "intent": "Separate command and query responsibilities.",
                "motivation": "Different models for read and write operations optimize performance.",
                "applicability": "When read and write operations have different requirements.",
                "consequences": "Optimized read/write models, increased complexity, eventual consistency.",
                "examples": [
                    "High-traffic web applications",
                    "Real-time dashboards",
                    "E-commerce systems",
                    "IoT data processing"
                ],
                "implementations": [
                    "# Separate models for commands and queries\n# Command side handles writes\n# Query side handles reads\n# Synchronization between sides"
                ],
                "related_patterns": ["Event Sourcing", "Repository", "API Gateway"]
            }
        }
    
    def _create_pattern_text(self, pattern_info: Dict[str, Any]) -> str:
        """Create text representation of pattern for embedding."""
        text_parts = []
        
        text_parts.append(f"Pattern: {pattern_info['description']}")
        text_parts.append(f"Intent: {pattern_info['intent']}")
        text_parts.append(f"Motivation: {pattern_info['motivation']}")
        text_parts.append(f"Applicability: {pattern_info['applicability']}")
        
        # Add examples
        if pattern_info.get("examples"):
            examples = " | ".join(pattern_info["examples"])
            text_parts.append(f"Examples: {examples}")
        
        # Add implementation hints
        if pattern_info.get("implementations"):
            impl = pattern_info["implementations"][0][:200]  # First 200 chars
            text_parts.append(f"Implementation: {impl}")
        
        return " | ".join(text_parts)
    
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
    
    def _generate_embedding_id(self, pattern_name: str) -> str:
        """Generate unique embedding ID for pattern."""
        return hashlib.sha256(f"pattern:{pattern_name}".encode()).hexdigest()[:32]
