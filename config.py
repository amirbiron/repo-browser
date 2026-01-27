import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """הגדרות פרויקט"""
    
    # Flask
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_ENV', 'production') == 'development'
    
    # MongoDB
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/multi_repo_browser')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', '').strip()
    MONGODB_DEFAULT_DB_NAME = 'multi_repo_browser'
    
    # Git Mirror
    REPO_MIRROR_PATH = os.getenv('REPO_MIRROR_PATH', '/var/data/repos')
    
    # GitHub
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    
    # Timeouts (seconds)
    GIT_CLONE_TIMEOUT = 600
    GIT_FETCH_TIMEOUT = 120
    GIT_COMMAND_TIMEOUT = 30
    
    # Search limits
    MAX_SEARCH_RESULTS = 100
    SEARCH_TIMEOUT = 10
