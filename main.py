#!/usr/bin/env python3
"""
Vector-Health AI Nutritionist Bot
Main application entry point
"""

import sys
import os
import logging

from src.app import create_app
from config.settings import Config

def main():
    """Main application entry point"""
    try:
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('vector-health-bot.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting Vector-Health AI Nutritionist Bot")
        
        # Create Flask application
        app = create_app()
        
        # Run the application
        port = int(os.environ.get('PORT', 5000))
        app.run(
            host='0.0.0.0',
            port=port,
            debug=Config.DEBUG
        )
        
    except Exception as e:
        logging.error(f"Failed to start application: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()

