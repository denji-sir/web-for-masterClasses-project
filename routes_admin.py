"""
Маршруты для административной панели
Требования: 5.1, 5.2, 5.3, 5.4, 5.5
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from forms import (LoginForm, AdminCreateUserForm, AdminUserForm, AdminRoleForm, 
                   MasterclassForm)
from services import (UserService, AdminService, MasterclassService, 
                     RegistrationService, EventCreatorService, ReviewService)
from models import User, EventCreator, Masterclass

# Blueprint для администраторов
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def login_required(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для проверки роли администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'warning')
            return redirect(url_for('admin.login'))
        
        user = UserService.get_user_by_id(session['user_id'])
        if not user or not user.is_admin():
            flash('Доступ запрещен. Требуются права администратора', 'error')
            return redirect(url_for('public.index'))
        
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Страница входа для администраторов
    Требования: 5.1
    """
    # Если пользователь уже вошел, перенаправить на панель
    if 'user_id' in session:
        user = UserService.get_user_by_id(session['user_id'])
        if user and user.is_admin():
            return redirect(url_for('admin.dashboard'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = UserService.authenticate_user(form.email.data, form.password.data)
        
        if user:
            if user.is_admin():
                session['user_id'] = user.id
                session['user_role'] = user.role
                session['user_name'] = user.name
                
                flash(f'Добро пожаловать, {user.name}!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash('У вас нет прав администратора', 'error')
        else:
            flash('Неверный email или пароль', 'error')
    
    return render_template('admin/login.html', form=form)


@admin_bp.route('/logout')
@login_required
def logout():
    """
    Выход из системы
    Требования: 5.1
    """
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('admin.login'))


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    """
    Административная панель с общей статистикой
    Требования: 5.1
    """
    user = UserService.get_user_by_id(session['user_id'])
    
    # Получить статистику системы
    stats = AdminService.get_system_statistics()
    
    # Получить последних пользователей
    recent_users = AdminService.get_all_users()[:5]
    
    # Получить последние мастер-классы
    recent_masterclasses = AdminService.get_all_masterclasses()[:5]
    
    return render_template(
        'admin/dashboard.html',
        user=user,
        stats=stats,
        recent_users=recent_users,
        recent_masterclasses=recent_masterclasses
    )


@admin_bp.route('/users')
@admin_required
def users():
    """
    Список всех пользователей
    Требования: 5.1, 5.2
    """
    user = UserService.get_user_by_id(session['user_id'])
    
    # Получить параметры фильтрации
    show_inactive = request.args.get('show_inactive', 'false') == 'true'
    role_filter = request.args.get('role', None)
    
    # Получить всех пользователей
    all_users = AdminService.get_all_users(include_inactive=show_inactive)
    
    # Фильтрация по роли
    if role_filter:
        all_users = [u for u in all_users if u.role == role_filter]
    
    return render_template(
        'admin/users.html',
        user=user,
        all_users=all_users,
        show_inactive=show_inactive,
        role_filter=role_filter
    )


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """
    Создание нового пользователя
    Требования: 5.1, 5.2
    """
    user = UserService.get_user_by_id(session['user_id'])
    form = AdminCreateUserForm()
    
    if form.validate_on_submit():
        new_user = UserService.create_user(
            email=form.email.data,
            password=form.password.data,
            name=form.name.data,
            phone=form.phone.data,
            role=form.role.data
        )
        
        if new_user:
            # Если роль event_creator, создать профиль
            if form.role.data == 'event_creator':
                EventCreatorService.create_event_creator(new_user.id)
            
            flash(f'Пользователь {new_user.name} успешно создан', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Ошибка создания пользователя', 'error')
    
    return render_template('admin/create_user.html', user=user, form=form)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """
    Редактирование пользователя
    Требования: 5.1, 5.2
    """
    current_user = UserService.get_user_by_id(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    
    form = AdminUserForm()
    
    if form.validate_on_submit():
        # Обновить данные пользователя
        update_data = {
            'name': form.name.data,
            'email': form.email.data,
            'phone': form.phone.data,
            'is_active': form.is_active.data
        }
        
        # Обработать изменение роли
        old_role = target_user.role
        new_role = form.role.data
        
        if old_role != new_role:
            success = AdminService.assign_role(user_id, new_role)
            if not success:
                flash('Ошибка назначения роли', 'error')
                return redirect(url_for('admin.edit_user', user_id=user_id))
        
        success = UserService.update_user(user_id, **update_data)
        
        if success:
            flash(f'Пользователь {form.name.data} успешно обновлен', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Ошибка обновления пользователя', 'error')
    
    # Заполнить форму текущими данными
    form.name.data = target_user.name
    form.email.data = target_user.email
    form.phone.data = target_user.phone
    form.role.data = target_user.role
    form.is_active.data = target_user.is_active
    
    return render_template(
        'admin/edit_user.html',
        user=current_user,
        target_user=target_user,
        form=form
    )


@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@admin_required
def block_user(user_id):
    """
    Блокировка пользователя
    Требования: 5.2
    """
    # Проверить, что это не текущий пользователь
    if user_id == session['user_id']:
        flash('Вы не можете заблокировать себя', 'error')
        return redirect(url_for('admin.users'))
    
    target_user = User.query.get_or_404(user_id)
    
    success = AdminService.block_user(user_id)
    
    if success:
        flash(f'Пользователь {target_user.name} заблокирован', 'success')
    else:
        flash('Ошибка блокировки пользователя', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
@admin_required
def unblock_user(user_id):
    """
    Разблокировка пользователя
    Требования: 5.2
    """
    target_user = User.query.get_or_404(user_id)
    
    success = AdminService.unblock_user(user_id)
    
    if success:
        flash(f'Пользователь {target_user.name} разблокирован', 'success')
    else:
        flash('Ошибка разблокировки пользователя', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """
    Удаление пользователя
    Требования: 5.2
    """
    # Проверить, что это не текущий пользователь
    if user_id == session['user_id']:
        flash('Вы не можете удалить себя', 'error')
        return redirect(url_for('admin.users'))
    
    target_user = User.query.get_or_404(user_id)
    user_name = target_user.name
    
    success = AdminService.delete_user(user_id)
    
    if success:
        flash(f'Пользователь {user_name} удален', 'success')
    else:
        flash('Ошибка удаления пользователя. Возможно, это последний администратор', 'error')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/assign-role', methods=['GET', 'POST'])
@admin_required
def assign_role(user_id):
    """
    Назначение роли пользователю
    Требования: 5.5
    """
    current_user = UserService.get_user_by_id(session['user_id'])
    target_user = User.query.get_or_404(user_id)
    
    form = AdminRoleForm()
    
    if form.validate_on_submit():
        success = AdminService.assign_role(user_id, form.role.data)
        
        if success:
            flash(f'Роль "{form.role.data}" назначена пользователю {target_user.name}', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Ошибка назначения роли', 'error')
    
    # Заполнить форму текущей ролью
    form.role.data = target_user.role
    
    return render_template(
        'admin/assign_role.html',
        user=current_user,
        target_user=target_user,
        form=form
    )


@admin_bp.route('/masterclasses')
@admin_required
def masterclasses():
    """
    Список всех мастер-классов
    Требования: 5.3
    """
    user = UserService.get_user_by_id(session['user_id'])
    
    # Получить параметры фильтрации
    show_inactive = request.args.get('show_inactive', 'false') == 'true'
    category_filter = request.args.get('category', None)
    
    # Получить все мастер-классы
    all_masterclasses = AdminService.get_all_masterclasses(include_inactive=show_inactive)
    
    # Фильтрация по категории
    if category_filter:
        all_masterclasses = [m for m in all_masterclasses if m.category == category_filter]
    
    return render_template(
        'admin/masterclasses.html',
        user=user,
        masterclasses=all_masterclasses,
        show_inactive=show_inactive,
        category_filter=category_filter
    )


@admin_bp.route('/masterclasses/<int:masterclass_id>')
@admin_required
def masterclass_detail(masterclass_id):
    """
    Детальная информация о мастер-классе
    Требования: 5.3
    """
    user = UserService.get_user_by_id(session['user_id'])
    masterclass = Masterclass.query.get_or_404(masterclass_id)
    
    # Получить список участников
    participants = RegistrationService.get_masterclass_participants(masterclass_id)
    
    return render_template(
        'admin/masterclass_detail.html',
        user=user,
        masterclass=masterclass,
        participants=participants
    )


@admin_bp.route('/masterclasses/<int:masterclass_id>/delete', methods=['POST'])
@admin_required
def delete_masterclass(masterclass_id):
    """
    Удаление мастер-класса
    Требования: 5.4
    """
    masterclass = Masterclass.query.get_or_404(masterclass_id)
    masterclass_title = masterclass.title
    
    # Удалить мастер-класс (без проверки creator_id, т.к. администратор)
    success = MasterclassService.delete_masterclass(masterclass_id)
    
    if success:
        flash(f'Мастер-класс "{masterclass_title}" удален. Участники уведомлены', 'success')
    else:
        flash('Ошибка удаления мастер-класса', 'error')
    
    return redirect(url_for('admin.masterclasses'))


@admin_bp.route('/masterclasses/<int:masterclass_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_masterclass_active(masterclass_id):
    """
    Активация/деактивация мастер-класса
    Требования: 5.3
    """
    masterclass = Masterclass.query.get_or_404(masterclass_id)
    
    # Переключить статус активности
    new_status = not masterclass.is_active
    success = MasterclassService.update_masterclass(
        masterclass_id,
        is_active=new_status
    )
    
    if success:
        status_text = 'активирован' if new_status else 'деактивирован'
        flash(f'Мастер-класс "{masterclass.title}" {status_text}', 'success')
    else:
        flash('Ошибка изменения статуса мастер-класса', 'error')
    
    return redirect(url_for('admin.masterclasses'))


@admin_bp.route('/reviews')
@admin_required
def reviews():
    """
    Модерация отзывов
    Требования: 10.4
    """
    user = UserService.get_user_by_id(session['user_id'])
    
    # Получить параметры фильтрации
    show_approved = request.args.get('show_approved', 'false') == 'true'
    
    if show_approved:
        # Показать все отзывы
        from models import Review
        all_reviews = Review.query.order_by(Review.created_at.desc()).all()
    else:
        # Показать только неодобренные отзывы
        all_reviews = ReviewService.get_pending_reviews()
    
    return render_template(
        'admin/reviews.html',
        user=user,
        reviews=all_reviews,
        show_approved=show_approved
    )


@admin_bp.route('/reviews/<int:review_id>/approve', methods=['POST'])
@admin_required
def approve_review(review_id):
    """
    Одобрить отзыв
    Требования: 10.4
    """
    success = ReviewService.approve_review(review_id)
    
    if success:
        flash('Отзыв одобрен', 'success')
    else:
        flash('Ошибка одобрения отзыва', 'error')
    
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/reject', methods=['POST'])
@admin_required
def reject_review(review_id):
    """
    Отклонить отзыв
    Требования: 10.4
    """
    success = ReviewService.reject_review(review_id)
    
    if success:
        flash('Отзыв отклонен', 'success')
    else:
        flash('Ошибка отклонения отзыва', 'error')
    
    return redirect(url_for('admin.reviews'))


@admin_bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@admin_required
def delete_review(review_id):
    """
    Удалить отзыв
    Требования: 10.4
    """
    success = ReviewService.delete_review(review_id)
    
    if success:
        flash('Отзыв удален', 'success')
    else:
        flash('Ошибка удаления отзыва', 'error')
    
    return redirect(url_for('admin.reviews'))
