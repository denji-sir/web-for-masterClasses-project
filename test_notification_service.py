"""
Тесты для системы уведомлений
Требования: 7.1, 7.2, 7.3, 7.4, 7.5
"""

import pytest
import os
from datetime import datetime, timedelta
from flask import Flask
from app import create_app
from extensions import db, mail
from models import User, EventCreator, Masterclass, Registration, Notification
from services import NotificationService, EmailService


@pytest.fixture
def app():
    """Создать тестовое приложение"""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Создать тестовый клиент"""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Создать тестового пользователя"""
    with app.app_context():
        user = User(
            email='test@example.com',
            name='Test User',
            role='user'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def sample_creator(app):
    """Создать тестового создателя ивентов"""
    with app.app_context():
        user = User(
            email='creator@example.com',
            name='Creator User',
            role='event_creator'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        creator = EventCreator(
            user_id=user.id,
            company_name='Test Company'
        )
        db.session.add(creator)
        db.session.commit()
        return creator


@pytest.fixture
def sample_masterclass(app, sample_creator):
    """Создать тестовый мастер-класс"""
    with app.app_context():
        creator = db.session.merge(sample_creator)
        masterclass = Masterclass(
            creator_id=creator.id,
            title='Test Masterclass',
            description='Test Description',
            date_time=datetime.utcnow() + timedelta(days=2),
            max_participants=10,
            price=1000.00,
            category='Programming'
        )
        db.session.add(masterclass)
        db.session.commit()
        return masterclass


class TestNotificationService:
    """Тесты для NotificationService"""
    
    def test_create_notification(self, app, sample_user):
        """Тест создания системного уведомления - Требование: 7.1"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            notification = NotificationService.create_notification(
                user_id=user.id,
                notification_type='reminder',
                title='Test Notification',
                message='This is a test message'
            )
            
            assert notification is not None
            assert notification.user_id == user.id
            assert notification.type == 'reminder'
            assert notification.title == 'Test Notification'
            assert notification.message == 'This is a test message'
            assert notification.is_read is False
    
    def test_get_user_notifications(self, app, sample_user):
        """Тест получения уведомлений пользователя"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            # Создать несколько уведомлений
            NotificationService.create_notification(
                user_id=user.id,
                notification_type='reminder',
                title='Notification 1',
                message='Message 1'
            )
            NotificationService.create_notification(
                user_id=user.id,
                notification_type='update',
                title='Notification 2',
                message='Message 2'
            )
            
            notifications = NotificationService.get_user_notifications(user.id)
            
            assert len(notifications) == 2
            assert notifications[0].title == 'Notification 2'  # Последнее первым
            assert notifications[1].title == 'Notification 1'
    
    def test_get_unread_notifications(self, app, sample_user):
        """Тест получения непрочитанных уведомлений"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            # Создать уведомления
            n1 = NotificationService.create_notification(
                user_id=user.id,
                notification_type='reminder',
                title='Unread',
                message='Message'
            )
            n2 = NotificationService.create_notification(
                user_id=user.id,
                notification_type='update',
                title='Read',
                message='Message'
            )
            
            # Отметить одно как прочитанное
            NotificationService.mark_notification_as_read(n2.id)
            
            unread = NotificationService.get_user_notifications(user.id, unread_only=True)
            
            assert len(unread) == 1
            assert unread[0].title == 'Unread'
    
    def test_mark_notification_as_read(self, app, sample_user):
        """Тест отметки уведомления как прочитанного"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            notification = NotificationService.create_notification(
                user_id=user.id,
                notification_type='reminder',
                title='Test',
                message='Message'
            )
            
            assert notification.is_read is False
            
            result = NotificationService.mark_notification_as_read(notification.id)
            
            assert result is True
            
            updated = Notification.query.get(notification.id)
            assert updated.is_read is True
    
    def test_mark_all_as_read(self, app, sample_user):
        """Тест отметки всех уведомлений как прочитанных"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            # Создать несколько уведомлений
            for i in range(3):
                NotificationService.create_notification(
                    user_id=user.id,
                    notification_type='reminder',
                    title=f'Notification {i}',
                    message='Message'
                )
            
            unread_count = NotificationService.get_unread_count(user.id)
            assert unread_count == 3
            
            result = NotificationService.mark_all_as_read(user.id)
            assert result is True
            
            unread_count = NotificationService.get_unread_count(user.id)
            assert unread_count == 0
    
    def test_delete_notification(self, app, sample_user):
        """Тест удаления уведомления"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            notification = NotificationService.create_notification(
                user_id=user.id,
                notification_type='reminder',
                title='Test',
                message='Message'
            )
            
            notification_id = notification.id
            
            result = NotificationService.delete_notification(notification_id)
            assert result is True
            
            deleted = Notification.query.get(notification_id)
            assert deleted is None
    
    def test_get_unread_count(self, app, sample_user):
        """Тест подсчета непрочитанных уведомлений"""
        with app.app_context():
            user = db.session.merge(sample_user)
            
            # Создать уведомления
            for i in range(5):
                NotificationService.create_notification(
                    user_id=user.id,
                    notification_type='reminder',
                    title=f'Notification {i}',
                    message='Message'
                )
            
            count = NotificationService.get_unread_count(user.id)
            assert count == 5
    
    def test_send_status_update(self, app, sample_masterclass):
        """Тест отправки уведомления об обновлении статуса - Требование: 7.1, 7.5"""
        with app.app_context():
            with mail.record_messages() as outbox:
                masterclass = db.session.merge(sample_masterclass)
                
                # Создать регистрацию
                user = User(
                    email='participant@example.com',
                    name='Participant',
                    role='user'
                )
                user.set_password('password')
                db.session.add(user)
                db.session.commit()
                
                registration = Registration(
                    masterclass_id=masterclass.id,
                    user_name='Participant',
                    user_email='participant@example.com'
                )
                db.session.add(registration)
                db.session.commit()
                
                # Отправить обновление статуса
                result = NotificationService.send_status_update(
                    masterclass,
                    'Время мастер-класса изменено'
                )
                
                assert result is True
                assert len(outbox) == 1
                assert 'Обновление мастер-класса' in outbox[0].subject
                
                # Проверить, что создано системное уведомление
                notification = Notification.query.filter_by(user_id=user.id).first()
                assert notification is not None
                assert notification.type == 'update'
    
    def test_send_reminders_for_upcoming_masterclasses(self, app, sample_creator):
        """Тест отправки напоминаний за 24 часа - Требование: 7.2"""
        with app.app_context():
            with mail.record_messages() as outbox:
                creator = db.session.merge(sample_creator)
                
                # Создать мастер-класс через 24 часа
                masterclass = Masterclass(
                    creator_id=creator.id,
                    title='Tomorrow Masterclass',
                    description='Test',
                    date_time=datetime.utcnow() + timedelta(hours=24),
                    max_participants=10,
                    price=1000.00
                )
                db.session.add(masterclass)
                db.session.commit()
                
                # Создать регистрацию
                user = User(
                    email='reminder@example.com',
                    name='Reminder User',
                    role='user'
                )
                user.set_password('password')
                db.session.add(user)
                db.session.commit()
                
                registration = Registration(
                    masterclass_id=masterclass.id,
                    user_name='Reminder User',
                    user_email='reminder@example.com'
                )
                db.session.add(registration)
                db.session.commit()
                
                # Отправить напоминания
                count = NotificationService.send_reminders_for_upcoming_masterclasses()
                
                assert count == 1
                assert len(outbox) == 1
                assert 'Напоминание' in outbox[0].subject
    
    def test_send_cancellation_notification(self, app, sample_masterclass):
        """Тест отправки уведомления об отмене - Требование: 7.3"""
        with app.app_context():
            with mail.record_messages() as outbox:
                masterclass = db.session.merge(sample_masterclass)
                
                # Создать пользователя
                user = User(
                    email='cancel@example.com',
                    name='Cancel User',
                    role='user'
                )
                user.set_password('password')
                db.session.add(user)
                db.session.commit()
                
                result = NotificationService.send_cancellation_notification(
                    'cancel@example.com',
                    'Cancel User',
                    masterclass
                )
                
                assert result is True
                assert len(outbox) == 1
                assert 'отменен' in outbox[0].subject.lower()
                
                # Проверить системное уведомление
                notification = Notification.query.filter_by(user_id=user.id).first()
                assert notification is not None
                assert notification.type == 'cancellation'


class TestEmailService:
    """Тесты для EmailService"""
    
    def test_send_reminder_email(self, app, sample_masterclass):
        """Тест отправки email напоминания - Требование: 7.2"""
        with app.app_context():
            with mail.record_messages() as outbox:
                masterclass = db.session.merge(sample_masterclass)
                
                result = EmailService.send_reminder_email(
                    'test@example.com',
                    'Test User',
                    masterclass
                )
                
                assert result is True
                assert len(outbox) == 1
                assert 'Напоминание' in outbox[0].subject
                assert 'завтра' in outbox[0].body
    
    def test_send_status_update_email(self, app, sample_masterclass):
        """Тест отправки email об обновлении статуса - Требование: 7.1, 7.5"""
        with app.app_context():
            with mail.record_messages() as outbox:
                masterclass = db.session.merge(sample_masterclass)
                
                result = EmailService.send_status_update_email(
                    'test@example.com',
                    'Test User',
                    masterclass,
                    'Время изменено на 15:00'
                )
                
                assert result is True
                assert len(outbox) == 1
                assert 'Обновление мастер-класса' in outbox[0].subject
                assert 'Время изменено на 15:00' in outbox[0].body
    
    def test_send_calendar_invite(self, app, sample_masterclass):
        """Тест отправки календарного приглашения - Требование: 7.4"""
        with app.app_context():
            with mail.record_messages() as outbox:
                masterclass = db.session.merge(sample_masterclass)
                
                result = EmailService.send_calendar_invite(
                    'test@example.com',
                    'Test User',
                    masterclass
                )
                
                assert result is True
                assert len(outbox) == 1
                assert 'Календарное приглашение' in outbox[0].subject
                
                # Проверить, что есть вложение
                assert len(outbox[0].attachments) == 1
                attachment = outbox[0].attachments[0]
                assert attachment.content_type == 'text/calendar'
                assert 'masterclass' in attachment.filename


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
