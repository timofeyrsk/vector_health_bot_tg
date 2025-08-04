from flask import Blueprint, request, jsonify
import logging
from services.health_service import HealthService
from database.connection import get_db

health_bp = Blueprint('health', __name__)
logger = logging.getLogger(__name__)

@health_bp.route('/profile/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    """Get user profile by user ID"""
    try:
        db = next(get_db())
        health_service = HealthService(db)
        profile = health_service.get_user_profile(user_id)
        
        if not profile:
            return jsonify({'error': 'Профиль пользователя не найден'}), 404
        
        return jsonify({
            'user_id': profile.user_id,
            'gender': profile.gender,
            'age': profile.age,
            'height_cm': profile.height_cm,
            'current_weight_kg': float(profile.current_weight_kg) if profile.current_weight_kg else None,
            'target_weight_kg': float(profile.target_weight_kg) if profile.target_weight_kg else None,
            'goal': profile.goal,
            'activity_level': profile.activity_level,
            'bmr': float(profile.bmr) if profile.bmr else None,
            'tdee': float(profile.tdee) if profile.tdee else None,
            'daily_calorie_target': profile.daily_calorie_target,
            'daily_protein_target_g': float(profile.daily_protein_target_g) if profile.daily_protein_target_g else None,
            'daily_fat_target_g': float(profile.daily_fat_target_g) if profile.daily_fat_target_g else None,
            'daily_carbs_target_g': float(profile.daily_carbs_target_g) if profile.daily_carbs_target_g else None
        })
        
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@health_bp.route('/food_logs/<int:user_id>', methods=['GET'])
def get_food_logs(user_id):
    """Get food logs for a user"""
    try:
        db = next(get_db())
        health_service = HealthService(db)
        
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        food_logs = health_service.get_food_logs(user_id, limit=limit, offset=offset)
        
        return jsonify({
            'food_logs': [
                {
                    'log_id': str(log.log_id),
                    'created_at': log.created_at.isoformat(),
                    'description': log.description,
                    'dish_name': log.dish_name,
                    'calories': log.calories,
                    'protein_g': float(log.protein_g) if log.protein_g else None,
                    'fat_g': float(log.fat_g) if log.fat_g else None,
                    'carbs_g': float(log.carbs_g) if log.carbs_g else None,
                    'log_type': log.log_type
                }
                for log in food_logs
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting food logs: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@health_bp.route('/activity_logs/<int:user_id>', methods=['GET'])
def get_activity_logs(user_id):
    """Get activity logs for a user"""
    try:
        db = next(get_db())
        health_service = HealthService(db)
        
        # Get query parameters
        limit = request.args.get('limit', 30, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        activity_logs = health_service.get_activity_logs(user_id, limit=limit, offset=offset)
        
        return jsonify({
            'activity_logs': [
                {
                    'log_id': str(log.log_id),
                    'date': log.date.isoformat(),
                    'active_calories': log.active_calories,
                    'steps': log.steps,
                    'sleep_duration_min': log.sleep_duration_min
                }
                for log in activity_logs
            ]
        })
        
    except Exception as e:
        logger.error(f"Error getting activity logs: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

@health_bp.route('/daily_summary/<int:user_id>', methods=['GET'])
def get_daily_summary(user_id):
    """Get daily summary for a user"""
    try:
        from datetime import date
        
        db = next(get_db())
        health_service = HealthService(db)
        
        # Get date parameter or use today
        date_str = request.args.get('date')
        target_date = date.fromisoformat(date_str) if date_str else date.today()
        
        summary = health_service.get_daily_summary(user_id, target_date)
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error getting daily summary: {str(e)}")
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500

