"""Main error prevention engine."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Any

from .models import ErrorPreventionRequest, ErrorPreventionResponse, AutoFix
from .detector import ErrorDetector
from .rules import RuleEngine

logger = logging.getLogger(__name__)


class ErrorPreventionEngine:
    """Main error prevention engine."""
    
    def __init__(self) -> None:
        self.detector = ErrorDetector()
        self.rule_engine = RuleEngine()
    
    async def analyze_code(self, request: ErrorPreventionRequest) -> ErrorPreventionResponse:
        """Analyze code for potential errors."""
        return await self.detector.detect_errors(request)
    
    async def apply_auto_fixes(self, issues: List[str], code: str) -> List[AutoFix]:
        """Apply automatic fixes to the code."""
        fixes = []
        
        for issue_id in issues:
            try:
                fix = await self._generate_auto_fix(issue_id, code)
                if fix:
                    fixes.append(fix)
            except Exception as e:
                logger.error(f"Error generating auto-fix for issue {issue_id}: {e}")
        
        return fixes
    
    async def _generate_auto_fix(self, issue_id: str, code: str) -> Optional[AutoFix]:
        """Generate an automatic fix for a specific issue."""
        # This is a placeholder implementation
        # In a real system, this would analyze the specific issue and generate appropriate fixes
        
        return AutoFix(
            issue_id=issue_id,
            original_code=code,
            fixed_code=code,  # Would be modified in real implementation
            description="Auto-fix applied",
            confidence=0.8,
            applied=False
        )
    
    def get_available_rules(self, language: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available error prevention rules."""
        if language:
            rules = self.rule_engine.get_rules_for_language(language)
        else:
            rules = self.rule_engine.rules + self.rule_engine.custom_rules
        
        return [
            {
                "name": rule.name,
                "description": rule.description,
                "category": rule.category.value,
                "severity": rule.severity.value,
                "language": rule.language,
                "enabled": rule.enabled,
                "auto_fix": rule.auto_fix
            }
            for rule in rules
        ]
    
    def enable_rule(self, rule_name: str) -> bool:
        """Enable a specific rule."""
        return self.rule_engine.enable_rule(rule_name)
    
    def disable_rule(self, rule_name: str) -> bool:
        """Disable a specific rule."""
        return self.rule_engine.disable_rule(rule_name)
    
    def get_rule_statistics(self) -> Dict[str, Any]:
        """Get statistics about the rule engine."""
        return self.rule_engine.get_rule_statistics()
