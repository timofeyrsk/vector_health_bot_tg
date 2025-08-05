import schedule
import time
import logging
import threading
from datetime import date, datetime, time as datetime_time
from typing import List
import pytz
from sqlalchemy import func
from database.connection import get_db
from services.health_service import HealthService
from services.openai_service import OpenAIService
from services.telegram_service import TelegramService
from models.user_profile import UserProfile

logger = logging.getLogger(__name__)

class SchedulerService:
    def __init__(self):
        """Initialize scheduler service"""
        self.telegram_service = TelegramService()
        self.openai_service = OpenAIService()
        self.is_running = False
        self.scheduler_thread = None
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        
        # Schedule smart checking every minute
        schedule.every().minute.at(":00").do(self.check_and_send_reports)
        
        # Schedule weekly reports on Sunday at 19:00 MSK (7 PM)
        schedule.every().sunday.at("19:00").do(self.send_weekly_reports)
        
        # Start scheduler in a separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduler started successfully")
        logger.info("Smart daily reports checking every minute")
        logger.info("Weekly reports scheduled on Sunday at 19:00 MSK")
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def check_and_send_reports(self):
        """Smart function to check and send daily reports based on user's individual time settings"""
        try:
            # Get current time in Moscow timezone
            moscow_tz = pytz.timezone('Europe/Moscow')
            current_msk_datetime = datetime.now(moscow_tz)
            current_msk_time = current_msk_datetime.time()
            
            logger.debug(f"Checking for daily reports at {current_msk_time.strftime('%H:%M')} MSK")
            
            db = next(get_db())
            health_service = HealthService(db)
            
            # Find users whose daily_report_time matches current MSK time
            users_to_notify = self._get_users_for_daily_report(db, current_msk_time)
            
            if not users_to_notify:
                logger.debug(f"No users found for daily report at {current_msk_time.strftime('%H:%M')} MSK")
                return
            
            logger.info(f"Found {len(users_to_notify)} users for daily report at {current_msk_time.strftime('%H:%M')} MSK")
            
            # Send reports to each user
            success_count = 0
            for user in users_to_notify:
                try:
                    logger.info(f"Sending daily report to user {user.user_id} (chat_id: {user.chat_id})")
                    self._send_daily_report_to_user(user.user_id, health_service)
                    success_count += 1
                    time.sleep(1)  # Small delay between users to avoid rate limits
                except Exception as e:
                    logger.error(f"Error sending daily report to user {user.user_id}: {str(e)}")
                    continue
            
            logger.info(f"Daily reports sent successfully to {success_count}/{len(users_to_notify)} users at {current_msk_time.strftime('%H:%M')} MSK")
            
        except Exception as e:
            logger.error(f"Error in check_and_send_reports: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()
    
    def _send_daily_reports_legacy(self):
        """Legacy function - replaced by check_and_send_reports for individual time settings"""
        try:
            logger.info("Starting legacy daily reports sending...")
            
            db = next(get_db())
            health_service = HealthService(db)
            
            # Get all active users
            active_users = self._get_active_users(db)
            
            if not active_users:
                logger.info("No active users found for daily reports")
                return
            
            logger.info(f"Found {len(active_users)} active users for daily reports")
            
            for user in active_users:
                try:
                    self._send_daily_report_to_user(user.user_id, health_service)
                    time.sleep(1)  # Small delay between users to avoid rate limits
                except Exception as e:
                    logger.error(f"Error sending daily report to user {user.user_id}: {str(e)}")
                    continue
            
            logger.info("Daily reports sending completed")
            
        except Exception as e:
            logger.error(f"Error in send_daily_reports: {str(e)}")
    
    def send_weekly_reports(self):
        """Send weekly reports to all active users"""
        try:
            logger.info("Starting weekly reports sending...")
            
            db = next(get_db())
            health_service = HealthService(db)
            
            # Get all active users
            active_users = self._get_active_users(db)
            
            if not active_users:
                logger.info("No active users found for weekly reports")
                return
            
            logger.info(f"Found {len(active_users)} active users for weekly reports")
            
            for user in active_users:
                try:
                    self._send_weekly_report_to_user(user.user_id, health_service)
                    time.sleep(1)  # Small delay between users to avoid rate limits
                except Exception as e:
                    logger.error(f"Error sending weekly report to user {user.user_id}: {str(e)}")
                    continue
            
            logger.info("Weekly reports sending completed")
            
        except Exception as e:
            logger.error(f"Error in send_weekly_reports: {str(e)}")
    
    def _get_active_users(self, db) -> List[UserProfile]:
        """Get all active users who have completed onboarding"""
        try:
            # Get users who have completed onboarding (all required fields filled)
            users = db.query(UserProfile).filter(
                UserProfile.gender.isnot(None),
                UserProfile.age.isnot(None),
                UserProfile.height_cm.isnot(None),
                UserProfile.current_weight_kg.isnot(None),
                UserProfile.goal.isnot(None),
                UserProfile.target_weight_kg.isnot(None),
                UserProfile.activity_level.isnot(None)
            ).all()
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting active users: {str(e)}")
            return []
    
    def _get_users_for_daily_report(self, db, current_msk_time: datetime_time) -> List[UserProfile]:
        """Get users whose daily_report_time matches current MSK time"""
        try:
            # Find users whose daily_report_time matches current MSK time (hours and minutes)
            # Convert current time to time object for direct comparison with TIME field
            users = db.query(UserProfile).filter(
                UserProfile.daily_report_time.isnot(None),
                UserProfile.gender.isnot(None),
                UserProfile.age.isnot(None),
                UserProfile.height_cm.isnot(None),
                UserProfile.current_weight_kg.isnot(None),
                UserProfile.goal.isnot(None),
                UserProfile.target_weight_kg.isnot(None),
                UserProfile.activity_level.isnot(None),
                UserProfile.daily_report_time == current_msk_time
            ).all()
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users for daily report: {str(e)}")
            return []
    
    def _send_daily_report_to_user(self, user_id: int, health_service: HealthService):
        """Send daily report to specific user"""
        try:
            logger.debug(f"Generating daily report for user {user_id}")
            
            # Get daily summary
            summary_data = health_service.get_daily_summary(user_id, date.today())
            
            if not summary_data:
                logger.warning(f"No summary data available for user {user_id}")
                return
            
            # Generate AI report
            report = self.openai_service.generate_daily_report(summary_data)
            
            if not report:
                logger.error(f"Failed to generate AI report for user {user_id}")
                return
            
            # Get user's chat_id
            chat_id = self._get_user_chat_id(user_id)
            
            if chat_id:
                # Send the report
                message = f"📊 Ежедневный отчет\n\n{report}"
                self.telegram_service.send_ai_message(chat_id, message)
                logger.info(f"Daily report sent successfully to user {user_id} (chat_id: {chat_id})")
            else:
                logger.warning(f"Could not find chat_id for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending daily report to user {user_id}: {str(e)}")
            raise
    
    def _send_weekly_report_to_user(self, user_id: int, health_service: HealthService):
        """Send weekly report to specific user"""
        try:
            # Get weekly summary (you might need to implement this)
            # For now, we'll send a simple weekly message
            chat_id = self._get_user_chat_id(user_id)
            
            if chat_id:
                message = """📈 Еженедельный отчет

Это ваша еженедельная сводка! 

Хотите получить подробный анализ вашего прогресса за неделю? Отправьте команду /summary или задайте мне любой вопрос о вашем питании.

Продолжайте в том же духе! 💪"""
                
                self.telegram_service.send_message(chat_id, message)
                logger.info(f"Weekly report sent to user {user_id}")
            else:
                logger.warning(f"Could not find chat_id for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending weekly report to user {user_id}: {str(e)}")
    
    def _get_user_chat_id(self, user_id: int) -> int:
        """Get user's chat_id from database"""
        try:
            db = next(get_db())
            user_profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
            
            if user_profile and user_profile.chat_id:
                return user_profile.chat_id
            else:
                logger.warning(f"No chat_id found for user {user_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting chat_id for user {user_id}: {str(e)}")
            return None
    
    def send_manual_daily_report(self, user_id: int, chat_id: int):
        """Send daily report manually (for testing or immediate sending)"""
        try:
            logger.info(f"Manual daily report requested for user {user_id}")
            db = next(get_db())
            health_service = HealthService(db)
            
            self._send_daily_report_to_user(user_id, health_service)
            logger.info(f"Manual daily report sent successfully to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending manual daily report: {str(e)}")
            raise
    
    def test_scheduler_logic(self, test_time: str = None):
        """Test the scheduler logic with a specific time (for debugging)"""
        try:
            if test_time:
                # Parse test time (format: "HH:MM")
                hour, minute = map(int, test_time.split(':'))
                test_msk_time = datetime_time(hour, minute)
                logger.info(f"Testing scheduler logic with time: {test_time}")
            else:
                # Use current MSK time
                moscow_tz = pytz.timezone('Europe/Moscow')
                current_msk_datetime = datetime.now(moscow_tz)
                test_msk_time = current_msk_datetime.time()
                logger.info(f"Testing scheduler logic with current MSK time: {test_msk_time.strftime('%H:%M')}")
            
            db = next(get_db())
            
            # Find users for the test time
            users_to_notify = self._get_users_for_daily_report(db, test_msk_time)
            
            logger.info(f"Test results: Found {len(users_to_notify)} users for time {test_msk_time.strftime('%H:%M')}")
            
            for user in users_to_notify:
                logger.info(f"  - User {user.user_id} (chat_id: {user.chat_id}) - daily_report_time: {user.daily_report_time}")
            
            return users_to_notify
            
        except Exception as e:
            logger.error(f"Error in test_scheduler_logic: {str(e)}")
            return []
        finally:
            if 'db' in locals():
                db.close()

# Global scheduler instance
scheduler = SchedulerService() 