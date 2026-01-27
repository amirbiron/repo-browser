from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import logging

from services.git_mirror_service import GitMirrorService

logger = logging.getLogger(__name__)


@dataclass
class RepoConfig:
    """הגדרות ריפו"""
    name: str
    url: str
    default_branch: str = "main"
    is_private: bool = False
    last_sync: Optional[datetime] = None
    sync_status: str = "pending"  # pending, syncing, synced, error


class RepoManagerService:
    """
    ניהול ריפוים מרובים
    אחראי על:
    - הוספה/הסרה של ריפוים
    - סנכרון אוטומטי
    - מעקב סטטוס
    """
    
    def __init__(self, db, git_service: GitMirrorService):
        self.db = db
        self.git_service = git_service
        self.repos_collection = db.repos
    
    def add_repo(self, url: str, name: str = None) -> Dict:
        """
        הוספת ריפו חדש
        
        Args:
            url: GitHub URL (https://github.com/owner/repo)
            name: שם ייחודי (ברירת מחדל: נגזר מה-URL)
        
        Returns:
            Dict עם success, repo_info או error
        """
        # Validate URL
        if not self._validate_github_url(url):
            return {"success": False, "error": "Invalid GitHub URL"}
        
        # Extract name if not provided
        if not name:
            name = self._extract_repo_name(url)
        
        # Check if already exists
        if self.repos_collection.find_one({"name": name}):
            return {"success": False, "error": "Repo already exists"}
        
        # Create mirror
        result = self.git_service.init_mirror(url, name)
        if not result["success"]:
            return result
        
        # Save to DB
        repo_config = {
            "name": name,
            "url": url,
            "default_branch": "main",  # Will be updated after first sync
            "created_at": datetime.utcnow(),
            "last_sync": datetime.utcnow(),
            "sync_status": "synced"
        }
        
        self.repos_collection.insert_one(repo_config)
        
        # Index files
        self._index_repo_files(name)
        
        return {"success": True, "repo": repo_config}
    
    def remove_repo(self, name: str) -> Dict:
        """הסרת ריפו"""
        # Remove from DB
        self.repos_collection.delete_one({"name": name})
        self.db.repo_files.delete_many({"repo_name": name})
        
        # Remove mirror directory (safely!)
        mirror_path = self.git_service._get_repo_path(name)
        self.git_service._safe_rmtree(mirror_path)
        
        logger.info(f"Repo removed: {name}")
        return {"success": True}
    
    def list_repos(self) -> List[Dict]:
        """רשימת כל הריפוים"""
        repos = list(self.repos_collection.find({}, {"_id": 0}))
        
        # Enrich with mirror info
        for repo in repos:
            mirror_info = self.git_service.get_mirror_info(repo["name"])
            if mirror_info:
                repo["size_mb"] = mirror_info.get("size_mb", 0)
                repo["current_sha"] = mirror_info.get("current_sha")
        
        return repos
    
    def sync_repo(self, name: str) -> Dict:
        """סנכרון ריפו (fetch updates)"""
        # Update status
        self.repos_collection.update_one(
            {"name": name},
            {"$set": {"sync_status": "syncing"}}
        )
        
        try:
            result = self.git_service.fetch_updates(name)
            
            if result["success"]:
                # Re-index files if needed
                self._index_repo_files(name)
                
                self.repos_collection.update_one(
                    {"name": name},
                    {"$set": {
                        "sync_status": "synced",
                        "last_sync": datetime.utcnow()
                    }}
                )
            else:
                self.repos_collection.update_one(
                    {"name": name},
                    {"$set": {
                        "sync_status": "error",
                        "last_error": result.get("error", "Unknown error")
                    }}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed for {name}: {e}")
            self.repos_collection.update_one(
                {"name": name},
                {"$set": {"sync_status": "error", "last_error": str(e)}}
            )
            return {"success": False, "error": str(e)}
    
    def sync_all_repos(self) -> Dict:
        """סנכרון כל הריפוים"""
        results = {}
        for repo in self.list_repos():
            results[repo["name"]] = self.sync_repo(repo["name"])
        return results
    
    def _index_repo_files(self, repo_name: str):
        """אינדוקס קבצי הריפו ל-MongoDB"""
        files = self.git_service.list_all_files(repo_name)
        if not files:
            logger.warning(f"No files found for {repo_name}")
            return
        
        # Delete old entries
        self.db.repo_files.delete_many({"repo_name": repo_name})
        
        # Batch insert
        docs = []
        for file_path in files:
            info = self.git_service.get_file_info(repo_name, file_path)
            docs.append({
                "repo_name": repo_name,
                "path": file_path,
                "language": self._detect_language(file_path),
                "size": info.get("size", 0) if info else 0,
                "lines": info.get("lines", 0) if info else 0
            })
        
        if docs:
            self.db.repo_files.insert_many(docs)
            logger.info(f"Indexed {len(docs)} files for {repo_name}")
    
    def _detect_language(self, file_path: str) -> str:
        """זיהוי שפת תכנות לפי סיומת"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'css',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'shell',
            '.bash': 'shell',
            '.sql': 'sql',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.kt': 'kotlin',
            '.rb': 'ruby',
            '.php': 'php',
        }
        
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')
    
    def _validate_github_url(self, url: str) -> bool:
        """Validate GitHub URL format"""
        pattern = r'^https://github\.com/[^/]+/[^/]+(?:\.git)?/?$'
        return bool(re.match(pattern, url, re.IGNORECASE))
    
    def _extract_repo_name(self, url: str) -> str:
        """Extract repo name from URL"""
        # https://github.com/owner/repo.git -> owner_repo
        parts = url.rstrip('/').rstrip('.git').split('/')
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1]
            return f"{owner}_{repo}"
        return "unknown_repo"
