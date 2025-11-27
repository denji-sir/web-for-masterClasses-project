"""
Маршруты для панели создателей ивентов
Требования: 4.1, 4.2, 4.3, 4.4, 4.5
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from forms import (LoginForm, UserRegistrationForm, MasterclassForm, 
                   EventCreatorProfileForm)
from services import (UserService, EventCreatorService, MasterclassService, 
                     RegistrationService)
from models import User, EventCreator, Masterclass

# Blueprint для создателей ивентов
creator_bp = Blueprint('creator', __name__, url_prefix='/creator')


def login_required(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('creator.login'))
        return f(*args, **kwargs)
    return decorated_function


def creator_required(f):
    """Декоратор для проверки роли создателя ивентов"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('creator.login'))
        
        user = UserService.get_user_by_id(session['user_id'])
        if not user or not user.is_event_creator():
            flash('Доступ запрещен. Требуется роль создателя ивентов', 'error')
            return redirect(url_for('public.index'))
        
        return f(*args, **kwargs)
    return decorated_function


@creator_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Страница входа для создателей ивентов
    Требования: 4.1
    """
    # Если пользователь уже вошел, перенаправить на панель
    if 'user_id' in session:
        return redirect(url_for('creator.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = UserService.authenticate_user(form.email.data, form.password.data)
        
        if user:
            if user.is_event_creator():
                session['user_id'] = user.id
                session['user_role'] = user.role
                session['user_name'] = user.name
                
                flash(f'Добро пожаловать, {user.name}!', 'success')
                return redirect(url_for('creator.dashboard'))
            else:
                flash('У вас нет прав создателя ивентов', 'error')
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('creator/login.html', form=form)


@creator_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Страница регистрации для создателей ивентов
    Требования: 4.1
    """
    # Если пользователь уже вошел, перенаправить на панель
    if 'user_id' in session:
        return redirect(url_for('creator.dashboard'))
    
    form = UserRegistrationForm()
    
    if form.validate_on_submit():
        # Создать пользователя с ролью event_creator
        user = UserService.create_user(
            email=form.email.data,
            password=form.password.data,
            name=form.name.data,
            phone=form.phone.data,
            role='event_creator'
        )
        
        if user:
            # Создать профиль создателя ивентов
            creator = EventCreatorService.create_event_creator(user.id)
            
            if creator:
                flash('Регистрация успешна! Теперь вы можете войти', 'success')
                return redirect(url_for('creator.login'))
            else:
                flash('Ошибка создания профиля создателя', 'error')
        else:
            flash('Ошибка регистрации. Email уже используется', 'error')
    
    return render_template('creator/register.html', form=form)


@creator_bp.route('/logout')
@login_required
def logout():
    """
    Выход из системы
    Требования: 4.1
    """
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('creator.login'))


@creator_bp.route('/dashboard')
@creator_required
def dashboard():
    """
    Панель управления создателя ивентов со списком его мастер-классов и статистикой
    Требования: 4.1, 9.1
    """
    from services import AnalyticsService
    
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('public.index'))
    
    # Получить все мастер-классы создателя
    masterclasses = EventCreatorService.get_creator_masterclasses(creator.id)
    
    # Получить расширенную статистику через AnalyticsService
    stats = AnalyticsService.get_creator_stats(creator.id)
    
    # Получить краткий отчет о доходах за последний месяц
    revenue_report = AnalyticsService.get_revenue_report(creator.id, period='month')
    
    return render_template(
        'creator/dashboard.html',
        user=user,
        creator=creator,
        masterclasses=masterclasses,
        stats=stats,
        revenue_report=revenue_report
    )


@creator_bp.route('/profile', methods=['GET', 'POST'])
@creator_required
def profile():
    """
    Страница профиля создателя ивентов
    Требования: 4.1
    """
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    form = EventCreatorProfileForm()
    
    if form.validate_on_submit():
        success = EventCreatorService.update_creator_profile(
            creator.id,
            company_name=form.company_name.data,
            description=form.description.data
        )
        
        if success:
            flash('Профиль успешно обновлен', 'success')
            return redirect(url_for('creator.profile'))
        else:
            flash('Ошибка обновления профиля', 'error')
    
    # Заполнить форму текущими данными
    form.company_name.data = creator.company_name
    form.description.data = creator.description
    
    return render_template('creator/profile.html', user=user, creator=creator, form=form)


@creator_bp.route('/masterclass/create', methods=['GET', 'POST'])
@creator_required
def create_masterclass():
    """
    Создание нового мастер-класса
    Требования: 4.2
    """
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    form = MasterclassForm()
    
    if form.validate_on_submit():
        masterclass = MasterclassService.create_masterclass(
            creator_id=creator.id,
            title=form.title.data,
            description=form.description.data,
            date_time=form.date_time.data,
            max_participants=form.max_participants.data,
            price=form.price.data,
            category=form.category.data
        )
        
        if masterclass:
            flash(f'Мастер-класс "{masterclass.title}" успешно создан', 'success')
            return redirect(url_for('creator.dashboard'))
        else:
            flash('Ошибка создания мастер-класса', 'error')
    
    return render_template('creator/create_masterclass.html', form=form, user=user)


@creator_bp.route('/masterclass/<int:masterclass_id>/edit', methods=['GET', 'POST'])
@creator_required
def edit_masterclass(masterclass_id):
    """
    Редактирование собственного мастер-класса
    Требования: 4.3
    """
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Проверить, что мастер-класс принадлежит текущему создателю
    if masterclass.creator_id != creator.id:
        flash('У вас нет прав для редактирования этого мастер-класса', 'error')
        return redirect(url_for('creator.dashboard'))
    
    form = MasterclassForm()
    
    if form.validate_on_submit():
        success = MasterclassService.update_masterclass(
            masterclass_id=masterclass_id,
            creator_id=creator.id,
            title=form.title.data,
            description=form.description.data,
            date_time=form.date_time.data,
            max_participants=form.max_participants.data,
            price=form.price.data,
            category=form.category.data
        )
        
        if success:
            flash(f'Мастер-класс "{form.title.data}" успешно обновлен', 'success')
            return redirect(url_for('creator.dashboard'))
        else:
            flash('Ошибка обновления мастер-класса', 'error')
    
    # Заполнить форму текущими данными
    form.title.data = masterclass.title
    form.description.data = masterclass.description
    form.date_time.data = masterclass.date_time
    form.max_participants.data = masterclass.max_participants
    form.price.data = masterclass.price
    form.category.data = masterclass.category
    
    return render_template(
        'creator/edit_masterclass.html',
        form=form,
        masterclass=masterclass,
        user=user
    )


@creator_bp.route('/masterclass/<int:masterclass_id>/participants')
@creator_required
def view_participants(masterclass_id):
    """
    Просмотр списка участников своего мастер-класса
    Требования: 4.5
    """
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Проверить, что мастер-класс принадлежит текущему создателю
    if masterclass.creator_id != creator.id:
        flash('У вас нет прав для просмотра участников этого мастер-класса', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Получить список участников
    participants = RegistrationService.get_masterclass_participants(masterclass_id)
    
    return render_template(
        'creator/participants.html',
        masterclass=masterclass,
        participants=participants,
        user=user
    )


@creator_bp.route('/masterclass/<int:masterclass_id>/delete', methods=['POST'])
@creator_required
def delete_masterclass(masterclass_id):
    """
    Удаление собственного мастер-класса
    Требования: 4.4
    """
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Проверить, что мастер-класс принадлежит текущему создателю
    if masterclass.creator_id != creator.id:
        flash('У вас нет прав для удаления этого мастер-класса', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass_title = masterclass.title
    
    # Удалить мастер-класс
    success = MasterclassService.delete_masterclass(masterclass_id, creator_id=creator.id)
    
    if success:
        flash(f'Мастер-класс "{masterclass_title}" успешно удален. Участники уведомлены', 'success')
    else:
        flash('Ошибка удаления мастер-класса', 'error')
    
    return redirect(url_for('creator.dashboard'))


@creator_bp.route('/analytics')
@creator_required
def analytics():
    """
    Страница аналитики и статистики создателя
    Требования: 9.1, 9.2
    """
    from services import AnalyticsService
    
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Получить общую статистику
    stats = AnalyticsService.get_creator_stats(creator.id)
    
    # Получить отчет о доходах
    revenue_report = AnalyticsService.get_revenue_report(creator.id, period='all')
    
    # Получить статистику популярности
    popularity_stats = AnalyticsService.get_popularity_stats(creator.id)
    
    return render_template(
        'creator/analytics.html',
        user=user,
        creator=creator,
        stats=stats,
        revenue_report=revenue_report,
        popularity_stats=popularity_stats
    )


@creator_bp.route('/masterclass/<int:masterclass_id>/analytics')
@creator_required
def masterclass_analytics(masterclass_id):
    """
    Детальная аналитика конкретного мастер-класса
    Требования: 9.2
    """
    from services import AnalyticsService
    
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Проверить, что мастер-класс принадлежит текущему создателю
    if masterclass.creator_id != creator.id:
        flash('У вас нет прав для просмотра аналитики этого мастер-класса', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Получить аналитику мастер-класса
    analytics_data = AnalyticsService.get_masterclass_analytics(masterclass_id)
    
    return render_template(
        'creator/masterclass_analytics.html',
        user=user,
        creator=creator,
        masterclass=masterclass,
        analytics=analytics_data
    )


@creator_bp.route('/masterclass/<int:masterclass_id>/export-csv')
@creator_required
def export_participants_csv(masterclass_id):
    """
    Экспорт списка участников в CSV
    Требования: 9.4
    """
    from flask import Response
    from services import AnalyticsService
    
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    masterclass = MasterclassService.get_masterclass_by_id(masterclass_id)
    
    if not masterclass:
        flash('Мастер-класс не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Проверить, что мастер-класс принадлежит текущему создателю
    if masterclass.creator_id != creator.id:
        flash('У вас нет прав для экспорта участников этого мастер-класса', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Экспортировать CSV
    csv_content = AnalyticsService.export_participants_csv(masterclass_id)
    
    if not csv_content:
        flash('Ошибка экспорта данных', 'error')
        return redirect(url_for('creator.view_participants', masterclass_id=masterclass_id))
    
    # Создать ответ с CSV файлом
    filename = f"participants_{masterclass.title.replace(' ', '_')}_{masterclass.date_time.strftime('%Y%m%d')}.csv"
    
    return Response(
        csv_content,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


@creator_bp.route('/calendar')
@creator_required
def calendar_view():
    """
    Календарный вид мастер-классов
    Требования: 9.3, 9.5
    """
    from services import AnalyticsService
    from datetime import datetime
    
    user = UserService.get_user_by_id(session['user_id'])
    creator = EventCreatorService.get_creator_by_user_id(user.id)
    
    if not creator:
        flash('Профиль создателя не найден', 'error')
        return redirect(url_for('creator.dashboard'))
    
    # Получить параметры года и месяца из запроса
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    # Если не указаны, использовать текущие
    if not year or not month:
        now = datetime.utcnow()
        year = now.year
        month = now.month
    
    # Получить календарные события
    calendar_events = AnalyticsService.get_calendar_view(creator.id, year, month)
    
    return render_template(
        'creator/calendar.html',
        user=user,
        creator=creator,
        calendar_events=calendar_events,
        current_year=year,
        current_month=month
    )
