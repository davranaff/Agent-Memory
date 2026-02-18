"""Git integration utilities for Agent Brain."""

from __future__ import annotations

import logging
import subprocess
import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.paths import resolve_project_path
from .hooks import PreCommitHooks
from .review import CodeReviewAssistant, CodeReviewRequest

logger = logging.getLogger(__name__)


class GitIntegration:
    """Git integration utilities for Agent Brain."""
    
    def __init__(self, project_path: str) -> None:
        resolved_path = resolve_project_path(project_path)
        self.project_path = resolved_path.resolved_path
        if resolved_path.used_mapping:
            logger.info(
                "Resolved git project path via PROJECT_PATH_MAPPINGS: %s -> %s",
                project_path,
                self.project_path,
            )
        self.hooks = PreCommitHooks(str(self.project_path))
        self.review_assistant = CodeReviewAssistant()
    
    def is_git_repository(self) -> bool:
        """Check if the directory is a git repository."""
        return (self.project_path / ".git").exists()
    
    def get_staged_files(self) -> List[str]:
        """Get list of staged files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.splitlines() if result.stdout else []
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get staged files: {e}")
            return []
    
    def get_changed_files(self, commit_range: Optional[str] = None) -> List[str]:
        """Get list of changed files."""
        try:
            if commit_range:
                cmd = ["git", "diff", "--name-only", commit_range]
            else:
                cmd = ["git", "diff", "--name-only", "HEAD~1", "HEAD"]
            
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.splitlines() if result.stdout else []
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get changed files: {e}")
            return []
    
    def get_file_content(self, file_path: str) -> str:
        """Get file content."""
        try:
            full_path = self.project_path / file_path
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return ""
    
    def get_file_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.php': 'php',
            '.rb': 'ruby',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.dart': 'dart',
            '.scala': 'scala',
            '.lua': 'lua'
        }
        
        return language_map.get(extension, 'unknown')
    
    async def run_pre_commit_check(self, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run pre-commit check on files."""
        if files is None:
            files = self.get_staged_files()
        
        if not files:
            return {
                "success": True,
                "message": "No files to check",
                "results": []
            }
        
        try:
            results = await self.hooks.run_hooks(files)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "hook_name": result.hook_name,
                    "status": result.status,
                    "message": result.message,
                    "details": result.details,
                    "execution_time": result.execution_time
                })
            
            overall_status = "passed"
            if any(r["status"] == "failed" for r in formatted_results):
                overall_status = "failed"
            elif any(r["status"] == "warning" for r in formatted_results):
                overall_status = "warning"
            
            return {
                "success": overall_status == "passed",
                "overall_status": overall_status,
                "files_checked": len(files),
                "results": formatted_results
            }
            
        except Exception as e:
            logger.error(f"Pre-commit check failed: {e}")
            return {
                "success": False,
                "message": f"Pre-commit check failed: {str(e)}",
                "results": []
            }
    
    async def review_commit(self, commit_hash: Optional[str] = None) -> Dict[str, Any]:
        """Review a commit."""
        try:
            if commit_hash:
                # Get files changed in specific commit
                cmd = ["git", "show", "--name-only", "--format=", commit_hash]
                result = subprocess.run(
                    cmd,
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                files = result.stdout.splitlines() if result.stdout else []
            else:
                # Review staged files
                files = self.get_staged_files()
            
            if not files:
                return {
                    "success": True,
                    "message": "No files to review",
                    "reviews": []
                }
            
            reviews = []
            for file_path in files:
                content = self.get_file_content(file_path)
                language = self.get_file_language(file_path)
                
                if content and language != 'unknown':
                    try:
                        request = CodeReviewRequest(
                            code=content,
                            language=language,
                            file_path=file_path,
                            review_type="comprehensive",
                            include_suggestions=True
                        )
                        
                        review_result = await self.review_assistant.review_code(request)
                        
                        reviews.append({
                            "file_path": file_path,
                            "language": language,
                            "overall_score": review_result.overall_score,
                            "issues_count": len(review_result.issues),
                            "issues": [
                                {
                                    "line_number": issue.line_number,
                                    "severity": issue.severity.value,
                                    "category": issue.category.value,
                                    "message": issue.message,
                                    "suggestion": issue.suggestion
                                }
                                for issue in review_result.issues
                            ],
                            "suggestions": review_result.suggestions,
                            "metrics": review_result.metrics,
                            "summary": review_result.summary
                        })
                    
                    except Exception as e:
                        logger.error(f"Failed to review file {file_path}: {e}")
                        reviews.append({
                            "file_path": file_path,
                            "language": language,
                            "error": str(e)
                        })
            
            # Calculate overall statistics
            total_issues = sum(r.get("issues_count", 0) for r in reviews)
            avg_score = sum(r.get("overall_score", 0) for r in reviews) / len(reviews) if reviews else 0
            
            return {
                "success": True,
                "commit_hash": commit_hash,
                "files_reviewed": len(reviews),
                "total_issues": total_issues,
                "average_score": avg_score,
                "reviews": reviews
            }
            
        except Exception as e:
            logger.error(f"Commit review failed: {e}")
            return {
                "success": False,
                "message": f"Commit review failed: {str(e)}",
                "reviews": []
            }
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get commit history."""
        try:
            cmd = ["git", "log", f"--oneline", f"-{limit}", "--format=%H|%s|%an"]
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            commits = []
            for line in result.stdout.splitlines():
                parts = line.split('|', 2)
                if len(parts) == 3:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "message": parts[2]
                    })
            
            return commits
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get commit history: {e}")
            return []
    
    def get_branch_info(self) -> Dict[str, Any]:
        """Get current branch information."""
        try:
            # Get current branch
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = result.stdout.strip()
            
            # Get all branches
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            all_branches = [line.strip() for line in result.stdout.splitlines()]
            
            # Get remote branches
            result = subprocess.run(
                ["git", "branch", "-r"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            remote_branches = [line.strip() for line in result.stdout.splitlines()]
            
            return {
                "current_branch": current_branch,
                "local_branches": all_branches,
                "remote_branches": remote_branches,
                "total_branches": len(all_branches)
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get branch info: {e}")
            return {}
    
    def get_repository_info(self) -> Dict[str, Any]:
        """Get repository information."""
        try:
            # Get remote URL
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            remote_url = result.stdout.strip() if result.returncode == 0 else None
            
            # Get user info
            result = subprocess.run(
                ["git", "config", "user.name"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            user_name = result.stdout.strip() if result.returncode == 0 else None
            
            result = subprocess.run(
                ["git", "config", "user.email"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            user_email = result.stdout.strip() if result.returncode == 0 else None
            
            return {
                "remote_url": remote_url,
                "user_name": user_name,
                "user_email": user_email,
                "is_git_repo": self.is_git_repository(),
                "project_path": str(self.project_path)
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get repository info: {e}")
            return {
                "is_git_repo": self.is_git_repository(),
                "project_path": str(self.project_path)
            }
    
    def create_commit(self, message: str, files: List[str]) -> bool:
        """Create a commit with the given message and files."""
        try:
            # Stage files
            for file_path in files:
                subprocess.run(
                    ["git", "add", file_path],
                    cwd=self.project_path,
                    check=True
                )
            
            # Create commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_path,
                check=True
            )
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create commit: {e}")
            return False
    
    def install_agent_brain_hooks(self) -> bool:
        """Install Agent Brain pre-commit hooks."""
        return self.hooks.install_hooks()
    
    def uninstall_agent_brain_hooks(self) -> bool:
        """Uninstall Agent Brain pre-commit hooks."""
        return self.hooks.uninstall_hooks()
    
    def generate_hooks_config(self) -> str:
        """Generate hooks configuration."""
        return self.hooks.generate_config()
    
    def get_git_status(self) -> Dict[str, Any]:
        """Get git status information."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            status_lines = result.stdout.splitlines()
            
            staged = []
            modified = []
            untracked = []
            
            for line in status_lines:
                status_code = line[:2]
                file_path = line[3:]
                
                if status_code in ["A", "M"]:  # Added or Modified
                    staged.append(file_path)
                elif status_code == " ":
                    modified.append(file_path)
                elif status_code == "??":
                    untracked.append(file_path)
            
            return {
                "staged": staged,
                "modified": modified,
                "untracked": untracked,
                "total_files": len(staged) + len(modified) + len(untracked)
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get git status: {e}")
            return {}
