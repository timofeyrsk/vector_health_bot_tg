import requests
import json
import logging
from typing import Dict, Optional
from datetime import datetime, date, time
from config.settings import Config
from services.openai_service import OpenAIService
from services.health_service import HealthService
from services.terra_service import TerraService
from database.connection import get_db
from utils.telegram_utils import parse_markdown_to_entities, clean_keyboard_markup
from utils.user_states import state_manager, States

logger = logging.getLogger(__name__)

class TelegramService:
    def __init__(self):
        """Initialize Telegram service"""
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.openai_service = OpenAIService()
        self.terra_service = TerraService()
    
    def process_update(self, update: Dict) -> Dict:
        """Process incoming Telegram update"""
        try:
            if 'message' in update:
                return self._process_message(update['message'])
            elif 'callback_query' in update:
                return self._process_callback_query(update['callback_query'])
            else:
                logger.warning(f"Unknown update type: {update.keys()}")
                return {'status': 'ignored', 'reason': 'Unknown update type'}
                
        except Exception as e:
            logger.error(f"Error processing Telegram update: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _process_message(self, message: Dict) -> Dict:
        """Process incoming message"""
        try:
            user_id = message['from']['id']
            chat_id = message['chat']['id']
            
            # Handle different message types
            if 'text' in message:
                return self._handle_text_message(user_id, chat_id, message['text'])
            elif 'photo' in message:
                return self._handle_photo_message(user_id, chat_id, message['photo'])
            else:
                self.send_message(chat_id, "Я могу обрабатывать только текстовые сообщения и фотографии.")
                return {'status': 'unsupported_message_type'}
                
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_text_message(self, user_id: int, chat_id: int, text: str) -> Dict:
        """Handle text messages"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Check if user exists
            user_profile = health_service.get_user_profile(user_id)
            
            if text.startswith('/start'):
                return self._handle_start_command(user_id, chat_id, user_profile)
            elif text.startswith('/connect_wearable'):
                return self._handle_connect_wearable_command(user_id, chat_id, user_profile)
            elif text.startswith('/summary'):
                return self._handle_summary_command(user_id, chat_id, user_profile)
            elif text.startswith('/help'):
                return self._handle_help_command(chat_id)
            elif not user_profile:
                # User not onboarded, start onboarding
                return self._handle_start_command(user_id, chat_id, None)
            elif user_profile and not self._is_onboarding_complete(user_profile):
                # Continue onboarding
                return self._handle_onboarding_step(user_id, chat_id, text, user_profile)
            else:
                # Check if user is in a dialog state
                current_state = state_manager.get_state_name(user_id)
                if current_state:
                    return self._handle_dialog_state(user_id, chat_id, text, current_state, user_profile)
                else:
                    # Regular message - could be food logging or Q&A
                    return self._handle_regular_message(user_id, chat_id, text, user_profile)
                
        except Exception as e:
            logger.error(f"Error handling text message: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_photo_message(self, user_id: int, chat_id: int, photos: list) -> Dict:
        """Handle photo messages for food logging"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile or not self._is_onboarding_complete(user_profile):
                message = "❌ *Профиль не настроен*\\n\\nПожалуйста, сначала завершите настройку профиля, отправив /start"
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'user_not_onboarded'}
            
            # Get the highest resolution photo
            photo = max(photos, key=lambda x: x['width'] * x['height'])
            file_id = photo['file_id']
            
            # Get file URL from Telegram
            file_info = self._get_file_info(file_id)
            if not file_info:
                message = "❌ *Ошибка обработки фото*\\n\\nИзвините, не удалось обработать вашу фотографию. Попробуйте еще раз."
                keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'error', 'reason': 'Could not get file info'}
            
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_info['file_path']}"
            
            # Analyze food from photo using the existing image analysis function
            self.send_message(chat_id, "🔍 Анализирую вашу фотографию еды...")
            
            try:
                food_data = self.openai_service.analyze_food_from_image(file_url)
                
                # Log the food
                food_log = health_service.log_food_from_photo(user_id, food_data, file_url)
                
                # Send confirmation message
                message = f"""✅ *Еда успешно записана!*

🍽️ {food_data['dish_name']}
📊 *Информация о питании:*
• Калории: {food_data['calories']} ккал
• Белки: {food_data['protein_g']}г
• Жиры: {food_data['fat_g']}г
• Углеводы: {food_data['carbs_g']}г
• Вес: ~{food_data['estimated_weight_g']}г

📝 *Ингредиенты:* {food_data['estimated_ingredients']}

Что дальше?"""
                
                keyboard = [
                    [
                        {'text': '📸 Анализ еще фото', 'callback_data': 'photo_analysis'},
                        {'text': '📊 Дневная сводка', 'callback_data': 'summary'}
                    ],
                    [{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]
                ]
                
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'success', 'food_log_id': str(food_log.log_id)}
                
            except Exception as e:
                logger.error(f"Error analyzing food photo: {str(e)}")
                message = "❌ *Ошибка анализа фото*\\n\\nИзвините, не удалось проанализировать вашу фотографию еды. Попробуйте описать ее текстом."
                keyboard = [
                    [{'text': '📝 Описать текстом', 'callback_data': 'food_log'}],
                    [{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]
                ]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'error', 'error': str(e)}
                
        except Exception as e:
            logger.error(f"Error handling photo message: {str(e)}")
            message = "❌ *Ошибка обработки*\\n\\nИзвините, произошла ошибка при обработке фотографии. Попробуйте позже."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_start_command(self, user_id: int, chat_id: int, user_profile) -> Dict:
        """Handle /start command and begin onboarding"""
        db = None
        try:
            if user_profile and self._is_onboarding_complete(user_profile):
                # Show main menu using unified function
                return self.send_main_menu_message(chat_id, user_id)
            else:
                message = """👋 *Добро пожаловать в Vector-Health AI Nutritionist!*

Я ваш персональный ИИ-нутрициолог. Я помогу вам отслеживать питание, анализировать приемы пищи и достигать ваших целей в области здоровья.

Давайте начнем с настройки вашего профиля. Какой у вас пол?
Пожалуйста, ответьте: *Мужской* или *Женский*"""
                
                # Create or update user profile to start onboarding
                db = next(get_db())
                health_service = HealthService(db)
                if not user_profile:
                    health_service.create_user_profile(user_id, chat_id)
                
                self.send_message(chat_id, message)
            
            return {'status': 'success', 'action': 'onboarding_started'}
            
        except Exception as e:
            logger.error(f"Error handling start command: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_connect_wearable_command(self, user_id: int, chat_id: int, user_profile) -> Dict:
        """Handle /connect_wearable command"""
        try:
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля, отправив /start"
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'user_not_found'}
            
            # Generate Terra auth URL
            auth_url = self.terra_service.generate_auth_url(user_id)
            
            message = f"""🔗 *Подключение фитнес-трекера*

Подключите ваш фитнес-трекер для автоматического отслеживания активности и получения полной картины вашего здоровья.

📱 *Поддерживаемые устройства:*
• Garmin
• Fitbit
• Oura Ring
• Withings
• Apple Health
• Google Fit

🔗 Нажмите кнопку ниже для подключения:"""
            
            keyboard = [
                [{'text': '🔗 Подключить устройство', 'url': auth_url}],
                [{'text': 'ℹ️ Подробнее о трекерах', 'callback_data': 'help_wearables'}],
                [{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]
            ]
            
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'success', 'auth_url': auth_url}
            
        except Exception as e:
            logger.error(f"Error handling connect wearable command: {str(e)}")
            message = "❌ *Ошибка подключения*\\n\\nИзвините, произошла ошибка при создании ссылки для подключения. Попробуйте позже."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
    
    def _handle_summary_command(self, user_id: int, chat_id: int, user_profile) -> Dict:
        """Handle /summary command"""
        db = None
        try:
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля, отправив /start"
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'user_not_found'}
            
            db = next(get_db())
            health_service = HealthService(db)
            
            # Get daily summary using new universal function
            summary_data = health_service.generate_report(user_id, 'daily')
            
            if not summary_data:
                message = "❌ Ошибка при получении данных. Попробуйте позже."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'No data available'}
            
            # Generate AI report
            report = self.openai_service.generate_report(summary_data, 'daily')
            
            # Combine report and options in one message
            message = f"📊 *Дневной отчет*\n\n{report}\n\nДополнительные опции:"
            
            keyboard = [
                [
                    {'text': '📈 Недельный отчет', 'callback_data': 'weekly_summary'}
                ],
                [
                    {'text': '🎯 Главное меню', 'callback_data': 'main_menu'}
                ]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'summary': summary_data}
            
        except Exception as e:
            logger.error(f"Error handling summary command: {str(e)}")
            message = "❌ Ошибка при генерации отчета. Попробуйте позже."
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_help_command(self, chat_id: int) -> Dict:
        """Handle /help command"""
        message = """ℹ️ *Vector-Health AI Nutritionist - Помощь*

🤖 Я ваш персональный ИИ-нутрициолог, который поможет вам достичь ваших целей в области здоровья.

📋 *Что умеет бот:*
• 🍽️ Анализировать еду по фото и описанию
• 📊 Вести дневник питания
• ❓ Отвечать на вопросы о питании
• 📈 Создавать персональные отчеты
• 🔗 Синхронизироваться с фитнес-трекерами

💡 *Как использовать:*
• Отправляйте фото еды для автоматического анализа
• Описывайте еду текстом
• Задавайте любые вопросы о питании
• Получайте ежедневные отчеты

🕐 Ежедневные отчеты отправляются автоматически в 20:00

Выберите раздел для получения подробной информации:"""
        
        keyboard = [
            [
                {'text': '🍽️ Запись еды', 'callback_data': 'help_food_log'},
                {'text': '📊 Отчеты', 'callback_data': 'help_reports'}
            ],
            [
                {'text': '❓ Вопросы', 'callback_data': 'help_questions'},
                {'text': '🔗 Трекеры', 'callback_data': 'help_wearables'}
            ],
            [
                {'text': '🎯 Главное меню', 'callback_data': 'main_menu'}
            ]
        ]
        
        self.send_message_with_keyboard(chat_id, message, keyboard)
        return {'status': 'success', 'action': 'help_sent'}
    
    def _handle_onboarding_step(self, user_id: int, chat_id: int, text: str, user_profile) -> Dict:
        """Handle onboarding steps"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Determine current onboarding step based on what's missing
            if not user_profile.gender:
                return self._handle_gender_input(health_service, user_id, chat_id, text)
            elif not user_profile.age:
                return self._handle_age_input(health_service, user_id, chat_id, text)
            elif not user_profile.height_cm:
                return self._handle_height_input(health_service, user_id, chat_id, text)
            elif not user_profile.current_weight_kg:
                return self._handle_current_weight_input(health_service, user_id, chat_id, text)
            elif not user_profile.goal:
                return self._handle_goal_input(health_service, user_id, chat_id, text)
            elif not user_profile.target_weight_kg:
                return self._handle_target_weight_input(health_service, user_id, chat_id, text)
            elif not user_profile.activity_level:
                return self._handle_activity_level_input(health_service, user_id, chat_id, text)
            else:
                # Onboarding complete, calculate targets
                health_service.calculate_user_targets(user_id)
                self.send_message(chat_id, """🎉 Настройка профиля завершена!

Ваш персональный план питания готов. Я рассчитал ваши дневные нормы калорий и макронутриентов на основе ваших целей.

Теперь вы можете:
📸 Отправлять фотографии приемов пищи для автоматической записи
📝 Описывать еду текстом
📊 Получать дневные отчеты с помощью /summary
🔗 Подключать носимые устройства с помощью /connect_wearable

Давайте начнем ваш путь к здоровью! Отправьте мне фотографию или описание вашего следующего приема пищи.""")
                return {'status': 'success', 'action': 'onboarding_complete'}
                
        except Exception as e:
            logger.error(f"Error handling onboarding step: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_regular_message(self, user_id: int, chat_id: int, text: str, user_profile) -> Dict:
        """Handle regular messages using unified AI processing"""
        db = None
        try:
            # Подготовка контекста пользователя
            user_context = None
            if user_profile:
                db = next(get_db())
                health_service = HealthService(db)
                
                user_context = {
                    'goal': user_profile.goal,
                    'age': user_profile.age,
                    'gender': user_profile.gender,
                    'daily_calorie_target': user_profile.daily_calorie_target,
                    'daily_protein_target_g': user_profile.daily_protein_target_g,
                    'daily_fat_target_g': user_profile.daily_fat_target_g,
                    'daily_carbs_target_g': user_profile.daily_carbs_target_g
                }
                
                # Если вопрос может касаться личных данных, добавляем недавние логи
                if any(word in text.lower() for word in ['мой', 'моя', 'мое', 'я', 'сегодня', 'вчера', 'неделя']):
                    from datetime import date
                    summary = health_service.get_daily_summary(user_id, date.today())
                    user_context['recent_data'] = summary
            
            # Отправляем сообщение о том, что обрабатываем
            self.send_message(chat_id, "🤔 Анализирую ваше сообщение...")
            
            # Используем новую универсальную функцию
            result = self.openai_service.process_user_message(text, user_context)
            
            # Обрабатываем результат в зависимости от намерения
            if result['intent'] == 'food_log':
                return self._handle_food_log_result(user_id, chat_id, text, result['analysis'])
            elif result['intent'] == 'nutrition_question':
                return self._handle_nutrition_question_result(chat_id, result['answer'])
            else:
                logger.error(f"Unknown intent: {result['intent']}")
                message = "❌ *Ошибка обработки*\\n\\nИзвините, произошла ошибка при обработке вашего сообщения. Попробуйте еще раз."
                keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
                self.send_message_with_keyboard(chat_id, message, keyboard)
                return {'status': 'error', 'error': f"Unknown intent: {result['intent']}"}
                
        except ValueError as e:
            logger.error(f"Value error in message processing: {str(e)}")
            message = "❌ *Ошибка анализа*\\n\\nИзвините, произошла ошибка при анализе вашего сообщения. Попробуйте еще раз."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        except Exception as e:
            logger.error(f"Error handling regular message: {str(e)}")
            message = "❌ *Временная ошибка*\\n\\nИзвините, произошла временная ошибка. Попробуйте позже."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_food_log_result(self, user_id: int, chat_id: int, original_text: str, food_analysis: Dict) -> Dict:
        """Handle food log result from unified AI processing"""
        try:
            # Log the food to database
            db = next(get_db())
            health_service = HealthService(db)
            food_log = health_service.log_food_from_text(user_id, original_text, food_analysis)
            
            # Send confirmation message
            message = f"""✅ *Еда успешно записана!*

🍽️ {food_analysis['dish_name']}
📊 *Информация о питании:*
• Калории: {food_analysis['calories']} ккал
• Белки: {food_analysis['protein_g']}г
• Жиры: {food_analysis['fat_g']}г
• Углеводы: {food_analysis['carbs_g']}г
• Вес: ~{food_analysis['estimated_weight_g']}г

📝 *Ингредиенты:* {food_analysis['estimated_ingredients']}

Что дальше?"""
            
            keyboard = [
                [
                    {'text': '🍽️ Записать еще', 'callback_data': 'food_log'},
                    {'text': '📊 Дневная сводка', 'callback_data': 'summary'}
                ],
                [{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]
            ]
            
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'success', 'food_log_id': str(food_log.log_id)}
            
        except Exception as e:
            logger.error(f"Error handling food log result: {str(e)}")
            message = "❌ *Ошибка сохранения*\\n\\nИзвините, произошла ошибка при сохранении записи еды. Попробуйте еще раз."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
    
    def _handle_nutrition_question_result(self, chat_id: int, answer: str) -> Dict:
        """Handle nutrition question result from unified AI processing"""
        try:
            # Send AI answer using HTML formatting to avoid MarkdownV2 issues
            self.send_ai_message(chat_id, f"❓ *Ответ на ваш вопрос:*\\n\\n{answer}")
            
            # Send follow-up message with navigation
            follow_up_message = """💡 *Есть еще вопросы?*

Выберите действие:"""
            
            keyboard = [
                [
                    {'text': '❓ Задать еще вопрос', 'callback_data': 'nutrition_question'},
                    {'text': '🍽️ Записать еду', 'callback_data': 'food_log'}
                ],
                [{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]
            ]
            
            self.send_message_with_keyboard(chat_id, follow_up_message, keyboard)
            return {'status': 'success', 'answer': answer}
            
        except Exception as e:
            logger.error(f"Error handling nutrition question result: {str(e)}")
            message = "❌ *Ошибка отправки*\\n\\nИзвините, произошла ошибка при отправке ответа. Попробуйте позже."
            keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            self.send_message_with_keyboard(chat_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
    

    
    # Onboarding helper methods
    def _handle_gender_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        gender = text.lower().strip()
        if gender in ['мужской', 'м', 'мужчина', 'male', 'm', 'man']:
            health_service.update_user_profile(user_id, {'gender': 'male'})
            self.send_message(chat_id, "Отлично! Сколько вам лет? (Пожалуйста, введите число)")
        elif gender in ['женский', 'ж', 'женщина', 'female', 'f', 'woman']:
            health_service.update_user_profile(user_id, {'gender': 'female'})
            self.send_message(chat_id, "Отлично! Сколько вам лет? (Пожалуйста, введите число)")
        else:
            self.send_message(chat_id, "Пожалуйста, введите 'Мужской' или 'Женский'")
        return {'status': 'success'}
    
    def _handle_age_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        try:
            age = int(text.strip())
            if 10 <= age <= 120:
                health_service.update_user_profile(user_id, {'age': age})
                self.send_message(chat_id, "Отлично! Какой у вас рост в сантиметрах? (например, 175)")
            else:
                self.send_message(chat_id, "Пожалуйста, введите корректный возраст от 10 до 120 лет")
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите ваш возраст числом")
        return {'status': 'success'}
    
    def _handle_height_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        try:
            height = int(text.strip())
            if 100 <= height <= 250:
                health_service.update_user_profile(user_id, {'height_cm': height})
                self.send_message(chat_id, "Понятно! Какой у вас текущий вес в килограммах? (например, 70.5)")
            else:
                self.send_message(chat_id, "Пожалуйста, введите корректный рост от 100 до 250 см")
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите ваш рост в сантиметрах числом")
        return {'status': 'success'}
    
    def _handle_current_weight_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        try:
            weight = float(text.strip())
            if 30 <= weight <= 300:
                health_service.update_user_profile(user_id, {'current_weight_kg': weight})
                self.send_message(chat_id, """Какова ваша основная цель?

1. Сбросить вес - Уменьшить массу тела
2. Поддерживать вес - Оставаться на текущем весе
3. Набрать вес - Увеличить массу тела

Пожалуйста, ответьте: Сбросить, Поддерживать или Набрать""")
            else:
                self.send_message(chat_id, "Пожалуйста, введите корректный вес от 30 до 300 кг")
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите ваш вес числом \\(например, 70\\.5\\)")
        return {'status': 'success'}
    
    def _handle_goal_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        """Handle goal input - now sends buttons instead of asking for text"""
        message = """Какова ваша основная цель?

1. Сбросить вес - Уменьшить массу тела
2. Поддерживать вес - Оставаться на текущем весе  
3. Набрать вес - Увеличить массу тела

Выберите вашу цель:"""
        
        keyboard = [
            [{'text': '1️⃣ Сбросить вес', 'callback_data': 'onboarding_goal_lose'}],
            [{'text': '2️⃣ Поддерживать вес', 'callback_data': 'onboarding_goal_maintain'}],
            [{'text': '3️⃣ Набрать вес', 'callback_data': 'onboarding_goal_gain'}]
        ]
        
        self.send_message_with_keyboard(chat_id, message, keyboard)
        return {'status': 'success'}
    
    def _handle_target_weight_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        try:
            target_weight = float(text.strip())
            if 30 <= target_weight <= 300:
                health_service.update_user_profile(user_id, {'target_weight_kg': target_weight})
                
                message = """Какой у вас уровень активности?

1. Малоподвижный – Минимальные физические нагрузки
2. Умеренный - Легкие упражнения 1-3 раза в неделю
3. Активный - Умеренные упражнения 3-5 раз в неделю

Выберите ваш уровень активности:"""
                
                keyboard = [
                    [{'text': '1️⃣ Малоподвижный', 'callback_data': 'onboarding_activity_sedentary'}],
                    [{'text': '2️⃣ Умеренный', 'callback_data': 'onboarding_activity_moderate'}],
                    [{'text': '3️⃣ Активный', 'callback_data': 'onboarding_activity_active'}]
                ]
                
                self.send_message_with_keyboard(chat_id, message, keyboard)
            else:
                self.send_message(chat_id, "Пожалуйста, введите корректный целевой вес от 30 до 300 кг")
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите ваш целевой вес числом (например, 65)")
        return {'status': 'success'}
    
    def _handle_activity_level_input(self, health_service, user_id: int, chat_id: int, text: str) -> Dict:
        activity_text = text.lower().strip()
        if activity_text in ['малоподвижный', 'сидячий', 'sedentary', 'sed']:
            health_service.update_user_profile(user_id, {'activity_level': 'sedentary'})
        elif activity_text in ['умеренный', 'moderate', 'mod']:
            health_service.update_user_profile(user_id, {'activity_level': 'moderate'})
        elif activity_text in ['активный', 'active', 'act']:
            health_service.update_user_profile(user_id, {'activity_level': 'active'})
        else:
            self.send_message(chat_id, "Пожалуйста, ответьте 'Малоподвижный', 'Умеренный' или 'Активный'")
            return {'status': 'success'}
        
        # Onboarding complete, calculate targets
        health_service.calculate_user_targets(user_id)
        self.send_message(chat_id, """🎉 Настройка профиля завершена!

Ваш персональный план питания готов! Я рассчитал ваши дневные нормы калорий и макронутриентов на основе ваших целей.

Теперь вы можете:
📸 Отправлять фотографии приемов пищи для автоматической записи
📝 Описывать еду текстом
📊 Получать дневные отчеты с помощью /summary
🔗 Подключать носимые устройства с помощью /connect_wearable

Давайте начнем ваш путь к здоровью! Отправьте мне фотографию или описание вашего следующего приема пищи.""")
        return {'status': 'success'}
    
    def _is_onboarding_complete(self, user_profile) -> bool:
        """Check if user onboarding is complete"""
        required_fields = [
            user_profile.gender,
            user_profile.age,
            user_profile.height_cm,
            user_profile.current_weight_kg,
            user_profile.goal,
            user_profile.target_weight_kg,
            user_profile.activity_level
        ]
        return all(field is not None for field in required_fields)
    
    def _get_file_info(self, file_id: str) -> Optional[Dict]:
        """Get file information from Telegram"""
        try:
            response = requests.get(f"{self.base_url}/getFile", params={'file_id': file_id})
            response.raise_for_status()
            return response.json().get('result')
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    def send_message(self, chat_id: int, text: str, reply_markup: dict = None) -> bool:
        """
        Universal message sending function using Message Entities instead of parse_mode.
        """
        try:
            # Parse markdown to entities
            plain_text, entities = parse_markdown_to_entities(text)
            
            # Build payload
            payload = {
                'chat_id': chat_id,
                'text': plain_text
            }
            
            # Add entities if any
            if entities:
                payload['entities'] = entities
            
            # Add reply markup if provided
            if reply_markup:
                # Проверяем, что reply_markup является словарем
                if not isinstance(reply_markup, dict):
                    logger.error(f"Invalid reply_markup type: {type(reply_markup)}, value: {reply_markup}")
                    # Не добавляем некорректный reply_markup
                else:
                    # Clean keyboard text to prevent formatting errors
                    if 'inline_keyboard' in reply_markup:
                        cleaned_keyboard = clean_keyboard_markup(reply_markup['inline_keyboard'])
                        payload['reply_markup'] = {'inline_keyboard': cleaned_keyboard}
                    else:
                        # Если это не inline_keyboard, передаем как есть
                        payload['reply_markup'] = reply_markup
            
            # Логируем payload перед отправкой
            logger.debug(f"Telegram payload: {payload}")
            
            # Send message
            response = requests.post(f"{self.base_url}/sendMessage", json=payload)
            try:
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Telegram API error: {response.text}")
                raise
            return True
            
        except Exception as e:
            # Логируем подробности ошибки
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error sending message: {str(e)} | Response: {e.response.text}")
            else:
                logger.error(f"Error sending message: {str(e)}")
            return False
    
    def send_ai_message(self, chat_id: int, text: str) -> bool:
        """
        Send AI-generated message with automatic markdown parsing.
        
        Args:
            chat_id: Telegram chat ID
            text: AI-generated text (can contain markdown formatting)
            
        Returns:
            bool: True if message sent successfully, False otherwise
        """
        return self.send_message(chat_id, text)
    
    def set_webhook(self, webhook_url: str) -> Dict:
        """Set Telegram webhook URL"""
        try:
            payload = {
                'url': webhook_url,
                'allowed_updates': ['message', 'callback_query']
            }
            
            response = requests.post(f"{self.base_url}/setWebhook", json=payload)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error setting webhook: {str(e)}")
            raise
    
    # ===== NAVIGATION METHODS =====
    
    def _process_callback_query(self, callback_query: Dict) -> Dict:
        """Process callback query"""
        try:
            callback_data = callback_query.get('data', '')
            user_id = callback_query['from']['id']
            chat_id = callback_query['message']['chat']['id']
            message_id = callback_query['message']['message_id']
            logger.debug(f"Processing callback query: {callback_data}")
            self._answer_callback_query(callback_query['id'])

            # Новый роутинг по формату prefix:action:id[:payload]
            parts = callback_data.split(':')
            if len(parts) == 1:
                # Короткие команды (главное меню и т.д.)
                if callback_data == 'main_menu':
                    return self._handle_main_menu_callback(user_id, chat_id, message_id)
                elif callback_data == 'food_log':
                    return self._handle_food_log_callback(user_id, chat_id, message_id)
                elif callback_data == 'photo_analysis':
                    return self._handle_photo_analysis_callback(user_id, chat_id, message_id)
                elif callback_data == 'nutrition_question':
                    return self._handle_nutrition_question_callback(user_id, chat_id, message_id)
                elif callback_data == 'summary':
                    return self._handle_summary_callback(user_id, chat_id, message_id)
                elif callback_data == 'statistics':
                    return self._handle_statistics_callback(user_id, chat_id, message_id)
                elif callback_data == 'help':
                    return self._handle_help_callback(user_id, chat_id, message_id)
                elif callback_data == 'profile':
                    return self._handle_profile_callback(user_id, chat_id, message_id)
                elif callback_data == 'settings':
                    return self._handle_settings_callback(user_id, chat_id, message_id)
                elif callback_data == 'support':
                    return self._handle_support_callback(user_id, chat_id, message_id)
                elif callback_data == 'weekly_summary':
                    return self._handle_weekly_summary_callback(user_id, chat_id, message_id)
                elif callback_data == 'start_onboarding':
                    return self._handle_start_onboarding_callback(user_id, chat_id, message_id)
                elif callback_data == 'back_to_main':
                    return self._handle_back_to_main_callback(user_id, chat_id, message_id)
                elif callback_data == 'stats_today':
                    return self._handle_stats_today_callback(user_id, chat_id, message_id)
                elif callback_data == 'stats_week':
                    return self._handle_stats_week_callback(user_id, chat_id, message_id)
                elif callback_data == 'stats_month':
                    return self._handle_stats_month_callback(user_id, chat_id, message_id)
                elif callback_data == 'stats_progress':
                    return self._handle_stats_progress_callback(user_id, chat_id, message_id)
                elif callback_data == 'onboarding_goal_lose':
                    return self._handle_onboarding_goal_callback(user_id, chat_id, message_id, 'lose_weight')
                elif callback_data == 'onboarding_goal_maintain':
                    return self._handle_onboarding_goal_callback(user_id, chat_id, message_id, 'maintain_weight')
                elif callback_data == 'onboarding_goal_gain':
                    return self._handle_onboarding_goal_callback(user_id, chat_id, message_id, 'gain_weight')
                elif callback_data == 'onboarding_activity_sedentary':
                    return self._handle_onboarding_activity_callback(user_id, chat_id, message_id, 'sedentary')
                elif callback_data == 'onboarding_activity_moderate':
                    return self._handle_onboarding_activity_callback(user_id, chat_id, message_id, 'moderate')
                elif callback_data == 'onboarding_activity_active':
                    return self._handle_onboarding_activity_callback(user_id, chat_id, message_id, 'active')
                # ... другие короткие команды ...
                else:
                    logger.warning(f"Unknown callback data: {callback_data}")
                    return {'status': 'ignored', 'reason': 'Unknown callback data'}
            else:
                prefix = parts[0]
                action = parts[1] if len(parts) > 1 else None
                obj_id = parts[2] if len(parts) > 2 else None
                payload = parts[3] if len(parts) > 3 else None
                # Еда: food:options:<id>, food:delete:<id>, food:edit_field:<id>:<field>
                if prefix == 'food':
                    if action == 'options':
                        return self._handle_food_edit_callback(user_id, chat_id, message_id, obj_id)
                    elif action == 'delete':
                        return self._handle_food_delete_callback(user_id, chat_id, message_id, obj_id)
                    elif action == 'edit_field':
                        return self._handle_food_edit_field_callback(user_id, chat_id, message_id, obj_id, payload)
                # Навигация: nav:back:<target>
                elif prefix == 'nav' and action == 'back':
                    # Например, nav:back:settings_edit_food
                    if obj_id == 'settings_edit_food':
                        return self._handle_settings_edit_food_callback(user_id, chat_id, message_id)
                    elif obj_id == 'settings':
                        return self._handle_settings_callback(user_id, chat_id, message_id)
                    # ... другие возвраты ...
                # Настройки: settings:action
                elif prefix == 'settings':
                    if action == 'goal':
                        return self._handle_settings_goal_callback(user_id, chat_id, message_id)
                    elif action == 'reports_time':
                        return self._handle_settings_reports_time_callback(user_id, chat_id, message_id)
                    elif action == 'reset':
                        return self._handle_settings_reset_callback(user_id, chat_id, message_id)
                    elif action == 'edit_food':
                        return self._handle_settings_edit_food_callback(user_id, chat_id, message_id)
                    elif action == 'reset_confirm':
                        return self._handle_settings_reset_confirm_callback(user_id, chat_id, message_id)
                    elif action == 'reset_cancel':
                        return self._handle_settings_reset_cancel_callback(user_id, chat_id, message_id)
                # ... другие кастомные роуты ...
                logger.warning(f"Unknown structured callback data: {callback_data}")
                return {'status': 'ignored', 'reason': 'Unknown structured callback data'}
        except Exception as e:
            logger.error(f"Error processing callback query: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _answer_callback_query(self, callback_query_id: str, text: str = None) -> bool:
        """Answer callback query to remove loading state"""
        try:
            payload = {'callback_query_id': callback_query_id}
            if text:
                payload['text'] = text
            
            response = requests.post(f"{self.base_url}/answerCallbackQuery", json=payload)
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Error answering callback query: {str(e)}")
            return False
    
    def send_message_with_keyboard(self, chat_id: int, text: str, keyboard: list) -> bool:
        """Send message with inline keyboard using new entity system"""
        try:
            # Логируем исходную клавиатуру
            logger.debug(f"Original keyboard: {keyboard}")
            
            # Clean keyboard text
            cleaned_keyboard = clean_keyboard_markup(keyboard)
            logger.debug(f"Cleaned keyboard: {cleaned_keyboard}")
            
            # Создаем правильную структуру reply_markup
            reply_markup = {'inline_keyboard': cleaned_keyboard}
            logger.debug(f"Reply markup: {reply_markup}")
            
            return self.send_message(chat_id, text, reply_markup)
        except Exception as e:
            logger.error(f"Error sending message with keyboard: {str(e)}")
            return False
    
    def edit_message_with_keyboard(self, chat_id: int, message_id: int, text: str, keyboard: list) -> bool:
        """Edit message with inline keyboard using new entity system"""
        try:
            # Parse markdown to entities
            plain_text, entities = parse_markdown_to_entities(text)
            
            # Clean keyboard text
            cleaned_keyboard = clean_keyboard_markup(keyboard)
            
            # Build payload
            payload = {
                'chat_id': chat_id,
                'message_id': message_id,
                'text': plain_text,
                'reply_markup': {
                    'inline_keyboard': cleaned_keyboard
                }
            }
            
            # Add entities if any
            if entities:
                payload['entities'] = entities
            
            # Debug logging
            logger.debug(f"Editing message payload: {payload}")
            
            response = requests.post(f"{self.base_url}/editMessageText", json=payload)
            
            if not response.ok:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                logger.error(f"Payload was: {payload}")
            
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Error editing message with keyboard: {str(e)}")
            logger.error(f"Chat ID: {chat_id}, Message ID: {message_id}, Text: {text[:100]}...")
            return False
    
    def _get_main_menu_keyboard(self) -> list:
        """Get main menu keyboard"""
        return [
            [
                {'text': '🍽️ Записать еду', 'callback_data': 'food_log'},
                {'text': '📸 Анализ фото', 'callback_data': 'photo_analysis'}
            ],
            [
                {'text': '📊 Дневная сводка', 'callback_data': 'summary'},
                {'text': '📈 Статистика', 'callback_data': 'statistics'}
            ],
            [
                {'text': '❓ Задать вопрос', 'callback_data': 'nutrition_question'},
                {'text': '👤 Мой профиль', 'callback_data': 'profile'}
            ],
            [
                {'text': '🔗 Подключить трекер', 'callback_data': 'connect_wearable'},
                {'text': '⚙️ Настройки', 'callback_data': 'settings'}
            ],
            [
                {'text': 'ℹ️ Помощь', 'callback_data': 'help'},
                {'text': '📞 Поддержка', 'callback_data': 'support'}
            ]
        ]
    
    def _get_back_keyboard(self) -> list:
        """Get back to main menu keyboard"""
        return [
            [{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]
        ]
    
    def _handle_main_menu_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle main menu callback"""
        try:
            return self.send_main_menu_message(chat_id, user_id, message_id)
        except Exception as e:
            logger.error(f"Error handling main menu callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_food_log_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle food log callback"""
        try:
            message = """🍽️ Запись еды

Отправьте мне:
• Фотографию вашей еды
• Текстовое описание (например, "куриная грудка 200г")

Я автоматически проанализирую питательную ценность и запишу в ваш дневник."""
            
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'food_log_instructions_shown'}
            
        except Exception as e:
            logger.error(f"Error handling food log callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_nutrition_question_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle nutrition question callback"""
        try:
            message = """❓ Задать вопрос о питании

Просто напишите ваш вопрос, и я дам подробный ответ с рекомендациями.

Примеры вопросов:
• "Какие продукты богаты белком?"
• "Как правильно питаться для похудения?"
• "Сколько воды нужно пить в день?"
• "Что есть перед тренировкой?"""
            
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'nutrition_question_instructions_shown'}
            
        except Exception as e:
            logger.error(f"Error handling nutrition question callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_summary_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle summary callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ Профиль не найден. Сначала завершите настройку."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get daily summary using new universal function
            summary_data = health_service.generate_report(user_id, 'daily')
            
            if not summary_data:
                message = "❌ Ошибка при получении данных. Попробуйте позже."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'No data available'}
            
            # Generate AI report
            report = self.openai_service.generate_report(summary_data, 'daily')
            
            # Combine report and options in one message
            message = f"📊 *Дневной отчет*\n\n{report}\n\nДополнительные опции:"
            
            keyboard = [
                [
                    {'text': '📈 Недельный отчет', 'callback_data': 'weekly_summary'}
                ],
                [
                    {'text': '🎯 Главное меню', 'callback_data': 'main_menu'}
                ]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'summary': summary_data}
            
        except Exception as e:
            logger.error(f"Error handling summary callback: {str(e)}")
            message = "❌ Ошибка при генерации отчета. Попробуйте позже."
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_help_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle help callback"""
        try:
            message = """ℹ️ Помощь

🤖 Vector-Health AI Nutritionist - ваш персональный ИИ-нутрициолог

📋 Что умеет бот:
• 🍽️ Анализировать еду по фото и описанию
• 📊 Вести дневник питания
• ❓ Отвечать на вопросы о питании
• 📈 Создавать персональные отчеты
• 🔗 Синхронизироваться с фитнес-трекерами

💡 Как использовать:
• Отправляйте фото еды для автоматического анализа
• Описывайте еду текстом
• Задавайте любые вопросы о питании
• Получайте ежедневные отчеты

🕐 Ежедневные отчеты отправляются автоматически в 20:00

📞 Поддержка: @support_username"""
            
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'help_shown'}
            
        except Exception as e:
            logger.error(f"Error handling help callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_connect_wearable_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle connect wearable callback"""
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ Сначала завершите настройку профиля."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Generate Terra auth URL
            auth_url = self.terra_service.generate_auth_url(user_id)
            
            message = f"""🔗 Подключение фитнес-трекера

Подключите ваш фитнес-трекер для автоматического отслеживания активности:

📱 Поддерживаемые устройства:
• Garmin
• Fitbit
• Oura Ring
• Withings
• Apple Health
• Google Fit

🔗 Нажмите кнопку ниже для подключения:"""
            
            keyboard = [
                [{'text': '🔗 Подключить устройство', 'url': auth_url}],
                [{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'wearable_connect_shown'}
            
        except Exception as e:
            logger.error(f"Error handling connect wearable callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_profile_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle profile callback"""
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ Профиль не найден. Сначала завершите настройку."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            message = f"""👤 Ваш профиль

📊 Основная информация:
• Цель: {user_profile.goal.replace('_', ' ').title()}
• Возраст: {user_profile.age} лет
• Рост: {user_profile.height_cm} см
• Текущий вес: {user_profile.current_weight_kg} кг
• Целевой вес: {user_profile.target_weight_kg} кг
• Уровень активности: {user_profile.activity_level.replace('_', ' ').title()}

🎯 Дневные нормы:
• Калории: {user_profile.daily_calorie_target} ккал
• Белки: {user_profile.daily_protein_target_g} г
• Жиры: {user_profile.daily_fat_target_g} г
• Углеводы: {user_profile.daily_carbs_target_g} г

📅 Дата регистрации: {user_profile.created_at.strftime('%d.%m.%Y')}"""
            
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'profile_shown'}
            
        except Exception as e:
            logger.error(f"Error handling profile callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_back_to_main_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle back to main menu callback"""
        return self._handle_main_menu_callback(user_id, chat_id, message_id)

    def _handle_photo_analysis_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle photo analysis callback"""
        try:
            message = """📸 *Анализ фотографий еды*

Отправьте мне фотографию вашего приема пищи, и я автоматически:

🔍 *Проанализирую:*
• Название блюда
• Калорийность
• Содержание белков, жиров, углеводов
• Примерный вес порции
• Список ингредиентов

📊 *Запишу в ваш дневник питания*

💡 *Советы для лучшего анализа:*
• Снимайте еду при хорошем освещении
• Старайтесь, чтобы блюдо занимало большую часть кадра
• Избегайте размытых фотографий"""
            
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'photo_analysis_instructions_shown'}
            
        except Exception as e:
            logger.error(f"Error handling photo analysis callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_statistics_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle statistics callback"""
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get basic statistics
            from datetime import date, timedelta
            today = date.today()
            
            # Calculate weekly statistics
            total_entries = 0
            total_calories = 0
            days_with_data = 0
            
            for i in range(7):
                check_date = today - timedelta(days=i)
                day_data = health_service.get_daily_summary(user_id, check_date)
                if day_data.get('total_entries', 0) > 0:
                    total_entries += day_data.get('total_entries', 0)
                    total_calories += day_data.get('total_calories', 0)
                    days_with_data += 1
            
            avg_calories = total_calories / 7 if days_with_data > 0 else 0
            goal_achievement = (avg_calories / user_profile.daily_calorie_target * 100) if user_profile.daily_calorie_target > 0 else 0
            
            message = f"""📈 *Ваша статистика*

📊 *За последние 7 дней:*
• Записей еды: {total_entries}
• Средние калории в день: {avg_calories:.0f} ккал
• Достижение цели: {goal_achievement:.1f}%

🎯 *Ваши цели:*
• Цель: {user_profile.goal.replace('_', ' ').title()}
• Текущий вес: {user_profile.current_weight_kg} кг
• Целевой вес: {user_profile.target_weight_kg} кг

Выберите период для детальной статистики:"""
            
            keyboard = [
                [
                    {'text': '📅 Сегодня', 'callback_data': 'stats_today'},
                    {'text': '📊 Неделя', 'callback_data': 'stats_week'}
                ],
                [
                    {'text': '📈 Месяц', 'callback_data': 'stats_month'},
                    {'text': '📋 Прогресс', 'callback_data': 'stats_progress'}
                ],
                [{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'statistics_shown'}
            
        except Exception as e:
            logger.error(f"Error handling statistics callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            # Закрываем соединение с базой данных
            if db:
                db.close()
    
    def _handle_settings_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle settings callback"""
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Format report time for display
            report_time_display = "Не установлено"
            if user_profile.daily_report_time:
                report_time_display = user_profile.daily_report_time.strftime("%H:%M")
            
            message = f"""⚙️ *Настройки профиля*

👤 *Текущие настройки:*
• Цель: {user_profile.goal.replace('_', ' ').title() if user_profile.goal else 'Не установлена'}
• Дневная норма: {user_profile.daily_calorie_target or 'Не установлена'} ккал
• Время отчёта: {report_time_display}

Выберите, что хотите изменить:"""
            
            keyboard = [
                [
                    {'text': 'Изменить цель', 'callback_data': 'settings:goal'},
                    {'text': 'Время отчёта', 'callback_data': 'settings:reports_time'}
                ],
                [
                    {'text': 'Сбросить профиль', 'callback_data': 'settings:reset'},
                    {'text': 'Изменить приём пищи', 'callback_data': 'settings:edit_food'}
                ],
                [{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'settings_shown'}
            
        except Exception as e:
            logger.error(f"Error handling settings callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_support_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle support callback"""
        try:
            message = """📞 *Поддержка*

Если у вас возникли вопросы или проблемы, мы готовы помочь!

💬 *Способы связи:*
• Telegram: @support_username
• Email: support@vector-health.com
• Время работы: 24/7

❓ *Частые вопросы:*
• Как изменить цель?
• Почему не работает анализ фото?
• Как подключить трекер?

🔧 *Техническая поддержка:*
• Проблемы с ботом
• Ошибки в отчетах
• Настройка уведомлений

Выберите тему для получения помощи:"""
            
            keyboard = [
                [
                    {'text': '❓ FAQ', 'callback_data': 'support_faq'},
                    {'text': '🔧 Техподдержка', 'callback_data': 'support_tech'}
                ],
                [
                    {'text': '💬 Написать в чат', 'callback_data': 'support_chat'},
                    {'text': '📧 Email', 'callback_data': 'support_email'}
                ],
                [{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'support_shown'}
            
        except Exception as e:
            logger.error(f"Error handling support callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_weekly_summary_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle weekly summary callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get weekly summary using new universal function
            summary_data = health_service.generate_report(user_id, 'weekly')
            
            if not summary_data:
                message = "❌ Ошибка при получении данных. Попробуйте позже."
                keyboard = self._get_back_keyboard()
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'No data available'}
            
            # Generate AI report
            report = self.openai_service.generate_report(summary_data, 'weekly')
            
            # Combine report and options in one message
            message = f"📈 *Недельный отчет*\n\n{report}\n\nДополнительные опции:"
            
            keyboard = [
                [
                    {'text': '📊 Дневной отчет', 'callback_data': 'summary'}
                ],
                [
                    {'text': '🎯 Главное меню', 'callback_data': 'main_menu'}
                ]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'summary': summary_data}
            
        except Exception as e:
            logger.error(f"Error handling weekly summary callback: {str(e)}")
            message = "❌ Ошибка при генерации недельного отчета. Попробуйте позже."
            keyboard = self._get_back_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()
    

    
    def _handle_start_onboarding_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle start onboarding callback"""
        try:
            message = """🚀 *Настройка профиля*

Давайте настроим ваш персональный профиль для достижения ваших целей в области здоровья.

📋 *Что нам понадобится:*
• Пол и возраст
• Рост и текущий вес
• Цель (похудение/поддержание/набор веса)
• Уровень активности

Готовы начать? Нажмите кнопку ниже."""
            
            keyboard = [
                [{'text': '✅ Начать настройку', 'callback_data': 'onboarding_gender'}],
                [{'text': '🔙 Назад', 'callback_data': 'back_to_main'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'onboarding_started'}
            
        except Exception as e:
            logger.error(f"Error handling start onboarding callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    # Help section callbacks
    def _handle_help_food_log_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle help food log callback"""
        try:
            message = """🍽️ *Запись еды - Подробная инструкция*

📸 *Фотографии еды:*
• Снимайте еду при хорошем освещении
• Старайтесь, чтобы блюдо занимало большую часть кадра
• Избегайте размытых фотографий
• Можно снимать несколько блюд на одной тарелке

📝 *Текстовое описание:*
• Будьте конкретны: "куриная грудка на гриле, 200г"
• Указывайте способ приготовления: "вареная", "жареная", "на пару"
• Добавляйте соусы и добавки: "с оливковым маслом", "с солью"

📊 *Что анализируется:*
• Название блюда
• Калорийность
• Белки, жиры, углеводы
• Примерный вес порции
• Список ингредиентов

💡 *Советы:*
• Записывайте еду сразу после приема
• Не забывайте про напитки и перекусы
• Указывайте размер порции для точности"""
            
            keyboard = [
                [{'text': '📸 Примеры фото', 'callback_data': 'help_photo_examples'}],
                [{'text': '🔙 Назад к помощи', 'callback_data': 'help'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'help_food_log_shown'}
            
        except Exception as e:
            logger.error(f"Error handling help food log callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_help_reports_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle help reports callback"""
        try:
            message = """📊 *Отчеты - Подробная информация*

📈 *Типы отчетов:*
• *Дневной отчет* - анализ питания за день
• *Недельный отчет* - тенденции за неделю


📋 *Что включают отчеты:*
• Общее потребление калорий
• Распределение макронутриентов
• Сравнение с вашими целями
• Рекомендации по улучшению
• Тренды и паттерны питания

⏰ *Автоматические отчеты:*
• Время отправки: 20:00
• Можно изменить в настройках
• Отправляются только при наличии записей еды

💡 *Как получить отчет:*
• Нажмите кнопку "📊 Дневная сводка"
• Используйте команду /summary
• Отчеты генерируются автоматически"""
            
            keyboard = [
                [{'text': '📊 Получить отчет', 'callback_data': 'summary'}],
                [{'text': '🔙 Назад к помощи', 'callback_data': 'help'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'help_reports_shown'}
            
        except Exception as e:
            logger.error(f"Error handling help reports callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_help_questions_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle help questions callback"""
        try:
            message = """❓ *Вопросы о питании - Как это работает*

🤖 *ИИ-нутрициолог:*
Я использую передовые технологии искусственного интеллекта для предоставления персонализированных рекомендаций по питанию.

💬 *Примеры вопросов:*
• "Какие продукты богаты белком?"
• "Как правильно питаться для похудения?"
• "Сколько воды нужно пить в день?"
• "Что есть перед тренировкой?"
• "Как улучшить мой рацион?"
• "Какие витамины мне нужны?"

📊 *Персонализация:*
• Учитываю ваши цели и профиль
• Анализирую ваши пищевые привычки
• Даю рекомендации на основе ваших данных
• Учитываю ограничения и предпочтения

💡 *Советы для лучших ответов:*
• Будьте конкретны в вопросах
• Указывайте контекст (тренировки, диета, здоровье)
• Задавайте уточняющие вопросы
• Используйте данные из вашего профиля"""
            
            keyboard = [
                [{'text': '❓ Задать вопрос', 'callback_data': 'nutrition_question'}],
                [{'text': '🔙 Назад к помощи', 'callback_data': 'help'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'help_questions_shown'}
            
        except Exception as e:
            logger.error(f"Error handling help questions callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_help_wearables_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle help wearables callback"""
        try:
            message = """🔗 *Фитнес-трекеры - Подключение и использование*

📱 *Поддерживаемые устройства:*
• **Garmin** - часы и фитнес-трекеры
• **Fitbit** - браслеты и часы
• **Oura Ring** - умное кольцо
• **Withings** - весы и трекеры
• **Apple Health** - данные с iPhone
• **Google Fit** - данные с Android

🔄 *Что синхронизируется:*
• Активность и шаги
• Сожженные калории
• Качество сна
• Частота сердечных сокращений
• Вес (если доступно)

📊 *Преимущества подключения:*
• Более точные расчеты калорий
• Учет физической активности
• Анализ сна и восстановления
• Полная картина здоровья
• Персонализированные рекомендации

🔒 *Безопасность:*
• Данные передаются по защищенному соединению
• Мы не храним пароли от ваших аккаунтов
• Вы можете отключить синхронизацию в любое время
• Соблюдаем все стандарты защиты данных"""
            
            keyboard = [
                [{'text': '🔗 Подключить трекер', 'callback_data': 'connect_wearable'}],
                [{'text': '🔙 Назад к помощи', 'callback_data': 'help'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'help_wearables_shown'}
            
        except Exception as e:
            logger.error(f"Error handling help wearables callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def _handle_stats_today_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle today's statistics callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get today's data
            from datetime import date
            today = date.today()
            today_data = health_service.get_daily_summary(user_id, today)
            
            message = f"""📅 *Статистика за сегодня*

🍽️ *Питание:*
• Записей еды: {today_data.get('total_entries', 0)}
• Общие калории: {today_data.get('total_calories', 0):.0f} ккал
• Белки: {today_data.get('total_protein', 0):.1f}г
• Жиры: {today_data.get('total_fat', 0):.1f}г
• Углеводы: {today_data.get('total_carbs', 0):.1f}г

🎯 *Цель:*
• Норма: {user_profile.daily_calorie_target} ккал
• Достижение: {(today_data.get('total_calories', 0) / user_profile.daily_calorie_target * 100):.1f}%"""
            
            keyboard = [
                [{'text': '📊 Неделя', 'callback_data': 'stats_week'}],
                [{'text': '📈 Месяц', 'callback_data': 'stats_month'}],
                [{'text': '🔙 Назад к статистике', 'callback_data': 'statistics'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'today_stats_shown'}
            
        except Exception as e:
            logger.error(f"Error handling today stats callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()
    
    def _handle_stats_week_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle weekly statistics callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get weekly data
            from datetime import date, timedelta
            today = date.today()
            
            # Calculate weekly averages
            total_entries = 0
            total_calories = 0
            days_with_data = 0
            
            for i in range(7):
                check_date = today - timedelta(days=i)
                day_data = health_service.get_daily_summary(user_id, check_date)
                if day_data.get('total_entries', 0) > 0:
                    total_entries += day_data.get('total_entries', 0)
                    total_calories += day_data.get('total_calories', 0)
                    days_with_data += 1
            
            avg_calories = total_calories / 7 if days_with_data > 0 else 0
            
            message = f"""📊 *Статистика за неделю*

📈 *Общие показатели:*
• Дней с записями: {days_with_data}/7
• Всего записей: {total_entries}
• Средние калории в день: {avg_calories:.0f} ккал

🎯 *Достижение цели:*
• Среднее достижение: {(avg_calories / user_profile.daily_calorie_target * 100):.1f}%"""
            
            keyboard = [
                [{'text': '📅 Сегодня', 'callback_data': 'stats_today'}],
                [{'text': '📈 Месяц', 'callback_data': 'stats_month'}],
                [{'text': '🔙 Назад к статистике', 'callback_data': 'statistics'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'week_stats_shown'}
            
        except Exception as e:
            logger.error(f"Error handling week stats callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()
    
    def _handle_stats_month_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle monthly statistics callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Get monthly data (last 30 days)
            from datetime import date, timedelta
            today = date.today()
            
            # Calculate monthly averages
            total_entries = 0
            total_calories = 0
            days_with_data = 0
            
            for i in range(30):
                check_date = today - timedelta(days=i)
                day_data = health_service.get_daily_summary(user_id, check_date)
                if day_data.get('total_entries', 0) > 0:
                    total_entries += day_data.get('total_entries', 0)
                    total_calories += day_data.get('total_calories', 0)
                    days_with_data += 1
            
            avg_calories = total_calories / 30 if days_with_data > 0 else 0
            consistency = (days_with_data / 30) * 100
            
            message = f"""📈 *Статистика за месяц*

📊 *Общие показатели:*
• Дней с записями: {days_with_data}/30
• Консистентность: {consistency:.1f}%
• Всего записей: {total_entries}
• Средние калории в день: {avg_calories:.0f} ккал

🎯 *Достижение цели:*
• Среднее достижение: {(avg_calories / user_profile.daily_calorie_target * 100):.1f}%"""
            
            keyboard = [
                [{'text': '📅 Сегодня', 'callback_data': 'stats_today'}],
                [{'text': '📊 Неделя', 'callback_data': 'stats_week'}],
                [{'text': '🔙 Назад к статистике', 'callback_data': 'statistics'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'month_stats_shown'}
            
        except Exception as e:
            logger.error(f"Error handling month stats callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()
    
    def _handle_stats_progress_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle progress statistics callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile:
                message = "❌ *Профиль не найден*\\n\\nСначала завершите настройку профиля."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'error', 'reason': 'Profile not found'}
            
            # Calculate progress towards goal
            current_weight = user_profile.current_weight_kg
            target_weight = user_profile.target_weight_kg
            goal = user_profile.goal
            
            if goal == 'lose_weight':
                progress = ((current_weight - target_weight) / (current_weight - target_weight + 0.1)) * 100
            elif goal == 'gain_weight':
                progress = ((target_weight - current_weight) / (target_weight - current_weight + 0.1)) * 100
            else:  # maintain_weight
                progress = 100
            
            message = f"""📋 *Прогресс к цели*

🎯 *Ваша цель:*
• {goal.replace('_', ' ').title()}
• Текущий вес: {current_weight} кг
• Целевой вес: {target_weight} кг
• Прогресс: {progress:.1f}%

💪 *Следующие шаги:*
• Продолжайте вести дневник питания
• Следите за калорийностью
• Регулярно взвешивайтесь"""
            
            keyboard = [
                [{'text': '📅 Сегодня', 'callback_data': 'stats_today'}],
                [{'text': '📊 Неделя', 'callback_data': 'stats_week'}],
                [{'text': '🔙 Назад к статистике', 'callback_data': 'statistics'}]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'progress_stats_shown'}
            
        except Exception as e:
            logger.error(f"Error handling progress stats callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()
    
    def send_message_with_main_menu_button(self, chat_id: int, text: str, inline_keyboard: list = None) -> bool:
        """Send message with inline keyboard and main menu button"""
        try:
            # Parse markdown to entities
            plain_text, entities = parse_markdown_to_entities(text)
            
            # Build payload
            payload = {
                'chat_id': chat_id,
                'text': plain_text
            }
            
            # Add entities if any
            if entities:
                payload['entities'] = entities
            
            # Build inline keyboard
            if inline_keyboard:
                cleaned_keyboard = clean_keyboard_markup(inline_keyboard)
                # Add main menu button to the keyboard
                cleaned_keyboard.append([{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}])
            else:
                # If no keyboard provided, create one with just main menu button
                cleaned_keyboard = [[{'text': '🎯 Главное меню', 'callback_data': 'main_menu'}]]
            
            payload['reply_markup'] = {
                'inline_keyboard': cleaned_keyboard
            }
            
            # Логируем payload перед отправкой
            logger.debug(f"Telegram payload with main menu: {payload}")
            
            # Send message
            response = requests.post(f"{self.base_url}/sendMessage", json=payload)
            try:
                response.raise_for_status()
            except Exception as e:
                logger.error(f"Telegram API error: {response.text}")
                raise
            return True
            
        except Exception as e:
            # Логируем подробности ошибки
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Error sending message with main menu: {str(e)} | Response: {e.response.text}")
            else:
                logger.error(f"Error sending message with main menu: {str(e)}")
            return False
    
    def _handle_main_menu_text(self, user_id: int, chat_id: int, user_profile) -> Dict:
        """Handle main menu button press"""
        try:
            return self.send_main_menu_message(chat_id, user_id)
        except Exception as e:
            logger.error(f"Error handling main menu text: {str(e)}")
            return {'status': 'error', 'error': str(e)}
    
    def send_main_menu_message(self, chat_id: int, user_id: int, message_id: int = None) -> Dict:
        """Send unified main menu message with full user profile"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            user_profile = health_service.get_user_profile(user_id)
            
            if not user_profile or not self._is_onboarding_complete(user_profile):
                message = """👋 *Добро пожаловать в Vector-Health AI Nutritionist!*

Я ваш персональный ИИ-нутрициолог. Для начала работы нужно настроить профиль.

Нажмите кнопку ниже, чтобы начать настройку."""
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
            else:
                message = f"""🎯 *Vector-Health AI Nutritionist*

Добро пожаловать! Я ваш персональный ИИ-нутрициолог.

📊 *Ваш профиль:*
• Цель: {user_profile.goal.replace('_', ' ').title()}
• Дневная норма: {user_profile.daily_calorie_target} ккал
• Белки: {user_profile.daily_protein_target_g}г | Жиры: {user_profile.daily_fat_target_g}г | Углеводы: {user_profile.daily_carbs_target_g}г

Выберите действие:"""
                keyboard = self._get_main_menu_keyboard()
            
            # Send or edit message based on whether message_id is provided
            if message_id:
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            else:
                self.send_message_with_main_menu_button(chat_id, message, keyboard)
            
            return {'status': 'success', 'action': 'main_menu_shown'}
            
        except Exception as e:
            logger.error(f"Error sending main menu message: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_dialog_state(self, user_id: int, chat_id: int, text: str, current_state: str, user_profile) -> Dict:
        """Handle user input when in a dialog state"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            if current_state == States.GOAL_CHANGE_CURRENT_WEIGHT:
                return self._handle_goal_change_current_weight(user_id, chat_id, text, health_service)
            elif current_state == States.GOAL_CHANGE_TARGET_WEIGHT:
                return self._handle_goal_change_target_weight(user_id, chat_id, text, health_service)
            elif current_state == States.REPORT_TIME_INPUT:
                return self._handle_report_time_input(user_id, chat_id, text, health_service)
            elif current_state.startswith('food_edit_'):
                return self._handle_food_edit_input(user_id, chat_id, text, current_state, health_service)
            else:
                # Unknown state, clear it and return to main menu
                state_manager.clear_state(user_id)
                return self.send_main_menu_message(chat_id, user_id)
                
        except Exception as e:
            logger.error(f"Error handling dialog state: {str(e)}")
            state_manager.clear_state(user_id)
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_settings_goal_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle goal change callback"""
        try:
            state_manager.set_state(user_id, States.GOAL_CHANGE_CURRENT_WEIGHT)
            message = "Введите ваш текущий вес (кг):"
            keyboard = [[{'text': '🔙 Отмена', 'callback_data': 'back_to_main'}]]
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'goal_change_started'}
        except Exception as e:
            logger.error(f"Error handling goal change callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_settings_reports_time_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle report time change callback"""
        try:
            state_manager.set_state(user_id, States.REPORT_TIME_INPUT)
            message = "Введите желаемое время для получения ежедневного отчета в формате ЧЧ:ММ (например, 21:00):"
            keyboard = [[{'text': '🔙 Отмена', 'callback_data': 'back_to_main'}]]
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'report_time_change_started'}
        except Exception as e:
            logger.error(f"Error handling report time callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_settings_reset_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle profile reset callback"""
        try:
            message = """⚠️ *Внимание!*

Вы уверены, что хотите сбросить свой профиль? Все ваши цели и настройки будут удалены, и вам придется пройти регистрацию заново. Данные о приемах пищи и активности останутся."""
            
            keyboard = [
                [
                    {'text': 'Да, сбросить', 'callback_data': 'settings:reset_confirm'},
                    {'text': 'Отмена', 'callback_data': 'settings:reset_cancel'}
                ]
            ]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'reset_confirmation_shown'}
        except Exception as e:
            logger.error(f"Error handling reset callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_settings_reset_confirm_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle profile reset confirmation"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Reset user profile (clear all fields except user_id and chat_id)
            reset_data = {
                'gender': None,
                'age': None,
                'height_cm': None,
                'current_weight_kg': None,
                'target_weight_kg': None,
                'goal': None,
                'activity_level': None,
                'bmr': None,
                'tdee': None,
                'daily_calorie_target': None,
                'daily_protein_target_g': None,
                'daily_fat_target_g': None,
                'daily_carbs_target_g': None,
                'daily_report_time': None,
                'terra_user_id': None
            }
            
            success = health_service.update_user_profile(user_id, reset_data)
            
            if success:
                message = "✅ Профиль успешно сброшен! Теперь давайте настроим его заново."
                keyboard = [[{'text': '🚀 Начать настройку', 'callback_data': 'start_onboarding'}]]
            else:
                message = "❌ Ошибка при сбросе профиля. Попробуйте позже."
                keyboard = [[{'text': '🔙 Назад в меню', 'callback_data': 'back_to_main'}]]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'profile_reset'}
            
        except Exception as e:
            logger.error(f"Error handling reset confirm callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_settings_reset_cancel_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle profile reset cancellation"""
        try:
            return self._handle_settings_callback(user_id, chat_id, message_id)
        except Exception as e:
            logger.error(f"Error handling reset cancel callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_settings_edit_food_callback(self, user_id: int, chat_id: int, message_id: int) -> Dict:
        """Handle food edit callback"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            # Get today's food logs
            today = date.today()
            food_logs = health_service.get_food_logs_for_date(user_id, today)
            if not food_logs:
                message = "📝 У вас нет записей о приемах пищи за сегодня."
                keyboard = [[{'text': '🔙 Назад в настройки', 'callback_data': 'nav:back:settings'}]]
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'success', 'action': 'no_food_logs_today'}
            message = "Выберите приём пищи, который хотите изменить или удалить:"
            keyboard = []
            for food_log in food_logs:
                dish_name = food_log.dish_name[:20] + "..." if len(food_log.dish_name) > 20 else food_log.dish_name
                weight_text = f"{food_log.estimated_weight_g}г" if food_log.estimated_weight_g else "~г"
                button_text = f"{dish_name} - {food_log.calories} ккал, {weight_text}"
                callback_data = f'food:options:{food_log.log_id}'
                keyboard.append([{'text': button_text, 'callback_data': callback_data}])
            keyboard.append([{'text': '🔙 Назад в настройки', 'callback_data': 'nav:back:settings'}])
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'food_edit_list_shown'}
        except Exception as e:
            logger.error(f"Error handling food edit callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_food_edit_callback(self, user_id: int, chat_id: int, message_id: int, log_id: str) -> Dict:
        """Handle food edit selection (new format)"""
        try:
            message = "Что вы хотите сделать?"
            keyboard = [
                [
                    {'text': 'Изменить', 'callback_data': f'food:edit_field:{log_id}:select'},
                    {'text': 'Удалить', 'callback_data': f'food:delete:{log_id}'}
                ],
                [{'text': '🔙 Назад', 'callback_data': 'nav:back:settings_edit_food'}]
            ]
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'food_action_selection'}
        except Exception as e:
            logger.error(f"Error handling food edit callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_food_edit_field_callback(self, user_id: int, chat_id: int, message_id: int, log_id: str, field: str) -> Dict:
        """Handle food edit field selection (new format)"""
        try:
            if field == 'select':
                message = "Какое поле вы хотите изменить?"
                keyboard = [
                    [{'text': 'Калории', 'callback_data': f'food:edit_field:{log_id}:calories'}],
                    [{'text': 'Вес (г)', 'callback_data': f'food:edit_field:{log_id}:weight'}],
                    [{'text': 'Белки (г)', 'callback_data': f'food:edit_field:{log_id}:protein'}],
                    [{'text': 'Жиры (г)', 'callback_data': f'food:edit_field:{log_id}:fat'}],
                    [{'text': 'Углеводы (г)', 'callback_data': f'food:edit_field:{log_id}:carbs'}]
                ]
                keyboard.append([{'text': '🔙 Назад', 'callback_data': f'food:options:{log_id}'}])
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
                return {'status': 'success', 'action': 'food_edit_field_selection'}
            
            # Handle specific field selection
            field_state_map = {
                'calories': States.FOOD_EDIT_CALORIES,
                'weight': States.FOOD_EDIT_WEIGHT,
                'protein': States.FOOD_EDIT_PROTEIN,
                'fat': States.FOOD_EDIT_FAT,
                'carbs': States.FOOD_EDIT_CARBS
            }
            
            state = field_state_map.get(field)
            if not state:
                self.edit_message_with_keyboard(chat_id, message_id, "Ошибка: неизвестное поле.", 
                                               [[{'text': '🔙 Назад', 'callback_data': f'food:options:{log_id}'}]])
                return {'status': 'error', 'error': 'Unknown field'}
            
            # Set state and store log_id
            state_manager.set_state(user_id, state)
            state_manager.update_state_data(user_id, {'log_id': log_id})
            
            # Get field display name
            field_names = {
                'calories': 'калорий',
                'weight': 'веса (г)',
                'protein': 'белков (г)',
                'fat': 'жиров (г)',
                'carbs': 'углеводов (г)'
            }
            
            field_name = field_names.get(field, field)
            message = f"Введите новое количество {field_name}:"
            keyboard = [[{'text': '🔙 Отмена', 'callback_data': f'food:options:{log_id}'}]]
            
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'food_edit_started'}
            
        except Exception as e:
            logger.error(f"Error handling food edit field callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _handle_food_delete_callback(self, user_id: int, chat_id: int, message_id: int, log_id: str) -> Dict:
        """Handle food deletion (new format)"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Delete the food log
            success = health_service.delete_food_log(log_id)
            
            if success:
                message = "✅ Запись о приёме пищи успешно удалена!"
            else:
                message = "❌ Ошибка при удалении записи. Попробуйте позже."
            
            keyboard = [[{'text': '🔙 Назад к списку', 'callback_data': 'nav:back:settings_edit_food'}]]
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'action': 'food_deleted'}
            
        except Exception as e:
            logger.error(f"Error handling food delete callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_goal_change_current_weight(self, user_id: int, chat_id: int, text: str, health_service) -> Dict:
        """Handle current weight input for goal change"""
        try:
            weight = float(text.strip())
            if weight <= 0 or weight > 500:
                self.send_message(chat_id, "Пожалуйста, введите корректный вес (от 1 до 500 кг):")
                return {'status': 'success', 'action': 'invalid_weight'}
            
            # Store current weight and ask for target weight
            state_manager.set_state(user_id, States.GOAL_CHANGE_TARGET_WEIGHT, {'current_weight': weight})
            
            self.send_message(chat_id, "Введите ваш желаемый вес (кг):")
            return {'status': 'success', 'action': 'target_weight_requested'}
            
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите число (например, 70.5):")
            return {'status': 'success', 'action': 'invalid_input'}
        except Exception as e:
            logger.error(f"Error handling current weight input: {str(e)}")
            state_manager.clear_state(user_id)
            return {'status': 'error', 'error': str(e)}

    def _handle_goal_change_target_weight(self, user_id: int, chat_id: int, text: str, health_service) -> Dict:
        """Handle target weight input for goal change"""
        try:
            target_weight = float(text.strip())
            if target_weight <= 0 or target_weight > 500:
                self.send_message(chat_id, "Пожалуйста, введите корректный вес (от 1 до 500 кг):")
                return {'status': 'success', 'action': 'invalid_weight'}
            
            # Get stored current weight
            state_data = state_manager.get_state_data(user_id)
            current_weight = state_data.get('current_weight')
            
            # Debug logging
            logger.info(f"Goal change target weight - User: {user_id}, State data: {state_data}, Current weight: {current_weight}")
            
            if not current_weight:
                self.send_message(chat_id, "Ошибка: не найден текущий вес. Попробуйте снова.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Missing current weight'}
            
            # Update user profile
            updates = {
                'current_weight_kg': current_weight,
                'target_weight_kg': target_weight
            }
            
            success = health_service.update_user_profile(user_id, updates)
            
            if success:
                # Recalculate targets
                health_service.calculate_user_targets(user_id)
                
                # Get updated profile
                user_profile = health_service.get_user_profile(user_id)
                
                message = f"""✅ *Цели успешно обновлены!*

📊 *Новые показатели:*
• Текущий вес: {current_weight} кг
• Целевой вес: {target_weight} кг
• BMR: {user_profile.bmr} ккал
• TDEE: {user_profile.tdee} ккал
• Дневная норма: {user_profile.daily_calorie_target} ккал
• Белки: {user_profile.daily_protein_target_g}г
• Жиры: {user_profile.daily_fat_target_g}г
• Углеводы: {user_profile.daily_carbs_target_g}г"""
                
                # Clear state and show main menu
                state_manager.clear_state(user_id)
                return self.send_main_menu_message(chat_id, user_id)
            else:
                self.send_message(chat_id, "❌ Ошибка при обновлении целей. Попробуйте позже.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Failed to update goals'}
            
        except ValueError:
            self.send_message(chat_id, "Пожалуйста, введите число (например, 65.0):")
            return {'status': 'success', 'action': 'invalid_input'}
        except Exception as e:
            logger.error(f"Error handling target weight input: {str(e)}")
            state_manager.clear_state(user_id)
            return {'status': 'error', 'error': str(e)}

    def _handle_report_time_input(self, user_id: int, chat_id: int, text: str, health_service) -> Dict:
        """Handle report time input"""
        try:
            # Parse time input (HH:MM format)
            time_str = text.strip()
            
            # Validate time format
            try:
                hour, minute = map(int, time_str.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("Invalid time range")
                report_time = time(hour, minute)
            except (ValueError, TypeError):
                self.send_message(chat_id, "Пожалуйста, введите время в формате ЧЧ:ММ (например, 21:00):")
                return {'status': 'success', 'action': 'invalid_time_format'}
            
            # Update user profile
            success = health_service.update_user_profile(user_id, {'daily_report_time': report_time})
            
            if success:
                message = f"✅ Время ежедневного отчета установлено на {time_str} (МСК)"
                state_manager.clear_state(user_id)
                return self.send_main_menu_message(chat_id, user_id)
            else:
                self.send_message(chat_id, "❌ Ошибка при установке времени. Попробуйте позже.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Failed to update report time'}
            
        except Exception as e:
            logger.error(f"Error handling report time input: {str(e)}")
            state_manager.clear_state(user_id)
            return {'status': 'error', 'error': str(e)}

    def _handle_food_edit_input(self, user_id: int, chat_id: int, text: str, current_state: str, health_service) -> Dict:
        """Handle food edit input based on current state"""
        try:
            state_data = state_manager.get_state_data(user_id)
            log_id = state_data.get('log_id')
            
            if not log_id:
                self.send_message(chat_id, "Ошибка: не найден ID записи. Попробуйте снова.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Missing log_id'}
            
            # Parse the new value
            try:
                new_value = float(text.strip())
                if new_value < 0:
                    raise ValueError("Negative value")
            except ValueError:
                self.send_message(chat_id, "Пожалуйста, введите положительное число:")
                return {'status': 'success', 'action': 'invalid_input'}
            
            # Determine which field to update based on state
            field_map = {
                States.FOOD_EDIT_CALORIES: 'calories',
                States.FOOD_EDIT_WEIGHT: 'estimated_weight_g',
                States.FOOD_EDIT_PROTEIN: 'protein_g',
                States.FOOD_EDIT_FAT: 'fat_g',
                States.FOOD_EDIT_CARBS: 'carbs_g'
            }
            
            field = field_map.get(current_state)
            if not field:
                self.send_message(chat_id, "Ошибка: неизвестное поле для редактирования.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Unknown edit field'}
            
            # Get current food log data for comparison
            current_food_log = health_service.get_food_log_by_id(log_id)
            if not current_food_log:
                self.send_message(chat_id, "Ошибка: запись о еде не найдена.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Food log not found'}
            
            # Update the food log
            success = health_service.update_food_log(log_id, {field: new_value})
            
            if success:
                # Get updated food log to show new values
                updated_food_log = health_service.get_food_log_by_id(log_id)
                
                # Get field display name for success message
                field_names = {
                    'calories': 'Калории',
                    'estimated_weight_g': 'Вес',
                    'protein_g': 'Белки',
                    'fat_g': 'Жиры',
                    'carbs_g': 'Углеводы'
                }
                field_name = field_names.get(field, field)
                
                # Create success message
                if field == 'estimated_weight_g':
                    # Show recalculated nutrition values when weight is changed
                    message = f"""✅ *Вес успешно обновлен!*

📊 *Новые значения:*
• Вес: {new_value}г (было {float(current_food_log.estimated_weight_g)}г)
• Калории: {int(updated_food_log.calories)} ккал (было {int(current_food_log.calories)} ккал)
• Белки: {float(updated_food_log.protein_g)}г (было {float(current_food_log.protein_g)}г)
• Жиры: {float(updated_food_log.fat_g)}г (было {float(current_food_log.fat_g)}г)
• Углеводы: {float(updated_food_log.carbs_g)}г (было {float(current_food_log.carbs_g)}г)

🔄 *Значения пересчитаны пропорционально новому весу*"""
                else:
                    # For other fields, show simple update message
                    message = f"✅ {field_name} успешно обновлено на {new_value}"
                
                state_manager.clear_state(user_id)
                return self.send_main_menu_message(chat_id, user_id)
            else:
                self.send_message(chat_id, "❌ Ошибка при обновлении записи. Попробуйте позже.")
                state_manager.clear_state(user_id)
                return {'status': 'error', 'error': 'Failed to update food log'}
            
        except Exception as e:
            logger.error(f"Error handling food edit input: {str(e)}")
            state_manager.clear_state(user_id)
            return {'status': 'error', 'error': str(e)}

    def _handle_onboarding_goal_callback(self, user_id: int, chat_id: int, message_id: int, goal: str) -> Dict:
        """Handle goal selection during onboarding"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Update user profile with selected goal
            health_service.update_user_profile(user_id, {'goal': goal})
            
            if goal == 'maintain_weight':
                # For maintain weight, set target = current weight and go to activity
                user_profile = health_service.get_user_profile(user_id)
                health_service.update_user_profile(user_id, {'target_weight_kg': user_profile.current_weight_kg})
                
                message = """Какой у вас уровень активности?

1. Малоподвижный – Минимальные физические нагрузки
2. Умеренный - Легкие упражнения 1-3 раза в неделю
3. Активный - Умеренные упражнения 3-5 раз в неделю

Выберите ваш уровень активности:"""
                
                keyboard = [
                    [{'text': '1️⃣ Малоподвижный', 'callback_data': 'onboarding_activity_sedentary'}],
                    [{'text': '2️⃣ Умеренный', 'callback_data': 'onboarding_activity_moderate'}],
                    [{'text': '3️⃣ Активный', 'callback_data': 'onboarding_activity_active'}]
                ]
                
                self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            else:
                # Ask for target weight
                message = "Какой у вас целевой вес в килограммах? (например, 65)"
                self.edit_message_with_keyboard(chat_id, message_id, message, [])
            
            return {'status': 'success', 'goal': goal}
            
        except Exception as e:
            logger.error(f"Error handling onboarding goal callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()

    def _handle_onboarding_activity_callback(self, user_id: int, chat_id: int, message_id: int, activity: str) -> Dict:
        """Handle activity level selection during onboarding"""
        db = None
        try:
            db = next(get_db())
            health_service = HealthService(db)
            
            # Update user profile with selected activity level
            health_service.update_user_profile(user_id, {'activity_level': activity})
            
            # Calculate user targets
            health_service.calculate_user_targets(user_id)
            
            # Get updated profile to show calculated values
            user_profile = health_service.get_user_profile(user_id)
            
            # Send completion message
            message = f"""🎉 *Настройка профиля завершена!*

Ваш персональный план питания готов! Я рассчитал ваши дневные нормы на основе ваших целей.

📊 *Ваши дневные нормы:*
• Калории: {user_profile.daily_calorie_target} ккал
• Белки: {user_profile.daily_protein_target_g}г
• Жиры: {user_profile.daily_fat_target_g}г
• Углеводы: {user_profile.daily_carbs_target_g}г

Теперь вы можете:
📸 Отправлять фотографии приемов пищи для автоматической записи
📝 Описывать еду текстом
📊 Получать дневные отчеты с помощью /summary
🔗 Подключать носимые устройства с помощью /connect_wearable

Давайте начнем ваш путь к здоровью! Отправьте мне фотографию или описание вашего следующего приема пищи."""
            
            keyboard = self._get_main_menu_keyboard()
            self.edit_message_with_keyboard(chat_id, message_id, message, keyboard)
            return {'status': 'success', 'activity': activity}
            
        except Exception as e:
            logger.error(f"Error handling onboarding activity callback: {str(e)}")
            return {'status': 'error', 'error': str(e)}
        finally:
            if db:
                db.close()