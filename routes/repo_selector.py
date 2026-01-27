from flask import Blueprint, request, jsonify
from services.repo_manager import RepoManagerService
from services.git_mirror_service import get_mirror_service
from database.db_manager import get_db
import logging

logger = logging.getLogger(__name__)

selector_bp = Blueprint('selector', __name__, url_prefix='/repos')


@selector_bp.route('/', methods=['GET'])
def list_repos():
    """רשימת כל הריפוים"""
    manager = RepoManagerService(get_db(), get_mirror_service())
    return jsonify(manager.list_repos())


@selector_bp.route('/', methods=['POST'])
def add_repo():
    """הוספת ריפו חדש"""
    data = request.json or {}
    url = data.get('url', '')
    name = data.get('name')
    
    if not url:
        return jsonify({"error": "URL is required"}), 400
    
    manager = RepoManagerService(get_db(), get_mirror_service())
    result = manager.add_repo(url, name)
    
    if result["success"]:
        return jsonify(result), 201
    else:
        return jsonify(result), 400


@selector_bp.route('/<name>', methods=['DELETE'])
def remove_repo(name: str):
    """הסרת ריפו"""
    manager = RepoManagerService(get_db(), get_mirror_service())
    result = manager.remove_repo(name)
    return jsonify(result)


@selector_bp.route('/<name>/sync', methods=['POST'])
def sync_repo(name: str):
    """סנכרון ריפו"""
    manager = RepoManagerService(get_db(), get_mirror_service())
    result = manager.sync_repo(name)
    return jsonify(result)


@selector_bp.route('/sync-all', methods=['POST'])
def sync_all():
    """סנכרון כל הריפוים"""
    manager = RepoManagerService(get_db(), get_mirror_service())
    result = manager.sync_all_repos()
    return jsonify(result)


@selector_bp.route('/validate-url', methods=['POST'])
def validate_url():
    """בדיקת תקינות URL"""
    data = request.json or {}
    url = data.get('url', '')
    
    manager = RepoManagerService(get_db(), get_mirror_service())
    is_valid = manager._validate_github_url(url)
    
    return jsonify({
        "valid": is_valid,
        "suggested_name": manager._extract_repo_name(url) if is_valid else None
    })
