import logging
from typing import Dict, List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from models.user_profile import UserProfile
from models.food_log import FoodLog
from models.activity_log import ActivityLog
from services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class HealthService:
    def __init__(self, db: Session):
        """Initialize health service with database session"""
        self.db = db
        self.openai_service = OpenAIService()
    
    def create_user_profile(self, user_id: int, chat_id: int = None) -> UserProfile:
        """Create a new user profile"""
        try:
            user_profile = UserProfile(user_id=user_id, chat_id=chat_id)
            self.db.add(user_profile)
            self.db.commit()
            self.db.refresh(user_profile)
            
            logger.info(f"Created user profile for user {user_id} with chat_id {chat_id}")
            return user_profile
            
        except Exception as e:
            logger.error(f"Error creating user profile: {str(e)}")
            self.db.rollback()
            raise
    
    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """Get user profile by user ID"""
        try:
            return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        except Exception as e:
            logger.error(f"Error getting user profile: {str(e)}")
            return None
    
    def update_user_profile(self, user_id: int, updates: Dict) -> bool:
        """Update user profile with given data"""
        try:
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                return False
            
            for key, value in updates.items():
                if hasattr(user_profile, key):
                    setattr(user_profile, key, value)
            
            self.db.commit()
            logger.info(f"Updated user profile for user {user_id}: {updates}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user profile: {str(e)}")
            self.db.rollback()
            return False
    
    def calculate_user_targets(self, user_id: int) -> bool:
        """Calculate BMR, TDEE, and daily targets for user"""
        try:
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                return False
            
            # Calculate BMR using Mifflin-St Jeor Equation
            if user_profile.gender == 'male':
                bmr = (10 * float(user_profile.current_weight_kg) + 
                      6.25 * user_profile.height_cm - 
                      5 * user_profile.age + 5)
            else:  # female
                bmr = (10 * float(user_profile.current_weight_kg) + 
                      6.25 * user_profile.height_cm - 
                      5 * user_profile.age - 161)
            
            # Calculate TDEE based on activity level
            activity_multipliers = {
                'sedentary': 1.2,
                'moderate': 1.55,
                'active': 1.725
            }
            
            tdee = bmr * activity_multipliers.get(user_profile.activity_level, 1.2)
            
            # Adjust calories based on goal
            if user_profile.goal == 'lose_weight':
                daily_calories = int(tdee - 500)  # 500 calorie deficit
            elif user_profile.goal == 'gain_weight':
                daily_calories = int(tdee + 500)  # 500 calorie surplus
            else:  # maintain_weight
                daily_calories = int(tdee)
            
            # Calculate macronutrient targets
            # Protein: 1.6-2.2g per kg body weight (use 1.8g)
            protein_target = float(user_profile.current_weight_kg) * 1.8
            
            # Fat: 20-35% of calories (use 25%)
            fat_calories = daily_calories * 0.25
            fat_target = fat_calories / 9  # 9 calories per gram of fat
            
            # Carbs: remaining calories
            protein_calories = protein_target * 4  # 4 calories per gram of protein
            carb_calories = daily_calories - protein_calories - fat_calories
            carb_target = carb_calories / 4  # 4 calories per gram of carbs
            
            # Update user profile
            updates = {
                'bmr': round(bmr, 2),
                'tdee': round(tdee, 2),
                'daily_calorie_target': daily_calories,
                'daily_protein_target_g': round(protein_target, 2),
                'daily_fat_target_g': round(fat_target, 2),
                'daily_carbs_target_g': round(carb_target, 2)
            }
            
            return self.update_user_profile(user_id, updates)
            
        except Exception as e:
            logger.error(f"Error calculating user targets: {str(e)}")
            return False
    
    def log_food_from_photo(self, user_id: int, food_data: Dict, photo_url: str) -> FoodLog:
        """Log food from photo analysis"""
        try:
            # Generate embedding for the food
            embedding_text = f"{food_data['dish_name']} {food_data['estimated_ingredients']}"
            embedding = self.openai_service.generate_embedding(embedding_text)
            
            food_log = FoodLog(
                user_id=user_id,
                description=f"Photo: {food_data['dish_name']}",
                dish_name=food_data['dish_name'],
                estimated_ingredients=food_data['estimated_ingredients'],
                estimated_weight_g=food_data['estimated_weight_g'],
                calories=food_data['calories'],
                protein_g=food_data['protein_g'],
                fat_g=food_data['fat_g'],
                carbs_g=food_data['carbs_g'],
                food_embedding_vector=str(embedding),  # Store as string for now
                log_type='photo',
                photo_url=photo_url
            )
            
            self.db.add(food_log)
            self.db.commit()
            self.db.refresh(food_log)
            
            logger.info(f"Logged food from photo for user {user_id}: {food_data['dish_name']}")
            return food_log
            
        except Exception as e:
            logger.error(f"Error logging food from photo: {str(e)}")
            self.db.rollback()
            raise
    
    def log_food_from_text(self, user_id: int, description: str, food_data: Dict) -> FoodLog:
        """Log food from text description"""
        try:
            # Generate embedding for the food
            embedding_text = f"{food_data['dish_name']} {food_data['estimated_ingredients']}"
            embedding = self.openai_service.generate_embedding(embedding_text)
            
            food_log = FoodLog(
                user_id=user_id,
                description=description,
                dish_name=food_data['dish_name'],
                estimated_ingredients=food_data['estimated_ingredients'],
                estimated_weight_g=food_data['estimated_weight_g'],
                calories=food_data['calories'],
                protein_g=food_data['protein_g'],
                fat_g=food_data['fat_g'],
                carbs_g=food_data['carbs_g'],
                food_embedding_vector=str(embedding),  # Store as string for now
                log_type='text'
            )
            
            self.db.add(food_log)
            self.db.commit()
            self.db.refresh(food_log)
            
            logger.info(f"Logged food from text for user {user_id}: {food_data['dish_name']}")
            return food_log
            
        except Exception as e:
            logger.error(f"Error logging food from text: {str(e)}")
            self.db.rollback()
            raise
    
    def get_food_logs(self, user_id: int, limit: int = 50, offset: int = 0) -> List[FoodLog]:
        """Get food logs for a user"""
        try:
            return (self.db.query(FoodLog)
                   .filter(FoodLog.user_id == user_id)
                   .order_by(FoodLog.created_at.desc())
                   .limit(limit)
                   .offset(offset)
                   .all())
        except Exception as e:
            logger.error(f"Error getting food logs: {str(e)}")
            return []
    
    def get_activity_logs(self, user_id: int, limit: int = 30, offset: int = 0) -> List[ActivityLog]:
        """Get activity logs for a user"""
        try:
            return (self.db.query(ActivityLog)
                   .filter(ActivityLog.user_id == user_id)
                   .order_by(ActivityLog.date.desc())
                   .limit(limit)
                   .offset(offset)
                   .all())
        except Exception as e:
            logger.error(f"Error getting activity logs: {str(e)}")
            return []
    
    def get_daily_summary(self, user_id: int, target_date: date) -> Dict:
        """Get daily summary for a user"""
        try:
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                return {}
            
            # Get food logs for the day
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            food_logs = (self.db.query(FoodLog)
                        .filter(FoodLog.user_id == user_id)
                        .filter(FoodLog.created_at >= start_datetime)
                        .filter(FoodLog.created_at <= end_datetime)
                        .all())
            
            # Calculate totals
            total_calories = sum(log.calories or 0 for log in food_logs)
            total_protein = sum(float(log.protein_g or 0) for log in food_logs)
            total_fat = sum(float(log.fat_g or 0) for log in food_logs)
            total_carbs = sum(float(log.carbs_g or 0) for log in food_logs)
            
            # Get activity log for the day
            activity_log = (self.db.query(ActivityLog)
                           .filter(ActivityLog.user_id == user_id)
                           .filter(ActivityLog.date == target_date)
                           .first())
            
            # Calculate calories out
            base_calories_out = float(user_profile.tdee or 0)
            active_calories = activity_log.active_calories if activity_log else 0
            total_calories_out = base_calories_out + (active_calories or 0)
            
            return {
                'date': target_date.isoformat(),
                'goal': user_profile.goal,
                'daily_calorie_target': user_profile.daily_calorie_target,
                'daily_protein_target_g': float(user_profile.daily_protein_target_g or 0),
                'daily_fat_target_g': float(user_profile.daily_fat_target_g or 0),
                'daily_carbs_target_g': float(user_profile.daily_carbs_target_g or 0),
                'calories_consumed': total_calories,
                'protein_consumed': total_protein,
                'fat_consumed': total_fat,
                'carbs_consumed': total_carbs,
                'calories_out': total_calories_out,
                'active_calories': active_calories,
                'steps': activity_log.steps if activity_log else None,
                'sleep_duration_min': activity_log.sleep_duration_min if activity_log else None,
                'calorie_balance': total_calories - total_calories_out,
                'total_entries': len(food_logs),
                'total_calories': total_calories,
                'total_protein': total_protein,
                'total_fat': total_fat,
                'total_carbs': total_carbs
            }
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {str(e)}")
            return {}
    
    def search_similar_foods(self, query: str, user_id: int, limit: int = 10) -> List[FoodLog]:
        """Search for similar foods using vector similarity (simplified version)"""
        try:
            # Generate embedding for the query
            query_embedding = self.openai_service.generate_embedding(query)
            
            # For now, return recent food logs (vector search would require pgvector setup)
            # In production, this would use vector similarity search
            food_logs = (self.db.query(FoodLog)
                        .filter(FoodLog.user_id == user_id)
                        .filter(FoodLog.dish_name.ilike(f'%{query}%'))
                        .order_by(FoodLog.created_at.desc())
                        .limit(limit)
                        .all())
            
            return food_logs
            
        except Exception as e:
            logger.error(f"Error searching similar foods: {str(e)}")
            return []

    def get_food_logs_for_date(self, user_id: int, target_date: date) -> List[FoodLog]:
        """Get food logs for a specific date"""
        try:
            start_datetime = datetime.combine(target_date, datetime.min.time())
            end_datetime = datetime.combine(target_date, datetime.max.time())
            
            return (self.db.query(FoodLog)
                   .filter(FoodLog.user_id == user_id)
                   .filter(FoodLog.created_at >= start_datetime)
                   .filter(FoodLog.created_at <= end_datetime)
                   .order_by(FoodLog.created_at.desc())
                   .all())
        except Exception as e:
            logger.error(f"Error getting food logs for date: {str(e)}")
            return []

    def get_food_log_by_id(self, log_id: str) -> Optional[FoodLog]:
        """Get food log by ID"""
        try:
            return self.db.query(FoodLog).filter(FoodLog.log_id == log_id).first()
        except Exception as e:
            logger.error(f"Error getting food log by ID: {str(e)}")
            return None

    def update_food_log(self, log_id: str, updates: Dict) -> bool:
        """Update food log with given data"""
        try:
            food_log = self.get_food_log_by_id(log_id)
            if not food_log:
                return False
            
            # Check if weight is being updated and we need to recalculate nutrition
            if 'estimated_weight_g' in updates and food_log.estimated_weight_g:
                old_weight = float(food_log.estimated_weight_g)
                new_weight = float(updates['estimated_weight_g'])
                
                # Calculate ratio for proportional recalculation
                if old_weight > 0:
                    ratio = new_weight / old_weight
                    
                    # Recalculate nutrition values proportionally
                    # Convert to appropriate types for database storage
                    updates['calories'] = int(round(float(food_log.calories) * ratio))
                    updates['protein_g'] = round(float(food_log.protein_g) * ratio, 2)
                    updates['fat_g'] = round(float(food_log.fat_g) * ratio, 2)
                    updates['carbs_g'] = round(float(food_log.carbs_g) * ratio, 2)
                    
                    logger.info(f"Recalculated nutrition for food log {log_id}: weight {old_weight}g -> {new_weight}g, ratio {ratio:.3f}")
            
            for key, value in updates.items():
                if hasattr(food_log, key):
                    setattr(food_log, key, value)
            
            self.db.commit()
            logger.info(f"Updated food log {log_id}: {updates}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating food log: {str(e)}")
            self.db.rollback()
            return False

    def recalculate_food_nutrition(self, log_id: str, new_weight_g: float) -> bool:
        """Recalculate nutrition values for a food log based on new weight"""
        try:
            food_log = self.get_food_log_by_id(log_id)
            if not food_log or not food_log.estimated_weight_g:
                return False
            
            old_weight = float(food_log.estimated_weight_g)
            ratio = new_weight_g / old_weight
            
            # Update nutrition values proportionally with proper type conversion
            updates = {
                'estimated_weight_g': new_weight_g,
                'calories': int(round(float(food_log.calories) * ratio)),
                'protein_g': round(float(food_log.protein_g) * ratio, 2),
                'fat_g': round(float(food_log.fat_g) * ratio, 2),
                'carbs_g': round(float(food_log.carbs_g) * ratio, 2)
            }
            
            return self.update_food_log(log_id, updates)
            
        except Exception as e:
            logger.error(f"Error recalculating food nutrition: {str(e)}")
            return False

    def delete_food_log(self, log_id: str) -> bool:
        """Delete food log by ID"""
        try:
            food_log = self.get_food_log_by_id(log_id)
            if not food_log:
                return False
            
            self.db.delete(food_log)
            self.db.commit()
            logger.info(f"Deleted food log {log_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting food log: {str(e)}")
            self.db.rollback()
            return False

    def generate_report(self, user_id: int, period: str) -> Dict:
        """
        Generate universal report for different periods (daily, weekly)
        
        Args:
            user_id: User ID
            period: 'daily' or 'weekly'
            
        Returns:
            Dictionary with report data
        """
        try:
            from datetime import date, timedelta
            import calendar
            
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                return {}
            
            # Calculate date range based on period
            today = date.today()
            
            if period == 'daily':
                start_date = today
                end_date = today
                period_days = 1
            elif period == 'weekly':
                # Get last Monday (or today if it's Monday)
                days_since_monday = today.weekday()
                start_date = today - timedelta(days=days_since_monday)
                end_date = today
                period_days = (end_date - start_date).days + 1
            else:
                raise ValueError(f"Invalid period: {period}. Only 'daily' and 'weekly' are supported.")
            
            # Get food logs for the period
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            food_logs = (self.db.query(FoodLog)
                        .filter(FoodLog.user_id == user_id)
                        .filter(FoodLog.created_at >= start_datetime)
                        .filter(FoodLog.created_at <= end_datetime)
                        .all())
            
            # Calculate totals
            total_calories = sum(log.calories or 0 for log in food_logs)
            total_protein = sum(float(log.protein_g or 0) for log in food_logs)
            total_fat = sum(float(log.fat_g or 0) for log in food_logs)
            total_carbs = sum(float(log.carbs_g or 0) for log in food_logs)
            
            # Get activity logs for the period
            activity_logs = (self.db.query(ActivityLog)
                           .filter(ActivityLog.user_id == user_id)
                           .filter(ActivityLog.date >= start_date)
                           .filter(ActivityLog.date <= end_date)
                           .all())
            
            # Calculate activity totals
            total_steps = sum(log.steps or 0 for log in activity_logs)
            total_active_calories = sum(log.active_calories or 0 for log in activity_logs)
            total_sleep_minutes = sum(log.sleep_duration_min or 0 for log in activity_logs)
            
            # Calculate averages
            avg_steps_per_day = total_steps / period_days if period_days > 0 else 0
            avg_sleep_hours = (total_sleep_minutes / 60) / period_days if period_days > 0 else 0
            
            # Calculate calories out (base TDEE + active calories)
            base_calories_out = float(user_profile.tdee or 0) * period_days
            total_calories_out = base_calories_out + total_active_calories
            
            # Calculate period targets (daily targets * number of days)
            period_calorie_target = user_profile.daily_calorie_target * period_days if user_profile.daily_calorie_target else 0
            period_protein_target = float(user_profile.daily_protein_target_g or 0) * period_days
            period_fat_target = float(user_profile.daily_fat_target_g or 0) * period_days
            period_carbs_target = float(user_profile.daily_carbs_target_g or 0) * period_days
            
            # Calculate remaining targets for daily reports only
            if period == 'daily':
                remaining_days = 1
                # Calculate actual remaining (can be negative for surplus)
                remaining_calories = period_calorie_target - total_calories
                remaining_protein = period_protein_target - total_protein
                remaining_fat = period_fat_target - total_fat
                remaining_carbs = period_carbs_target - total_carbs
                
                # Calculate average daily targets for remaining days (use max(0, ...) for recommendations)
                avg_daily_calories_remaining = max(0, remaining_calories) / remaining_days if remaining_days > 0 else 0
                avg_daily_protein_remaining = max(0, remaining_protein) / remaining_days if remaining_days > 0 else 0
                avg_daily_fat_remaining = max(0, remaining_fat) / remaining_days if remaining_days > 0 else 0
                avg_daily_carbs_remaining = max(0, remaining_carbs) / remaining_days if remaining_days > 0 else 0
            else:
                # For weekly reports, don't calculate remaining days recommendations
                remaining_days = 0
                remaining_calories = 0
                remaining_protein = 0
                remaining_fat = 0
                remaining_carbs = 0
                avg_daily_calories_remaining = 0
                avg_daily_protein_remaining = 0
                avg_daily_fat_remaining = 0
                avg_daily_carbs_remaining = 0
            
            # Prepare list of eaten foods for daily reports
            eaten_foods = []
            if period == 'daily':
                for log in food_logs:
                    food_info = {
                        'dish_name': log.dish_name or log.description,
                        'weight_g': float(log.estimated_weight_g or 0),
                        'calories': log.calories or 0
                    }
                    eaten_foods.append(food_info)
            
            return {
                'period': period,
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period_days': period_days,
                'remaining_days': remaining_days,
                'goal': user_profile.goal,
                'daily_calorie_target': user_profile.daily_calorie_target,
                'daily_protein_target_g': float(user_profile.daily_protein_target_g or 0),
                'daily_fat_target_g': float(user_profile.daily_fat_target_g or 0),
                'daily_carbs_target_g': float(user_profile.daily_carbs_target_g or 0),
                'period_calorie_target': period_calorie_target,
                'period_protein_target': period_protein_target,
                'period_fat_target': period_fat_target,
                'period_carbs_target': period_carbs_target,
                'calories_consumed': total_calories,
                'protein_consumed': total_protein,
                'fat_consumed': total_fat,
                'carbs_consumed': total_carbs,
                'calories_out': total_calories_out,
                'active_calories': total_active_calories,
                'steps': total_steps,
                'avg_steps_per_day': avg_steps_per_day,
                'sleep_duration_min': total_sleep_minutes,
                'avg_sleep_hours': avg_sleep_hours,
                'calorie_balance': total_calories - total_calories_out,
                'total_entries': len(food_logs),
                'total_calories': total_calories,
                'total_protein': total_protein,
                'total_fat': total_fat,
                'total_carbs': total_carbs,
                # Additional fields for better recommendations
                'remaining_calories': remaining_calories,
                'remaining_protein': remaining_protein,
                'remaining_fat': remaining_fat,
                'remaining_carbs': remaining_carbs,
                'avg_daily_calories_remaining': avg_daily_calories_remaining,
                'avg_daily_protein_remaining': avg_daily_protein_remaining,
                'avg_daily_fat_remaining': avg_daily_fat_remaining,
                'avg_daily_carbs_remaining': avg_daily_carbs_remaining,
                # List of eaten foods for daily reports
                'eaten_foods': eaten_foods
            }
            
        except Exception as e:
            logger.error(f"Error generating {period} report: {str(e)}")
            return {}
    
    def get_user_context_for_llm(self, user_id: int, question: str) -> Dict:
        """
        Get comprehensive user context for LLM analysis based on question content
        
        Args:
            user_id: User ID
            question: User's question text for context analysis
            
        Returns:
            Dictionary with user profile, history, and today's summary
        """
        try:
            from datetime import date, timedelta
            import re
            
            # Get user profile
            user_profile = self.get_user_profile(user_id)
            if not user_profile:
                return {}
            
            # Analyze question for time period keywords
            question_lower = question.lower()
            
            # Define time period patterns
            time_patterns = {
                'yesterday': ['вчера', 'вчерашний', 'вчерашняя', 'вчерашнее'],
                'today': ['сегодня', 'сегодняшний', 'сегодняшняя', 'сегодняшнее'],
                'week': ['неделя', 'неделю', 'недели', 'за неделю', 'на неделе', 'прошлая неделя'],
                'month': ['месяц', 'месяца', 'за месяц', 'в этом месяце', 'прошлый месяц'],
                'recent': ['недавно', 'последние', 'за последние', 'недавний']
            }
            
            # Determine time period from question
            target_period = 'today'  # default
            for period, keywords in time_patterns.items():
                if any(keyword in question_lower for keyword in keywords):
                    target_period = period
                    break
            
            # Calculate date range based on period
            today = date.today()
            
            if target_period == 'yesterday':
                start_date = today - timedelta(days=1)
                end_date = today - timedelta(days=1)
                period_description = "Вчерашний день"
            elif target_period == 'today':
                start_date = today
                end_date = today
                period_description = "Сегодняшний день"
            elif target_period == 'week':
                start_date = today - timedelta(days=7)
                end_date = today
                period_description = "Последние 7 дней"
            elif target_period == 'month':
                start_date = today - timedelta(days=30)
                end_date = today
                period_description = "Последние 30 дней"
            elif target_period == 'recent':
                start_date = today - timedelta(days=3)
                end_date = today
                period_description = "Последние 3 дня"
            else:
                start_date = today
                end_date = today
                period_description = "Сегодняшний день"
            
            # Get food logs for the period
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            food_logs = (self.db.query(FoodLog)
                        .filter(FoodLog.user_id == user_id)
                        .filter(FoodLog.created_at >= start_datetime)
                        .filter(FoodLog.created_at <= end_datetime)
                        .order_by(FoodLog.created_at.desc())
                        .all())
            
            # Format food logs for context
            formatted_food_logs = []
            for log in food_logs:
                food_info = {
                    'dish_name': log.dish_name or log.description,
                    'calories': log.calories or 0,
                    'protein_g': float(log.protein_g or 0),
                    'fat_g': float(log.fat_g or 0),
                    'carbs_g': float(log.carbs_g or 0),
                    'weight_g': float(log.estimated_weight_g or 0),
                    'created_at': log.created_at.strftime('%Y-%m-%d %H:%M') if log.created_at else None
                }
                formatted_food_logs.append(food_info)
            
            # Calculate totals for the period
            total_calories = sum(log.calories or 0 for log in food_logs)
            total_protein = sum(float(log.protein_g or 0) for log in food_logs)
            total_fat = sum(float(log.fat_g or 0) for log in food_logs)
            total_carbs = sum(float(log.carbs_g or 0) for log in food_logs)
            
            # Get today's summary for comparison
            today_summary = self.get_daily_summary(user_id, today)
            
            # Build context dictionary
            context = {
                "profile": {
                    "goal": user_profile.goal,
                    "daily_calorie_target": user_profile.daily_calorie_target,
                    "daily_protein_target_g": float(user_profile.daily_protein_target_g or 0),
                    "daily_fat_target_g": float(user_profile.daily_fat_target_g or 0),
                    "daily_carbs_target_g": float(user_profile.daily_carbs_target_g or 0),
                    "age": user_profile.age,
                    "gender": user_profile.gender,
                    "current_weight_kg": user_profile.current_weight_kg,
                    "target_weight_kg": user_profile.target_weight_kg,
                    "activity_level": user_profile.activity_level
                },
                "history": {
                    "period_description": period_description,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "food_logs": formatted_food_logs,
                    "total_entries": len(food_logs),
                    "total_calories": total_calories,
                    "total_protein": total_protein,
                    "total_fat": total_fat,
                    "total_carbs": total_carbs
                },
                "today_summary": today_summary
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting user context for LLM: {str(e)}")
            return {}

