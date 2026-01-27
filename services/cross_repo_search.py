from typing import List, Dict
import logging
from services.git_mirror_service import GitMirrorService
from services.repo_search_service import RepoSearchService

logger = logging.getLogger(__name__)


class CrossRepoSearchService:
    """
    חיפוש גלובלי בכל הריפוים
    """
    
    def __init__(self, db, git_service: GitMirrorService):
        self.db = db
        self.git_service = git_service
        self.repo_search = RepoSearchService(db)
    
    def search_all_repos(
        self,
        query: str,
        search_type: str = "content",
        repos: List[str] = None,  # None = all repos
        file_pattern: str = None,
        language: str = None,
        max_results_per_repo: int = 20,
        total_max_results: int = 100
    ) -> Dict:
        """
        חיפוש בכל הריפוים
        
        Returns:
            {
                "results": [
                    {"repo": "repo1", "path": "...", "line": 10, "content": "..."},
                    ...
                ],
                "by_repo": {
                    "repo1": {"count": 5, "results": [...]},
                    "repo2": {"count": 3, "results": [...]}
                },
                "total": 8,
                "query": "...",
                "truncated": False
            }
        """
        
        # Get list of repos to search
        if repos is None:
            repo_list = [r["name"] for r in self.db.repos.find({}, {"name": 1})]
        else:
            repo_list = repos
        
        all_results = []
        by_repo = {}
        
        for repo_name in repo_list:
            if len(all_results) >= total_max_results:
                break
            
            result = self.repo_search.search(
                repo_name=repo_name,
                query=query,
                search_type=search_type,
                file_pattern=file_pattern,
                language=language,
                max_results=max_results_per_repo
            )
            
            if result.get("error"):
                logger.warning(f"Search failed for {repo_name}: {result['error']}")
                continue
            
            repo_results = result.get("results", [])
            
            # Add repo name to each result
            for r in repo_results:
                r["repo"] = repo_name
            
            by_repo[repo_name] = {
                "count": len(repo_results),
                "results": repo_results
            }
            
            all_results.extend(repo_results)
        
        # Truncate if needed
        truncated = len(all_results) > total_max_results
        all_results = all_results[:total_max_results]
        
        return {
            "results": all_results,
            "by_repo": by_repo,
            "total": len(all_results),
            "query": query,
            "search_type": search_type,
            "truncated": truncated
        }
