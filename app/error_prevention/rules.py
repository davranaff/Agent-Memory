"""Error prevention rules."""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Any

from .models import PreventionRule, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)


class RuleEngine:
    """Manages and executes error prevention rules."""
    
    def __init__(self) -> None:
        self.rules = self._load_default_rules()
        self.custom_rules = []
    
    def get_rules_for_language(self, language: str, categories: Optional[List[ErrorCategory]] = None) -> List[PreventionRule]:
        """Get rules for a specific language and categories."""
        rules = [rule for rule in self.rules if rule.language == language or rule.language == 'all']
        
        if categories:
            rules = [rule for rule in rules if rule.category in categories]
        
        return [rule for rule in rules if rule.enabled]
    
    def add_custom_rule(self, rule: PreventionRule) -> None:
        """Add a custom rule."""
        self.custom_rules.append(rule)
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a rule by name."""
        for rule in self.rules + self.custom_rules:
            if rule.name == rule_name:
                rule.enabled = True
                return True
        return False
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a rule by name."""
        for rule in self.rules + self.custom_rules:
            if rule.name == rule_name:
                rule.enabled = False
                return True
        return False
    
    def _load_default_rules(self) -> List[PreventionRule]:
        """Load default error prevention rules."""
        rules = []
        
        # Python rules
        python_rules = [
            PreventionRule(
                name="python_unreachable_code",
                description="Detect unreachable code after return statements",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"return\s+.*\n\s+.*",
                suggestion="Remove unreachable code after return statement",
                auto_fix=False,
                language="python"
            ),
            PreventionRule(
                name="python_unused_import",
                description="Detect unused import statements",
                category=ErrorCategory.MAINTAINABILITY,
                severity=ErrorSeverity.LOW,
                pattern=r"^import\s+\w+",
                suggestion="Remove unused import statement",
                auto_fix=True,
                language="python"
            ),
            PreventionRule(
                name="python_bare_except",
                description="Detect bare except clauses",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.HIGH,
                pattern=r"except\s*:",
                suggestion="Specify exception type in except clause",
                auto_fix=False,
                language="python"
            ),
            PreventionRule(
                name="python_eval_usage",
                description="Detect usage of eval() function",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"eval\s*\(",
                suggestion="Avoid using eval() - use safer alternatives",
                auto_fix=False,
                language="python"
            ),
            PreventionRule(
                name="python_hardcoded_password",
                description="Detect hardcoded passwords",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"password\s*=\s*[\"'][^\"']+[\"']",
                suggestion="Use environment variables or configuration files for passwords",
                auto_fix=False,
                language="python"
            ),
            PreventionRule(
                name="python_none_comparison",
                description="Detect comparison with None using == or !=",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"(==|!=)\s*None",
                suggestion="Use 'is' and 'is not' for None comparisons",
                auto_fix=True,
                language="python"
            ),
            PreventionRule(
                name="python_mutable_default",
                description="Detect mutable default arguments",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.HIGH,
                pattern=r"def\s+\w+\([^)]*=\s*\[",
                suggestion="Use None as default and initialize mutable objects inside function",
                auto_fix=False,
                language="python"
            )
        ]
        
        # JavaScript rules
        javascript_rules = [
            PreventionRule(
                name="js_eval_usage",
                description="Detect usage of eval() function",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"eval\s*\(",
                suggestion="Avoid using eval() - use safer alternatives",
                auto_fix=False,
                language="javascript"
            ),
            PreventionRule(
                name="js_equality_operator",
                description="Detect use of == instead of ===",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"==\s*(?!true|false|null)",
                suggestion="Use === for strict equality comparison",
                auto_fix=True,
                language="javascript"
            ),
            PreventionRule(
                name="js_var_declaration",
                description="Detect usage of var instead of let/const",
                category=ErrorCategory.MAINTAINABILITY,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"\bvar\s+",
                suggestion="Use let or const instead of var",
                auto_fix=True,
                language="javascript"
            ),
            PreventionRule(
                name="js_missing_semicolon",
                description="Detect missing semicolons",
                category=ErrorCategory.SYNTAX,
                severity=ErrorSeverity.LOW,
                pattern=r"[^;]\s*\n",
                suggestion="Add semicolon at end of statement",
                auto_fix=True,
                language="javascript"
            )
        ]
        
        # Java rules
        java_rules = [
            PreventionRule(
                name="java_empty_catch",
                description="Detect empty catch blocks",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"catch\s*\([^)]+\)\s*\{\s*\}",
                suggestion="Add proper exception handling in catch block",
                auto_fix=False,
                language="java"
            ),
            PreventionRule(
                name="java_magic_number",
                description="Detect magic numbers",
                category=ErrorCategory.MAINTAINABILITY,
                severity=ErrorSeverity.LOW,
                pattern=r"\b\d{2,}\b",
                suggestion="Replace magic numbers with named constants",
                auto_fix=False,
                language="java"
            ),
            PreventionRule(
                name="java_string_equality",
                description="Detect string comparison using ==",
                category=ErrorCategory.LOGIC,
                severity=ErrorSeverity.HIGH,
                pattern=r"==\s*\"[^\"]*\"",
                suggestion="Use .equals() for string comparison",
                auto_fix=True,
                language="java"
            )
        ]
        
        # Security rules (language-agnostic)
        security_rules = [
            PreventionRule(
                name="hardcoded_secret",
                description="Detect hardcoded secrets",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(password|secret|token|key)\s*=\s*[\"'][^\"']+[\"']",
                suggestion="Use environment variables or secure storage for secrets",
                auto_fix=False,
                language="all"
            ),
            PreventionRule(
                name="sql_injection",
                description="Detect potential SQL injection",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                pattern=r"(execute|query)\s*\(\s*['\"].*\+\s*",
                suggestion="Use parameterized queries to prevent SQL injection",
                auto_fix=False,
                language="all"
            ),
            PreventionRule(
                name="path_traversal",
                description="Detect potential path traversal",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.HIGH,
                pattern=r"\.\./",
                suggestion="Validate and sanitize file paths",
                auto_fix=False,
                language="all"
            )
        ]
        
        # Performance rules
        performance_rules = [
            PreventionRule(
                name="nested_loops",
                description="Detect deeply nested loops",
                category=ErrorCategory.PERFORMANCE,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"for.*\n\s*for.*\n\s*for",
                suggestion="Consider optimizing nested loops or using better algorithms",
                auto_fix=False,
                language="all"
            ),
            PreventionRule(
                name="large_string_concatenation",
                description="Detect inefficient string concatenation in loops",
                category=ErrorCategory.PERFORMANCE,
                severity=ErrorSeverity.MEDIUM,
                pattern=r"for.*\n.*\+\s*=",
                suggestion="Use StringBuilder or similar for efficient string concatenation",
                auto_fix=False,
                language="all"
            )
        ]
        
        # Memory rules
        memory_rules = [
            PreventionRule(
                name="memory_leak_pattern",
                description="Detect potential memory leak patterns",
                category=ErrorCategory.MEMORY,
                severity=ErrorSeverity.HIGH,
                pattern=r"new\s+\w+\[.*\]",
                suggestion="Ensure proper memory management and deallocation",
                auto_fix=False,
                language="all"
            )
        ]
        
        rules.extend(python_rules)
        rules.extend(javascript_rules)
        rules.extend(java_rules)
        rules.extend(security_rules)
        rules.extend(performance_rules)
        rules.extend(memory_rules)
        
        return rules
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded rules."""
        all_rules = self.rules + self.custom_rules
        
        stats = {
            "total_rules": len(all_rules),
            "enabled_rules": len([r for r in all_rules if r.enabled]),
            "custom_rules": len(self.custom_rules),
            "by_language": {},
            "by_category": {},
            "by_severity": {}
        }
        
        for rule in all_rules:
            # Language statistics
            lang = rule.language
            stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
            
            # Category statistics
            cat = rule.category.value
            stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1
            
            # Severity statistics
            sev = rule.severity.value
            stats["by_severity"][sev] = stats["by_severity"].get(sev, 0) + 1
        
        return stats
