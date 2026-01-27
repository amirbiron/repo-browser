from flask import Blueprint, request, jsonify
from services.git_mirror_service import get_mirror_service
from services.repo_search_service import create_search_service
from services.cross_repo_search import CrossRepoSearchService
from database.db_manager import get_db
import logging

logger = logging.getLogger(__name__)

repo_bp = Blueprint('repo', __name__, url_prefix='/repo')


# ========================================
# Tree API
# ========================================

@repo_bp.route('/api/tree')
def api_tree():
    """
    API לקבלת עץ הקבצים
    
    Query params:
        repo: שם הריפו (חובה ב-multi-repo mode)
        path: נתיב לתיקייה ספציפית
        types: סינון לפי סוגי קבצים
    """
    db = get_db()
    repo_name = request.args.get('repo', '')
    path = request.args.get('path', '')
    types_param = request.args.get('types', '').strip()
    
    if not repo_name:
        # Multi-repo mode: return list of repos as root
        repos = list(db.repos.find({}, {"name": 1, "url": 1, "sync_status": 1, "_id": 0}))
        return jsonify([
            {
                "name": r["name"],
                "path": r["name"],
                "type": "directory",
                "is_repo_root": True,
                "sync_status": r.get("sync_status", "unknown")
            }
            for r in repos
        ])
    
    # Get files from repo
    git_service = get_mirror_service()
    files = git_service.list_all_files(repo_name)
    
    if files is None:
        return jsonify({"error": "Failed to list files"}), 500
    
    # Build tree structure
    tree = []
    
    # Filter by path prefix if specified
    if path:
        files = [f for f in files if f.startswith(path.rstrip('/') + '/')]
    
    # Filter by file types
    if types_param:
        allowed_types = set(types_param.split(','))
        files = [f for f in files if any(f.endswith('.' + t) for t in allowed_types)]
    
    # Build simple tree (flat list with type detection)
    for file_path in files:
        tree.append({
            "name": file_path.split('/')[-1],
            "path": file_path,
            "type": "file"
        })
    
    return jsonify(tree)


# ========================================
# File API
# ========================================

@repo_bp.route('/api/file/<repo_name>/<path:file_path>')
def api_get_file(repo_name: str, file_path: str):
    """API לקבלת תוכן קובץ"""
    git_service = get_mirror_service()
    db = get_db()
    
    # Get content
    content = git_service.get_file_content(repo_name, file_path)
    if content is None:
        return jsonify({"error": "File not found"}), 404
    
    # Get metadata
    metadata = db.repo_files.find_one({
        "repo_name": repo_name,
        "path": file_path
    })
    
    return jsonify({
        "repo": repo_name,
        "path": file_path,
        "content": content,
        "language": metadata.get("language", "text") if metadata else "text",
        "size": len(content),
        "lines": content.count("\n") + 1
    })


# ========================================
# Search API
# ========================================

@repo_bp.route('/api/search')
def api_search():
    """
    API לחיפוש
    
    Query params:
        q: מילת החיפוש
        type: סוג החיפוש (content, filename, function, class)
        repo: שם ריפו ספציפי (ריק = כל הריפוים)
        pattern: סינון קבצים (*.py)
        language: סינון לפי שפה
    """
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'content')
    repo_name = request.args.get('repo', '')
    file_pattern = request.args.get('pattern', '')
    language = request.args.get('language', '')
    
    if not query or len(query) < 2:
        return jsonify({"error": "Query too short", "results": []})
    
    db = get_db()
    
    if repo_name:
        # Single repo search
        search_service = create_search_service(db)
        return jsonify(search_service.search(
            repo_name=repo_name,
            query=query,
            search_type=search_type,
            file_pattern=file_pattern or None,
            language=language or None
        ))
    else:
        # Cross-repo search
        cross_search = CrossRepoSearchService(db, get_mirror_service())
        return jsonify(cross_search.search_all_repos(
            query=query,
            search_type=search_type,
            file_pattern=file_pattern or None,
            language=language or None
        ))


# ========================================
# History API
# ========================================

@repo_bp.route('/api/history')
def api_history():
    """
    היסטוריית קובץ
    
    Query params:
        repo: שם הריפו
        file: נתיב הקובץ
        limit: מספר commits
        skip: offset
    """
    repo_name = request.args.get('repo', '')
    file_path = request.args.get('file', '')
    limit = request.args.get('limit', 20, type=int)
    skip = request.args.get('skip', 0, type=int)
    
    if not repo_name or not file_path:
        return jsonify({"error": "Missing repo or file parameter"}), 400
    
    git_service = get_mirror_service()
    return jsonify(git_service.get_file_history(
        repo_name=repo_name,
        file_path=file_path,
        limit=limit,
        skip=skip
    ))


@repo_bp.route('/api/file-at-commit/<repo_name>/<commit>')
def api_file_at_commit(repo_name: str, commit: str):
    """תוכן קובץ ב-commit ספציפי"""
    file_path = request.args.get('file', '')
    
    if not file_path:
        return jsonify({"error": "Missing file parameter"}), 400
    
    git_service = get_mirror_service()
    return jsonify(git_service.get_file_at_commit(
        repo_name=repo_name,
        file_path=file_path,
        commit=commit
    ))


@repo_bp.route('/api/diff/<repo_name>/<commit1>/<commit2>')
def api_diff(repo_name: str, commit1: str, commit2: str):
    """Diff בין commits"""
    file_path = request.args.get('file')
    context = request.args.get('context', 3, type=int)
    
    git_service = get_mirror_service()
    return jsonify(git_service.get_diff(
        repo_name=repo_name,
        commit1=commit1,
        commit2=commit2,
        file_path=file_path,
        context_lines=context
    ))


@repo_bp.route('/api/search-history')
def api_search_history():
    """חיפוש בהיסטוריה"""
    repo_name = request.args.get('repo', '')
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'message')  # message or code
    file_path = request.args.get('file')
    limit = request.args.get('limit', 20, type=int)
    
    if not repo_name or not query:
        return jsonify({"error": "Missing repo or query"}), 400
    
    git_service = get_mirror_service()
    return jsonify(git_service.search_history(
        repo_name=repo_name,
        query=query,
        search_type=search_type,
        file_path=file_path,
        limit=limit
    ))


@repo_bp.route('/api/commit/<repo_name>/<commit>')
def api_commit_info(repo_name: str, commit: str):
    """מידע על commit"""
    git_service = get_mirror_service()
    return jsonify(git_service.get_commit_info(repo_name, commit))
