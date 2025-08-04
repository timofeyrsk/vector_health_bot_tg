from flask import Blueprint, request, jsonify
import logging
import hmac
import hashlib
from config.settings import Config
from services.terra_service import TerraService

terra_bp = Blueprint('terra', __name__)
logger = logging.getLogger(__name__)

@terra_bp.route('/webhook', methods=['POST'])
def terra_webhook():
    """Handle incoming Terra API webhook requests"""
    try:
        # Verify webhook signature if secret is configured
        if Config.TERRA_WEBHOOK_SECRET:
            signature = request.headers.get('X-Terra-Signature')
            if not verify_terra_signature(request.data, signature):
                logger.error("Invalid Terra webhook signature")
                return jsonify({'error': 'Неверная подпись'}), 401
        
        data = request.get_json()
        
        if not data:
            logger.error("No JSON data received from Terra")
            return jsonify({'error': 'Данные JSON не получены'}), 400
        
        # Process the webhook data with TerraService
        terra_service = TerraService()
        result = terra_service.process_webhook(data)
        
        return jsonify({'status': 'ok', 'result': result})
        
    except Exception as e:
        logger.error(f"Error processing Terra webhook: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@terra_bp.route('/auth', methods=['POST'])
def terra_auth():
    """Generate Terra authentication URL for user"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'user_id обязателен'}), 400
        
        terra_service = TerraService()
        auth_url = terra_service.generate_auth_url(user_id)
        
        return jsonify({'auth_url': auth_url})
        
    except Exception as e:
        logger.error(f"Error generating Terra auth URL: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

def verify_terra_signature(payload, signature):
    """Verify Terra webhook signature"""
    if not signature or not Config.TERRA_WEBHOOK_SECRET:
        return False
    
    expected_signature = hmac.new(
        Config.TERRA_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

