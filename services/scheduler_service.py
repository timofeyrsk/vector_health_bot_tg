import schedule
import time
import logging
import threading
from datetime import date, datetime
from typing import List
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
        
        # Schedule daily reports at 20:00 (8 PM)
        schedule.every().day.at("20:00").do(self.send_daily_reports)
        
        # Schedule weekly reports on Sunday at 19:00 (7 PM)
        schedule.every().sunday.at("19:00").do(self.send_weekly_reports)
        
        # Start scheduler in a separate thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Scheduler started successfully")
        logger.info("Daily reports scheduled at 20:00")
        logger.info("Weekly reports scheduled on Sunday at 19:00")
    
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
    
    def send_daily_reports(self):
        """Send daily reports to all active users"""
        try:
            logger.info("Starting daily reports sending...")
            
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
    
    def _send_daily_report_to_user(self, user_id: int, health_service: HealthService):
        """Send daily report to specific user"""
        try:
            # Get daily summary
            summary_data = health_service.get_daily_summary(user_id, date.today())
            
            # Generate AI report
            report = self.openai_service.generate_daily_report(summary_data)
            
            # Get user's chat_id (you might need to store this in user profile)
            # For now, we'll need to get it from the database or store it
            chat_id = self._get_user_chat_id(user_id)
            
            if chat_id:
                # Send the report
                message = f"📊 Ежедневный отчет\n\n{report}"
                self.telegram_service.send_ai_message(chat_id, message)
                logger.info(f"Daily report sent to user {user_id}")
            else:
                logger.warning(f"Could not find chat_id for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error sending daily report to user {user_id}: {str(e)}")
    
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
            db = next(get_db())
            health_service = HealthService(db)
            
            self._send_daily_report_to_user(user_id, health_service)
            
        except Exception as e:
            logger.error(f"Error sending manual daily report: {str(e)}")
            raise

# Global scheduler instance
scheduler = SchedulerService() 