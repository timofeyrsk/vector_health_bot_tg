# Routes package
from .telegram_routes import telegram_bp
from .terra_routes import terra_bp
from .health_routes import health_bp

__all__ = ['telegram_bp', 'terra_bp', 'health_bp'] 