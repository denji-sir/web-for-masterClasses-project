"""
Тесты для обработки граничных случаев
Требования: 1.4, 2.3, 3.4, 5.4
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration
from services import MasterclassService, RegistrationService, UserService
from error_handlers import (
    MasterclassFullError, DuplicateRegistrationError, 
    CancellationTooLateError, TimeConstraintError,
    DataValidationError, DatabaseConnectionError
)


@pytest.fixture
def app():
    """Create and configure a test app instance"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def event_creator(app):
    """Create a test event creator"""
    with app.app_context():
        # Check if creator already exists
        existing_user = User.query.filter_by(email='creator@test.com').first()
        if existing_user:
            creator = EventCreator.query.filter_by(user_id=existing_user.id).first()
            if creator:
                return creator.id
        
        user = User(email='creator@test.com', name='Test Creator', role='event_creator')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        creator = EventCreator(user_id=user.id, company_name='Test Company')
        db.session.add(creator)
        db.session.commit()
        
        creator_id = creator.id
        db.session.expunge_all()  # Detach all objects from session
        
        return creator_id


def test_full_masterclass_error(app, event_creator):
    """
    Тест обработки заполненного мастер-класса
    Требование: 1.4
    """
    with app.app_context():
        # Создать мастер-класс с 2 местами
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Full Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=2,
            price=1000
        )
        
        # Зарегистрировать 2 пользователей
        RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='User 1',
            user_email='user1@test.com',
            user_phone='1234567890'
        )
        
        RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='User 2',
            user_email='user2@test.com',
            user_phone='1234567891'
        )
        
        # Попытка зарегистрировать третьего пользователя должна вызвать исключение
        with pytest.raises(MasterclassFullError) as exc_info:
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='User 3',
                user_email='user3@test.com',
                user_phone='1234567892'
            )
        
        assert 'полностью заполнен' in str(exc_info.value)
        assert masterclass.title in str(exc_info.value)


def test_duplicate_registration_error(app, event_creator):
    """
    Тест обработки повторной регистрации
    Требование: 2.3, 2.5
    """
    with app.app_context():
        # Создать мастер-класс
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Test Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10,
            price=1000
        )
        
        # Первая регистрация
        registration = RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='Test User',
            user_email='test@test.com',
            user_phone='1234567890'
        )
        
        assert registration is not None
        
        # Попытка повторной регистрации должна вызвать исключение
        with pytest.raises(DuplicateRegistrationError) as exc_info:
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='Test User',
                user_email='test@test.com',
                user_phone='1234567890'
            )
        
        assert 'уже зарегистрирован' in str(exc_info.value)
        assert 'test@test.com' in str(exc_info.value)


def test_cancellation_too_late_error(app, event_creator):
    """
    Тест обработки отмены регистрации менее чем за 24 часа
    Требование: 3.4
    """
    with app.app_context():
        # Создать мастер-класс через 12 часов (менее 24 часов)
        near_future_date = datetime.utcnow() + timedelta(hours=12)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Soon Masterclass',
            description='Test',
            date_time=near_future_date,
            max_participants=10,
            price=1000
        )
        
        # Зарегистрировать пользователя
        registration = RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='Test User',
            user_email='test@test.com',
            user_phone='1234567890'
        )
        
        assert registration is not None
        
        # Попытка отмены должна вызвать исключение
        with pytest.raises(CancellationTooLateError) as exc_info:
            RegistrationService.cancel_registration(
                masterclass_id=masterclass.id,
                user_email='test@test.com'
            )
        
        assert 'невозможна' in str(exc_info.value)
        assert '24 часа' in str(exc_info.value)


def test_successful_cancellation_within_time_limit(app, event_creator):
    """
    Тест успешной отмены регистрации более чем за 24 часа
    Требование: 3.2, 3.3, 3.4
    """
    with app.app_context():
        # Создать мастер-класс через 48 часов (более 24 часов)
        future_date = datetime.utcnow() + timedelta(hours=48)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Future Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10,
            price=1000
        )
        
        # Зарегистрировать пользователя
        registration = RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='Test User',
            user_email='test@test.com',
            user_phone='1234567890'
        )
        
        assert registration is not None
        assert masterclass.current_participants == 1
        
        # Отмена должна пройти успешно
        success = RegistrationService.cancel_registration(
            masterclass_id=masterclass.id,
            user_email='test@test.com'
        )
        
        assert success is True
        
        # Проверить, что счетчик участников уменьшился
        db.session.refresh(masterclass)
        assert masterclass.current_participants == 0


def test_data_validation_error_empty_name(app, event_creator):
    """
    Тест валидации пустого имени
    Требование: 5.1
    """
    with app.app_context():
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Test Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10,
            price=1000
        )
        
        # Попытка регистрации с пустым именем
        with pytest.raises(DataValidationError) as exc_info:
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='',
                user_email='test@test.com',
                user_phone='1234567890'
            )
        
        assert 'user_name' in str(exc_info.value)
        assert 'пустым' in str(exc_info.value)


def test_data_validation_error_invalid_email(app, event_creator):
    """
    Тест валидации некорректного email
    Требование: 5.2
    """
    with app.app_context():
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Test Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10,
            price=1000
        )
        
        # Попытка регистрации с некорректным email
        with pytest.raises(DataValidationError) as exc_info:
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='Test User',
                user_email='invalid-email',
                user_phone='1234567890'
            )
        
        assert 'email' in str(exc_info.value)


def test_masterclass_creation_validation(app, event_creator):
    """
    Тест валидации при создании мастер-класса
    Требование: 5.1
    """
    with app.app_context():
        future_date = datetime.utcnow() + timedelta(days=7)
        
        # Попытка создать мастер-класс с пустым названием
        with pytest.raises(DataValidationError) as exc_info:
            MasterclassService.create_masterclass(
                creator_id=event_creator,
                title='',
                description='Test',
                date_time=future_date,
                max_participants=10,
                price=1000
            )
        
        assert 'title' in str(exc_info.value)


def test_masterclass_creation_past_date(app, event_creator):
    """
    Тест валидации даты в прошлом
    Требование: 5.1
    """
    with app.app_context():
        past_date = datetime.utcnow() - timedelta(days=1)
        
        # Попытка создать мастер-класс с датой в прошлом
        with pytest.raises(DataValidationError) as exc_info:
            MasterclassService.create_masterclass(
                creator_id=event_creator,
                title='Past Masterclass',
                description='Test',
                date_time=past_date,
                max_participants=10,
                price=1000
            )
        
        assert 'date_time' in str(exc_info.value)
        assert 'будущем' in str(exc_info.value)


def test_registration_on_past_masterclass(app, event_creator):
    """
    Тест попытки регистрации на прошедший мастер-класс
    Требование: 2.3
    """
    with app.app_context():
        # Создать мастер-класс в будущем
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Test Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10,
            price=1000
        )
        
        # Вручную изменить дату на прошлую
        masterclass.date_time = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        
        # Попытка регистрации должна вызвать исключение
        with pytest.raises(TimeConstraintError) as exc_info:
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='Test User',
                user_email='test@test.com',
                user_phone='1234567890'
            )
        
        assert 'прошло' in str(exc_info.value) or 'закрыта' in str(exc_info.value)


def test_concurrent_registration_limit(app, event_creator):
    """
    Тест контроля лимита участников при одновременных регистрациях
    Требование: 5.3
    """
    with app.app_context():
        # Создать мастер-класс с 1 местом
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=event_creator,
            title='Limited Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=1,
            price=1000
        )
        
        # Первая регистрация должна пройти
        registration1 = RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='User 1',
            user_email='user1@test.com',
            user_phone='1234567890'
        )
        
        assert registration1 is not None
        
        # Вторая регистрация должна быть отклонена
        with pytest.raises(MasterclassFullError):
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='User 2',
                user_email='user2@test.com',
                user_phone='1234567891'
            )
        
        # Проверить, что зарегистрирован только один пользователь
        db.session.refresh(masterclass)
        assert masterclass.current_participants == 1
        assert masterclass.is_full is True
