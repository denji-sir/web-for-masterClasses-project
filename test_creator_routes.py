"""
Тесты для маршрутов создателей ивентов
Требования: 4.1, 4.2, 4.3, 4.4, 4.5
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration
from services import UserService, EventCreatorService, MasterclassService


@pytest.fixture
def app():
    """Создать тестовое приложение"""
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
    """Создать тестовый клиент"""
    return app.test_client()


@pytest.fixture
def event_creator_user(app):
    """Создать пользователя-создателя ивентов"""
    with app.app_context():
        user = UserService.create_user(
            email='creator@test.com',
            password='password123',
            name='Test Creator',
            phone='+1234567890',
            role='event_creator'
        )
        creator = EventCreatorService.create_event_creator(
            user_id=user.id,
            company_name='Test Company',
            description='Test Description'
        )
        user_id = user.id
    return user_id


def test_creator_registration(client):
    """
    Тест регистрации создателя ивентов
    Требования: 4.1
    """
    response = client.post('/creator/register', data={
        'name': 'New Creator',
        'email': 'newcreator@test.com',
        'phone': '+9876543210',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    assert b'success' in response.data or b'login' in response.data.lower()


def test_creator_login(client, event_creator_user):
    """
    Тест входа создателя ивентов
    Требования: 4.1
    """
    response = client.post('/creator/login', data={
        'email': 'creator@test.com',
        'password': 'password123'
    }, follow_redirects=True)
    
    assert response.status_code == 200


def test_creator_dashboard_requires_login(client):
    """
    Тест доступа к панели управления без входа
    Требования: 4.1
    """
    response = client.get('/creator/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower() or 'войдите'.encode('utf-8') in response.data.lower()


def test_create_masterclass(client, event_creator_user, app):
    """
    Тест создания мастер-класса
    Требования: 4.2
    """
    # Войти в систему
    with client.session_transaction() as sess:
        sess['user_id'] = event_creator_user
        sess['user_role'] = 'event_creator'
    
    future_date = datetime.utcnow() + timedelta(days=7)
    
    response = client.post('/creator/masterclass/create', data={
        'title': 'Test Masterclass',
        'description': 'Test Description',
        'date_time': future_date.strftime('%Y-%m-%dT%H:%M'),
        'max_participants': 20,
        'price': 1000,
        'category': 'programming'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Проверить, что мастер-класс создан
    with app.app_context():
        masterclass = Masterclass.query.filter_by(title='Test Masterclass').first()
        assert masterclass is not None
        assert masterclass.max_participants == 20


def test_edit_masterclass(client, event_creator_user, app):
    """
    Тест редактирования мастер-класса
    Требования: 4.3
    """
    # Создать мастер-класс
    with app.app_context():
        creator = EventCreatorService.get_creator_by_user_id(event_creator_user)
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator.id,
            title='Original Title',
            description='Original Description',
            date_time=future_date,
            max_participants=10,
            price=500
        )
        masterclass_id = masterclass.id
    
    # Войти в систему
    with client.session_transaction() as sess:
        sess['user_id'] = event_creator_user
        sess['user_role'] = 'event_creator'
    
    # Редактировать мастер-класс
    response = client.post(f'/creator/masterclass/{masterclass_id}/edit', data={
        'title': 'Updated Title',
        'description': 'Updated Description',
        'date_time': future_date.strftime('%Y-%m-%dT%H:%M'),
        'max_participants': 15,
        'price': 750,
        'category': 'design'
    }, follow_redirects=True)
    
    assert response.status_code == 200
    
    # Проверить, что мастер-класс обновлен
    with app.app_context():
        masterclass = Masterclass.query.get(masterclass_id)
        assert masterclass.title == 'Updated Title'
        assert masterclass.max_participants == 15


def test_view_participants(client, event_creator_user, app):
    """
    Тест просмотра участников мастер-класса
    Требования: 4.5
    """
    # Создать мастер-класс и регистрацию
    with app.app_context():
        creator = EventCreatorService.get_creator_by_user_id(event_creator_user)
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator.id,
            title='Test Masterclass',
            description='Test Description',
            date_time=future_date,
            max_participants=10
        )
        
        # Добавить участника
        registration = Registration(
            masterclass_id=masterclass.id,
            user_name='Test Participant',
            user_email='participant@test.com',
            user_phone='+1111111111'
        )
        masterclass.current_participants += 1
        db.session.add(registration)
        db.session.commit()
        masterclass_id = masterclass.id
    
    # Войти в систему
    with client.session_transaction() as sess:
        sess['user_id'] = event_creator_user
        sess['user_role'] = 'event_creator'
    
    # Просмотреть участников
    response = client.get(f'/creator/masterclass/{masterclass_id}/participants')
    
    assert response.status_code == 200
    assert b'Test Participant' in response.data
    assert b'participant@test.com' in response.data


def test_delete_masterclass(client, event_creator_user, app):
    """
    Тест удаления мастер-класса
    Требования: 4.4
    """
    # Создать мастер-класс
    with app.app_context():
        creator = EventCreatorService.get_creator_by_user_id(event_creator_user)
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator.id,
            title='To Delete',
            description='Test Description',
            date_time=future_date,
            max_participants=10
        )
        masterclass_id = masterclass.id
    
    # Войти в систему
    with client.session_transaction() as sess:
        sess['user_id'] = event_creator_user
        sess['user_role'] = 'event_creator'
    
    # Удалить мастер-класс
    response = client.post(f'/creator/masterclass/{masterclass_id}/delete', follow_redirects=True)
    
    assert response.status_code == 200
    
    # Проверить, что мастер-класс удален
    with app.app_context():
        masterclass = Masterclass.query.get(masterclass_id)
        assert masterclass is None


def test_creator_cannot_edit_others_masterclass(client, app):
    """
    Тест: создатель не может редактировать чужие мастер-классы
    Требования: 4.3
    """
    # Создать двух создателей
    with app.app_context():
        user1 = UserService.create_user(
            email='creator1@test.com',
            password='password123',
            name='Creator 1',
            role='event_creator'
        )
        creator1 = EventCreatorService.create_event_creator(user1.id)
        
        user2 = UserService.create_user(
            email='creator2@test.com',
            password='password123',
            name='Creator 2',
            role='event_creator'
        )
        creator2 = EventCreatorService.create_event_creator(user2.id)
        
        # Создать мастер-класс от имени creator1
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator1.id,
            title='Creator 1 Masterclass',
            description='Test',
            date_time=future_date,
            max_participants=10
        )
        masterclass_id = masterclass.id
        user2_id = user2.id
    
    # Войти как creator2
    with client.session_transaction() as sess:
        sess['user_id'] = user2_id
        sess['user_role'] = 'event_creator'
    
    # Попытаться редактировать мастер-класс creator1
    response = client.get(f'/creator/masterclass/{masterclass_id}/edit', follow_redirects=True)
    
    assert response.status_code == 200
    assert 'нет прав'.encode('utf-8') in response.data.lower() or b'dashboard' in response.data.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
