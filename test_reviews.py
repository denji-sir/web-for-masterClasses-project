"""
Тесты для системы отзывов и рейтингов
Требования: 10.4
"""
import pytest
from datetime import datetime, timedelta
from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration, Review
from services import ReviewService


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
        # Создать пользователя
        user = User(email='user@test.com', name='Test User', role='user')
        user.set_password('password')
        db.session.add(user)
        
        # Создать создателя ивентов
        creator_user = User(email='creator@test.com', name='Creator', role='event_creator')
        creator_user.set_password('password')
        db.session.add(creator_user)
        db.session.flush()
        
        creator = EventCreator(user_id=creator_user.id, company_name='Test Company')
        db.session.add(creator)
        db.session.flush()
        
        # Создать прошедший мастер-класс
        past_masterclass = Masterclass(
            creator_id=creator.id,
            title='Past Masterclass',
            description='Test description',
            date_time=datetime.utcnow() - timedelta(days=7),
            max_participants=10,
            price=1000,
            category='programming'
        )
        db.session.add(past_masterclass)
        db.session.flush()
        
        # Создать регистрацию
        registration = Registration(
            masterclass_id=past_masterclass.id,
            user_name=user.name,
            user_email=user.email,
            user_phone='1234567890'
        )
        db.session.add(registration)
        
        db.session.commit()
        
        return {
            'user': user,
            'creator': creator,
            'past_masterclass': past_masterclass
        }


def test_create_review(app, sample_data):
    """
    Тест создания отзыва
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Создать отзыв
        review = ReviewService.create_review(
            user_id=user.id,
            masterclass_id=masterclass.id,
            rating=5,
            comment='Great masterclass!'
        )
        
        assert review is not None
        assert review.rating == 5
        assert review.comment == 'Great masterclass!'
        assert review.is_approved == True


def test_cannot_review_upcoming_masterclass(app, sample_data):
    """
    Тест: нельзя оставить отзыв на предстоящий мастер-класс
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        creator = EventCreator.query.first()
        
        # Создать предстоящий мастер-класс
        future_masterclass = Masterclass(
            creator_id=creator.id,
            title='Future Masterclass',
            description='Test',
            date_time=datetime.utcnow() + timedelta(days=7),
            max_participants=10,
            price=1000
        )
        db.session.add(future_masterclass)
        db.session.commit()
        
        # Попытаться создать отзыв
        from error_handlers import DataValidationError
        with pytest.raises(DataValidationError):
            ReviewService.create_review(
                user_id=user.id,
                masterclass_id=future_masterclass.id,
                rating=5,
                comment='Test'
            )


def test_cannot_review_without_participation(app, sample_data):
    """
    Тест: нельзя оставить отзыв без участия в мастер-классе
    Требования: 10.4
    """
    with app.app_context():
        # Создать нового пользователя без регистрации
        new_user = User(email='newuser@test.com', name='New User', role='user')
        new_user.set_password('password')
        db.session.add(new_user)
        db.session.commit()
        
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Попытаться создать отзыв
        from error_handlers import DataValidationError
        with pytest.raises(DataValidationError):
            ReviewService.create_review(
                user_id=new_user.id,
                masterclass_id=masterclass.id,
                rating=5,
                comment='Test'
            )


def test_get_masterclass_reviews(app, sample_data):
    """
    Тест получения отзывов о мастер-классе
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Создать отзыв
        ReviewService.create_review(
            user_id=user.id,
            masterclass_id=masterclass.id,
            rating=4,
            comment='Good masterclass'
        )
        
        # Получить отзывы
        reviews = ReviewService.get_masterclass_reviews(masterclass.id)
        
        assert len(reviews) == 1
        assert reviews[0].rating == 4


def test_get_average_rating(app, sample_data):
    """
    Тест расчета среднего рейтинга
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Создать отзыв
        ReviewService.create_review(
            user_id=user.id,
            masterclass_id=masterclass.id,
            rating=5,
            comment='Excellent!'
        )
        
        # Получить средний рейтинг
        avg_rating = ReviewService.get_masterclass_average_rating(masterclass.id)
        
        assert avg_rating == 5.0


def test_review_moderation(app, sample_data):
    """
    Тест модерации отзывов
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Создать отзыв
        review = ReviewService.create_review(
            user_id=user.id,
            masterclass_id=masterclass.id,
            rating=3,
            comment='Average'
        )
        
        # Отклонить отзыв
        success = ReviewService.reject_review(review.id)
        assert success == True
        
        # Проверить, что отзыв отклонен
        updated_review = Review.query.get(review.id)
        assert updated_review.is_approved == False
        
        # Одобрить отзыв
        success = ReviewService.approve_review(review.id)
        assert success == True
        
        # Проверить, что отзыв одобрен
        updated_review = Review.query.get(review.id)
        assert updated_review.is_approved == True


def test_can_user_review(app, sample_data):
    """
    Тест проверки возможности оставить отзыв
    Требования: 10.4
    """
    with app.app_context():
        user = User.query.filter_by(email='user@test.com').first()
        masterclass = Masterclass.query.filter_by(title='Past Masterclass').first()
        
        # Пользователь может оставить отзыв
        can_review = ReviewService.can_user_review(user.id, masterclass.id)
        assert can_review == True
        
        # Создать отзыв
        ReviewService.create_review(
            user_id=user.id,
            masterclass_id=masterclass.id,
            rating=5,
            comment='Great!'
        )
        
        # Пользователь больше не может оставить отзыв
        can_review = ReviewService.can_user_review(user.id, masterclass.id)
        assert can_review == False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
