from flask import Flask, render_template, send_from_directory
import atexit
import logging
import os

from config import Config
from database.db_manager import init_db, close_db
from routes.repo_browser import repo_bp
from routes.repo_selector import selector_bp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app():
    """Application factory"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize database
    with app.app_context():
        try:
            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    # Register blueprints
    app.register_blueprint(repo_bp)
    app.register_blueprint(selector_bp)
    
    # Routes
    @app.route('/')
    def index():
        """Main page"""
        return render_template('repo/index.html')
    
    @app.route('/health')
    def health():
        """Health check endpoint for Render"""
        return {"status": "healthy"}
    
    # Cleanup when the process exits
    atexit.register(close_db)
    
    logger.info("Application created successfully")
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
