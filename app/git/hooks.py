"""Pre-commit hooks integration for Agent Brain."""

from __future__ import annotations

import logging
import os
import subprocess
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from app.models.git import PreCommitCheckRequest
from app.memory.embeddings import OllamaEmbeddingProvider
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class HookResult:
    """Result of a pre-commit hook execution."""
    hook_name: str
    status: str  # "passed", "failed", "warning"
    message: str
    details: Dict[str, Any]
    execution_time: float


class PreCommitHooks:
    """Pre-commit hooks manager for Agent Brain."""
    
    def __init__(self, project_path: str) -> None:
        self.project_path = Path(project_path)
        self.hooks_config = self._load_hooks_config()
        self.embedding_provider = OllamaEmbeddingProvider(
            base_url=get_settings().ollama_base_url,
            model="nomic-embed-text",
            dim=768
        )
    
    def _load_hooks_config(self) -> Dict[str, Any]:
        """Load pre-commit hooks configuration."""
        config_path = self.project_path / ".agent-brain-hooks.json"
        
        default_config = {
            "hooks": {
                "code_quality": {
                    "enabled": True,
                    "max_file_size": 10000,
                    "max_line_length": 120,
                    "check_todo": True
                },
                "pattern_detection": {
                    "enabled": True,
                    "min_confidence": 0.7,
                    "required_patterns": []
                },
                "security_scan": {
                    "enabled": True,
                    "check_secrets": True,
                    "check_eval_usage": True,
                    "check_hardcoded_credentials": True
                },
                "semantic_analysis": {
                    "enabled": True,
                    "check_code_similarity": True,
                    "min_similarity_threshold": 0.8
                },
                "documentation": {
                    "enabled": True,
                    "require_docstrings": False,
                    "check_readme": True
                }
            },
            "ignore_patterns": [
                "*.log",
                "*.tmp",
                "node_modules/*",
                ".git/*",
                "__pycache__/*"
            ]
        }
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                    # Merge with default config
                    default_config.update(user_config)
            except Exception as e:
                logger.warning(f"Failed to load hooks config: {e}")
        
        return default_config
    
    async def run_hooks(self, staged_files: List[str]) -> List[HookResult]:
        """Run all enabled pre-commit hooks on staged files."""
        results = []
        
        for hook_name, hook_config in self.hooks_config["hooks"].items():
            if not hook_config.get("enabled", True):
                continue
            
            try:
                result = await self._run_single_hook(hook_name, staged_files, hook_config)
                results.append(result)
            except Exception as e:
                logger.error(f"Error running hook {hook_name}: {e}")
                results.append(HookResult(
                    hook_name=hook_name,
                    status="failed",
                    message=f"Hook execution failed: {str(e)}",
                    details={},
                    execution_time=0.0
                ))
        
        return results
    
    async def _run_single_hook(self, hook_name: str, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Run a single pre-commit hook."""
        import time
        start_time = time.time()
        
        try:
            if hook_name == "code_quality":
                result = await self._code_quality_hook(files, config)
            elif hook_name == "pattern_detection":
                result = await self._pattern_detection_hook(files, config)
            elif hook_name == "security_scan":
                result = await self._security_scan_hook(files, config)
            elif hook_name == "semantic_analysis":
                result = await self._semantic_analysis_hook(files, config)
            elif hook_name == "documentation":
                result = await self._documentation_hook(files, config)
            else:
                result = HookResult(
                    hook_name=hook_name,
                    status="passed",
                    message="Unknown hook, skipping",
                    details={},
                    execution_time=0.0
                )
            
            result.execution_time = time.time() - start_time
            return result
            
        except Exception as e:
            return HookResult(
                hook_name=hook_name,
                status="failed",
                message=f"Hook failed: {str(e)}",
                details={"error": str(e)},
                execution_time=time.time() - start_time
            )
    
    async def _code_quality_hook(self, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Code quality pre-commit hook."""
        issues = []
        warnings = []
        
        max_file_size = config.get("max_file_size", 10000)
        max_line_length = config.get("max_line_length", 120)
        check_todo = config.get("check_todo", True)
        
        for file_path in files:
            if not self._should_check_file(file_path):
                continue
            
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    continue
                
                # Check file size
                file_size = file_path_obj.stat().st_size
                if file_size > max_file_size:
                    warnings.append(f"Large file: {file_path} ({file_size} bytes)")
                
                # Check line length and TODO comments
                with open(file_path_obj, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.rstrip('\n')
                        
                        # Check line length
                        if len(line) > max_line_length:
                            issues.append(f"Line {line_num} in {file_path} is too long ({len(line)} chars)")
                        
                        # Check for TODO comments
                        if check_todo and ("TODO" in line or "FIXME" in line):
                            warnings.append(f"TODO/FIXME found at line {line_num} in {file_path}")
                
            except Exception as e:
                warnings.append(f"Could not read file {file_path}: {str(e)}")
        
        status = "failed" if issues else "warning" if warnings else "passed"
        message = f"Found {len(issues)} issues and {len(warnings)} warnings"
        
        return HookResult(
            hook_name="code_quality",
            status=status,
            message=message,
            details={
                "issues": issues,
                "warnings": warnings,
                "files_checked": len(files)
            },
            execution_time=0.0
        )
    
    async def _pattern_detection_hook(self, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Pattern detection pre-commit hook."""
        pattern_issues = []
        
        min_confidence = config.get("min_confidence", 0.7)
        required_patterns = config.get("required_patterns", [])
        
        for file_path in files:
            if not self._should_check_file(file_path):
                continue
            
            try:
                # Detect patterns in the file
                detected_patterns = await self._detect_patterns_in_file(file_path)
                
                # Check for required patterns
                for required_pattern in required_patterns:
                    if not any(p["pattern"] == required_pattern for p in detected_patterns):
                        pattern_issues.append(f"Missing required pattern '{required_pattern}' in {file_path}")
                
                # Check for low confidence patterns
                low_confidence_patterns = [
                    p for p in detected_patterns if p["confidence"] < min_confidence
                ]
                
                if low_confidence_patterns:
                    pattern_issues.append(
                        f"Low confidence patterns detected in {file_path}: "
                        f"{', '.join(p['pattern'] for p in low_confidence_patterns)}"
                    )
                
            except Exception as e:
                pattern_issues.append(f"Pattern detection failed for {file_path}: {str(e)}")
        
        status = "failed" if pattern_issues else "passed"
        message = f"Pattern detection completed with {len(pattern_issues)} issues"
        
        return HookResult(
            hook_name="pattern_detection",
            status=status,
            message=message,
            details={
                "issues": pattern_issues,
                "files_checked": len(files)
            },
            execution_time=0.0
        )
    
    async def _security_scan_hook(self, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Security scanning pre-commit hook."""
        security_issues = []
        
        check_secrets = config.get("check_secrets", True)
        check_eval_usage = config.get("check_eval_usage", True)
        check_hardcoded_credentials = config.get("check_hardcoded_credentials", True)
        
        # Common secret patterns
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]
        
        for file_path in files:
            if not self._should_check_file(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for hardcoded secrets
                    if check_secrets or check_hardcoded_credentials:
                        import re
                        for pattern in secret_patterns:
                            matches = re.findall(pattern, content, re.IGNORECASE)
                            for match in matches:
                                security_issues.append(f"Potential secret found in {file_path}: {match[:50]}...")
                    
                    # Check for eval usage
                    if check_eval_usage:
                        if "eval(" in content or "exec(" in content:
                            security_issues.append(f"eval/exec usage detected in {file_path}")
                
            except Exception as e:
                security_issues.append(f"Security scan failed for {file_path}: {str(e)}")
        
        status = "failed" if security_issues else "passed"
        message = f"Security scan completed with {len(security_issues)} issues"
        
        return HookResult(
            hook_name="security_scan",
            status=status,
            message=message,
            details={
                "issues": security_issues,
                "files_checked": len(files)
            },
            execution_time=0.0
        )
    
    async def _semantic_analysis_hook(self, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Semantic analysis pre-commit hook."""
        semantic_issues = []
        
        check_similarity = config.get("check_code_similarity", True)
        min_similarity_threshold = config.get("min_similarity_threshold", 0.8)
        
        if not check_similarity:
            return HookResult(
                hook_name="semantic_analysis",
                status="passed",
                message="Semantic similarity check disabled",
                details={},
                execution_time=0.0
            )
        
        # This would integrate with the semantic search system
        # For now, placeholder implementation
        for file_path in files:
            if not self._should_check_file(file_path):
                continue
            
            try:
                # Placeholder for semantic similarity check
                # In production, this would use the semantic search engine
                pass
                
            except Exception as e:
                semantic_issues.append(f"Semantic analysis failed for {file_path}: {str(e)}")
        
        status = "failed" if semantic_issues else "passed"
        message = f"Semantic analysis completed with {len(semantic_issues)} issues"
        
        return HookResult(
            hook_name="semantic_analysis",
            status=status,
            message=message,
            details={
                "issues": semantic_issues,
                "files_checked": len(files)
            },
            execution_time=0.0
        )
    
    async def _documentation_hook(self, files: List[str], config: Dict[str, Any]) -> HookResult:
        """Documentation pre-commit hook."""
        doc_issues = []
        
        require_docstrings = config.get("require_docstrings", False)
        check_readme = config.get("check_readme", True)
        
        # Check for README
        if check_readme:
            readme_files = [
                f for f in files 
                if f.lower().endswith(('readme.md', 'readme.rst', 'readme.txt'))
            ]
            
            if not any(readme_files):
                doc_issues.append("No README file found")
        
        # Check docstrings (placeholder)
        if require_docstrings:
            for file_path in files:
                if file_path.endswith(('.py', '.js', '.ts', '.java')):
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            if 'def ' in content or 'class ' in content:
                                # Simple check for docstrings
                                if '"""' not in content and "'''" not in content:
                                    doc_issues.append(f"Missing docstrings in {file_path}")
                    except Exception:
                        pass
        
        status = "failed" if doc_issues else "passed"
        message = f"Documentation check completed with {len(doc_issues)} issues"
        
        return HookResult(
            hook_name="documentation",
            status=status,
            message=message,
            details={
                "issues": doc_issues,
                "files_checked": len(files)
            },
            execution_time=0.0
        )
    
    def _should_check_file(self, file_path: str) -> bool:
        """Check if file should be processed by hooks."""
        file_path = Path(file_path)
        
        # Check ignore patterns
        for pattern in self.hooks_config.get("ignore_patterns", []):
            if file_path.match(pattern):
                return False
        
        # Check if file exists
        if not file_path.exists():
            return False
        
        # Check if it's a text file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read first 1KB
            return True
        except UnicodeDecodeError:
            return False
        except Exception:
            return False
    
    async def _detect_patterns_in_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Detect patterns in a single file."""
        # This would integrate with the pattern detection system
        # For now, return placeholder
        return []
    
    def generate_config(self) -> str:
        """Generate default pre-commit hooks configuration."""
        config = self.hooks_config.copy()
        return json.dumps(config, indent=2)
    
    def install_hooks(self) -> bool:
        """Install pre-commit hooks in the repository."""
        try:
            # Create .agent-brain-hooks.json
            config_path = self.project_path / ".agent-brain-hooks.json"
            with open(config_path, 'w') as f:
                json.dump(self.hooks_config, f, indent=2)
            
            # Create pre-commit hook script
            hooks_dir = self.project_path / ".git" / "hooks"
            hooks_dir.mkdir(exist_ok=True)
            
            pre_commit_script = f"""#!/bin/bash
# Agent Brain Pre-commit Hook
echo "Running Agent Brain pre-commit hooks..."

# Get staged files
STAGED_FILES=$(git diff --cached --name-only)

# Run hooks via API
python -c "
import sys
sys.path.append('{self.project_path}')
from app.git.hooks import PreCommitHooks
import asyncio

async def run_hooks():
    hooks = PreCommitHooks('{self.project_path}')
    results = await hooks.run_hooks(STAGED_FILES.split('\\\\n'))
    
    failed = False
    for result in results:
        if result.status == 'failed':
            print(f'❌ {{result.hook_name}}: {{result.message}}')
            failed = True
        elif result.status == 'warning':
            print(f'⚠️  {{result.hook_name}}: {{result.message}}')
        else:
            print(f'✅ {{result.hook_name}}: Passed')
    
    if failed:
        print('\\\\nPre-commit hooks failed! Fix the issues and try again.')
        sys.exit(1)
    else:
        print('\\\\nAll pre-commit hooks passed! 🎉')

asyncio.run(run_hooks())
"""

            pre_commit_file = hooks_dir / "pre-commit"
            with open(pre_commit_file, 'w') as f:
                f.write(pre_commit_script)
            
            # Make hook executable
            os.chmod(pre_commit_file, 0o755)
            
            print(f"✅ Pre-commit hooks installed in {self.project_path}")
            print(f"📄 Configuration saved to {config_path}")
            print(f"🔗 Hook script: {pre_commit_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to install hooks: {e}")
            return False
    
    def uninstall_hooks(self) -> bool:
        """Uninstall pre-commit hooks from the repository."""
        try:
            # Remove hook script
            pre_commit_file = self.project_path / ".git" / "hooks" / "pre-commit"
            if pre_commit_file.exists():
                pre_commit_file.unlink()
            
            # Remove config file
            config_file = self.project_path / ".agent-brain-hooks.json"
            if config_file.exists():
                config_file.unlink()
            
            print(f"✅ Pre-commit hooks uninstalled from {self.project_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to uninstall hooks: {e}")
            return False
