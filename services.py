"""
Сервисы для бизнес-логики веб-портала мастер-классов
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from flask import current_app
from flask_mail import Message
from sqlalchemy.exc import IntegrityError, OperationalError, DatabaseError
from sqlalchemy import and_, or_
from extensions import db, mail
from models import User, EventCreator, Masterclass, Registration, UserProfile, Notification, Review
from error_handlers import (
    MasterclassFullError, DuplicateRegistrationError, TimeConstraintError,
    CancellationTooLateError, DatabaseConnectionError, DataValidationError,
    safe_database_operation, validate_masterclass_capacity,
    validate_time_constraint_for_cancellation
)
import logging

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для управления пользователями и аутентификации"""
    
    @staticmethod
    def create_user(email: str, password: str, name: str, phone: str = None, role: str = 'user') -> Optional[User]:
        """
        Создать нового пользователя
        Требования: 5.1, 5.2
        """
        try:
            # Валидация email формата
            if not UserService.validate_email(email):
                return None
            
            user = User(
                email=email.lower().strip(),
                name=name.strip(),
                phone=phone.strip() if phone else None,
                role=role
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            return user
            
        except IntegrityError:
            db.session.rollback()
            return None
    
    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """
        Аутентификация пользователя
        Требования: 5.1
        """
        user = User.query.filter_by(email=email.lower().strip(), is_active=True).first()
        if user and user.check_password(password):
            return user
        return None
    
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        return User.query.filter_by(id=user_id, is_active=True).first()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Получить пользователя по email"""
        return User.query.filter_by(email=email.lower().strip(), is_active=True).first()
    
    @staticmethod
    def update_user(user_id: int, **kwargs) -> bool:
        """
        Обновить данные пользователя
        Требования: 5.1
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            for key, value in kwargs.items():
                if hasattr(user, key) and key != 'id':
                    if key == 'email' and value:
                        if not UserService.validate_email(value):
                            return False
                        setattr(user, key, value.lower().strip())
                    elif key == 'password':
                        user.set_password(value)
                    else:
                        setattr(user, key, value)
            
            db.session.commit()
            return True
            
        except IntegrityError:
            db.session.rollback()
            return False
    
    @staticmethod
    def deactivate_user(user_id: int) -> bool:
        """
        Деактивировать пользователя
        Требования: 5.2
        """
        try:
            user = User.query.get(user_id)
            if user:
                user.is_active = False
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Валидация email адреса
        Требования: 5.2
        """
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email.strip()))


class EventCreatorService:
    """Сервис для бизнес-логики создателей ивентов"""
    
    @staticmethod
    def create_event_creator(user_id: int, company_name: str = None, description: str = None) -> Optional[EventCreator]:
        """
        Создать профиль создателя ивентов
        Требования: 4.1
        """
        try:
            # Проверить, что пользователь существует и имеет соответствующую роль
            user = User.query.get(user_id)
            if not user or user.role != 'event_creator':
                return None
            
            # Проверить, что профиль создателя еще не существует
            existing_creator = EventCreator.query.filter_by(user_id=user_id).first()
            if existing_creator:
                return existing_creator
            
            creator = EventCreator(
                user_id=user_id,
                company_name=company_name.strip() if company_name else None,
                description=description.strip() if description else None
            )
            
            db.session.add(creator)
            db.session.commit()
            return creator
            
        except Exception:
            db.session.rollback()
            return None
    
    @staticmethod
    def get_creator_by_user_id(user_id: int) -> Optional[EventCreator]:
        """Получить создателя по ID пользователя"""
        return EventCreator.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def get_creator_masterclasses(creator_id: int) -> List[Masterclass]:
        """
        Получить все мастер-классы создателя
        Требования: 4.1
        """
        return Masterclass.query.filter_by(creator_id=creator_id).order_by(Masterclass.date_time.desc()).all()
    
    @staticmethod
    def update_creator_profile(creator_id: int, **kwargs) -> bool:
        """
        Обновить профиль создателя ивентов
        Требования: 4.1
        """
        try:
            creator = EventCreator.query.get(creator_id)
            if not creator:
                return False
            
            for key, value in kwargs.items():
                if hasattr(creator, key) and key != 'id':
                    setattr(creator, key, value)
            
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False


class MasterclassService:
    """Сервис для общих операций с мастер-классами"""
    
    @staticmethod
    def get_available_masterclasses(category: str = None, limit: int = None) -> List[Masterclass]:
        """
        Получить доступные мастер-классы
        Требования: 1.1, 1.5, 5.4
        """
        try:
            query = Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time > datetime.utcnow()
            )
            
            if category:
                query = query.filter(Masterclass.category == category)
            
            query = query.order_by(Masterclass.date_time.asc())
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        
        except (OperationalError, DatabaseError) as e:
            logger.error(f"Database error while fetching masterclasses: {e}")
            raise DatabaseConnectionError(e)
        
        except Exception as e:
            logger.error(f"Unexpected error fetching masterclasses: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_masterclass_by_id(masterclass_id: int) -> Optional[Masterclass]:
        """Получить мастер-класс по ID"""
        return Masterclass.query.filter_by(id=masterclass_id, is_active=True).first()
    
    @staticmethod
    def create_masterclass(creator_id: int, title: str, description: str, date_time: datetime,
                          max_participants: int, price: float = None, category: str = None) -> Optional[Masterclass]:
        """
        Создать новый мастер-класс
        Требования: 4.2, 5.1, 5.4
        """
        try:
            # Валидация входных данных - Требование: 5.1
            if not title or not title.strip():
                raise DataValidationError('title', 'Название не может быть пустым')
            
            if max_participants <= 0:
                raise DataValidationError('max_participants', 'Количество участников должно быть больше 0')
            
            if max_participants > 1000:
                raise DataValidationError('max_participants', 'Количество участников не может превышать 1000')
            
            # Проверить, что дата в будущем - Требование: 5.1
            if date_time <= datetime.utcnow():
                raise DataValidationError('date_time', 'Дата и время должны быть в будущем')
            
            # Проверить, что создатель существует - Требование: 5.1
            try:
                creator = EventCreator.query.get(creator_id)
                if not creator:
                    logger.error(f"Event creator {creator_id} not found")
                    return None
            except (OperationalError, DatabaseError) as e:
                logger.error(f"Database error while fetching creator: {e}")
                raise DatabaseConnectionError(e)
            
            # Создать мастер-класс с безопасной операцией БД - Требование: 5.4
            def create_mc():
                masterclass = Masterclass(
                    creator_id=creator_id,
                    title=title.strip(),
                    description=description.strip() if description else None,
                    date_time=date_time,
                    max_participants=max_participants,
                    price=price,
                    category=category.strip() if category else None
                )
                db.session.add(masterclass)
                return masterclass
            
            masterclass = safe_database_operation(create_mc)
            logger.info(f"Masterclass '{title}' created successfully by creator {creator_id}")
            return masterclass
            
        except (DataValidationError, DatabaseConnectionError):
            raise
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error creating masterclass: {e}", exc_info=True)
            return None
    
    @staticmethod
    def update_masterclass(masterclass_id: int, creator_id: int = None, **kwargs) -> bool:
        """
        Обновить мастер-класс
        Требования: 4.3
        """
        try:
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                return False
            
            # Проверить права доступа (если указан creator_id)
            if creator_id and masterclass.creator_id != creator_id:
                return False
            
            for key, value in kwargs.items():
                if hasattr(masterclass, key) and key not in ['id', 'creator_id', 'current_participants']:
                    setattr(masterclass, key, value)
            
            masterclass.updated_at = datetime.utcnow()
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def delete_masterclass(masterclass_id: int, creator_id: int = None) -> bool:
        """
        Удалить мастер-класс
        Требования: 4.4, 5.4
        """
        try:
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                return False
            
            # Проверить права доступа (если указан creator_id)
            if creator_id and masterclass.creator_id != creator_id:
                return False
            
            # Получить всех зарегистрированных участников для уведомления
            registrations = masterclass.registrations.all()
            
            # Удалить мастер-класс (каскадное удаление регистраций)
            db.session.delete(masterclass)
            db.session.commit()
            
            # Отправить уведомления участникам
            for registration in registrations:
                EmailService.send_cancellation_notification(
                    registration.user_email,
                    registration.user_name,
                    masterclass
                )
            
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def search_masterclasses(query: str = None, category: str = None, 
                           date_from: datetime = None, date_to: datetime = None) -> List[Masterclass]:
        """
        Поиск мастер-классов по различным критериям
        Требования: 1.5
        """
        filters = [
            Masterclass.is_active == True,
            Masterclass.date_time > datetime.utcnow()
        ]
        
        if query:
            search_filter = or_(
                Masterclass.title.contains(query),
                Masterclass.description.contains(query)
            )
            filters.append(search_filter)
        
        if category:
            filters.append(Masterclass.category == category)
        
        if date_from:
            filters.append(Masterclass.date_time >= date_from)
        
        if date_to:
            filters.append(Masterclass.date_time <= date_to)
        
        return Masterclass.query.filter(and_(*filters)).order_by(Masterclass.date_time.asc()).all()


class RegistrationService:
    """Сервис для управления регистрациями"""
    
    @staticmethod
    def register_user(masterclass_id: int, user_name: str, user_email: str, user_phone: str = None) -> Optional[Registration]:
        """
        Зарегистрировать пользователя на мастер-класс
        Требования: 2.2, 2.4, 2.5, 1.4, 2.3, 5.4
        """
        try:
            # Валидация email - Требование: 5.2
            if not UserService.validate_email(user_email):
                raise DataValidationError('email', 'Некорректный формат email адреса')
            
            # Валидация имени - Требование: 5.1
            if not user_name or not user_name.strip():
                raise DataValidationError('user_name', 'Имя не может быть пустым')
            
            # Получить мастер-класс с обработкой ошибок БД - Требование: 5.4
            try:
                masterclass = Masterclass.query.get(masterclass_id)
            except (OperationalError, DatabaseError) as e:
                logger.error(f"Database error while fetching masterclass: {e}")
                raise DatabaseConnectionError(e)
            
            if not masterclass:
                logger.warning(f"Masterclass {masterclass_id} not found")
                return None
            
            # Проверить доступность мест - Требование: 1.4
            if masterclass.is_full:
                raise MasterclassFullError(masterclass.title)
            
            # Проверить, что мастер-класс активен и предстоящий - Требование: 2.3
            if not masterclass.is_active:
                logger.warning(f"Attempt to register for inactive masterclass {masterclass_id}")
                return None
            
            if not masterclass.is_upcoming:
                raise TimeConstraintError(
                    f"Регистрация на мастер-класс '{masterclass.title}' закрыта: мероприятие уже прошло"
                )
            
            # Проверить, что пользователь еще не зарегистрирован - Требование: 2.5
            existing_registration = Registration.query.filter_by(
                masterclass_id=masterclass_id,
                user_email=user_email.lower().strip()
            ).first()
            
            if existing_registration:
                raise DuplicateRegistrationError(user_email, masterclass.title)
            
            # Создать регистрацию с использованием безопасной операции БД - Требование: 5.4
            def create_registration():
                registration = Registration(
                    masterclass_id=masterclass_id,
                    user_name=user_name.strip(),
                    user_email=user_email.lower().strip(),
                    user_phone=user_phone.strip() if user_phone else None
                )
                
                # Увеличить счетчик участников
                masterclass.current_participants += 1
                
                db.session.add(registration)
                return registration
            
            registration = safe_database_operation(create_registration)
            
            # Отправить подтверждение и календарное приглашение
            try:
                # Отправить календарное приглашение - Требование: 7.4
                EmailService.send_calendar_invite(user_email, user_name, masterclass)
            except Exception as e:
                logger.error(f"Failed to send calendar invite: {e}")
                # Попробовать отправить обычное подтверждение
                try:
                    EmailService.send_registration_confirmation(user_email, user_name, masterclass)
                except Exception as e2:
                    logger.error(f"Failed to send confirmation email: {e2}")
                # Не прерываем регистрацию из-за ошибки отправки email
            
            logger.info(f"User {user_email} successfully registered for masterclass {masterclass_id}")
            return registration
            
        except (MasterclassFullError, DuplicateRegistrationError, TimeConstraintError, 
                DataValidationError, DatabaseConnectionError):
            # Пробрасываем кастомные исключения для обработки на уровне маршрутов
            raise
        
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error during registration: {e}")
            # Проверяем, не повторная ли это регистрация
            if 'unique_registration_per_masterclass' in str(e):
                raise DuplicateRegistrationError(user_email, masterclass.title if masterclass else "Unknown")
            raise
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error during registration: {e}", exc_info=True)
            return None
    
    @staticmethod
    def cancel_registration(masterclass_id: int, user_email: str) -> bool:
        """
        Отменить регистрацию пользователя
        Требования: 3.2, 3.3, 3.4, 5.4
        """
        try:
            # Валидация email - Требование: 5.2
            if not UserService.validate_email(user_email):
                raise DataValidationError('email', 'Некорректный формат email адреса')
            
            # Найти регистрацию с обработкой ошибок БД - Требование: 5.4
            try:
                registration = Registration.query.filter_by(
                    masterclass_id=masterclass_id,
                    user_email=user_email.lower().strip()
                ).first()
            except (OperationalError, DatabaseError) as e:
                logger.error(f"Database error while fetching registration: {e}")
                raise DatabaseConnectionError(e)
            
            if not registration:
                logger.warning(f"Registration not found for email {user_email} and masterclass {masterclass_id}")
                return False
            
            masterclass = registration.masterclass
            
            # Проверить временные ограничения (24 часа до начала) - Требование: 3.4
            validate_time_constraint_for_cancellation(masterclass)
            
            # Удалить регистрацию и уменьшить счетчик с безопасной операцией БД - Требование: 5.4
            def delete_registration():
                masterclass.current_participants -= 1
                db.session.delete(registration)
            
            safe_database_operation(delete_registration)
            
            # Отправить подтверждение отмены
            try:
                EmailService.send_cancellation_confirmation(user_email, registration.user_name, masterclass)
            except Exception as e:
                logger.error(f"Failed to send cancellation confirmation email: {e}")
                # Не прерываем отмену из-за ошибки отправки email
            
            logger.info(f"Registration cancelled for {user_email} on masterclass {masterclass_id}")
            return True
            
        except (TimeConstraintError, CancellationTooLateError, DataValidationError, DatabaseConnectionError):
            # Пробрасываем кастомные исключения для обработки на уровне маршрутов
            raise
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error during cancellation: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_user_registrations(user_email: str) -> List[Registration]:
        """
        Получить все регистрации пользователя по email
        Требования: 3.1
        """
        return Registration.query.filter_by(
            user_email=user_email.lower().strip()
        ).join(Masterclass).filter(
            Masterclass.is_active == True
        ).order_by(Masterclass.date_time.asc()).all()
    
    @staticmethod
    def get_masterclass_participants(masterclass_id: int) -> List[Registration]:
        """
        Получить всех участников мастер-класса
        Требования: 4.5
        """
        return Registration.query.filter_by(masterclass_id=masterclass_id).order_by(Registration.registered_at.asc()).all()


class EmailService:
    """Сервис для отправки уведомлений"""
    
    @staticmethod
    def send_registration_confirmation(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить подтверждение регистрации
        Требования: 2.4
        """
        try:
            subject = f"Подтверждение регистрации на мастер-класс: {masterclass.title}"
            
            body = f"""
Здравствуйте, {user_name}!

Вы успешно зарегистрировались на мастер-класс:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}
Создатель: {masterclass.creator.company_name or masterclass.creator.user.name}

Спасибо за регистрацию!

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            mail.send(msg)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_cancellation_confirmation(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить подтверждение отмены регистрации
        Требования: 3.3
        """
        try:
            subject = f"Отмена регистрации на мастер-класс: {masterclass.title}"
            
            body = f"""
Здравствуйте, {user_name}!

Ваша регистрация на мастер-класс была отменена:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}

Если у вас есть вопросы, свяжитесь с нами.

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            mail.send(msg)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_cancellation_notification(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить уведомление об отмене мастер-класса
        Требования: 4.4, 5.4
        """
        try:
            subject = f"Мастер-класс отменен: {masterclass.title}"
            
            body = f"""
Здравствуйте, {user_name}!

К сожалению, мастер-класс, на который вы были зарегистрированы, был отменен:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}

Приносим извинения за неудобства.

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            mail.send(msg)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_status_update_email(user_email: str, user_name: str, masterclass: Masterclass, message: str) -> bool:
        """
        Отправить email уведомление об изменении статуса мастер-класса
        Требования: 7.1, 7.5
        """
        try:
            subject = f"Обновление мастер-класса: {masterclass.title}"
            
            body = f"""
Здравствуйте, {user_name}!

Информация о мастер-классе, на который вы зарегистрированы, была обновлена:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}

Изменения:
{message}

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            mail.send(msg)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_reminder_email(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить email напоминание о предстоящем мастер-классе
        Требования: 7.2
        """
        try:
            subject = f"Напоминание: {masterclass.title} завтра!"
            
            body = f"""
Здравствуйте, {user_name}!

Напоминаем, что завтра состоится мастер-класс:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}
Создатель: {masterclass.creator.company_name or masterclass.creator.user.name}

Ждем вас!

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            mail.send(msg)
            return True
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки email: {e}")
            return False
    
    @staticmethod
    def send_calendar_invite(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить календарное приглашение (iCalendar format)
        Требования: 7.4
        """
        try:
            from icalendar import Calendar, Event as iCalEvent
            from datetime import timedelta as td
            
            # Создать календарное событие
            cal = Calendar()
            cal.add('prodid', '-//Masterclass Portal//mxm.dk//')
            cal.add('version', '2.0')
            
            event = iCalEvent()
            event.add('summary', masterclass.title)
            event.add('dtstart', masterclass.date_time)
            # Предполагаем, что мастер-класс длится 2 часа
            event.add('dtend', masterclass.date_time + td(hours=2))
            event.add('description', masterclass.description or '')
            event.add('location', 'Онлайн')
            event.add('organizer', masterclass.creator.company_name or masterclass.creator.user.name)
            
            cal.add_component(event)
            
            # Отправить email с вложением
            subject = f"Календарное приглашение: {masterclass.title}"
            
            body = f"""
Здравствуйте, {user_name}!

Вы зарегистрированы на мастер-класс:

Название: {masterclass.title}
Дата и время: {masterclass.date_time.strftime('%d.%m.%Y в %H:%M')}

Во вложении календарное приглашение для добавления в ваш календарь.

С уважением,
Команда портала мастер-классов
            """
            
            msg = Message(
                subject=subject,
                recipients=[user_email],
                body=body
            )
            
            # Добавить календарное приглашение как вложение
            msg.attach(
                filename=f"masterclass_{masterclass.id}.ics",
                content_type="text/calendar",
                data=cal.to_ical()
            )
            
            mail.send(msg)
            return True
            
        except ImportError:
            # Если библиотека icalendar не установлена, отправить обычное email
            logger.warning("icalendar library not installed, sending regular email")
            return EmailService.send_registration_confirmation(user_email, user_name, masterclass)
            
        except Exception as e:
            current_app.logger.error(f"Ошибка отправки календарного приглашения: {e}")
            return False


class AdminService:
    """Сервис для административных функций"""
    
    @staticmethod
    def get_all_users(include_inactive: bool = False) -> List[User]:
        """
        Получить всех пользователей
        Требования: 5.1
        """
        query = User.query
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(User.created_at.desc()).all()
    
    @staticmethod
    def get_all_event_creators() -> List[EventCreator]:
        """
        Получить всех создателей ивентов
        Требования: 5.1
        """
        return EventCreator.query.join(User).filter(User.is_active == True).order_by(EventCreator.created_at.desc()).all()
    
    @staticmethod
    def get_all_masterclasses(include_inactive: bool = False) -> List[Masterclass]:
        """
        Получить все мастер-классы
        Требования: 5.3
        """
        query = Masterclass.query
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.order_by(Masterclass.created_at.desc()).all()
    
    @staticmethod
    def block_user(user_id: int) -> bool:
        """
        Заблокировать пользователя
        Требования: 5.2
        """
        return UserService.deactivate_user(user_id)
    
    @staticmethod
    def unblock_user(user_id: int) -> bool:
        """
        Разблокировать пользователя
        Требования: 5.2
        """
        try:
            user = User.query.get(user_id)
            if user:
                user.is_active = True
                db.session.commit()
                return True
            return False
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def assign_role(user_id: int, role: str) -> bool:
        """
        Назначить роль пользователю
        Требования: 5.5
        """
        try:
            if role not in ['user', 'event_creator', 'admin']:
                return False
            
            user = User.query.get(user_id)
            if not user:
                return False
            
            old_role = user.role
            user.role = role
            
            # Если пользователь становится создателем ивентов, создать профиль
            if role == 'event_creator' and old_role != 'event_creator':
                existing_creator = EventCreator.query.filter_by(user_id=user_id).first()
                if not existing_creator:
                    creator = EventCreator(user_id=user_id)
                    db.session.add(creator)
            
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Удалить пользователя (только для администраторов)
        Требования: 5.2
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Проверить, что это не единственный администратор
            if user.role == 'admin':
                admin_count = User.query.filter_by(role='admin', is_active=True).count()
                if admin_count <= 1:
                    return False  # Нельзя удалить последнего администратора
            
            db.session.delete(user)
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_system_statistics() -> Dict[str, Any]:
        """
        Получить статистику системы
        Требования: 5.1
        """
        try:
            stats = {
                'total_users': User.query.filter_by(is_active=True).count(),
                'total_event_creators': EventCreator.query.join(User).filter(User.is_active == True).count(),
                'total_masterclasses': Masterclass.query.filter_by(is_active=True).count(),
                'total_registrations': Registration.query.join(Masterclass).filter(Masterclass.is_active == True).count(),
                'upcoming_masterclasses': Masterclass.query.filter(
                    Masterclass.is_active == True,
                    Masterclass.date_time > datetime.utcnow()
                ).count(),
                'past_masterclasses': Masterclass.query.filter(
                    Masterclass.is_active == True,
                    Masterclass.date_time <= datetime.utcnow()
                ).count()
            }
            return stats
        except Exception:
            return {}


class ReviewService:
    """Сервис для управления отзывами и рейтингами"""
    
    @staticmethod
    def create_review(user_id: int, masterclass_id: int, rating: int, comment: str = None) -> Optional[Review]:
        """
        Создать отзыв о мастер-классе
        Требования: 10.4
        """
        try:
            # Валидация рейтинга
            if rating < 1 or rating > 5:
                raise DataValidationError('rating', 'Рейтинг должен быть от 1 до 5')
            
            # Проверить, что пользователь существует
            user = User.query.get(user_id)
            if not user:
                logger.warning(f"User {user_id} not found")
                return None
            
            # Проверить, что мастер-класс существует
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                logger.warning(f"Masterclass {masterclass_id} not found")
                return None
            
            # Проверить, что мастер-класс уже прошел
            if masterclass.is_upcoming:
                raise DataValidationError('masterclass', 'Нельзя оставить отзыв на предстоящий мастер-класс')
            
            # Проверить, что пользователь участвовал в мастер-классе
            registration = Registration.query.filter_by(
                masterclass_id=masterclass_id,
                user_email=user.email
            ).first()
            
            if not registration:
                raise DataValidationError('registration', 'Вы не участвовали в этом мастер-классе')
            
            # Проверить, что отзыв еще не оставлен
            existing_review = Review.query.filter_by(
                user_id=user_id,
                masterclass_id=masterclass_id
            ).first()
            
            if existing_review:
                raise DataValidationError('review', 'Вы уже оставили отзыв на этот мастер-класс')
            
            # Создать отзыв
            review = Review(
                user_id=user_id,
                masterclass_id=masterclass_id,
                rating=rating,
                comment=comment.strip() if comment else None,
                is_approved=True  # По умолчанию одобрен
            )
            
            db.session.add(review)
            db.session.commit()
            
            logger.info(f"Review created by user {user_id} for masterclass {masterclass_id}")
            return review
            
        except (DataValidationError, DatabaseConnectionError):
            raise
        
        except IntegrityError as e:
            db.session.rollback()
            logger.error(f"Integrity error creating review: {e}")
            if 'unique_review' in str(e):
                raise DataValidationError('review', 'Вы уже оставили отзыв на этот мастер-класс')
            raise
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Unexpected error creating review: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_masterclass_reviews(masterclass_id: int, approved_only: bool = True) -> List[Review]:
        """
        Получить все отзывы о мастер-классе
        Требования: 10.4
        """
        query = Review.query.filter_by(masterclass_id=masterclass_id)
        
        if approved_only:
            query = query.filter_by(is_approved=True)
        
        return query.order_by(Review.created_at.desc()).all()
    
    @staticmethod
    def get_masterclass_average_rating(masterclass_id: int) -> Optional[float]:
        """
        Получить средний рейтинг мастер-класса
        Требования: 10.4
        """
        try:
            from sqlalchemy import func
            
            result = db.session.query(func.avg(Review.rating)).filter(
                Review.masterclass_id == masterclass_id,
                Review.is_approved == True
            ).scalar()
            
            return round(result, 1) if result else None
            
        except Exception as e:
            logger.error(f"Error calculating average rating: {e}")
            return None
    
    @staticmethod
    def get_masterclass_review_count(masterclass_id: int) -> int:
        """
        Получить количество отзывов о мастер-классе
        Требования: 10.4
        """
        return Review.query.filter_by(
            masterclass_id=masterclass_id,
            is_approved=True
        ).count()
    
    @staticmethod
    def get_user_review(user_id: int, masterclass_id: int) -> Optional[Review]:
        """
        Получить отзыв пользователя о мастер-классе
        Требования: 10.4
        """
        return Review.query.filter_by(
            user_id=user_id,
            masterclass_id=masterclass_id
        ).first()
    
    @staticmethod
    def update_review(review_id: int, user_id: int, rating: int = None, comment: str = None) -> bool:
        """
        Обновить отзыв
        Требования: 10.4
        """
        try:
            review = Review.query.get(review_id)
            if not review or review.user_id != user_id:
                return False
            
            if rating is not None:
                if rating < 1 or rating > 5:
                    raise DataValidationError('rating', 'Рейтинг должен быть от 1 до 5')
                review.rating = rating
            
            if comment is not None:
                review.comment = comment.strip() if comment else None
            
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def delete_review(review_id: int, user_id: int = None) -> bool:
        """
        Удалить отзыв
        Требования: 10.4
        """
        try:
            review = Review.query.get(review_id)
            if not review:
                return False
            
            # Проверить права доступа (если указан user_id)
            if user_id and review.user_id != user_id:
                return False
            
            db.session.delete(review)
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def approve_review(review_id: int) -> bool:
        """
        Одобрить отзыв (для администраторов)
        Требования: 10.4
        """
        try:
            review = Review.query.get(review_id)
            if not review:
                return False
            
            review.is_approved = True
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def reject_review(review_id: int) -> bool:
        """
        Отклонить отзыв (для администраторов)
        Требования: 10.4
        """
        try:
            review = Review.query.get(review_id)
            if not review:
                return False
            
            review.is_approved = False
            db.session.commit()
            return True
            
        except Exception:
            db.session.rollback()
            return False
    
    @staticmethod
    def get_pending_reviews() -> List[Review]:
        """
        Получить все неодобренные отзывы (для модерации)
        Требования: 10.4
        """
        return Review.query.filter_by(is_approved=False).order_by(Review.created_at.desc()).all()
    
    @staticmethod
    def can_user_review(user_id: int, masterclass_id: int) -> bool:
        """
        Проверить, может ли пользователь оставить отзыв
        Требования: 10.4
        """
        try:
            # Получить пользователя
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Получить мастер-класс
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                return False
            
            # Проверить, что мастер-класс уже прошел
            if masterclass.is_upcoming:
                return False
            
            # Проверить, что пользователь участвовал
            registration = Registration.query.filter_by(
                masterclass_id=masterclass_id,
                user_email=user.email
            ).first()
            
            if not registration:
                return False
            
            # Проверить, что отзыв еще не оставлен
            existing_review = Review.query.filter_by(
                user_id=user_id,
                masterclass_id=masterclass_id
            ).first()
            
            return existing_review is None
            
        except Exception as e:
            logger.error(f"Error checking if user can review: {e}")
            return False


class SearchService:
    """Сервис для комплексного поиска и фильтрации мастер-классов"""
    
    @staticmethod
    def search_masterclasses(
        query: str = None,
        category: str = None,
        date_from: datetime = None,
        date_to: datetime = None,
        price_min: float = None,
        price_max: float = None,
        min_rating: float = None,
        sort_by: str = 'date',
        sort_order: str = 'asc',
        only_available: bool = True
    ) -> List[Masterclass]:
        """
        Комплексный поиск мастер-классов с фильтрацией и сортировкой
        Требования: 8.1, 8.2, 8.3, 8.4
        """
        try:
            from sqlalchemy import func
            
            # Базовый запрос
            query_obj = Masterclass.query.filter(Masterclass.is_active == True)
            
            # Фильтр по доступности (только предстоящие)
            if only_available:
                query_obj = query_obj.filter(Masterclass.date_time > datetime.utcnow())
            
            # Полнотекстовый поиск по названию и описанию - Требование: 8.1
            if query:
                search_filter = or_(
                    Masterclass.title.ilike(f'%{query}%'),
                    Masterclass.description.ilike(f'%{query}%')
                )
                query_obj = query_obj.filter(search_filter)
            
            # Фильтрация по категории
            if category:
                query_obj = query_obj.filter(Masterclass.category == category)
            
            # Фильтрация по дате - Требование: 8.2
            if date_from:
                query_obj = query_obj.filter(Masterclass.date_time >= date_from)
            
            if date_to:
                query_obj = query_obj.filter(Masterclass.date_time <= date_to)
            
            # Фильтрация по цене - Требование: 8.3
            if price_min is not None:
                query_obj = query_obj.filter(Masterclass.price >= price_min)
            
            if price_max is not None:
                query_obj = query_obj.filter(Masterclass.price <= price_max)
            
            # Получить результаты
            masterclasses = query_obj.all()
            
            # Фильтрация по рейтингу (после получения из БД)
            if min_rating is not None:
                filtered_masterclasses = []
                for mc in masterclasses:
                    avg_rating = ReviewService.get_masterclass_average_rating(mc.id)
                    if avg_rating is not None and avg_rating >= min_rating:
                        filtered_masterclasses.append(mc)
                masterclasses = filtered_masterclasses
            
            # Сортировка результатов - Требование: 8.4
            masterclasses = SearchService._sort_masterclasses(
                masterclasses, 
                sort_by, 
                sort_order
            )
            
            return masterclasses
            
        except Exception as e:
            logger.error(f"Error in search_masterclasses: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _sort_masterclasses(
        masterclasses: List[Masterclass],
        sort_by: str = 'date',
        sort_order: str = 'asc'
    ) -> List[Masterclass]:
        """
        Сортировка результатов поиска
        Требования: 8.4
        """
        try:
            reverse = (sort_order == 'desc')
            
            if sort_by == 'date':
                # Сортировка по дате
                return sorted(masterclasses, key=lambda x: x.date_time, reverse=reverse)
            
            elif sort_by == 'price':
                # Сортировка по цене (None в конец)
                return sorted(
                    masterclasses,
                    key=lambda x: (x.price is None, x.price if x.price is not None else 0),
                    reverse=reverse
                )
            
            elif sort_by == 'popularity':
                # Сортировка по популярности (количество регистраций)
                return sorted(
                    masterclasses,
                    key=lambda x: x.current_participants,
                    reverse=not reverse  # Больше участников = более популярный
                )
            
            elif sort_by == 'title':
                # Сортировка по названию
                return sorted(masterclasses, key=lambda x: x.title.lower(), reverse=reverse)
            
            elif sort_by == 'rating':
                # Сортировка по рейтингу
                masterclasses_with_rating = []
                for mc in masterclasses:
                    rating = ReviewService.get_masterclass_average_rating(mc.id)
                    masterclasses_with_rating.append((mc, rating if rating is not None else 0))
                
                sorted_list = sorted(
                    masterclasses_with_rating,
                    key=lambda x: x[1],
                    reverse=not reverse  # Больший рейтинг = лучше
                )
                
                return [mc for mc, _ in sorted_list]
            
            else:
                # По умолчанию сортировка по дате
                return sorted(masterclasses, key=lambda x: x.date_time, reverse=reverse)
                
        except Exception as e:
            logger.error(f"Error sorting masterclasses: {e}")
            return masterclasses
    
    @staticmethod
    def filter_by_date_range(start_date: datetime, end_date: datetime) -> List[Masterclass]:
        """
        Фильтрация мастер-классов по диапазону дат
        Требования: 8.2
        """
        try:
            return Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time >= start_date,
                Masterclass.date_time <= end_date
            ).order_by(Masterclass.date_time.asc()).all()
            
        except Exception as e:
            logger.error(f"Error filtering by date range: {e}")
            return []
    
    @staticmethod
    def filter_by_price_range(min_price: float, max_price: float) -> List[Masterclass]:
        """
        Фильтрация мастер-классов по ценовому диапазону
        Требования: 8.3
        """
        try:
            return Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time > datetime.utcnow(),
                Masterclass.price >= min_price,
                Masterclass.price <= max_price
            ).order_by(Masterclass.date_time.asc()).all()
            
        except Exception as e:
            logger.error(f"Error filtering by price range: {e}")
            return []
    
    @staticmethod
    def save_search_preferences(user_id: int, preferences: Dict[str, Any]) -> bool:
        """
        Сохранить поисковые предпочтения пользователя
        Требования: 8.5
        """
        try:
            import json
            
            # Получить или создать профиль пользователя
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            if not profile:
                profile = UserProfile(user_id=user_id)
                db.session.add(profile)
            
            # Сохранить предпочтения в JSON формате
            # Используем поле interests для хранения поисковых предпочтений
            current_prefs = {}
            if profile.interests:
                try:
                    current_prefs = json.loads(profile.interests)
                except:
                    current_prefs = {}
            
            current_prefs['search_preferences'] = preferences
            profile.interests = json.dumps(current_prefs)
            
            db.session.commit()
            logger.info(f"Search preferences saved for user {user_id}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving search preferences: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_search_preferences(user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить сохраненные поисковые предпочтения пользователя
        Требования: 8.5
        """
        try:
            import json
            
            profile = UserProfile.query.filter_by(user_id=user_id).first()
            
            if not profile or not profile.interests:
                return None
            
            try:
                prefs = json.loads(profile.interests)
                return prefs.get('search_preferences')
            except:
                return None
                
        except Exception as e:
            logger.error(f"Error getting search preferences: {e}")
            return None
    
    @staticmethod
    def get_popular_categories() -> List[tuple]:
        """
        Получить популярные категории с количеством мастер-классов
        """
        try:
            from sqlalchemy import func
            
            results = db.session.query(
                Masterclass.category,
                func.count(Masterclass.id).label('count')
            ).filter(
                Masterclass.is_active == True,
                Masterclass.date_time > datetime.utcnow(),
                Masterclass.category.isnot(None)
            ).group_by(Masterclass.category).order_by(
                func.count(Masterclass.id).desc()
            ).all()
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting popular categories: {e}")
            return []
    
    @staticmethod
    def get_search_suggestions(query: str, limit: int = 5) -> List[str]:
        """
        Получить подсказки для автодополнения поиска
        Требования: 8.1
        """
        try:
            if not query or len(query) < 2:
                return []
            
            # Поиск по названиям мастер-классов
            masterclasses = Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time > datetime.utcnow(),
                Masterclass.title.ilike(f'%{query}%')
            ).limit(limit).all()
            
            suggestions = [mc.title for mc in masterclasses]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error getting search suggestions: {e}")
            return []
    
    @staticmethod
    def get_autocomplete_suggestions(query: str, limit: int = 10) -> List[str]:
        """
        Получить предложения автодополнения для поиска
        Требования: 8.5
        """
        try:
            if not query or len(query) < 2:
                return []
            
            suggestions = set()
            
            # Поиск по названиям мастер-классов
            masterclasses = Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time > datetime.utcnow(),
                or_(
                    Masterclass.title.ilike(f'%{query}%'),
                    Masterclass.description.ilike(f'%{query}%')
                )
            ).limit(limit * 2).all()
            
            # Добавляем названия
            for mc in masterclasses:
                if query.lower() in mc.title.lower():
                    suggestions.add(mc.title)
                
                # Добавляем категории
                if mc.category and query.lower() in mc.category.lower():
                    suggestions.add(mc.category)
            
            # Ограничиваем количество результатов
            return sorted(list(suggestions))[:limit]
            
        except Exception as e:
            logger.error(f"Error getting autocomplete suggestions: {e}")
            return []


class NotificationService:
    """Сервис для управления уведомлениями"""
    
    @staticmethod
    def create_notification(user_id: int, notification_type: str, title: str, message: str) -> Optional[Notification]:
        """
        Создать системное уведомление
        Требования: 7.1
        """
        try:
            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message
            )
            
            db.session.add(notification)
            db.session.commit()
            return notification
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def send_status_update(masterclass: Masterclass, message: str) -> bool:
        """
        Отправить уведомление об изменении статуса мастер-класса всем участникам
        Требования: 7.1, 7.5
        """
        try:
            registrations = masterclass.registrations.all()
            
            for registration in registrations:
                # Создать системное уведомление если пользователь зарегистрирован
                user = User.query.filter_by(email=registration.user_email).first()
                if user:
                    NotificationService.create_notification(
                        user_id=user.id,
                        notification_type='update',
                        title=f'Обновление: {masterclass.title}',
                        message=message
                    )
                
                # Отправить email уведомление
                EmailService.send_status_update_email(
                    registration.user_email,
                    registration.user_name,
                    masterclass,
                    message
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending status update: {e}")
            return False
    
    @staticmethod
    def send_reminder(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить напоминание о предстоящем мастер-классе
        Требования: 7.2
        """
        try:
            # Создать системное уведомление если пользователь зарегистрирован
            user = User.query.filter_by(email=user_email).first()
            if user:
                NotificationService.create_notification(
                    user_id=user.id,
                    notification_type='reminder',
                    title=f'Напоминание: {masterclass.title}',
                    message=f'Мастер-класс начнется завтра в {masterclass.date_time.strftime("%H:%M")}'
                )
            
            # Отправить email напоминание
            return EmailService.send_reminder_email(user_email, user_name, masterclass)
            
        except Exception as e:
            logger.error(f"Error sending reminder: {e}")
            return False
    
    @staticmethod
    def send_reminders_for_upcoming_masterclasses() -> int:
        """
        Отправить напоминания за 24 часа до начала мастер-классов
        Требования: 7.2
        """
        try:
            # Найти мастер-классы, которые начнутся через 24 часа (±1 час)
            now = datetime.utcnow()
            target_time = now + timedelta(hours=24)
            time_window_start = target_time - timedelta(hours=1)
            time_window_end = target_time + timedelta(hours=1)
            
            masterclasses = Masterclass.query.filter(
                Masterclass.is_active == True,
                Masterclass.date_time >= time_window_start,
                Masterclass.date_time <= time_window_end
            ).all()
            
            reminder_count = 0
            
            for masterclass in masterclasses:
                registrations = masterclass.registrations.all()
                
                for registration in registrations:
                    if NotificationService.send_reminder(
                        registration.user_email,
                        registration.user_name,
                        masterclass
                    ):
                        reminder_count += 1
            
            logger.info(f"Sent {reminder_count} reminders for {len(masterclasses)} masterclasses")
            return reminder_count
            
        except Exception as e:
            logger.error(f"Error sending reminders: {e}")
            return 0
    
    @staticmethod
    def send_cancellation_notification(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить уведомление об отмене мастер-класса
        Требования: 7.3
        """
        try:
            # Создать системное уведомление если пользователь зарегистрирован
            user = User.query.filter_by(email=user_email).first()
            if user:
                NotificationService.create_notification(
                    user_id=user.id,
                    notification_type='cancellation',
                    title=f'Отменен: {masterclass.title}',
                    message=f'К сожалению, мастер-класс "{masterclass.title}" был отменен'
                )
            
            # Отправить email уведомление
            return EmailService.send_cancellation_notification(user_email, user_name, masterclass)
            
        except Exception as e:
            logger.error(f"Error sending cancellation notification: {e}")
            return False
    
    @staticmethod
    def send_calendar_invite(user_email: str, user_name: str, masterclass: Masterclass) -> bool:
        """
        Отправить календарное приглашение при регистрации
        Требования: 7.4
        """
        try:
            return EmailService.send_calendar_invite(user_email, user_name, masterclass)
            
        except Exception as e:
            logger.error(f"Error sending calendar invite: {e}")
            return False
    
    @staticmethod
    def get_user_notifications(user_id: int, unread_only: bool = False, limit: int = None) -> List[Notification]:
        """
        Получить уведомления пользователя
        """
        try:
            query = Notification.query.filter_by(user_id=user_id)
            
            if unread_only:
                query = query.filter_by(is_read=False)
            
            query = query.order_by(Notification.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    @staticmethod
    def mark_notification_as_read(notification_id: int) -> bool:
        """
        Отметить уведомление как прочитанное
        """
        try:
            notification = Notification.query.get(notification_id)
            if notification:
                notification.is_read = True
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> bool:
        """
        Отметить все уведомления пользователя как прочитанные
        """
        try:
            Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking all notifications as read: {e}")
            return False
    
    @staticmethod
    def delete_notification(notification_id: int) -> bool:
        """
        Удалить уведомление
        """
        try:
            notification = Notification.query.get(notification_id)
            if notification:
                db.session.delete(notification)
                db.session.commit()
                return True
            return False
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting notification: {e}")
            return False
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """
        Получить количество непрочитанных уведомлений
        """
        try:
            return Notification.query.filter_by(user_id=user_id, is_read=False).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0


class AnalyticsService:
    """Сервис для сбора статистики и аналитики"""
    
    @staticmethod
    def get_creator_stats(creator_id: int) -> Dict[str, Any]:
        """
        Получить общую статистику создателя ивентов
        Требования: 9.1
        """
        try:
            # Получить все мастер-классы создателя
            masterclasses = Masterclass.query.filter_by(creator_id=creator_id).all()
            
            if not masterclasses:
                return {
                    'total_masterclasses': 0,
                    'upcoming_masterclasses': 0,
                    'past_masterclasses': 0,
                    'total_participants': 0,
                    'total_revenue': 0,
                    'average_rating': 0,
                    'total_reviews': 0
                }
            
            # Подсчет статистики
            now = datetime.utcnow()
            upcoming = [mc for mc in masterclasses if mc.date_time > now and mc.is_active]
            past = [mc for mc in masterclasses if mc.date_time <= now and mc.is_active]
            
            total_participants = sum(mc.current_participants for mc in masterclasses)
            
            # Подсчет доходов
            total_revenue = 0
            for mc in past:
                if mc.price:
                    total_revenue += float(mc.price) * mc.current_participants
            
            # Подсчет среднего рейтинга
            ratings = []
            total_reviews = 0
            for mc in masterclasses:
                avg_rating = ReviewService.get_masterclass_average_rating(mc.id)
                if avg_rating:
                    ratings.append(avg_rating)
                total_reviews += ReviewService.get_masterclass_review_count(mc.id)
            
            average_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
            
            stats = {
                'total_masterclasses': len(masterclasses),
                'upcoming_masterclasses': len(upcoming),
                'past_masterclasses': len(past),
                'total_participants': total_participants,
                'total_revenue': round(total_revenue, 2),
                'average_rating': average_rating,
                'total_reviews': total_reviews
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting creator stats: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def get_masterclass_analytics(masterclass_id: int) -> Dict[str, Any]:
        """
        Получить детальную аналитику по конкретному мастер-классу
        Требования: 9.2
        """
        try:
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                return {}
            
            # Процент заполняемости
            fill_percentage = round(
                (masterclass.current_participants / masterclass.max_participants) * 100, 1
            ) if masterclass.max_participants > 0 else 0
            
            # Рейтинг и отзывы
            average_rating = ReviewService.get_masterclass_average_rating(masterclass_id)
            review_count = ReviewService.get_masterclass_review_count(masterclass_id)
            reviews = ReviewService.get_masterclass_reviews(masterclass_id)
            
            # Доход
            revenue = 0
            if masterclass.price and not masterclass.is_upcoming:
                revenue = float(masterclass.price) * masterclass.current_participants
            
            # Статистика регистраций по времени
            registrations = Registration.query.filter_by(masterclass_id=masterclass_id).order_by(
                Registration.registered_at.asc()
            ).all()
            
            registration_timeline = []
            for reg in registrations:
                registration_timeline.append({
                    'date': reg.registered_at.strftime('%Y-%m-%d'),
                    'count': 1
                })
            
            analytics = {
                'masterclass_id': masterclass_id,
                'title': masterclass.title,
                'current_participants': masterclass.current_participants,
                'max_participants': masterclass.max_participants,
                'fill_percentage': fill_percentage,
                'is_full': masterclass.is_full,
                'average_rating': average_rating,
                'review_count': review_count,
                'revenue': round(revenue, 2),
                'registration_timeline': registration_timeline,
                'recent_reviews': [
                    {
                        'user': review.user.name,
                        'rating': review.rating,
                        'comment': review.comment,
                        'created_at': review.created_at.strftime('%Y-%m-%d')
                    }
                    for review in reviews[:5]  # Последние 5 отзывов
                ]
            }
            
            return analytics
            
        except Exception as e:
            logger.error(f"Error getting masterclass analytics: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def export_participants_csv(masterclass_id: int) -> Optional[str]:
        """
        Экспортировать список участников в формате CSV
        Требования: 9.4
        """
        try:
            import csv
            import io
            
            masterclass = Masterclass.query.get(masterclass_id)
            if not masterclass:
                return None
            
            participants = Registration.query.filter_by(masterclass_id=masterclass_id).order_by(
                Registration.registered_at.asc()
            ).all()
            
            # Создать CSV в памяти
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Заголовки
            writer.writerow(['№', 'Имя', 'Email', 'Телефон', 'Дата регистрации'])
            
            # Данные участников
            for idx, participant in enumerate(participants, 1):
                writer.writerow([
                    idx,
                    participant.user_name,
                    participant.user_email,
                    participant.user_phone or '',
                    participant.registered_at.strftime('%d.%m.%Y %H:%M')
                ])
            
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            logger.error(f"Error exporting participants CSV: {e}", exc_info=True)
            return None
    
    @staticmethod
    def get_revenue_report(creator_id: int, period: str = 'all') -> Dict[str, Any]:
        """
        Получить отчет о доходах создателя ивентов
        Требования: 9.1, 9.2
        """
        try:
            from sqlalchemy import func
            
            # Получить мастер-классы создателя
            query = Masterclass.query.filter_by(creator_id=creator_id, is_active=True)
            
            # Фильтр по периоду
            now = datetime.utcnow()
            if period == 'month':
                start_date = now - timedelta(days=30)
                query = query.filter(Masterclass.date_time >= start_date)
            elif period == 'year':
                start_date = now - timedelta(days=365)
                query = query.filter(Masterclass.date_time >= start_date)
            
            # Только прошедшие мастер-классы для подсчета доходов
            masterclasses = query.filter(Masterclass.date_time <= now).all()
            
            # Подсчет доходов по месяцам
            revenue_by_month = {}
            total_revenue = 0
            
            for mc in masterclasses:
                if mc.price:
                    revenue = float(mc.price) * mc.current_participants
                    total_revenue += revenue
                    
                    month_key = mc.date_time.strftime('%Y-%m')
                    if month_key not in revenue_by_month:
                        revenue_by_month[month_key] = 0
                    revenue_by_month[month_key] += revenue
            
            # Сортировка по месяцам
            revenue_timeline = [
                {'month': month, 'revenue': round(revenue, 2)}
                for month, revenue in sorted(revenue_by_month.items())
            ]
            
            report = {
                'period': period,
                'total_revenue': round(total_revenue, 2),
                'masterclasses_count': len(masterclasses),
                'revenue_timeline': revenue_timeline,
                'average_revenue_per_masterclass': round(
                    total_revenue / len(masterclasses), 2
                ) if masterclasses else 0
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error getting revenue report: {e}", exc_info=True)
            return {}
    
    @staticmethod
    def get_calendar_view(creator_id: int, year: int = None, month: int = None) -> List[Dict[str, Any]]:
        """
        Получить календарный вид мастер-классов создателя
        Требования: 9.3, 9.5
        """
        try:
            # Если год и месяц не указаны, использовать текущие
            if not year or not month:
                now = datetime.utcnow()
                year = now.year
                month = now.month
            
            # Начало и конец месяца
            from calendar import monthrange
            _, last_day = monthrange(year, month)
            
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, last_day, 23, 59, 59)
            
            # Получить мастер-классы в указанном диапазоне
            masterclasses = Masterclass.query.filter(
                Masterclass.creator_id == creator_id,
                Masterclass.is_active == True,
                Masterclass.date_time >= start_date,
                Masterclass.date_time <= end_date
            ).order_by(Masterclass.date_time.asc()).all()
            
            # Форматировать для календаря
            calendar_events = []
            for mc in masterclasses:
                event = {
                    'id': mc.id,
                    'title': mc.title,
                    'date': mc.date_time.strftime('%Y-%m-%d'),
                    'time': mc.date_time.strftime('%H:%M'),
                    'participants': f"{mc.current_participants}/{mc.max_participants}",
                    'fill_percentage': round(
                        (mc.current_participants / mc.max_participants) * 100, 1
                    ) if mc.max_participants > 0 else 0,
                    'is_full': mc.is_full,
                    'is_upcoming': mc.is_upcoming,
                    'category': mc.category
                }
                calendar_events.append(event)
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Error getting calendar view: {e}", exc_info=True)
            return []
    
    @staticmethod
    def get_popularity_stats(creator_id: int) -> Dict[str, Any]:
        """
        Получить статистику популярности мастер-классов
        Требования: 9.2
        """
        try:
            masterclasses = Masterclass.query.filter_by(
                creator_id=creator_id,
                is_active=True
            ).all()
            
            if not masterclasses:
                return {}
            
            # Сортировка по популярности (количество участников)
            sorted_by_participants = sorted(
                masterclasses,
                key=lambda x: x.current_participants,
                reverse=True
            )
            
            # Сортировка по рейтингу
            masterclasses_with_rating = []
            for mc in masterclasses:
                rating = ReviewService.get_masterclass_average_rating(mc.id)
                if rating:
                    masterclasses_with_rating.append((mc, rating))
            
            sorted_by_rating = sorted(
                masterclasses_with_rating,
                key=lambda x: x[1],
                reverse=True
            )
            
            # Топ-5 по участникам
            top_by_participants = [
                {
                    'id': mc.id,
                    'title': mc.title,
                    'participants': mc.current_participants,
                    'max_participants': mc.max_participants,
                    'fill_percentage': round(
                        (mc.current_participants / mc.max_participants) * 100, 1
                    ) if mc.max_participants > 0 else 0
                }
                for mc in sorted_by_participants[:5]
            ]
            
            # Топ-5 по рейтингу
            top_by_rating = [
                {
                    'id': mc.id,
                    'title': mc.title,
                    'rating': rating,
                    'review_count': ReviewService.get_masterclass_review_count(mc.id)
                }
                for mc, rating in sorted_by_rating[:5]
            ]
            
            # Статистика по категориям
            category_stats = {}
            for mc in masterclasses:
                category = mc.category or 'Без категории'
                if category not in category_stats:
                    category_stats[category] = {
                        'count': 0,
                        'total_participants': 0
                    }
                category_stats[category]['count'] += 1
                category_stats[category]['total_participants'] += mc.current_participants
            
            stats = {
                'top_by_participants': top_by_participants,
                'top_by_rating': top_by_rating,
                'category_stats': category_stats
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting popularity stats: {e}", exc_info=True)
            return {}
