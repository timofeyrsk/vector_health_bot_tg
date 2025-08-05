import openai
import json
import logging
from typing import Dict, List, Optional
from config.settings import Config

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        """Initialize OpenAI service"""
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
    
    def process_user_message(self, message: str, user_context: Optional[Dict] = None) -> Dict:
        """
        Универсальная функция для обработки сообщений пользователя.
        Анализирует намерение и возвращает структурированный JSON ответ.
        """
        try:
            # Подготовка контекста пользователя для промпта
            context_prompt = self._format_context_for_llm(user_context)
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Ты — эксперт по питанию и ИИ-ассистент. Твоя задача — проанализировать сообщение пользователя и определить его намерение.

**Для ответа на вопросы используй предоставленный ниже контекст о пользователе. Он включает его цели и историю питания.**

{context_prompt}

**Правила для nutrition_question:**
- Если пользователь спрашивает о прошлом ("Что я ел вчера?"), найди ответ в разделе "history" контекста.
- Если пользователь спрашивает, почему он превысил норму, сравни данные из "history" или "today_summary" с целями из "profile".
- Если пользователь просит рекомендации на ужин, проанализируй "today_summary", рассчитай оставшийся бюджет КБЖУ и дай конкретные предложения.
- **Всегда основывай свои ответы на предоставленных данных!**

Ты должен определить, является ли сообщение:
1. **food_log** - записью еды (описание приема пищи, фотография еды, информация о том, что пользователь съел)
2. **nutrition_question** - вопросом о питании, здоровье, диете или общим вопросом

ВАЖНО: Возвращай ответ СТРОГО в формате JSON без дополнительного текста.

Если это запись еды (food_log), верни:
{{
  "intent": "food_log",
  "analysis": {{
    "dish_name": "Название блюда",
    "estimated_ingredients": "Предполагаемые ингредиенты через запятую",
    "estimated_weight_g": 250,
    "calories": 450,
    "protein_g": 30,
    "fat_g": 32,
    "carbs_g": 5
  }}
}}

Если это вопрос о питании (nutrition_question), верни:
{{
  "intent": "nutrition_question",
  "answer": "Готовый к отправке текстовый ответ на вопрос пользователя"
}}

Правила определения:
- Если сообщение содержит описание еды, продуктов, приемов пищи, веса, калорий - это food_log
- Если сообщение содержит вопросы о питании, здоровье, диете, советах - это nutrition_question
- Если сообщение содержит команды (/start, /help и т.д.) - это nutrition_question
- Если неясно, но есть упоминания еды - это food_log

Будь точным в оценке питательной ценности для food_log и полезным в ответах для nutrition_question.

ВАЖНО для nutrition_question: Давай развернутые ответы (на 30% больше текста). Если даешь рекомендации по питанию на день - обязательно указывай примерные объемы блюд, размеры порций, конкретные продукты и их количество. Будь максимально практичным и детальным в советах."""
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                max_tokens=1300,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response for message processing: {content}")
            
            # Парсинг JSON ответа
            try:
                # Обработка JSON в markdown блоках
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                result = json.loads(content)
                
                # Валидация структуры ответа
                if 'intent' not in result:
                    raise ValueError("Missing 'intent' field in response")
                
                if result['intent'] == 'food_log':
                    if 'analysis' not in result:
                        raise ValueError("Missing 'analysis' field for food_log intent")
                    required_fields = ['dish_name', 'estimated_ingredients', 'estimated_weight_g', 
                                     'calories', 'protein_g', 'fat_g', 'carbs_g']
                    for field in required_fields:
                        if field not in result['analysis']:
                            raise ValueError(f"Missing '{field}' field in analysis")
                
                elif result['intent'] == 'nutrition_question':
                    if 'answer' not in result:
                        raise ValueError("Missing 'answer' field for nutrition_question intent")
                
                else:
                    raise ValueError(f"Unknown intent: {result['intent']}")
                
                return result
                
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error: {json_error}. Raw content: '{content}'")
                raise ValueError(f"Invalid JSON response from OpenAI: {json_error}")
            
        except openai.OpenAIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise ValueError(f"Ошибка API OpenAI: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing user message: {str(e)}")
            raise ValueError(f"Ошибка обработки сообщения: {str(e)}")
    
    def analyze_food_from_image(self, image_url: str) -> Dict:
        """Analyze food from image using GPT-4o Vision"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты эксперт по питанию. Проанализируй изображение еды и верни JSON объект со следующей структурой:
                        {
                            "dish_name": "string",
                            "estimated_ingredients": "string (список через запятую)",
                            "estimated_weight_g": number,
                            "calories": number,
                            "protein_g": number,
                            "fat_g": number,
                            "carbs_g": number
                        }
                        Будь как можно точнее в оценке питательной ценности на основе изображения. ВАЖНО: Возвращай только валидный JSON без дополнительного текста."""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Проанализируй это изображение еды и предоставь информацию о питательной ценности:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url}
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response for image analysis: {content}")
            
            # Try to parse JSON
            try:
                # Handle JSON wrapped in markdown code blocks
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                return json.loads(content)
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error: {json_error}. Raw content: '{content}'")
                
                # Fallback: create basic food data
                fallback_data = {
                    "dish_name": "Еда на изображении",
                    "estimated_ingredients": "неизвестно",
                    "estimated_weight_g": 250,
                    "calories": 400,
                    "protein_g": 15,
                    "fat_g": 20,
                    "carbs_g": 30
                }
                
                logger.warning(f"Using fallback data for image analysis: {fallback_data}")
                return fallback_data
            
        except Exception as e:
            logger.error(f"Error analyzing food from image: {str(e)}")
            
            # Fallback: create basic food data
            fallback_data = {
                "dish_name": "Еда на изображении",
                "estimated_ingredients": "неизвестно",
                "estimated_weight_g": 250,
                "calories": 400,
                "protein_g": 15,
                "fat_g": 20,
                "carbs_g": 30
            }
            
            logger.warning(f"Using fallback data due to OpenAI error: {fallback_data}")
            return fallback_data
    
    def analyze_food_from_text(self, description: str) -> Dict:
        """Analyze food from text description using GPT-4o"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты эксперт по питанию. Проанализируй описание еды и верни JSON объект со следующей структурой:
                        {
                            "dish_name": "string",
                            "estimated_ingredients": "string (список через запятую)",
                            "estimated_weight_g": number,
                            "calories": number,
                            "protein_g": number,
                            "fat_g": number,
                            "carbs_g": number
                        }
                        Будь как можно точнее в оценке питательной ценности на основе описания. ВАЖНО: Возвращай только валидный JSON без дополнительного текста."""
                    },
                    {
                        "role": "user",
                        "content": f"Проанализируй это описание еды и предоставь информацию о питательной ценности: {description}"
                    }
                ],
                max_tokens=500,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"OpenAI response for food analysis: {content}")
            
            # Try to parse JSON
            try:
                # Handle JSON wrapped in markdown code blocks
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                return json.loads(content)
            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error: {json_error}. Raw content: '{content}'")
                
                # Fallback: create basic food data
                fallback_data = {
                    "dish_name": description[:50] + "..." if len(description) > 50 else description,
                    "estimated_ingredients": "неизвестно",
                    "estimated_weight_g": 200,
                    "calories": 300,
                    "protein_g": 10,
                    "fat_g": 15,
                    "carbs_g": 25
                }
                
                logger.warning(f"Using fallback data for food analysis: {fallback_data}")
                return fallback_data
            
        except Exception as e:
            logger.error(f"Error analyzing food from text: {str(e)}")
            
            # Fallback: create basic food data
            fallback_data = {
                "dish_name": description[:50] + "..." if len(description) > 50 else description,
                "estimated_ingredients": "неизвестно",
                "estimated_weight_g": 200,
                "calories": 300,
                "protein_g": 10,
                "fat_g": 15,
                "carbs_g": 25
            }
            
            logger.warning(f"Using fallback data due to OpenAI error: {fallback_data}")
            return fallback_data
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate text embedding using text-embedding-3-small"""
        try:
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def generate_daily_report(self, user_data: Dict) -> str:
        """Generate personalized daily report using GPT-4o"""
        try:
            # Format eaten foods list
            eaten_foods_text = ""
            eaten_foods = user_data.get('eaten_foods', [])
            if eaten_foods:
                eaten_foods_text = "\n".join([
                    f"• {food['dish_name']} - {food['weight_g']:.0f}г ({food['calories']} ккал)"
                    for food in eaten_foods
                ])
            else:
                eaten_foods_text = "• Пока ничего не съедено"
            
            # Calculate percentages
            daily_calories = user_data.get('daily_calorie_target', 0)
            daily_protein = user_data.get('daily_protein_target_g', 0)
            daily_fat = user_data.get('daily_fat_target_g', 0)
            daily_carbs = user_data.get('daily_carbs_target_g', 0)
            
            calories_consumed = user_data.get('calories_consumed', 0)
            protein_consumed = user_data.get('protein_consumed', 0)
            fat_consumed = user_data.get('fat_consumed', 0)
            carbs_consumed = user_data.get('carbs_consumed', 0)
            
            # Calculate percentages
            calories_percent = (calories_consumed / daily_calories * 100) if daily_calories > 0 else 0
            protein_percent = (protein_consumed / daily_protein * 100) if daily_protein > 0 else 0
            fat_percent = (fat_consumed / daily_fat * 100) if daily_fat > 0 else 0
            carbs_percent = (carbs_consumed / daily_carbs * 100) if daily_carbs > 0 else 0
            
            # Format remaining/surplus values
            remaining_calories = user_data.get('remaining_calories', 0)
            remaining_protein = user_data.get('remaining_protein', 0)
            remaining_fat = user_data.get('remaining_fat', 0)
            remaining_carbs = user_data.get('remaining_carbs', 0)
            
            def format_remaining(value, unit):
                if value >= 0:
                    return f"+{value:.0f} {unit}"
                else:
                    return f"Профицит {abs(value):.0f} {unit}"
            
            prompt = f"""
            Ты — AI-диетолог. Создай краткий, структурированный дневной отчет о питании.
            
            Профиль пользователя:
            - Цель: {user_data.get('goal', 'Неизвестно')}
            - Дневная норма калорий: {daily_calories:.0f} ккал
            - Дневная норма белка: {daily_protein:.1f}г
            - Дневная норма жиров: {daily_fat:.1f}г
            - Дневная норма углеводов: {daily_carbs:.1f}г
            
            Сегодня съедено:
            {eaten_foods_text}
            
            Сегодняшняя активность:
            - Шаги: {user_data.get('steps', 0)}
            - Активные калории сожжены: {user_data.get('active_calories', 0)}
            - Продолжительность сна: {user_data.get('sleep_duration_min', 0) / 60:.1f} часов
            
            Создай отчет в следующей структуре:
            
            ✅ СЪЕДЕНО СЕГОДНЯ:
            {eaten_foods_text}
            
            📊 ПРОГРЕСС СЕГОДНЯ
            • Калории: {calories_consumed:.0f} из {daily_calories:.0f} ккал ({calories_percent:.0f}%)
            • Белки: {protein_consumed:.1f} из {daily_protein:.1f}г ({protein_percent:.0f}%)
            • Жиры: {fat_consumed:.1f} из {daily_fat:.1f}г ({fat_percent:.0f}%)
            • Углеводы: {carbs_consumed:.1f} из {daily_carbs:.1f}г ({carbs_percent:.0f}%)
            
            🎯 ЧТО ОСТАЛОСЬ ДО ЦЕЛИ
            • Калории: {format_remaining(remaining_calories, 'ккал')}
            • Белки: {format_remaining(remaining_protein, 'г')}
            • Жиры: {format_remaining(remaining_fat, 'г')}
            • Углеводы: {format_remaining(remaining_carbs, 'г')}
            
            💡 РЕКОМЕНДАЦИИ НА СЕГОДНЯ
            {self._generate_recommendations_prompt(remaining_calories, remaining_protein, remaining_fat, remaining_carbs)}
            
            🏃‍♂️ АКТИВНОСТЬ
            • Шаги: {user_data.get('steps', 0)}
            • Сон: {user_data.get('sleep_duration_min', 0) / 60:.1f} часов
            
            Будь кратким, конкретным и практичным. Никакой лишней воды!"""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты нутрициолог, создающий краткие, структурированные отчеты. Будь конкретным, практичным и избегай лишних слов."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1100
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            raise
    
    def _format_context_for_llm(self, user_context: Optional[Dict]) -> str:
        """Format user context for LLM prompt"""
        if not user_context:
            return ""
        
        # Extract profile information
        profile = user_context.get('profile', {})
        history = user_context.get('history', {})
        today_summary = user_context.get('today_summary', {})
        
        context_parts = []
        
        # Profile section
        if profile:
            context_parts.append(f"""**ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:**
• Цель: {profile.get('goal', 'Неизвестно')}
• Возраст: {profile.get('age', 'Неизвестно')}
• Пол: {profile.get('gender', 'Неизвестно')}
• Текущий вес: {profile.get('current_weight_kg', 'Неизвестно')} кг
• Целевой вес: {profile.get('target_weight_kg', 'Неизвестно')} кг
• Уровень активности: {profile.get('activity_level', 'Неизвестно')}
• Дневная норма калорий: {profile.get('daily_calorie_target', 'Неизвестно')} ккал
• Дневная норма белка: {profile.get('daily_protein_target_g', 'Неизвестно')}г
• Дневная норма жиров: {profile.get('daily_fat_target_g', 'Неизвестно')}г
• Дневная норма углеводов: {profile.get('daily_carbs_target_g', 'Неизвестно')}г""")
        
        # History section
        if history and history.get('food_logs'):
            food_logs_text = []
            for food in history['food_logs']:
                food_logs_text.append(f"• {food['dish_name']} - {food['weight_g']:.0f}г ({food['calories']} ккал, Б:{food['protein_g']:.1f}г, Ж:{food['fat_g']:.1f}г, У:{food['carbs_g']:.1f}г)")
            
            context_parts.append(f"""**ИСТОРИЯ ПИТАНИЯ ({history.get('period_description', 'Период')}):**
{chr(10).join(food_logs_text)}
**Итого за период:** {history.get('total_calories', 0)} ккал, Б:{history.get('total_protein', 0):.1f}г, Ж:{history.get('total_fat', 0):.1f}г, У:{history.get('total_carbs', 0):.1f}г""")
        
        # Today's summary section
        if today_summary:
            context_parts.append(f"""**СЕГОДНЯШНЯЯ СВОДКА:**
• Потреблено калорий: {today_summary.get('calories_consumed', 0)} из {profile.get('daily_calorie_target', 0)} ккал
• Потреблено белка: {today_summary.get('protein_consumed', 0):.1f} из {profile.get('daily_protein_target_g', 0)}г
• Потреблено жиров: {today_summary.get('fat_consumed', 0):.1f} из {profile.get('daily_fat_target_g', 0)}г
• Потреблено углеводов: {today_summary.get('carbs_consumed', 0):.1f} из {profile.get('daily_carbs_target_g', 0)}г
• Шаги: {today_summary.get('steps', 0)}
• Активные калории: {today_summary.get('active_calories', 0)} ккал""")
        
        return "\n\n".join(context_parts)
    
    def _generate_recommendations_prompt(self, remaining_calories: float, remaining_protein: float, 
                                       remaining_fat: float, remaining_carbs: float) -> str:
        """Generate specific recommendations prompt based on remaining nutrients"""
        
        # Check if user is in surplus
        is_calorie_surplus = remaining_calories < 0
        is_protein_surplus = remaining_protein < 0
        is_fat_surplus = remaining_fat < 0
        is_carbs_surplus = remaining_carbs < 0
        
        if is_calorie_surplus:
            return f"""
            Твоя задача — помочь пользователю избежать дальнейшего переедания.
            
            Текущий статус:
            • Калории: Профицит {abs(remaining_calories):.0f} ккал
            • Белки: {remaining_protein:+.0f}г
            • Жиры: {remaining_fat:+.0f}г  
            • Углеводы: {remaining_carbs:+.0f}г
            
            Рекомендации:
            • Избегай дальнейших приемов пищи
            • Пей больше воды и зеленого чая
            • Если нужно что-то съесть, выбирай низкокалорийные овощи (огурец, сельдерей)
            • Следующий прием пищи планируй с учетом профицита"""
        else:
            return f"""
            Твоя задача — помочь пользователю закрыть его дневные цели по питанию.
            
            Оставшийся бюджет КБЖУ:
            • Калории: {remaining_calories:.0f} ккал
            • Белки: {remaining_protein:.1f}г
            • Жиры: {remaining_fat:.1f}г
            • Углеводы: {remaining_carbs:.1f}г
            
            Предложи 3-4 конкретных варианта блюд (с примерным весом или составом), которые идеально впишутся в этот остаток.
            Учитывай баланс макронутриентов и давай практичные советы."""

    def generate_report(self, user_data: Dict, period: str) -> str:
        """
        Generate universal report for different periods (daily, weekly)
        
        Args:
            user_data: Report data from health_service
            period: 'daily' or 'weekly'
            
        Returns:
            Formatted report text
        """
        try:
            period_names = {
                'daily': 'СЕГОДНЯ',
                'weekly': 'ЗА НЕДЕЛЮ'
            }
            
            period_name = period_names.get(period, period.upper())
            
            if period == 'daily':
                # Use existing daily report logic
                return self.generate_daily_report(user_data)
            
            # For weekly reports only
            prompt = f"""
            Создай ТОЛЬКО недельный отчет о питании. НЕ создавай месячный отчет.
            
            Период: {user_data.get('start_date')} - {user_data.get('end_date')} ({user_data.get('period_days')} дней)
            
            Профиль пользователя:
            - Цель: {user_data.get('goal', 'Неизвестно')}
            - Дневная норма калорий: {user_data.get('daily_calorie_target', 'Неизвестно')}
            - Дневная норма белка: {user_data.get('daily_protein_target_g', 'Неизвестно')}г
            - Дневная норма жиров: {user_data.get('daily_fat_target_g', 'Неизвестно')}г
            - Дневная норма углеводов: {user_data.get('daily_carbs_target_g', 'Неизвестно')}г
            
            Потребление за период:
            - Общее количество потребленных калорий: {user_data.get('calories_consumed', 0)}
            - Потребленный белок: {user_data.get('protein_consumed', 0)}г
            - Потребленные жиры: {user_data.get('fat_consumed', 0)}г
            - Потребленные углеводы: {user_data.get('carbs_consumed', 0)}г
            
            Цели за период:
            - Целевые калории: {user_data.get('period_calorie_target', 0)}
            - Целевой белок: {user_data.get('period_protein_target', 0)}г
            - Целевые жиры: {user_data.get('period_fat_target', 0)}г
            - Целевые углеводы: {user_data.get('period_carbs_target', 0)}г
            
            Активность за период:
            - Общие шаги: {user_data.get('steps', 0)}
            - Средние шаги в день: {user_data.get('avg_steps_per_day', 0):.0f}
            - Общие активные калории: {user_data.get('active_calories', 0)}
            - Средний сон в день: {user_data.get('avg_sleep_hours', 0):.1f} часов
            
            Создай ТОЛЬКО эту структуру:
            
            📊 ПРОГРЕСС ЗА НЕДЕЛЮ
            • Калории: X из Y ккал (Z%)
            • Белки: X из Y г (Z%)
            • Жиры: X из Y г (Z%)
            • Углеводы: X из Y г (Z%)
            
            🎯 ЧТО ОСТАЛОСЬ ДО ЦЕЛИ
            • Калории: +X ккал
            • Белки: +X г
            • Жиры: +X г
            • Углеводы: +X г
            
            🏃‍♂️ АКТИВНОСТЬ
            • Средние шаги в день: X
            • Средний сон: X часов
            
            ВАЖНО: Создай ТОЛЬКО недельный отчет. НЕ добавляй месячный отчет. НЕ добавляй рекомендации на оставшиеся дни."""
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты нутрициолог, создающий краткие, структурированные отчеты. Будь конкретным, практичным и избегай лишних слов. Для недельных отчетов создавай ТОЛЬКО недельный отчет, НЕ добавляй месячный отчет и НЕ давай рекомендации на оставшиеся дни."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=1200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error generating {period} report: {str(e)}")
            raise
    
    def answer_nutrition_question(self, question: str, user_context: Optional[Dict] = None) -> str:
        """Answer nutrition questions using GPT-4o"""
        try:
            context_prompt = ""
            if user_context:
                context_prompt = f"""
                Контекст пользователя:
                - Цель: {user_context.get('goal', 'Неизвестно')}
                - Возраст: {user_context.get('age', 'Неизвестно')}
                - Пол: {user_context.get('gender', 'Неизвестно')}
                - Дневная норма калорий: {user_context.get('daily_calorie_target', 'Неизвестно')}
                
                Недавние данные: {user_context.get('recent_data', {})}
                """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""Ты эксперт по питанию и здоровью. Отвечай на вопросы пользователей о питании, здоровье и фитнесе на русском языке.

{context_prompt}

Будь полезным, точным и дружелюбным. Давай практические советы, основанные на научных данных.

ВАЖНО: Давай развернутые ответы (на 30% больше текста). Если даешь рекомендации по питанию на день - обязательно указывай:
- Примерные объемы блюд (например, "200г куриной грудки", "1 стакан гречки")
- Размеры порций ("1 среднее яблоко", "2 столовые ложки оливкового масла")
- Конкретные продукты и их количество
- Время приема пищи
- Способы приготовления

Будь максимально практичным и детальным в советах. Пользователь должен точно понимать, что и сколько есть."""
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                max_tokens=1300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error answering nutrition question: {str(e)}")
            raise

