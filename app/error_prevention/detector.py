"""Error detector for the error prevention system."""

from __future__ import annotations

import logging
import re
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple

from .models import ErrorIssue, ErrorPreventionRequest, ErrorPreventionResponse, ErrorSeverity, ErrorCategory
from .rules import RuleEngine

logger = logging.getLogger(__name__)


class ErrorDetector:
    """Detects potential errors in code using rule-based analysis."""
    
    def __init__(self) -> None:
        self.rule_engine = RuleEngine()
    
    async def detect_errors(self, request: ErrorPreventionRequest) -> ErrorPreventionResponse:
        """Detect errors in the provided code."""
        start_time = time.time()
        
        try:
            # Get relevant rules
            rules = self.rule_engine.get_rules_for_language(
                request.language, 
                request.check_categories
            )
            
            # Analyze code with each rule
            all_issues = []
            code_lines = request.code.split('\n')
            
            for rule in rules:
                try:
                    issues = self._apply_rule(rule, request.code, code_lines, request)
                    all_issues.extend(issues)
                except Exception as e:
                    logger.error(f"Error applying rule {rule.name}: {e}")
                    continue
            
            # Filter by severity threshold
            filtered_issues = self._filter_by_severity(all_issues, request.severity_threshold)
            
            # Sort by severity and confidence
            filtered_issues.sort(key=lambda x: (
                self._severity_score(x.severity), 
                x.confidence
            ), reverse=True)
            
            # Limit results
            limited_issues = filtered_issues[:request.max_issues]
            
            # Calculate statistics
            processing_time = (time.time() - start_time) * 1000
            severity_dist = self._calculate_severity_distribution(limited_issues)
            category_dist = self._calculate_category_distribution(limited_issues)
            auto_fixes_count = len([i for i in limited_issues if i.auto_fix])
            
            return ErrorPreventionResponse(
                success=True,
                issues=limited_issues,
                total_issues=len(all_issues),
                severity_distribution=severity_dist,
                category_distribution=category_dist,
                processing_time_ms=processing_time,
                auto_fixes_available=auto_fixes_count,
                metadata={
                    "rules_applied": len(rules),
                    "lines_analyzed": len(code_lines),
                    "language": request.language,
                    "file_path": request.file_path
                }
            )
            
        except Exception as e:
            logger.error(f"Error in error detection: {e}")
            processing_time = (time.time() - start_time) * 1000
            
            return ErrorPreventionResponse(
                success=False,
                issues=[],
                total_issues=0,
                severity_distribution={},
                category_distribution={},
                processing_time_ms=processing_time,
                auto_fixes_available=0,
                metadata={
                    "error": str(e)
                }
            )
    
    def _apply_rule(self, rule, code: str, code_lines: List[str], request: ErrorPreventionRequest) -> List[ErrorIssue]:
        """Apply a single rule to detect errors."""
        issues = []
        
        try:
            # Compile regex pattern
            pattern = re.compile(rule.pattern, re.MULTILINE | re.IGNORECASE)
            
            # Find all matches
            for match in pattern.finditer(code):
                # Calculate line and column numbers
                line_number, column_number = self._get_position(code, match.start())
                
                # Extract code snippet
                snippet_start = max(0, match.start() - 50)
                snippet_end = min(len(code), match.end() + 50)
                snippet = code[snippet_start:snippet_end]
                
                # Calculate confidence based on context
                confidence = self._calculate_confidence(match, rule, code, line_number)
                
                # Create issue
                issue = ErrorIssue(
                    id=str(uuid.uuid4()),
                    title=f"{rule.category.value.title()}: {rule.name}",
                    description=rule.description,
                    severity=rule.severity,
                    category=rule.category,
                    line_number=line_number,
                    column_number=column_number,
                    code_snippet=snippet,
                    suggestion=rule.suggestion,
                    auto_fix=rule.auto_fix and request.include_auto_fixes,
                    confidence=confidence,
                    rule_name=rule.name,
                    metadata={
                        "pattern": rule.pattern,
                        "match_text": match.group(),
                        "match_start": match.start(),
                        "match_end": match.end()
                    }
                )
                
                issues.append(issue)
        
        except re.error as e:
            logger.error(f"Invalid regex pattern in rule {rule.name}: {e}")
        except Exception as e:
            logger.error(f"Error applying rule {rule.name}: {e}")
        
        return issues
    
    def _get_position(self, code: str, index: int) -> Tuple[int, int]:
        """Get line and column numbers from character index."""
        lines_before = code[:index].split('\n')
        line_number = len(lines_before)
        column_number = len(lines_before[-1]) + 1
        return line_number, column_number
    
    def _calculate_confidence(self, match, rule, code: str, line_number: int) -> float:
        """Calculate confidence score for a match."""
        base_confidence = 0.8
        
        # Adjust confidence based on context
        line_content = code.split('\n')[line_number - 1] if line_number > 0 else ""
        
        # Higher confidence for security issues
        if rule.category == ErrorCategory.SECURITY:
            base_confidence = 0.9
        
        # Lower confidence for maintainability issues
        elif rule.category == ErrorCategory.MAINTAINABILITY:
            base_confidence = 0.7
        
        # Adjust based on line context
        if line_content.strip().startswith('#') or line_content.strip().startswith('//'):
            base_confidence *= 0.5  # Lower confidence for commented code
        
        # Adjust based on rule complexity
        if '?' in rule.pattern or '*' in rule.pattern:
            base_confidence *= 0.9  # Slightly lower for complex patterns
        
        return min(1.0, max(0.1, base_confidence))
    
    def _filter_by_severity(self, issues: List[ErrorIssue], threshold: ErrorSeverity) -> List[ErrorIssue]:
        """Filter issues by severity threshold."""
        severity_scores = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        
        threshold_score = severity_scores[threshold]
        
        return [
            issue for issue in issues
            if severity_scores[issue.severity] >= threshold_score
        ]
    
    def _calculate_severity_distribution(self, issues: List[ErrorIssue]) -> Dict[str, int]:
        """Calculate distribution of issues by severity."""
        distribution = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }
        
        for issue in issues:
            distribution[issue.severity.value] += 1
        
        return distribution
    
    def _calculate_category_distribution(self, issues: List[ErrorIssue]) -> Dict[str, int]:
        """Calculate distribution of issues by category."""
        distribution = {}
        
        for issue in issues:
            category = issue.category.value
            distribution[category] = distribution.get(category, 0) + 1
        
        return distribution
    
    def _severity_score(self, severity: ErrorSeverity) -> int:
        """Get numeric score for severity."""
        scores = {
            ErrorSeverity.LOW: 1,
            ErrorSeverity.MEDIUM: 2,
            ErrorSeverity.HIGH: 3,
            ErrorSeverity.CRITICAL: 4
        }
        return scores.get(severity, 1)
