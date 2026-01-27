from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import ConnectionFailure
import logging
from config import Config

logger = logging.getLogger(__name__)

_db = None
_client = None


def init_db():
    """אתחול חיבור MongoDB"""
    global _db, _client
    
    try:
        _client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        _client.admin.command('ping')
        _db = _client.get_default_database()
        
        # Create indexes
        create_indexes()
        
        logger.info("MongoDB connected successfully")
        return _db
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        raise


def get_db():
    """קבלת instance של DB"""
    global _db
    if _db is None:
        init_db()
    return _db


def create_indexes():
    """יצירת indexes למסד הנתונים"""
    db = get_db()
    
    # repos collection
    db.repos.create_index([("name", ASCENDING)], unique=True)
    db.repos.create_index([("sync_status", ASCENDING)])
    
    # repo_files collection
    db.repo_files.create_index(
        [("repo_name", ASCENDING), ("path", ASCENDING)], 
        unique=True
    )
    db.repo_files.create_index([("repo_name", ASCENDING), ("language", ASCENDING)])
    db.repo_files.create_index([("repo_name", ASCENDING)])
    
    # Text index for filename search
    db.repo_files.create_index([("path", TEXT)])
    
    logger.info("Database indexes created")


def close_db():
    """סגירת חיבור DB"""
    global _client
    if _client:
        _client.close()
        logger.info("MongoDB connection closed")
