import requests
import json
import logging
from typing import Dict, Optional
from config.settings import Config
from database.connection import get_db
from models.user_profile import UserProfile
from models.activity_log import ActivityLog
from datetime import date

logger = logging.getLogger(__name__)

class TerraService:
    def __init__(self):
        """Initialize Terra service with API credentials"""
        self.dev_id = Config.TERRA_DEV_ID
        self.api_key = Config.TERRA_API_KEY
        self.base_url = "https://api.tryterra.co"
        self.headers = {
            'dev-id': self.dev_id,
            'x-api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def generate_auth_url(self, user_id: int) -> str:
        """Generate Terra authentication URL for a user"""
        try:
            endpoint = f"{self.base_url}/v2/auth/generateWidgetSession"
            
            payload = {
                "reference_id": str(user_id),  # Use Telegram user ID as reference
                "providers": ["GARMIN", "FITBIT", "OURA", "WITHINGS"],  # Supported providers
                "auth_success_redirect_url": "https://success.tryterra.co/",
                "auth_failure_redirect_url": "https://failure.tryterra.co/"
            }
            
            response = requests.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            return data.get('url')
            
        except Exception as e:
            logger.error(f"Error generating Terra auth URL: {str(e)}")
            raise
    
    def process_webhook(self, webhook_data: Dict) -> Dict:
        """Process incoming Terra webhook data"""
        try:
            webhook_type = webhook_data.get('type')
            
            if webhook_type == 'auth':
                return self._process_auth_webhook(webhook_data)
            elif webhook_type == 'activity':
                return self._process_activity_webhook(webhook_data)
            elif webhook_type == 'sleep':
                return self._process_sleep_webhook(webhook_data)
            else:
                logger.warning(f"Unknown webhook type: {webhook_type}")
                return {'status': 'ignored', 'reason': f'Unknown webhook type: {webhook_type}'}
                
        except Exception as e:
            logger.error(f"Error processing Terra webhook: {str(e)}")
            raise
    
    def _process_auth_webhook(self, webhook_data: Dict) -> Dict:
        """Process Terra authentication webhook"""
        try:
            user_data = webhook_data.get('user', {})
            terra_user_id = user_data.get('user_id')
            reference_id = user_data.get('reference_id')  # Our Telegram user ID
            
            if not terra_user_id or not reference_id:
                logger.error("Missing user_id or reference_id in auth webhook")
                return {'status': 'error', 'reason': 'Missing required fields'}
            
            # Update user profile with Terra user ID
            db = next(get_db())
            user_profile = db.query(UserProfile).filter(UserProfile.user_id == int(reference_id)).first()
            
            if user_profile:
                user_profile.terra_user_id = terra_user_id
                db.commit()
                logger.info(f"Updated user {reference_id} with Terra user ID: {terra_user_id}")
                return {'status': 'success', 'message': 'User authenticated with Terra'}
            else:
                logger.error(f"User profile not found for reference_id: {reference_id}")
                return {'status': 'error', 'reason': 'User profile not found'}
                
        except Exception as e:
            logger.error(f"Error processing auth webhook: {str(e)}")
            raise
    
    def _process_activity_webhook(self, webhook_data: Dict) -> Dict:
        """Process Terra activity webhook"""
        try:
            user_data = webhook_data.get('user', {})
            terra_user_id = user_data.get('user_id')
            data = webhook_data.get('data', [])
            
            if not terra_user_id or not data:
                logger.error("Missing user_id or data in activity webhook")
                return {'status': 'error', 'reason': 'Missing required fields'}
            
            # Find user by Terra user ID
            db = next(get_db())
            user_profile = db.query(UserProfile).filter(UserProfile.terra_user_id == terra_user_id).first()
            
            if not user_profile:
                logger.error(f"User profile not found for Terra user ID: {terra_user_id}")
                return {'status': 'error', 'reason': 'User profile not found'}
            
            # Process activity data
            processed_count = 0
            for activity_data in data:
                activity_date = activity_data.get('calendar_date')
                if not activity_date:
                    continue
                
                # Parse activity metrics
                active_calories = activity_data.get('active_durations_data', {}).get('active_calories')
                steps = activity_data.get('distance_data', {}).get('steps')
                
                # Create or update activity log
                activity_log = db.query(ActivityLog).filter(
                    ActivityLog.user_id == user_profile.user_id,
                    ActivityLog.date == date.fromisoformat(activity_date)
                ).first()
                
                if not activity_log:
                    activity_log = ActivityLog(
                        user_id=user_profile.user_id,
                        date=date.fromisoformat(activity_date)
                    )
                    db.add(activity_log)
                
                # Update activity data
                if active_calories is not None:
                    activity_log.active_calories = active_calories
                if steps is not None:
                    activity_log.steps = steps
                
                processed_count += 1
            
            db.commit()
            logger.info(f"Processed {processed_count} activity records for user {user_profile.user_id}")
            return {'status': 'success', 'processed_count': processed_count}
            
        except Exception as e:
            logger.error(f"Error processing activity webhook: {str(e)}")
            raise
    
    def _process_sleep_webhook(self, webhook_data: Dict) -> Dict:
        """Process Terra sleep webhook"""
        try:
            user_data = webhook_data.get('user', {})
            terra_user_id = user_data.get('user_id')
            data = webhook_data.get('data', [])
            
            if not terra_user_id or not data:
                logger.error("Missing user_id or data in sleep webhook")
                return {'status': 'error', 'reason': 'Missing required fields'}
            
            # Find user by Terra user ID
            db = next(get_db())
            user_profile = db.query(UserProfile).filter(UserProfile.terra_user_id == terra_user_id).first()
            
            if not user_profile:
                logger.error(f"User profile not found for Terra user ID: {terra_user_id}")
                return {'status': 'error', 'reason': 'User profile not found'}
            
            # Process sleep data
            processed_count = 0
            for sleep_data in data:
                sleep_date = sleep_data.get('calendar_date')
                if not sleep_date:
                    continue
                
                # Parse sleep duration (in seconds, convert to minutes)
                sleep_duration_seconds = sleep_data.get('sleep_durations_data', {}).get('asleep', {}).get('duration_asleep_state_seconds')
                sleep_duration_min = sleep_duration_seconds // 60 if sleep_duration_seconds else None
                
                # Create or update activity log
                activity_log = db.query(ActivityLog).filter(
                    ActivityLog.user_id == user_profile.user_id,
                    ActivityLog.date == date.fromisoformat(sleep_date)
                ).first()
                
                if not activity_log:
                    activity_log = ActivityLog(
                        user_id=user_profile.user_id,
                        date=date.fromisoformat(sleep_date)
                    )
                    db.add(activity_log)
                
                # Update sleep data
                if sleep_duration_min is not None:
                    activity_log.sleep_duration_min = sleep_duration_min
                
                processed_count += 1
            
            db.commit()
            logger.info(f"Processed {processed_count} sleep records for user {user_profile.user_id}")
            return {'status': 'success', 'processed_count': processed_count}
            
        except Exception as e:
            logger.error(f"Error processing sleep webhook: {str(e)}")
            raise
    
    def get_user_data(self, terra_user_id: str, data_type: str = 'activity') -> Optional[Dict]:
        """Get user data from Terra API"""
        try:
            endpoint = f"{self.base_url}/v2/{data_type}"
            params = {
                'user_id': terra_user_id,
                'start_date': '2024-01-01',  # Adjust as needed
                'end_date': date.today().isoformat()
            }
            
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting user data from Terra: {str(e)}")
            return None

