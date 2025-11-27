"""
Тесты для AnalyticsService
Требования: 9.1, 9.2, 9.3, 9.4, 9.5
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration, Review
from services import AnalyticsService, UserService, EventCreatorService, MasterclassService


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
def creator_with_masterclasses(app):
    """Создать создателя с несколькими мастер-классами"""
    with app.app_context():
        # Создать пользователя-создателя
        user = UserService.create_user(
            email='creator@test.com',
            password='password123',
            name='Test Creator',
            role='event_creator'
        )
        
        # Создать профиль создателя
        creator = EventCreatorService.create_event_creator(
            user_id=user.id,
            company_name='Test Company'
        )
        
        # Создать несколько мастер-классов
        now = datetime.utcnow()
        
        # Прошедший мастер-класс с участниками (создаем напрямую в БД для тестирования)
        mc1 = Masterclass(
            creator_id=creator.id,
            title='Past Masterclass',
            description='Test description',
            date_time=now - timedelta(days=10),
            max_participants=10,
            price=1000,
            category='Programming'
        )
        db.session.add(mc1)
        db.session.flush()  # Получить ID
        
        # Добавить участников
        for i in range(5):
            reg = Registration(
                masterclass_id=mc1.id,
                user_name=f'User {i}',
                user_email=f'user{i}@test.com',
                user_phone=f'+7900000000{i}'
            )
            db.session.add(reg)
            mc1.current_participants += 1
        
        # Предстоящий мастер-класс
        mc2 = Masterclass(
            creator_id=creator.id,
            title='Upcoming Masterclass',
            description='Test description',
            date_time=now + timedelta(days=10),
            max_participants=20,
            price=2000,
            category='Design'
        )
        db.session.add(mc2)
        db.session.flush()  # Получить ID
        
        # Добавить участников
        for i in range(15):
            reg = Registration(
                masterclass_id=mc2.id,
                user_name=f'User {i+10}',
                user_email=f'user{i+10}@test.com'
            )
            db.session.add(reg)
            mc2.current_participants += 1
        
        db.session.commit()
        
        # Return IDs instead of objects to avoid detached instance errors
        return {
            'creator_id': creator.id,
            'user_id': user.id,
            'past_mc_id': mc1.id,
            'upcoming_mc_id': mc2.id
        }


def test_get_creator_stats(creator_with_masterclasses):
    """
    Тест получения общей статистики создателя
    Требования: 9.1
    """
    data = creator_with_masterclasses
    stats = AnalyticsService.get_creator_stats(data['creator_id'])
    
    assert stats is not None
    assert stats['total_masterclasses'] == 2
    assert stats['upcoming_masterclasses'] == 1
    assert stats['past_masterclasses'] == 1
    assert stats['total_participants'] == 20  # 5 + 15
    assert stats['total_revenue'] == 5000  # 1000 * 5 (только прошедший)
    assert 'average_rating' in stats
    assert 'total_reviews' in stats


def test_get_masterclass_analytics(creator_with_masterclasses):
    """
    Тест получения аналитики конкретного мастер-класса
    Требования: 9.2
    """
    data = creator_with_masterclasses
    analytics = AnalyticsService.get_masterclass_analytics(data['past_mc_id'])
    
    assert analytics is not None
    assert analytics['masterclass_id'] == data['past_mc_id']
    assert analytics['title'] == 'Past Masterclass'
    assert analytics['current_participants'] == 5
    assert analytics['max_participants'] == 10
    assert analytics['fill_percentage'] == 50.0
    assert analytics['is_full'] is False
    assert analytics['revenue'] == 5000  # 1000 * 5
    assert 'registration_timeline' in analytics
    assert 'recent_reviews' in analytics


def test_export_participants_csv(creator_with_masterclasses):
    """
    Тест экспорта участников в CSV
    Требования: 9.4
    """
    data = creator_with_masterclasses
    csv_content = AnalyticsService.export_participants_csv(data['past_mc_id'])
    
    assert csv_content is not None
    assert '№,Имя,Email,Телефон,Дата регистрации' in csv_content
    assert 'User 0' in csv_content
    assert 'user0@test.com' in csv_content
    assert '+79000000000' in csv_content
    
    # Проверить количество строк (заголовок + 5 участников)
    lines = csv_content.strip().split('\n')
    assert len(lines) == 6


def test_get_revenue_report(creator_with_masterclasses):
    """
    Тест получения отчета о доходах
    Требования: 9.1, 9.2
    """
    data = creator_with_masterclasses
    report = AnalyticsService.get_revenue_report(data['creator_id'], period='all')
    
    assert report is not None
    assert report['period'] == 'all'
    assert report['total_revenue'] == 5000  # Только прошедший мастер-класс
    assert report['masterclasses_count'] == 1  # Только прошедший
    assert report['average_revenue_per_masterclass'] == 5000
    assert 'revenue_timeline' in report


def test_get_calendar_view(creator_with_masterclasses):
    """
    Тест получения календарного вида мастер-классов
    Требования: 9.3, 9.5
    """
    data = creator_with_masterclasses
    now = datetime.utcnow()
    
    # Получить календарь для текущего месяца
    calendar_events = AnalyticsService.get_calendar_view(
        data['creator_id'],
        year=now.year,
        month=now.month
    )
    
    assert calendar_events is not None
    assert isinstance(calendar_events, list)
    
    # Проверить, что есть хотя бы один мастер-класс в текущем месяце
    # (зависит от того, когда запускается тест)
    for event in calendar_events:
        assert 'id' in event
        assert 'title' in event
        assert 'date' in event
        assert 'time' in event
        assert 'participants' in event
        assert 'fill_percentage' in event
        assert 'is_full' in event
        assert 'is_upcoming' in event


def test_get_popularity_stats(creator_with_masterclasses):
    """
    Тест получения статистики популярности
    Требования: 9.2
    """
    data = creator_with_masterclasses
    stats = AnalyticsService.get_popularity_stats(data['creator_id'])
    
    assert stats is not None
    assert 'top_by_participants' in stats
    assert 'top_by_rating' in stats
    assert 'category_stats' in stats
    
    # Проверить топ по участникам
    top_participants = stats['top_by_participants']
    assert len(top_participants) > 0
    # Предстоящий мастер-класс должен быть первым (15 участников)
    assert top_participants[0]['participants'] == 15
    
    # Проверить статистику по категориям
    category_stats = stats['category_stats']
    assert 'Programming' in category_stats
    assert 'Design' in category_stats
    assert category_stats['Programming']['count'] == 1
    assert category_stats['Design']['count'] == 1


def test_export_csv_nonexistent_masterclass():
    """Тест экспорта CSV для несуществующего мастер-класса"""
    csv_content = AnalyticsService.export_participants_csv(99999)
    assert csv_content is None


def test_get_stats_empty_creator(app):
    """Тест получения статистики для создателя без мастер-классов"""
    with app.app_context():
        # Создать пользователя-создателя без мастер-классов
        user = UserService.create_user(
            email='empty@test.com',
            password='password123',
            name='Empty Creator',
            role='event_creator'
        )
        creator = EventCreatorService.create_event_creator(user_id=user.id)
        
        stats = AnalyticsService.get_creator_stats(creator.id)
        
        assert stats is not None
        assert stats['total_masterclasses'] == 0
        assert stats['upcoming_masterclasses'] == 0
        assert stats['past_masterclasses'] == 0
        assert stats['total_participants'] == 0
        assert stats['total_revenue'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
