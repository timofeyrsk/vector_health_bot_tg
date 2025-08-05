import os
import sys
import logging
import time
from sqlalchemy.orm import Session
from database.connection import get_db
from models.user_profile import UserProfile
from services.telegram_service import TelegramService

# --- ТЕКСТ СООБЩЕНИЯ ДЛЯ РАССЫЛКИ ---
MESSAGE_TEXT = """
👋 *Привет! У нас большое обновление!*

Мы внимательно изучили ваши отзывы и внесли несколько ключевых улучшений, чтобы сделать бота еще умнее и удобнее.

Вот что нового:

📊 **Дневная сводка стала подробнее!**
Теперь в отчете вы видите полный список съеденных за день блюд, а персональные рекомендации от ИИ стали еще точнее, так как формируются на основе вашего реального прогресса.

🧠 **Бот теперь "помнит" вашу историю питания!**
Задавайте вопросы вроде "Что я ел вчера?" или "Почему я превысил норму по жирам?", и ИИ ответит, основываясь на данных из вашего дневника. Ваши беседы стали по-настояшему персональными.

⏰ **Управляйте временем ежедневных отчетов!**
Хотите получать сводку в удобное для вас время? Просто зайдите в `⚙️ Настройки` -> `Время отчёта` и установите его (по МСК).

Спасибо, что вы с нами! Мы продолжаем делать бота лучше для вас. Попробуйте новые функции прямо сейчас!
"""
# -----------------------------------------

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_broadcast():
    logging.info("Starting broadcast...")
    db: Session = next(get_db())
    telegram_service = TelegramService()
    
    try:
        # Получаем все chat_id из базы
        users = db.query(UserProfile.chat_id).filter(UserProfile.chat_id.isnot(None)).all()
        chat_ids = [user.chat_id for user in users]
        
        if not chat_ids:
            logging.warning("No users with chat_id found.")
            return

        logging.info(f"Found {len(chat_ids)} users to message.")
        
        success_count = 0
        fail_count = 0
        
        for i, chat_id in enumerate(chat_ids):
            try:
                # Используем универсальную функцию отправки
                telegram_service.send_message(chat_id, MESSAGE_TEXT)
                logging.info(f"[{i+1}/{len(chat_ids)}] Message sent to chat_id: {chat_id}")
                success_count += 1
            except Exception as e:
                logging.error(f"Failed to send to chat_id: {chat_id}. Error: {e}")
                fail_count += 1
            
            # Небольшая задержка, чтобы избежать лимитов Telegram (1 сообщение в ~33 мс)
            time.sleep(0.04)

        logging.info("Broadcast finished.")
        logging.info(f"Successfully sent: {success_count}")
        logging.info(f"Failed to send: {fail_count}")

    finally:
        db.close()

if __name__ == "__main__":
    send_broadcast()