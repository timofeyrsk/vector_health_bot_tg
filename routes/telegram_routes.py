from flask import Blueprint, request, jsonify
import logging
from services.telegram_service import TelegramService

telegram_bp = Blueprint('telegram', __name__)
logger = logging.getLogger(__name__)

@telegram_bp.route('/webhook', methods=['POST'])
def telegram_webhook():
    """Handle incoming Telegram webhook requests"""
    try:
        update = request.get_json()
        
        if not update:
            logger.error("No JSON data received")
            return jsonify({'error': 'Данные JSON не получены'}), 400
        
        # Process the update with TelegramService
        telegram_service = TelegramService()
        result = telegram_service.process_update(update)
        
        return jsonify({'status': 'ok', 'result': result})
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@telegram_bp.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Set Telegram webhook URL"""
    try:
        data = request.get_json()
        webhook_url = data.get('webhook_url')
        
        if not webhook_url:
            return jsonify({'error': 'webhook_url обязателен'}), 400
        
        telegram_service = TelegramService()
        result = telegram_service.set_webhook(webhook_url)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

