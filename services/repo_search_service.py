import re
import logging
from typing import Dict, Any
from services.git_mirror_service import get_mirror_service

logger = logging.getLogger(__name__)


class RepoSearchService:
    """
    שירות חיפוש בקוד
    משלב:
    - git grep לחיפוש תוכן (מהיר!)
    - MongoDB לחיפוש metadata (שמות קבצים, פונקציות, מחלקות)
    """
    
    def __init__(self, db: Any = None):
        self.db = db
        self.git_service = get_mirror_service()
    
    def search(
        self,
        repo_name: str,
        query: str,
        search_type: str = "content",  # content, filename, function, class
        file_pattern: str = None,
        language: str = None,
        case_sensitive: bool = False,
        max_results: int = 50
    ) -> Dict:
        """
        חיפוש מאוחד בקוד
        
        search_types:
        - content: חיפוש בתוכן קבצים (git grep)
        - filename: חיפוש בשמות קבצים
        - function: חיפוש שמות פונקציות
        - class: חיפוש שמות מחלקות
        """
        
        if search_type == "content":
            return self._search_content(
                repo_name, query, file_pattern, case_sensitive, max_results
            )
        elif search_type == "filename":
            return self._search_filename(
                repo_name, query, language, max_results
            )
        elif search_type in ("function", "class"):
            return self._search_metadata(
                repo_name, query, search_type, language, max_results
            )
        else:
            return {"error": "Invalid search type", "results": []}
    
    def _search_content(
        self,
        repo_name: str,
        query: str,
        file_pattern: str,
        case_sensitive: bool,
        max_results: int
    ) -> Dict:
        """חיפוש תוכן עם git grep"""
        return self.git_service.search_with_git_grep(
            repo_name=repo_name,
            query=query,
            max_results=max_results,
            file_pattern=file_pattern,
            case_sensitive=case_sensitive
        )
    
    def _search_filename(
        self,
        repo_name: str,
        query: str,
        language: str,
        max_results: int
    ) -> Dict:
        """חיפוש בשמות קבצים"""
        if not self.db:
            return {"error": "Database not available", "results": []}
        
        # Build MongoDB query
        mongo_query = {"repo_name": repo_name}
        
        if language:
            mongo_query["language"] = language
        
        # Text search or regex
        if query:
            mongo_query["path"] = {"$regex": re.escape(query), "$options": "i"}
        
        try:
            cursor = self.db.repo_files.find(
                mongo_query,
                {"path": 1, "language": 1, "size": 1, "_id": 0}
            ).limit(max_results)
            
            results = []
            for doc in cursor:
                results.append({
                    "path": doc["path"],
                    "language": doc.get("language", "text"),
                    "size": doc.get("size", 0)
                })
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "search_type": "filename"
            }
            
        except Exception as e:
            logger.error(f"Filename search failed: {e}")
            return {"error": str(e), "results": []}
    
    def _search_metadata(
        self,
        repo_name: str,
        query: str,
        search_type: str,
        language: str,
        max_results: int
    ) -> Dict:
        """חיפוש functions/classes ב-MongoDB"""
        if not self.db:
            return {"error": "Database not available", "results": []}
        
        # Build query
        mongo_query = {"repo_name": repo_name}
        
        if language:
            mongo_query["language"] = language
        
        # Search in functions or classes array
        field_name = "functions" if search_type == "function" else "classes"
        mongo_query[field_name] = {"$regex": re.escape(query), "$options": "i"}
        
        try:
            cursor = self.db.repo_files.find(
                mongo_query,
                {"path": 1, "language": 1, field_name: 1, "_id": 0}
            ).limit(max_results)
            
            results = []
            for doc in cursor:
                # Match which functions/classes contain the query
                matching = [
                    name for name in doc.get(field_name, [])
                    if query.lower() in name.lower()
                ]
                
                results.append({
                    "path": doc["path"],
                    "language": doc.get("language", "text"),
                    "matches": matching
                })
            
            return {
                "results": results,
                "total": len(results),
                "query": query,
                "search_type": search_type
            }
            
        except Exception as e:
            logger.error(f"Metadata search failed: {e}")
            return {"error": str(e), "results": []}


def create_search_service(db=None):
    """Factory function"""
    return RepoSearchService(db)
