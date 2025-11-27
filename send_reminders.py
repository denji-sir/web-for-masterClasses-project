#!/usr/bin/env python
"""
Скрипт для отправки напоминаний о предстоящих мастер-классах
Требования: 7.2

Этот скрипт должен запускаться периодически (например, каждый час через cron)
для отправки напоминаний участникам за 24 часа до начала мастер-класса.

Пример использования в crontab:
0 * * * * cd /path/to/app && /path/to/venv/bin/python send_reminders.py
"""

import sys
import logging
from app import app
from services import NotificationService

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminders.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def send_reminders():
    """Отправить напоминания о предстоящих мастер-классах"""
    with app.app_context():
        try:
            logger.info("Starting reminder sending process...")
            count = NotificationService.send_reminders_for_upcoming_masterclasses()
            logger.info(f"Successfully sent {count} reminders")
            return count
        except Exception as e:
            logger.error(f"Error sending reminders: {e}", exc_info=True)
            return 0


if __name__ == '__main__':
    count = send_reminders()
    sys.exit(0 if count >= 0 else 1)
