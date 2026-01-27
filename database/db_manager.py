from pymongo import MongoClient, ASCENDING, TEXT
from pymongo.errors import ConnectionFailure, ConfigurationError
import logging
from config import Config

logger = logging.getLogger(__name__)

_db = None
_client = None


def _select_database(client):
    """בחירת מסד נתונים לחיבור MongoDB"""
    if Config.MONGODB_DB_NAME:
        logger.info(
            "Using MongoDB database name from MONGODB_DB_NAME: %s",
            Config.MONGODB_DB_NAME,
        )
        return client[Config.MONGODB_DB_NAME]

    try:
        return client.get_default_database()
    except ConfigurationError:
        fallback_name = Config.MONGODB_DEFAULT_DB_NAME
        logger.warning(
            "MongoDB URI has no default database; using fallback '%s'. "
            "Set MONGODB_DB_NAME or include a database name in MONGODB_URI.",
            fallback_name,
        )
        return client[fallback_name]


def init_db():
    """אתחול חיבור MongoDB"""
    global _db, _client
    
    try:
        _client = MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        _client.admin.command('ping')
        _db = _select_database(_client)
        
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
    
    # Text index for filename search (avoid clashing with "language" field)
    desired_text_index = {
        "name": "path_text",
        "default_language": "none",
        "language_override": "text_language",
    }
    existing_text_index = None
    index_info = db.repo_files.index_information()
    for name, info in index_info.items():
        if any(key[1] == "text" for key in info.get("key", [])):
            existing_text_index = (name, info)
            break
    
    if existing_text_index:
        name, info = existing_text_index
        current_override = info.get("language_override", "language")
        current_default = info.get("default_language", "english")
        if (
            current_override != desired_text_index["language_override"]
            or current_default != desired_text_index["default_language"]
        ):
            logger.info(
                "Dropping text index '%s' (override=%s, default=%s) to avoid "
                "conflicts with repo file language values.",
                name,
                current_override,
                current_default,
            )
            db.repo_files.drop_index(name)
            existing_text_index = None
    
    if not existing_text_index:
        db.repo_files.create_index(
            [("path", TEXT)],
            name=desired_text_index["name"],
            default_language=desired_text_index["default_language"],
            language_override=desired_text_index["language_override"],
        )
    
    logger.info("Database indexes created")


def close_db():
    """סגירת חיבור DB"""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")
