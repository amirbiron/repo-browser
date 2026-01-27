import os
import re
import subprocess
import logging
import shutil
from typing import Dict, List, Optional
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


class GitMirrorService:
    """
    שירות לניהול Git Mirror על דיסק מקומי
    
    שימוש:
        service = GitMirrorService()
        service.init_mirror("https://github.com/user/repo.git", "repo")
        service.fetch_updates("repo")
        content = service.get_file_content("repo", "src/main.py")
    """
    
    # Pattern validation
    REPO_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}$')
    FILE_PATH_PATTERN = re.compile(
        r'^(?!.*//)' # No //
        r'(?!/)'     # No leading /
        r'(?!-)'     # No leading '-' (avoid git flags)
        r'(?!.*\x00)' # No NUL
        r'[a-zA-Z0-9.\_/-]+'  # Allowed chars
        r'(?<!/)$'   # No trailing /
    )
    
    def __init__(self, base_path: str = None, github_token: str = None):
        """
        Args:
            base_path: נתיב לאחסון mirrors (ברירת מחדל: /var/data/repos)
            github_token: טוקן לגישה ל-Private repos
        """
        self.base_path = Path(base_path or Config.REPO_MIRROR_PATH)
        self.github_token = github_token or Config.GITHUB_TOKEN
        
        # Create base directory
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GitMirrorService initialized at {self.base_path}")
    
    # =====================================
    # Mirror Management
    # =====================================
    
    def init_mirror(self, repo_url: str, repo_name: str, timeout: int = None) -> Dict:
        """Clone ראשוני של ריפו כ-bare mirror"""
        if not self._validate_repo_name(repo_name):
            return {"success": False, "error": "Invalid repo name"}
        
        repo_path = self._get_repo_path(repo_name)
        
        if repo_path.exists():
            return {"success": False, "error": "Mirror already exists"}
        
        timeout = timeout or Config.GIT_CLONE_TIMEOUT
        
        try:
            # Clone as bare mirror
            cmd = ["git", "clone", "--mirror", repo_url, str(repo_path)]
            
            # Add token for private repos
            if self.github_token and "github.com" in repo_url:
                cmd[3] = self._add_token_to_url(repo_url)
            
            result = subprocess.run(
                cmd,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Clone failed: {result.stderr}"
                }
            
            logger.info(f"Mirror created: {repo_name}")
            return {
                "success": True,
                "repo_name": repo_name,
                "path": str(repo_path)
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Clone timeout"}
        except Exception as e:
            logger.error(f"Mirror init failed: {e}")
            return {"success": False, "error": str(e)}
    
    def fetch_updates(self, repo_name: str, timeout: int = None) -> Dict:
        """עדכון delta בלבד (fetch --all --prune)"""
        if not self.mirror_exists(repo_name):
            return {"success": False, "error": "Mirror not found"}
        
        repo_path = self._get_repo_path(repo_name)
        timeout = timeout or Config.GIT_FETCH_TIMEOUT
        
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "fetch", "--all", "--prune"],
                timeout=timeout,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return {"success": False, "error": f"Fetch failed: {result.stderr}"}
            
            logger.info(f"Mirror updated: {repo_name}")
            return {"success": True, "repo_name": repo_name}
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Fetch timeout"}
        except Exception as e:
            logger.error(f"Fetch failed: {e}")
            return {"success": False, "error": str(e)}
    
    def mirror_exists(self, repo_name: str) -> bool:
        """בדיקה אם mirror קיים"""
        repo_path = self._get_repo_path(repo_name)
        return repo_path.exists() and (repo_path / "HEAD").exists()
    
    def get_mirror_info(self, repo_name: str) -> Optional[Dict]:
        """קבלת מידע על mirror (גודל, SHA נוכחי)"""
        if not self.mirror_exists(repo_name):
            return None
        
        repo_path = self._get_repo_path(repo_name)
        
        try:
            # Get size
            size_bytes = sum(
                f.stat().st_size 
                for f in repo_path.rglob('*') if f.is_file()
            )
            
            # Get current SHA
            result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            current_sha = result.stdout.strip() if result.returncode == 0 else None
            
            return {
                "repo_name": repo_name,
                "path": str(repo_path),
                "size_bytes": size_bytes,
                "size_mb": round(size_bytes / (1024 * 1024), 2),
                "current_sha": current_sha
            }
        except Exception as e:
            logger.error(f"Failed to get mirror info: {e}")
            return None
    
    # =====================================
    # File Operations
    # =====================================
    
    def get_file_content(self, repo_name: str, file_path: str, ref: str = "HEAD") -> Optional[str]:
        """קריאת תוכן קובץ"""
        if not self._validate_file_path(file_path):
            logger.warning(f"Invalid file path: {file_path}")
            return None
        
        if not self.mirror_exists(repo_name):
            return None
        
        repo_path = self._get_repo_path(repo_name)
        
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "show", f"{ref}:{file_path}"],
                capture_output=True,
                text=True,
                timeout=Config.GIT_COMMAND_TIMEOUT,
                errors='replace'  # Handle encoding errors
            )
            
            if result.returncode != 0:
                return None
            
            return result.stdout
            
        except Exception as e:
            logger.error(f"Failed to read file: {e}")
            return None
    
    def list_all_files(self, repo_name: str, ref: str = "HEAD") -> Optional[List[str]]:
        """רשימת כל הקבצים בריפו"""
        if not self.mirror_exists(repo_name):
            return None
        
        repo_path = self._get_repo_path(repo_name)
        
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "ls-tree", "-r", "--name-only", ref],
                capture_output=True,
                text=True,
                timeout=Config.GIT_COMMAND_TIMEOUT
            )
            
            if result.returncode != 0:
                return None
            
            files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files: {e}")
            return None
    
    def get_file_info(self, repo_name: str, file_path: str, ref: str = "HEAD") -> Optional[Dict]:
        """מידע על קובץ (גודל, סוג)"""
        if not self._validate_file_path(file_path):
            return None
        
        content = self.get_file_content(repo_name, file_path, ref)
        if content is None:
            return None
        
        return {
            "path": file_path,
            "size": len(content.encode('utf-8')),
            "lines": content.count('\n') + 1,
            "extension": Path(file_path).suffix
        }
    
    # =====================================
    # Search
    # =====================================
    
    def search_with_git_grep(
        self, 
        repo_name: str, 
        query: str, 
        max_results: int = 100,
        file_pattern: str = None,
        case_sensitive: bool = True,
        ref: str = None
    ) -> Dict:
        """חיפוש בקוד עם git grep (מהיר מאוד!)"""
        if not self.mirror_exists(repo_name):
            return {"error": "Mirror not found", "results": []}
        
        if not query or len(query) < 2:
            return {"error": "Query too short", "results": []}
        
        repo_path = self._get_repo_path(repo_name)
        ref = ref or "HEAD"
        
        cmd = ["git", "-C", str(repo_path), "grep", "-n"]
        
        if not case_sensitive:
            cmd.append("-i")
        
        cmd.extend(["-e", query, ref, "--"])
        
        if file_pattern:
            cmd.append(file_pattern)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.SEARCH_TIMEOUT,
                errors='replace'
            )
            
            # git grep returns 1 if no matches found (not an error)
            if result.returncode not in (0, 1):
                return {"error": "Search failed", "results": []}
            
            results = []
            for line in result.stdout.splitlines()[:max_results]:
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    # Format: ref:path:line_number:content
                    results.append({
                        "path": parts[1],
                        "line": int(parts[2]),
                        "content": parts[3].strip()
                    })
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "truncated": len(result.stdout.splitlines()) > max_results
            }
            
        except subprocess.TimeoutExpired:
            return {"error": "Search timeout", "results": []}
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return {"error": str(e), "results": []}
    
    # =====================================
    # History & Diff
    # =====================================
    
    def get_file_history(
        self, 
        repo_name: str, 
        file_path: str, 
        ref: str = "HEAD",
        limit: int = 20,
        skip: int = 0
    ) -> Dict:
        """היסטוריית commits לקובץ"""
        if not self._validate_file_path(file_path):
            return {"error": "Invalid file path", "commits": []}
        
        if not self.mirror_exists(repo_name):
            return {"error": "Mirror not found", "commits": []}
        
        repo_path = self._get_repo_path(repo_name)
        
        try:
            # Format: hash|author|date|subject
            format_str = "%H|%an|%ai|%s"
            
            result = subprocess.run(
                [
                    "git", "-C", str(repo_path), "log",
                    f"--format={format_str}",
                    f"--skip={skip}",
                    f"-n{limit}",
                    ref, "--", file_path
                ],
                capture_output=True,
                text=True,
                timeout=Config.GIT_COMMAND_TIMEOUT
            )
            
            if result.returncode != 0:
                return {"error": "History failed", "commits": []}
            
            commits = []
            for line in result.stdout.splitlines():
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    })
            
            return {
                "commits": commits,
                "file": file_path,
                "total": len(commits)
            }
            
        except Exception as e:
            logger.error(f"History failed: {e}")
            return {"error": str(e), "commits": []}
    
    def get_file_at_commit(
        self, 
        repo_name: str, 
        file_path: str, 
        commit: str,
        max_size: int = 500 * 1024
    ) -> Dict:
        """תוכן קובץ ב-commit ספציפי"""
        content = self.get_file_content(repo_name, file_path, ref=commit)
        
        if content is None:
            return {"error": "File not found"}
        
        if len(content) > max_size:
            return {
                "error": "File too large",
                "size": len(content),
                "max_size": max_size
            }
        
        return {
            "content": content,
            "file": file_path,
            "commit": commit,
            "size": len(content)
        }
    
    def get_diff(
        self,
        repo_name: str,
        commit1: str,
        commit2: str,
        file_path: Optional[str] = None,
        context_lines: int = 3
    ) -> Dict:
        """Diff בין commits"""
        if not self.mirror_exists(repo_name):
            return {"error": "Mirror not found"}
        
        repo_path = self._get_repo_path(repo_name)
        
        cmd = [
            "git", "-C", str(repo_path), "diff",
            f"-U{context_lines}",
            commit1, commit2
        ]
        
        if file_path:
            if not self._validate_file_path(file_path):
                return {"error": "Invalid file path"}
            cmd.extend(["--", file_path])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.GIT_COMMAND_TIMEOUT,
                errors='replace'
            )
            
            if result.returncode not in (0, 1):  # 1 = differences found
                return {"error": "Diff failed"}
            
            return {
                "diff": result.stdout,
                "commit1": commit1,
                "commit2": commit2,
                "file": file_path
            }
            
        except Exception as e:
            logger.error(f"Diff failed: {e}")
            return {"error": str(e)}
    
    def get_commit_info(self, repo_name: str, commit: str) -> Dict:
        """פרטי commit בודד"""
        if not self.mirror_exists(repo_name):
            return {"error": "Mirror not found"}
        
        repo_path = self._get_repo_path(repo_name)
        
        try:
            # Get commit details
            format_str = "%H|%an|%ae|%ai|%s|%b"
            
            result = subprocess.run(
                ["git", "-C", str(repo_path), "show", "-s", f"--format={format_str}", commit],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"error": "Commit not found"}
            
            parts = result.stdout.split('|', 5)
            if len(parts) == 6:
                return {
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "date": parts[3],
                    "subject": parts[4],
                    "body": parts[5].strip()
                }
            
            return {"error": "Failed to parse commit"}
            
        except Exception as e:
            logger.error(f"Get commit info failed: {e}")
            return {"error": str(e)}
    
    def search_history(
        self,
        repo_name: str,
        query: str,
        search_type: str = "message",  # message or code
        file_path: Optional[str] = None,
        limit: int = 20
    ) -> Dict:
        """חיפוש בהיסטוריית commits"""
        if not self.mirror_exists(repo_name):
            return {"error": "Mirror not found", "commits": []}
        
        repo_path = self._get_repo_path(repo_name)
        
        cmd = ["git", "-C", str(repo_path), "log", f"-n{limit}"]
        
        if search_type == "message":
            cmd.extend(["--grep", query, "-i"])
        elif search_type == "code":
            cmd.extend(["-S", query])
        
        if file_path:
            cmd.extend(["--", file_path])
        
        # Format
        format_str = "%H|%an|%ai|%s"
        cmd.insert(4, f"--format={format_str}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=Config.SEARCH_TIMEOUT
            )
            
            if result.returncode != 0:
                return {"error": "Search failed", "commits": []}
            
            commits = []
            for line in result.stdout.splitlines():
                parts = line.split('|', 3)
                if len(parts) == 4:
                    commits.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "date": parts[2],
                        "message": parts[3]
                    })
            
            return {
                "commits": commits,
                "query": query,
                "search_type": search_type,
                "total": len(commits)
            }
            
        except Exception as e:
            logger.error(f"History search failed: {e}")
            return {"error": str(e), "commits": []}
    
    # =====================================
    # Helper Methods
    # =====================================
    
    def _get_repo_path(self, repo_name: str) -> Path:
        """Get full path to repo mirror"""
        return self.base_path / repo_name
    
    def _validate_repo_name(self, repo_name: str) -> bool:
        """Validate repo name"""
        return bool(self.REPO_NAME_PATTERN.match(repo_name))
    
    def _validate_file_path(self, file_path: str) -> bool:
        """וולידציה של נתיב קובץ - מונע path traversal"""
        if not file_path or '\x00' in file_path:
            return False
        
        if file_path.startswith('-'):
            return False
        
        # Normalize and check for traversal
        normalized = os.path.normpath(file_path)
        if normalized == '..' or normalized.startswith('..' + os.sep):
            return False
        
        if normalized.startswith('/'):
            return False
        
        return bool(self.FILE_PATH_PATTERN.match(file_path))
    
    def _add_token_to_url(self, url: str) -> str:
        """Add GitHub token to URL"""
        if not self.github_token:
            return url
        
        # https://github.com/owner/repo -> https://TOKEN@github.com/owner/repo
        return url.replace("https://", f"https://{self.github_token}@")
    
    def _safe_rmtree(self, path: Path):
        """Safe recursive delete"""
        # Safety checks
        if not path.exists():
            return
        
        if not str(path).startswith(str(self.base_path)):
            raise ValueError("Cannot delete outside base path")
        
        if path == self.base_path:
            raise ValueError("Cannot delete base path")
        
        shutil.rmtree(path)


# Singleton instance
_mirror_service = None


def get_mirror_service() -> GitMirrorService:
    """Get singleton instance"""
    global _mirror_service
    if _mirror_service is None:
        _mirror_service = GitMirrorService()
    return _mirror_service
