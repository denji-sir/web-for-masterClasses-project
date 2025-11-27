# Система уведомлений

## Обзор

Система уведомлений обеспечивает отправку уведомлений пользователям о различных событиях в портале мастер-классов.

**Требования:** 7.1, 7.2, 7.3, 7.4, 7.5

## Компоненты

### 1. Модель Notification (models.py)

Модель для хранения системных уведомлений в базе данных:

```python
class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'reminder', 'cancellation', 'update', 'registration'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
```

### 2. NotificationService (services.py)

Сервис для управления уведомлениями:

#### Основные методы:

- `create_notification(user_id, notification_type, title, message)` - Создать системное уведомление
- `send_status_update(masterclass, message)` - Отправить уведомление об изменении статуса всем участникам
- `send_reminder(user_email, user_name, masterclass)` - Отправить напоминание о предстоящем мастер-классе
- `send_reminders_for_upcoming_masterclasses()` - Отправить напоминания за 24 часа до начала
- `send_cancellation_notification(user_email, user_name, masterclass)` - Отправить уведомление об отмене
- `send_calendar_invite(user_email, user_name, masterclass)` - Отправить календарное приглашение
- `get_user_notifications(user_id, unread_only=False, limit=None)` - Получить уведомления пользователя
- `mark_notification_as_read(notification_id)` - Отметить уведомление как прочитанное
- `mark_all_as_read(user_id)` - Отметить все уведомления пользователя как прочитанные
- `delete_notification(notification_id)` - Удалить уведомление
- `get_unread_count(user_id)` - Получить количество непрочитанных уведомлений

### 3. EmailService (services.py)

Расширенный сервис для отправки email уведомлений:

#### Новые методы:

- `send_status_update_email(user_email, user_name, masterclass, message)` - Email об изменении статуса
- `send_reminder_email(user_email, user_name, masterclass)` - Email напоминание
- `send_calendar_invite(user_email, user_name, masterclass)` - Календарное приглашение (iCalendar)

## Типы уведомлений

1. **reminder** - Напоминание о предстоящем мастер-классе (за 24 часа)
2. **cancellation** - Уведомление об отмене мастер-класса
3. **update** - Уведомление об изменении деталей мастер-класса
4. **registration** - Подтверждение регистрации

## Использование

### Создание уведомления

```python
from services import NotificationService

# Создать системное уведомление
notification = NotificationService.create_notification(
    user_id=user.id,
    notification_type='reminder',
    title='Напоминание о мастер-классе',
    message='Ваш мастер-класс начнется завтра'
)
```

### Отправка уведомления об обновлении

```python
# Отправить уведомление всем участникам мастер-класса
NotificationService.send_status_update(
    masterclass=masterclass,
    message='Время мастер-класса изменено на 15:00'
)
```

### Отправка напоминаний

```python
# Отправить напоминания за 24 часа до начала
count = NotificationService.send_reminders_for_upcoming_masterclasses()
print(f"Отправлено {count} напоминаний")
```

### Получение уведомлений пользователя

```python
# Получить все уведомления
notifications = NotificationService.get_user_notifications(user_id)

# Получить только непрочитанные
unread = NotificationService.get_user_notifications(user_id, unread_only=True)

# Получить последние 10 уведомлений
recent = NotificationService.get_user_notifications(user_id, limit=10)
```

### Управление уведомлениями

```python
# Отметить как прочитанное
NotificationService.mark_notification_as_read(notification_id)

# Отметить все как прочитанные
NotificationService.mark_all_as_read(user_id)

# Удалить уведомление
NotificationService.delete_notification(notification_id)

# Получить количество непрочитанных
count = NotificationService.get_unread_count(user_id)
```

## Автоматическая отправка напоминаний

Для автоматической отправки напоминаний используйте скрипт `send_reminders.py`:

### Запуск вручную

```bash
python send_reminders.py
```

### Настройка cron (Linux/macOS)

Добавьте в crontab для запуска каждый час:

```bash
crontab -e
```

Добавьте строку:

```
0 * * * * cd /path/to/app && /path/to/venv/bin/python send_reminders.py >> /path/to/logs/reminders.log 2>&1
```

### Настройка Task Scheduler (Windows)

1. Откройте Task Scheduler
2. Создайте новую задачу
3. Настройте триггер на запуск каждый час
4. Укажите действие: запуск `python send_reminders.py`

## Календарные приглашения

Система автоматически отправляет календарные приглашения (iCalendar format) при регистрации на мастер-класс.

Приглашение включает:
- Название мастер-класса
- Дату и время начала
- Длительность (по умолчанию 2 часа)
- Описание
- Организатора

Пользователи могут добавить событие в свой календарь (Google Calendar, Outlook, Apple Calendar и т.д.)

## Конфигурация Email

Настройте параметры email в `config.py` или через переменные окружения:

```python
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_USERNAME = 'your-email@gmail.com'
MAIL_PASSWORD = 'your-app-password'
MAIL_DEFAULT_SENDER = 'noreply@masterclass-portal.com'
```

Или через `.env`:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=noreply@masterclass-portal.com
```

## Зависимости

Система требует следующие библиотеки:

- `Flask-Mail` - для отправки email
- `icalendar` - для создания календарных приглашений

Установка:

```bash
pip install -r requirements.txt
```

## Тестирование

Запустите тесты:

```bash
pytest test_notification_service.py -v
```

Тесты покрывают:
- Создание и управление уведомлениями
- Отправку различных типов уведомлений
- Календарные приглашения
- Напоминания за 24 часа

## Логирование

Все операции логируются в стандартный logger Flask:

```python
import logging
logger = logging.getLogger(__name__)
```

Логи включают:
- Успешную отправку уведомлений
- Ошибки при отправке email
- Количество отправленных напоминаний

## Обработка ошибок

Система устойчива к ошибкам:
- Ошибки отправки email не прерывают основные операции (регистрация, отмена)
- Если библиотека `icalendar` не установлена, отправляется обычное email
- Все ошибки логируются для последующего анализа

## Интеграция с существующим кодом

Система автоматически интегрирована с:

1. **RegistrationService.register_user()** - отправляет календарное приглашение при регистрации
2. **MasterclassService.delete_masterclass()** - отправляет уведомления об отмене
3. **RegistrationService.cancel_registration()** - отправляет подтверждение отмены

## Будущие улучшения

Возможные улучшения системы:

1. Push-уведомления для мобильных приложений
2. SMS уведомления
3. Настройки предпочтений уведомлений для пользователей
4. Шаблоны email с HTML форматированием
5. Поддержка нескольких языков
6. Уведомления в реальном времени через WebSocket
