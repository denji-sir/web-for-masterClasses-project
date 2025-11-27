"""
Тесты для SearchService
Требования: 8.1, 8.2, 8.3, 8.4, 8.5
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Review, UserProfile
from services import SearchService, ReviewService


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
def sample_data(app):
    """Создать тестовые данные"""
    with app.app_context():
        # Создать пользователя и создателя ивентов
        user = User(
            email='creator@test.com',
            name='Test Creator',
            role='event_creator',
            is_active=True
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()
        
        user_id = user.id  # Store ID before commit
        
        creator = EventCreator(
            user_id=user.id,
            company_name='Test Company'
        )
        db.session.add(creator)
        db.session.flush()
        
        # Создать мастер-классы с разными параметрами
        now = datetime.utcnow()
        
        # Мастер-класс 1: Программирование, дорогой, через неделю
        mc1 = Masterclass(
            creator_id=creator.id,
            title='Python для начинающих',
            description='Изучите основы программирования на Python',
            date_time=now + timedelta(days=7),
            max_participants=20,
            current_participants=5,
            price=5000.00,
            category='programming',
            is_active=True
        )
        db.session.add(mc1)
        
        # Мастер-класс 2: Дизайн, средняя цена, через 2 недели
        mc2 = Masterclass(
            creator_id=creator.id,
            title='Основы веб-дизайна',
            description='Научитесь создавать красивые веб-сайты',
            date_time=now + timedelta(days=14),
            max_participants=15,
            current_participants=10,
            price=3000.00,
            category='design',
            is_active=True
        )
        db.session.add(mc2)
        
        # Мастер-класс 3: Бизнес, бесплатный, через месяц
        mc3 = Masterclass(
            creator_id=creator.id,
            title='Стартап с нуля',
            description='Как создать успешный стартап',
            date_time=now + timedelta(days=30),
            max_participants=50,
            current_participants=2,
            price=0.00,
            category='business',
            is_active=True
        )
        db.session.add(mc3)
        
        # Мастер-класс 4: Программирование, дешевый, через 3 дня
        mc4 = Masterclass(
            creator_id=creator.id,
            title='JavaScript для веб-разработки',
            description='Изучите JavaScript и создайте интерактивный сайт',
            date_time=now + timedelta(days=3),
            max_participants=25,
            current_participants=15,
            price=2000.00,
            category='programming',
            is_active=True
        )
        db.session.add(mc4)
        
        db.session.commit()
        
        return {
            'user_id': user_id,
            'creator': creator,
            'masterclasses': [mc1, mc2, mc3, mc4]
        }


def test_search_by_query(app, sample_data):
    """
    Тест полнотекстового поиска по названию и описанию
    Требование: 8.1
    """
    with app.app_context():
        # Поиск по слову "Python"
        results = SearchService.search_masterclasses(query='Python')
        assert len(results) == 1
        assert 'Python' in results[0].title
        
        # Поиск по слову "основы" (в описании первого мастер-класса)
        results = SearchService.search_masterclasses(query='основы')
        assert len(results) >= 1
        
        # Поиск по слову "веб" (должен найти и дизайн, и JavaScript)
        results = SearchService.search_masterclasses(query='веб')
        assert len(results) == 2


def test_filter_by_category(app, sample_data):
    """
    Тест фильтрации по категории
    Требование: 8.1
    """
    with app.app_context():
        # Фильтр по категории "programming"
        results = SearchService.search_masterclasses(category='programming')
        assert len(results) == 2
        assert all(mc.category == 'programming' for mc in results)
        
        # Фильтр по категории "design"
        results = SearchService.search_masterclasses(category='design')
        assert len(results) == 1
        assert results[0].category == 'design'


def test_filter_by_date_range(app, sample_data):
    """
    Тест фильтрации по диапазону дат
    Требование: 8.2
    """
    with app.app_context():
        now = datetime.utcnow()
        
        # Фильтр: мастер-классы в ближайшие 10 дней
        results = SearchService.search_masterclasses(
            date_from=now,
            date_to=now + timedelta(days=10)
        )
        assert len(results) == 2  # mc1 (7 дней) и mc4 (3 дня)
        
        # Фильтр: мастер-классы через 2-4 недели
        results = SearchService.search_masterclasses(
            date_from=now + timedelta(days=13),
            date_to=now + timedelta(days=31)
        )
        assert len(results) >= 1  # mc2 (14 дней) и mc3 (30 дней)


def test_filter_by_price_range(app, sample_data):
    """
    Тест фильтрации по ценовому диапазону
    Требование: 8.3
    """
    with app.app_context():
        # Фильтр: бесплатные и дешевые (0-2500)
        results = SearchService.search_masterclasses(
            price_min=0,
            price_max=2500
        )
        assert len(results) == 2  # mc3 (0) и mc4 (2000)
        
        # Фильтр: дорогие (4000+)
        results = SearchService.search_masterclasses(
            price_min=4000
        )
        assert len(results) == 1  # mc1 (5000)


def test_sort_by_date(app, sample_data):
    """
    Тест сортировки по дате
    Требование: 8.4
    """
    with app.app_context():
        # Сортировка по дате (по возрастанию)
        results = SearchService.search_masterclasses(sort_by='date', sort_order='asc')
        assert len(results) == 4
        # Проверить, что даты идут по возрастанию
        for i in range(len(results) - 1):
            assert results[i].date_time <= results[i + 1].date_time
        
        # Сортировка по дате (по убыванию)
        results = SearchService.search_masterclasses(sort_by='date', sort_order='desc')
        assert len(results) == 4
        # Проверить, что даты идут по убыванию
        for i in range(len(results) - 1):
            assert results[i].date_time >= results[i + 1].date_time


def test_sort_by_price(app, sample_data):
    """
    Тест сортировки по цене
    Требование: 8.4
    """
    with app.app_context():
        # Сортировка по цене (по возрастанию)
        results = SearchService.search_masterclasses(sort_by='price', sort_order='asc')
        assert len(results) == 4
        # Проверить, что цены идут по возрастанию
        prices = [mc.price for mc in results if mc.price is not None]
        assert prices == sorted(prices)


def test_sort_by_popularity(app, sample_data):
    """
    Тест сортировки по популярности
    Требование: 8.4
    """
    with app.app_context():
        # Сортировка по популярности (по убыванию - больше участников = популярнее)
        results = SearchService.search_masterclasses(sort_by='popularity', sort_order='asc')
        assert len(results) == 4
        # Самый популярный должен быть первым (mc4 с 15 участниками)
        assert results[0].current_participants >= results[-1].current_participants


def test_combined_filters(app, sample_data):
    """
    Тест комбинированных фильтров
    Требования: 8.1, 8.2, 8.3, 8.4
    """
    with app.app_context():
        now = datetime.utcnow()
        
        # Комбинация: категория + цена + дата
        results = SearchService.search_masterclasses(
            category='programming',
            price_min=1000,
            price_max=6000,
            date_from=now,
            date_to=now + timedelta(days=10)
        )
        # Должен найти mc1 (Python, 5000, 7 дней) и mc4 (JavaScript, 2000, 3 дня)
        assert len(results) == 2
        assert all(mc.category == 'programming' for mc in results)


def test_save_and_get_search_preferences(app, sample_data):
    """
    Тест сохранения и получения поисковых предпочтений
    Требование: 8.5
    """
    with app.app_context():
        # Get user ID from sample data
        user_id = sample_data['user_id']
        
        # Сохранить предпочтения
        preferences = {
            'category': 'programming',
            'price_min': 1000,
            'price_max': 5000,
            'sort_by': 'price',
            'sort_order': 'asc'
        }
        
        result = SearchService.save_search_preferences(user_id, preferences)
        assert result is True
        
        # Получить предпочтения
        saved_prefs = SearchService.get_search_preferences(user_id)
        assert saved_prefs is not None
        assert saved_prefs['category'] == 'programming'
        assert saved_prefs['price_min'] == 1000
        assert saved_prefs['sort_by'] == 'price'


def test_get_popular_categories(app, sample_data):
    """
    Тест получения популярных категорий
    """
    with app.app_context():
        categories = SearchService.get_popular_categories()
        assert len(categories) > 0
        # programming должна быть самой популярной (2 мастер-класса)
        assert categories[0][0] == 'programming'
        assert categories[0][1] == 2


def test_get_search_suggestions(app, sample_data):
    """
    Тест получения подсказок для автодополнения
    Требование: 8.1
    """
    with app.app_context():
        # Поиск подсказок по "Py"
        suggestions = SearchService.get_search_suggestions('Py')
        assert len(suggestions) > 0
        assert any('Python' in s for s in suggestions)
        
        # Поиск подсказок по "веб"
        suggestions = SearchService.get_search_suggestions('веб')
        assert len(suggestions) >= 2


def test_search_with_no_results(app, sample_data):
    """
    Тест поиска без результатов
    """
    with app.app_context():
        # Поиск по несуществующему запросу
        results = SearchService.search_masterclasses(query='несуществующий запрос xyz')
        assert len(results) == 0
        
        # Фильтр по несуществующей категории
        results = SearchService.search_masterclasses(category='nonexistent')
        assert len(results) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
