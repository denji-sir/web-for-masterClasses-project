"""
Маршруты для веб-портала регистрации на мастер-классы
Требования: 1.1, 1.2, 1.3, 2.1, 2.2, 3.1, 3.2, 1.4, 2.3, 3.4, 5.4
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from forms import RegistrationForm, SearchForm, CancelRegistrationForm, AdvancedSearchForm, ReviewForm
from services import MasterclassService, RegistrationService, ReviewService, SearchService
from models import Masterclass
from error_handlers import (
    MasterclassFullError, DuplicateRegistrationError, TimeConstraintError,
    CancellationTooLateError, DatabaseConnectionError, DataValidationError
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Публичный blueprint
public_bp = Blueprint('public', __name__)


@public_bp.route('/')
@public_bp.route('/index')
def index():
    """
    Главная страница со списком мастер-классов
    Требования: 1.1, 1.2, 1.3, 5.4, 10.4
    """
    try:
        # Получить параметры фильтрации из URL
        category = request.args.get('category', None)
        
        # Получить доступные мастер-классы с обработкой ошибок БД - Требование: 5.4
        try:
            masterclasses = MasterclassService.get_available_masterclasses(category=category)
        except DatabaseConnectionError as e:
            logger.error(f"Database error fetching masterclasses: {e}")
            flash('Временные проблемы с базой данных. Показаны кэшированные данные', 'warning')
            masterclasses = []
        
        # Добавить рейтинги к мастер-классам - Требование: 10.4
        masterclass_ratings = {}
        for mc in masterclasses:
            rating = ReviewService.get_masterclass_average_rating(mc.id)
            count = ReviewService.get_masterclass_review_count(mc.id)
            masterclass_ratings[mc.id] = {'rating': rating, 'count': count}
        
        # Получить список категорий для фильтра
        categories = [
            ('programming', 'Программирование'),
            ('design', 'Дизайн'),
            ('business', 'Бизнес'),
            ('marketing', 'Маркетинг'),
            ('art', 'Искусство'),
            ('music', 'Музыка'),
            ('cooking', 'Кулинария'),
            ('photography', 'Фотография'),
            ('fitness', 'Фитнес'),
            ('other', 'Другое')
        ]
        
        return render_template(
            'public/index.html',
            masterclasses=masterclasses,
            categories=categories,
            selected_category=category,
            masterclass_ratings=masterclass_ratings
        )
    
    except Exception as e:
        # Общая обработка непредвиденных ошибок
        logger.error(f"Unexpected error in index route: {e}", exc_info=True)
        flash('Произошла ошибка при загрузке страницы', 'error')
        return render_template(
            'public/index.html',
            masterclasses=[],
            categories=[],
            selected_category=None,
            masterclass_ratings={}
        )


@public_bp.route('/masterclass/<int:masterclass_id>')
def masterclass_detail(masterclass_id):
    """
    Страница деталей мастер-класса
    Требования: 1.2, 1.3, 2.1, 10.4
    """
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('public.index'))
    
    # Создать форму регистрации
    form = RegistrationForm()
    
    # Получить рейтинг и отзывы
    average_rating = ReviewService.get_masterclass_average_rating(masterclass_id)
    review_count = ReviewService.get_masterclass_review_count(masterclass_id)
    recent_reviews = ReviewService.get_masterclass_reviews(masterclass_id)[:3]  # Последние 3 отзыва
    
    # Проверить, может ли текущий пользователь оставить отзыв
    user_id = session.get('user_id')
    can_review = False
    if user_id:
        can_review = ReviewService.can_user_review(user_id, masterclass_id)
    
    return render_template(
        'public/masterclass_detail.html',
        masterclass=masterclass,
        form=form,
        average_rating=average_rating,
        review_count=review_count,
        recent_reviews=recent_reviews,
        can_review=can_review
    )


@public_bp.route('/masterclass/<int:masterclass_id>/register', methods=['GET', 'POST'])
def register(masterclass_id):
    """
    Маршрут регистрации на мастер-класс
    Требования: 2.1, 2.2, 2.3, 2.4, 2.5, 1.4, 5.4
    """
    try:
        masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
        
        if not masterclass:
            flash('Мастер-класс не найден', 'error')
            return redirect(url_for('public.index'))
        
        # Проверить, можно ли зарегистрироваться - Требование: 1.4
        if not masterclass.can_register():
            if masterclass.is_full:
                flash('К сожалению, все места заняты', 'warning')
            elif not masterclass.is_upcoming:
                flash('Регистрация на этот мастер-класс уже закрыта', 'warning')
            else:
                flash('Регистрация на этот мастер-класс недоступна', 'warning')
            return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
        
        form = RegistrationForm()
        
        if form.validate_on_submit():
            try:
                # Попытка регистрации с обработкой ошибок - Требования: 1.4, 2.3, 5.4
                registration = RegistrationService.register_user(
                    masterclass_id=masterclass_id,
                    user_name=form.user_name.data,
                    user_email=form.user_email.data,
                    user_phone=form.user_phone.data
                )
                
                if registration:
                    flash(
                        f'Вы успешно зарегистрировались на мастер-класс "{masterclass.title}"! '
                        f'Подтверждение отправлено на {form.user_email.data}',
                        'success'
                    )
                    return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
                else:
                    flash('Ошибка регистрации. Пожалуйста, попробуйте позже', 'error')
            
            except MasterclassFullError as e:
                # Обработка заполненного мастер-класса - Требование: 1.4
                flash(str(e), 'warning')
                return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
            
            except DuplicateRegistrationError as e:
                # Обработка повторной регистрации - Требование: 2.3
                flash(str(e), 'info')
                return redirect(url_for('public.my_registrations'))
            
            except TimeConstraintError as e:
                # Обработка временных ограничений - Требование: 2.3
                flash(str(e), 'error')
                return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
            
            except DataValidationError as e:
                # Обработка ошибок валидации - Требование: 5.1
                flash(str(e), 'error')
            
            except DatabaseConnectionError as e:
                # Обработка ошибок БД - Требование: 5.4
                logger.error(f"Database error during registration: {e}")
                flash('Временные проблемы с базой данных. Пожалуйста, попробуйте позже', 'error')
        
        return render_template(
            'public/register.html',
            masterclass=masterclass,
            form=form
        )
    
    except DatabaseConnectionError as e:
        # Обработка ошибок БД на уровне маршрута - Требование: 5.4
        logger.error(f"Database error in register route: {e}")
        flash('Временные проблемы с базой данных. Пожалуйста, попробуйте позже', 'error')
        return redirect(url_for('public.index'))


@public_bp.route('/my-registrations', methods=['GET', 'POST'])
def my_registrations():
    """
    Поиск регистраций по email
    Требования: 3.1
    """
    form = SearchForm()
    registrations = []
    
    if form.validate_on_submit():
        # Получить регистрации пользователя
        registrations = RegistrationService.get_user_registrations(form.email.data)
        
        if not registrations:
            flash('Регистрации не найдены для указанного email', 'info')
    
    return render_template(
        'public/my_registrations.html',
        form=form,
        registrations=registrations
    )


@public_bp.route('/cancel-registration/<int:masterclass_id>', methods=['POST'])
def cancel_registration(masterclass_id):
    """
    Маршрут отмены регистрации
    Требования: 3.2, 3.3, 3.4, 5.4
    """
    try:
        # Получить email из формы
        email = request.form.get('email')
        
        if not email:
            flash('Email не указан', 'error')
            return redirect(url_for('public.my_registrations'))
        
        # Получить мастер-класс для проверки с обработкой ошибок БД - Требование: 5.4
        try:
            masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
        except DatabaseConnectionError as e:
            logger.error(f"Database error fetching masterclass: {e}")
            flash('Временные проблемы с базой данных. Пожалуйста, попробуйте позже', 'error')
            return redirect(url_for('public.my_registrations'))
        
        if not masterclass:
            flash('Мастер-класс не найден', 'error')
            return redirect(url_for('public.my_registrations'))
        
        # Попытка отмены регистрации с обработкой ошибок - Требования: 3.4, 5.4
        try:
            success = RegistrationService.cancel_registration(masterclass_id, email)
            
            if success:
                flash(
                    f'Регистрация на мастер-класс "{masterclass.title}" успешно отменена. '
                    f'Подтверждение отправлено на {email}',
                    'success'
                )
            else:
                flash('Ошибка отмены регистрации. Проверьте правильность email', 'error')
        
        except CancellationTooLateError as e:
            # Обработка отмены менее чем за 24 часа - Требование: 3.4
            flash(str(e), 'error')
        
        except TimeConstraintError as e:
            # Обработка других временных ограничений - Требование: 3.4
            flash(str(e), 'error')
        
        except DataValidationError as e:
            # Обработка ошибок валидации - Требование: 5.1
            flash(str(e), 'error')
        
        except DatabaseConnectionError as e:
            # Обработка ошибок БД - Требование: 5.4
            logger.error(f"Database error during cancellation: {e}")
            flash('Временные проблемы с базой данных. Пожалуйста, попробуйте позже', 'error')
        
        return redirect(url_for('public.my_registrations'))
    
    except Exception as e:
        # Общая обработка непредвиденных ошибок
        logger.error(f"Unexpected error in cancel_registration: {e}", exc_info=True)
        flash('Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже', 'error')
        return redirect(url_for('public.my_registrations'))


@public_bp.route('/search', methods=['GET'])
def search():
    """
    Расширенный поиск с поддержкой AJAX
    Требования: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    from flask import jsonify
    from services import SearchService
    
    # Проверяем, является ли запрос AJAX
    is_ajax = request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    form = AdvancedSearchForm(request.args)
    masterclasses = []
    masterclass_ratings = {}
    
    # Получить параметры поиска из URL
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    price_min = request.args.get('price_min', '').strip()
    price_max = request.args.get('price_max', '').strip()
    min_rating = request.args.get('min_rating', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    per_page = 12
    
    # Загрузить сохраненные предпочтения пользователя - Требование: 8.5
    user_id = session.get('user_id')
    saved_preferences = None
    if user_id:
        saved_preferences = SearchService.get_search_preferences(user_id)
    
    if request.args:
        # Преобразовать параметры
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        except:
            date_from_obj = None
        
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        except:
            date_to_obj = None
        
        try:
            price_min_val = float(price_min) if price_min else None
        except:
            price_min_val = None
        
        try:
            price_max_val = float(price_max) if price_max else None
        except:
            price_max_val = None
        
        try:
            min_rating_val = float(min_rating) if min_rating else None
        except:
            min_rating_val = None
        
        # Выполнить поиск с использованием SearchService - Требования: 8.1, 8.2, 8.3, 8.4
        all_masterclasses = SearchService.search_masterclasses(
            query=query if query else None,
            category=category if category else None,
            date_from=date_from_obj,
            date_to=date_to_obj,
            price_min=price_min_val,
            price_max=price_max_val,
            min_rating=min_rating_val,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Пагинация для бесконечной прокрутки
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        masterclasses = all_masterclasses[start_idx:end_idx]
        
        # Сохранить поисковые предпочтения - Требование: 8.5
        if user_id and request.args.get('save_preferences') == '1':
            preferences = {
                'category': category,
                'price_min': price_min_val,
                'price_max': price_max_val,
                'min_rating': min_rating_val,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
            SearchService.save_search_preferences(user_id, preferences)
            if not is_ajax:
                flash('Поисковые предпочтения сохранены', 'success')
        
        # Получить рейтинги для результатов
        for mc in masterclasses:
            rating = ReviewService.get_masterclass_average_rating(mc.id)
            count = ReviewService.get_masterclass_review_count(mc.id)
            masterclass_ratings[mc.id] = {'rating': rating, 'count': count}
    
    # Если это AJAX запрос, вернуть JSON
    if is_ajax:
        masterclasses_data = []
        for mc in masterclasses:
            mc_data = {
                'id': mc.id,
                'title': mc.title,
                'description': mc.description,
                'date_time': mc.date_time.strftime('%d.%m.%Y в %H:%M'),
                'category': mc.category,
                'price': float(mc.price) if mc.price else None,
                'max_participants': mc.max_participants,
                'current_participants': mc.current_participants,
                'rating': masterclass_ratings.get(mc.id, {}).get('rating'),
                'review_count': masterclass_ratings.get(mc.id, {}).get('count', 0)
            }
            masterclasses_data.append(mc_data)
        
        return jsonify({
            'masterclasses': masterclasses_data,
            'page': page,
            'has_more': len(all_masterclasses) > end_idx
        })
    
    # Получить популярные категории
    popular_categories = SearchService.get_popular_categories()
    
    return render_template(
        'public/search.html',
        form=form,
        masterclasses=masterclasses,
        masterclass_ratings=masterclass_ratings,
        popular_categories=popular_categories,
        saved_preferences=saved_preferences,
        current_sort=sort_by,
        current_order=sort_order
    )


@public_bp.route('/masterclass/<int:masterclass_id>/reviews')
def masterclass_reviews(masterclass_id):
    """
    Страница с отзывами о мастер-классе
    Требования: 10.4
    """
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('public.index'))
    
    # Получить отзывы
    reviews = ReviewService.get_masterclass_reviews(masterclass_id)
    
    # Получить средний рейтинг
    average_rating = ReviewService.get_masterclass_average_rating(masterclass_id)
    review_count = ReviewService.get_masterclass_review_count(masterclass_id)
    
    return render_template(
        'public/reviews.html',
        masterclass=masterclass,
        reviews=reviews,
        average_rating=average_rating,
        review_count=review_count
    )


@public_bp.route('/masterclass/<int:masterclass_id>/add-review', methods=['GET', 'POST'])
def add_review(masterclass_id):
    """
    Добавить отзыв о мастер-классе
    Требования: 10.4
    """
    # Проверить, что пользователь авторизован (используем session для простоты)
    user_id = session.get('user_id')
    if not user_id:
        flash('Для добавления отзыва необходимо войти в систему', 'warning')
        return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('public.index'))
    
    # Проверить, может ли пользователь оставить отзыв
    if not ReviewService.can_user_review(user_id, masterclass_id):
        flash('Вы не можете оставить отзыв на этот мастер-класс', 'warning')
        return redirect(url_for('public.masterclass_detail', masterclass_id=masterclass_id))
    
    form = ReviewForm()
    
    if form.validate_on_submit():
        try:
            review = ReviewService.create_review(
                user_id=user_id,
                masterclass_id=masterclass_id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            
            if review:
                flash('Спасибо за ваш отзыв!', 'success')
                return redirect(url_for('public.masterclass_reviews', masterclass_id=masterclass_id))
            else:
                flash('Ошибка при добавлении отзыва', 'error')
        
        except DataValidationError as e:
            flash(str(e), 'error')
        
        except Exception as e:
            logger.error(f"Error adding review: {e}")
            flash('Произошла ошибка при добавлении отзыва', 'error')
    
    return render_template(
        'public/add_review.html',
        masterclass=masterclass,
        form=form
    )


# API endpoints для AJAX запросов

@public_bp.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    """
    API для автодополнения поиска
    Требование: 8.5
    """
    from flask import jsonify
    
    query = request.args.get('q', '').strip()
    
    if len(query) < 2:
        return jsonify({'suggestions': []})
    
    try:
        # Получить предложения из названий мастер-классов
        suggestions = SearchService.get_autocomplete_suggestions(query)
        return jsonify({'suggestions': suggestions})
    except Exception as e:
        logger.error(f"Autocomplete error: {e}")
        return jsonify({'suggestions': []})


@public_bp.route('/search', methods=['GET'])
def search_with_ajax():
    """
    Расширенный поиск с поддержкой AJAX
    Требования: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    from flask import jsonify
    
    # Проверяем, является ли запрос AJAX
    is_ajax = request.args.get('ajax') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    form = AdvancedSearchForm(request.args)
    masterclasses = []
    masterclass_ratings = {}
    
    # Получить параметры поиска из URL
    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    price_min = request.args.get('price_min', '').strip()
    price_max = request.args.get('price_max', '').strip()
    min_rating = request.args.get('min_rating', '').strip()
    sort_by = request.args.get('sort_by', 'date')
    sort_order = request.args.get('sort_order', 'asc')
    page = int(request.args.get('page', 1))
    per_page = 12
    
    # Загрузить сохраненные предпочтения пользователя - Требование: 8.5
    user_id = session.get('user_id')
    saved_preferences = None
    if user_id:
        saved_preferences = SearchService.get_search_preferences(user_id)
    
    if request.args:
        # Преобразовать параметры
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d') if date_from else None
        except:
            date_from_obj = None
        
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d') if date_to else None
        except:
            date_to_obj = None
        
        try:
            price_min_val = float(price_min) if price_min else None
        except:
            price_min_val = None
        
        try:
            price_max_val = float(price_max) if price_max else None
        except:
            price_max_val = None
        
        try:
            min_rating_val = float(min_rating) if min_rating else None
        except:
            min_rating_val = None
        
        # Выполнить поиск с использованием SearchService - Требования: 8.1, 8.2, 8.3, 8.4
        all_masterclasses = SearchService.search_masterclasses(
            query=query if query else None,
            category=category if category else None,
            date_from=date_from_obj,
            date_to=date_to_obj,
            price_min=price_min_val,
            price_max=price_max_val,
            min_rating=min_rating_val,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # Пагинация для бесконечной прокрутки
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        masterclasses = all_masterclasses[start_idx:end_idx]
        
        # Сохранить поисковые предпочтения - Требование: 8.5
        if user_id and request.args.get('save_preferences') == '1':
            preferences = {
                'category': category,
                'price_min': price_min_val,
                'price_max': price_max_val,
                'min_rating': min_rating_val,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
            SearchService.save_search_preferences(user_id, preferences)
            if not is_ajax:
                flash('Поисковые предпочтения сохранены', 'success')
        
        # Получить рейтинги для результатов
        for mc in masterclasses:
            rating = ReviewService.get_masterclass_average_rating(mc.id)
            count = ReviewService.get_masterclass_review_count(mc.id)
            masterclass_ratings[mc.id] = {'rating': rating, 'count': count}
    
    # Если это AJAX запрос, вернуть JSON
    if is_ajax:
        masterclasses_data = []
        for mc in masterclasses:
            mc_data = {
                'id': mc.id,
                'title': mc.title,
                'description': mc.description,
                'date_time': mc.date_time.strftime('%d.%m.%Y в %H:%M'),
                'category': mc.category,
                'price': float(mc.price) if mc.price else None,
                'max_participants': mc.max_participants,
                'current_participants': mc.current_participants,
                'rating': masterclass_ratings.get(mc.id, {}).get('rating'),
                'review_count': masterclass_ratings.get(mc.id, {}).get('count', 0)
            }
            masterclasses_data.append(mc_data)
        
        return jsonify({
            'masterclasses': masterclasses_data,
            'page': page,
            'has_more': len(all_masterclasses) > end_idx
        })
    
    # Получить популярные категории
    popular_categories = SearchService.get_popular_categories()
    
    return render_template(
        'public/search.html',
        form=form,
        masterclasses=masterclasses,
        masterclass_ratings=masterclass_ratings,
        popular_categories=popular_categories,
        saved_preferences=saved_preferences,
        current_sort=sort_by,
        current_order=sort_order
    )
