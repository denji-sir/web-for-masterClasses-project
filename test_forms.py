"""
Тесты для форм веб-портала регистрации на мастер-классы
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass
from forms import (
    LoginForm, UserRegistrationForm, RegistrationForm, MasterclassForm,
    SearchForm, AdminUserForm, AdminCreateUserForm, AdminRoleForm,
    EventCreatorProfileForm, CancelRegistrationForm, AdvancedSearchForm
)


@pytest.fixture
def app():
    """Создать тестовое приложение"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Создать тестовый клиент"""
    return app.test_client()


def test_login_form_valid(app):
    """Тест валидной формы входа"""
    with app.test_request_context():
        form = LoginForm(data={
            'email': 'test@example.com',
            'password': 'password123'
        })
        assert form.validate()


def test_login_form_invalid_email(app):
    """Тест формы входа с некорректным email"""
    with app.test_request_context():
        form = LoginForm(data={
            'email': 'invalid-email',
            'password': 'password123'
        })
        assert not form.validate()
        assert 'email' in form.errors


def test_login_form_missing_password(app):
    """Тест формы входа без пароля"""
    with app.test_request_context():
        form = LoginForm(data={
            'email': 'test@example.com',
            'password': ''
        })
        assert not form.validate()
        assert 'password' in form.errors


def test_registration_form_valid(app):
    """Тест валидной формы регистрации на мастер-класс"""
    with app.test_request_context():
        form = RegistrationForm(data={
            'user_name': 'Иван Иванов',
            'user_email': 'ivan@example.com',
            'user_phone': '+79001234567'
        })
        assert form.validate()


def test_registration_form_invalid_email(app):
    """Тест формы регистрации с некорректным email"""
    with app.test_request_context():
        form = RegistrationForm(data={
            'user_name': 'Иван Иванов',
            'user_email': 'not-an-email',
            'user_phone': '+79001234567'
        })
        assert not form.validate()
        assert 'user_email' in form.errors


def test_registration_form_short_name(app):
    """Тест формы регистрации с коротким именем"""
    with app.test_request_context():
        form = RegistrationForm(data={
            'user_name': 'A',
            'user_email': 'test@example.com',
            'user_phone': '+79001234567'
        })
        assert not form.validate()
        assert 'user_name' in form.errors


def test_masterclass_form_valid(app):
    """Тест валидной формы мастер-класса"""
    with app.test_request_context():
        future_date = datetime.utcnow() + timedelta(days=7)
        form = MasterclassForm(data={
            'title': 'Программирование на Python',
            'description': 'Изучаем основы Python',
            'date_time': future_date,
            'max_participants': 20,
            'price': 2500.00,
            'category': 'programming'
        })
        assert form.validate()


def test_masterclass_form_past_date(app):
    """Тест формы мастер-класса с датой в прошлом"""
    with app.test_request_context():
        past_date = datetime.utcnow() - timedelta(days=1)
        form = MasterclassForm(data={
            'title': 'Программирование на Python',
            'description': 'Изучаем основы Python',
            'date_time': past_date,
            'max_participants': 20,
            'price': 2500.00,
            'category': 'programming'
        })
        assert not form.validate()
        assert 'date_time' in form.errors


def test_masterclass_form_invalid_participants(app):
    """Тест формы мастер-класса с некорректным количеством участников"""
    with app.test_request_context():
        future_date = datetime.utcnow() + timedelta(days=7)
        form = MasterclassForm(data={
            'title': 'Программирование на Python',
            'description': 'Изучаем основы Python',
            'date_time': future_date,
            'max_participants': 0,
            'price': 2500.00,
            'category': 'programming'
        })
        assert not form.validate()
        assert 'max_participants' in form.errors


def test_search_form_valid(app):
    """Тест валидной формы поиска"""
    with app.test_request_context():
        form = SearchForm(data={
            'email': 'test@example.com'
        })
        assert form.validate()


def test_search_form_invalid_email(app):
    """Тест формы поиска с некорректным email"""
    with app.test_request_context():
        form = SearchForm(data={
            'email': 'invalid'
        })
        assert not form.validate()
        assert 'email' in form.errors


def test_admin_user_form_valid(app):
    """Тест валидной формы управления пользователем"""
    with app.test_request_context():
        form = AdminUserForm(data={
            'name': 'Иван Иванов',
            'email': 'ivan@example.com',
            'phone': '+79001234567',
            'role': 'user',
            'is_active': True
        })
        assert form.validate()


def test_admin_role_form_valid(app):
    """Тест валидной формы назначения роли"""
    with app.test_request_context():
        form = AdminRoleForm(data={
            'role': 'event_creator'
        })
        assert form.validate()


def test_user_registration_form_valid(app):
    """Тест валидной формы регистрации пользователя"""
    with app.test_request_context():
        form = UserRegistrationForm(data={
            'name': 'Иван Иванов',
            'email': 'ivan@example.com',
            'phone': '+79001234567',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert form.validate()


def test_user_registration_form_password_mismatch(app):
    """Тест формы регистрации с несовпадающими паролями"""
    with app.test_request_context():
        form = UserRegistrationForm(data={
            'name': 'Иван Иванов',
            'email': 'ivan@example.com',
            'phone': '+79001234567',
            'password': 'password123',
            'confirm_password': 'different'
        })
        assert not form.validate()
        assert 'confirm_password' in form.errors


def test_user_registration_form_duplicate_email(app):
    """Тест формы регистрации с существующим email"""
    with app.app_context():
        # Создать пользователя
        user = User(email='existing@example.com', name='Existing User')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        
        # Попытаться зарегистрировать с тем же email
        form = UserRegistrationForm(data={
            'name': 'Новый пользователь',
            'email': 'existing@example.com',
            'phone': '+79001234567',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert not form.validate()
        assert 'email' in form.errors


def test_advanced_search_form_valid(app):
    """Тест валидной формы расширенного поиска"""
    with app.test_request_context():
        form = AdvancedSearchForm(data={
            'query': 'Python',
            'category': 'programming',
            'date_from': datetime(2024, 1, 1),
            'date_to': datetime(2024, 12, 31)
        })
        assert form.validate()


def test_advanced_search_form_invalid_date_range(app):
    """Тест формы расширенного поиска с некорректным диапазоном дат"""
    with app.test_request_context():
        form = AdvancedSearchForm(data={
            'query': 'Python',
            'category': 'programming',
            'date_from': datetime(2024, 12, 31),
            'date_to': datetime(2024, 1, 1)
        })
        assert not form.validate()
        assert 'date_to' in form.errors


def test_event_creator_profile_form_valid(app):
    """Тест валидной формы профиля создателя ивентов"""
    with app.test_request_context():
        form = EventCreatorProfileForm(data={
            'company_name': 'Моя компания',
            'description': 'Описание компании'
        })
        assert form.validate()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
