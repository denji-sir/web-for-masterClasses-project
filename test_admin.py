"""
Тесты для административной панели
Требования: 5.1, 5.2, 5.3, 5.4, 5.5
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration
from services import UserService, AdminService, MasterclassService


@pytest.fixture
def app():
    """Создать тестовое приложение"""
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        yield app
        db.session.remove()


@pytest.fixture
def client(app):
    """Создать тестовый клиент"""
    return app.test_client()


@pytest.fixture
def admin_user(app):
    """Создать администратора для тестов"""
    with app.app_context():
        admin = UserService.create_user(
            email='admin@test.com',
            password='admin123',
            name='Admin User',
            role='admin'
        )
        db.session.commit()
        admin_id = admin.id
        return admin_id


@pytest.fixture
def regular_user(app):
    """Создать обычного пользователя для тестов"""
    with app.app_context():
        user = UserService.create_user(
            email='user@test.com',
            password='user123',
            name='Regular User',
            role='user'
        )
        db.session.commit()
        user_id = user.id
        return user_id


@pytest.fixture
def event_creator_user(app):
    """Создать создателя ивентов для тестов"""
    with app.app_context():
        creator_user = UserService.create_user(
            email='creator@test.com',
            password='creator123',
            name='Event Creator',
            role='event_creator'
        )
        db.session.commit()
        creator_user_id = creator_user.id
        return creator_user_id


def test_admin_login_page(client):
    """Тест: страница входа администратора доступна"""
    response = client.get('/admin/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower() or b'admin' in response.data.lower()


def test_admin_authentication(client, app, admin_user):
    """Тест: аутентификация администратора работает"""
    with app.app_context():
        response = client.post('/admin/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)
        
        assert response.status_code == 200


def test_admin_dashboard_requires_auth(client):
    """Тест: панель администратора требует аутентификации"""
    response = client.get('/admin/dashboard')
    assert response.status_code == 302  # Redirect to login


def test_admin_can_view_all_users(client, app, admin_user, regular_user):
    """Тест: администратор может просматривать всех пользователей (Требование 5.1)"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        response = client.get('/admin/users')
        assert response.status_code == 200


def test_admin_can_create_user(client, app, admin_user):
    """Тест: администратор может создавать пользователей (Требование 5.1, 5.2)"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        response = client.post('/admin/users/create', data={
            'name': 'New User',
            'email': 'newuser@test.com',
            'phone': '1234567890',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'user',
            'is_active': True
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверить, что пользователь создан
        new_user = User.query.filter_by(email='newuser@test.com').first()
        assert new_user is not None
        assert new_user.name == 'New User'


def test_admin_can_block_user(client, app, admin_user, regular_user):
    """Тест: администратор может блокировать пользователей (Требование 5.2)"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        user_id = regular_user
        
        response = client.post(f'/admin/users/{user_id}/block', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверить, что пользователь заблокирован
        user = User.query.get(user_id)
        assert user.is_active == False


def test_admin_can_unblock_user(client, app, admin_user, regular_user):
    """Тест: администратор может разблокировать пользователей (Требование 5.2)"""
    with app.app_context():
        # Сначала заблокировать пользователя
        AdminService.block_user(regular_user)
        db.session.commit()
        
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        user_id = regular_user
        
        response = client.post(f'/admin/users/{user_id}/unblock', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверить, что пользователь разблокирован
        user = User.query.get(user_id)
        assert user.is_active == True


def test_admin_can_assign_role(client, app, admin_user, regular_user):
    """Тест: администратор может назначать роли (Требование 5.5)"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        user_id = regular_user
        
        response = client.post(f'/admin/users/{user_id}/assign-role', data={
            'role': 'event_creator'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        # Проверить, что роль изменена
        user = User.query.get(user_id)
        assert user.role == 'event_creator'


def test_admin_can_view_all_masterclasses(client, app, admin_user):
    """Тест: администратор может просматривать все мастер-классы (Требование 5.3)"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        response = client.get('/admin/masterclasses')
        assert response.status_code == 200


def test_admin_can_delete_masterclass(client, app, admin_user, event_creator_user):
    """Тест: администратор может удалять мастер-классы (Требование 5.4)"""
    with app.app_context():
        # Создать создателя ивентов
        from services import EventCreatorService
        creator = EventCreatorService.create_event_creator(event_creator_user)
        db.session.commit()
        
        # Создать мастер-класс
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator.id,
            title='Test Masterclass',
            description='Test Description',
            date_time=datetime.utcnow() + timedelta(days=7),
            max_participants=10,
            price=1000
        )
        db.session.commit()
        
        masterclass_id = masterclass.id
        
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        response = client.post(f'/admin/masterclasses/{masterclass_id}/delete', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверить, что мастер-класс удален
        deleted_masterclass = Masterclass.query.get(masterclass_id)
        assert deleted_masterclass is None


def test_admin_cannot_delete_self(client, app, admin_user):
    """Тест: администратор не может удалить себя"""
    with app.app_context():
        # Войти как администратор
        with client.session_transaction() as sess:
            sess['user_id'] = admin_user
            sess['user_role'] = 'admin'
        
        response = client.post(f'/admin/users/{admin_user}/delete', follow_redirects=True)
        assert response.status_code == 200
        
        # Проверить, что администратор не удален
        user = User.query.get(admin_user)
        assert user is not None


def test_admin_statistics(app, admin_user, regular_user):
    """Тест: получение статистики системы (Требование 5.1)"""
    with app.app_context():
        stats = AdminService.get_system_statistics()
        
        assert 'total_users' in stats
        assert 'total_event_creators' in stats
        assert 'total_masterclasses' in stats
        assert 'total_registrations' in stats
        assert stats['total_users'] >= 2  # admin + regular user


def test_non_admin_cannot_access_admin_panel(client, app, regular_user):
    """Тест: обычный пользователь не может получить доступ к админ-панели"""
    with app.app_context():
        # Войти как обычный пользователь
        with client.session_transaction() as sess:
            sess['user_id'] = regular_user
            sess['user_role'] = 'user'
        
        response = client.get('/admin/dashboard')
        assert response.status_code == 302  # Redirect


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
