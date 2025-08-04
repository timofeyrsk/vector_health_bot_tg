from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from config.settings import Config
from database.connection import init_db
from routes.telegram_routes import telegram_bp
from routes.terra_routes import terra_bp
from routes.health_routes import health_bp
from services.scheduler_service import scheduler

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Validate configuration
    Config.validate()
    
    # Enable CORS for all routes
    CORS(app, origins="*")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize database
    init_db()
    
    # Start scheduler for daily reports
    scheduler.start()
    
    # Register blueprints
    app.register_blueprint(telegram_bp, url_prefix='/telegram')
    app.register_blueprint(terra_bp, url_prefix='/terra')
    app.register_blueprint(health_bp, url_prefix='/health')
    
    @app.route('/')
    def index():
        return jsonify({
            'message': 'Vector-Health AI Nutritionist Bot API',
            'status': 'running',
            'version': '1.0.0'
        })
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)

