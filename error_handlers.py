"""
Обработчики ошибок и исключений для веб-портала мастер-классов
Требования: 1.4, 2.3, 3.4, 5.4
"""
from flask import render_template, flash, redirect, url_for, request
from sqlalchemy.exc import (
    IntegrityError, OperationalError, DatabaseError, 
    DataError, InvalidRequestError
)
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)


class MasterclassError(Exception):
    """Базовый класс для ошибок мастер-классов"""
    pass


class MasterclassFullError(MasterclassError):
    """
    Исключение для заполненных мастер-классов
    Требование: 1.4
    """
    def __init__(self, masterclass_title):
        self.masterclass_title = masterclass_title
        super().__init__(f"Мастер-класс '{masterclass_title}' полностью заполнен")


class RegistrationError(MasterclassError):
    """
    Исключение для ошибок регистрации
    Требование: 2.3
    """
    pass


class DuplicateRegistrationError(RegistrationError):
    """
    Исключение для повторной регистрации
    Требование: 2.3, 2.5
    """
    def __init__(self, email, masterclass_title):
        self.email = email
        self.masterclass_title = masterclass_title
        super().__init__(f"Пользователь {email} уже зарегистрирован на '{masterclass_title}'")


class TimeConstraintError(MasterclassError):
    """
    Исключение для нарушения временных ограничений
    Требование: 3.4
    """
    def __init__(self, message):
        super().__init__(message)


class CancellationTooLateError(TimeConstraintError):
    """
    Исключение для отмены регистрации менее чем за 24 часа
    Требование: 3.4
    """
    def __init__(self, masterclass_title, hours_remaining):
        self.masterclass_title = masterclass_title
        self.hours_remaining = hours_remaining
        super().__init__(
            f"Отмена регистрации на '{masterclass_title}' невозможна: "
            f"до начала осталось {hours_remaining:.1f} часов (требуется минимум 24 часа)"
        )


class DatabaseConnectionError(MasterclassError):
    """
    Исключение для ошибок подключения к базе данных
    Требование: 5.4
    """
    def __init__(self, original_error):
        self.original_error = original_error
        super().__init__(f"Ошибка подключения к базе данных: {str(original_error)}")


class DataValidationError(MasterclassError):
    """
    Исключение для ошибок валидации данных
    Требование: 5.1
    """
    def __init__(self, field, message):
        self.field = field
        super().__init__(f"Ошибка валидации поля '{field}': {message}")


def handle_database_error(error):
    """
    Обработчик ошибок базы данных
    Требование: 5.4
    """
    logger.error(f"Database error: {str(error)}", exc_info=True)
    
    if isinstance(error, OperationalError):
        # Ошибки подключения или операционные ошибки
        return render_template(
            'errors/database_error.html',
            error_message="Временные проблемы с базой данных. Пожалуйста, попробуйте позже."
        ), 503
    
    elif isinstance(error, IntegrityError):
        # Нарушение ограничений целостности
        error_message = "Ошибка сохранения данных. Возможно, такая запись уже существует."
        if 'unique_registration_per_masterclass' in str(error):
            error_message = "Вы уже зарегистрированы на этот мастер-класс."
        return render_template(
            'errors/database_error.html',
            error_message=error_message
        ), 400
    
    elif isinstance(error, DataError):
        # Ошибки данных (неверный формат, переполнение и т.д.)
        return render_template(
            'errors/database_error.html',
            error_message="Некорректный формат данных. Проверьте введенную информацию."
        ), 400
    
    else:
        # Общие ошибки базы данных
        return render_template(
            'errors/database_error.html',
            error_message="Произошла ошибка при работе с базой данных."
        ), 500


def handle_masterclass_full_error(error):
    """
    Обработчик ошибки заполненного мастер-класса
    Требование: 1.4
    """
    logger.warning(f"Masterclass full: {str(error)}")
    flash(f"К сожалению, все места на мастер-класс '{error.masterclass_title}' заняты.", 'warning')
    return redirect(url_for('public.index'))


def handle_duplicate_registration_error(error):
    """
    Обработчик ошибки повторной регистрации
    Требование: 2.3, 2.5
    """
    logger.info(f"Duplicate registration attempt: {str(error)}")
    flash(
        f"Вы уже зарегистрированы на мастер-класс '{error.masterclass_title}'. "
        f"Проверьте свои регистрации по email {error.email}.",
        'info'
    )
    return redirect(url_for('public.my_registrations'))


def handle_time_constraint_error(error):
    """
    Обработчик ошибок временных ограничений
    Требование: 3.4
    """
    logger.warning(f"Time constraint violation: {str(error)}")
    flash(str(error), 'error')
    return redirect(request.referrer or url_for('public.index'))


def handle_validation_error(error):
    """
    Обработчик ошибок валидации данных
    Требование: 5.1
    """
    logger.warning(f"Validation error: {str(error)}")
    flash(str(error), 'error')
    return redirect(request.referrer or url_for('public.index'))


def register_error_handlers(app):
    """
    Регистрация всех обработчиков ошибок в приложении
    Требования: 1.4, 2.3, 3.4, 5.4
    """
    
    # Обработчики HTTP ошибок
    @app.errorhandler(404)
    def not_found_error(error):
        """Обработчик ошибки 404 - страница не найдена"""
        logger.warning(f"404 error: {request.url}")
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden_error(error):
        """Обработчик ошибки 403 - доступ запрещен"""
        logger.warning(f"403 error: {request.url}")
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def internal_error(error):
        """Обработчик ошибки 500 - внутренняя ошибка сервера"""
        logger.error(f"500 error: {str(error)}", exc_info=True)
        from extensions import db
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    # Обработчики ошибок базы данных
    @app.errorhandler(OperationalError)
    def handle_operational_error(error):
        """Обработчик операционных ошибок БД - Требование: 5.4"""
        from extensions import db
        db.session.rollback()
        return handle_database_error(error)
    
    @app.errorhandler(IntegrityError)
    def handle_integrity_error(error):
        """Обработчик ошибок целостности БД - Требование: 5.4"""
        from extensions import db
        db.session.rollback()
        return handle_database_error(error)
    
    @app.errorhandler(DatabaseError)
    def handle_general_database_error(error):
        """Обработчик общих ошибок БД - Требование: 5.4"""
        from extensions import db
        db.session.rollback()
        return handle_database_error(error)
    
    # Обработчики кастомных ошибок
    @app.errorhandler(MasterclassFullError)
    def handle_full_masterclass(error):
        """Обработчик заполненных мастер-классов - Требование: 1.4"""
        return handle_masterclass_full_error(error)
    
    @app.errorhandler(DuplicateRegistrationError)
    def handle_duplicate_registration(error):
        """Обработчик повторной регистрации - Требование: 2.3"""
        return handle_duplicate_registration_error(error)
    
    @app.errorhandler(TimeConstraintError)
    def handle_time_constraint(error):
        """Обработчик временных ограничений - Требование: 3.4"""
        return handle_time_constraint_error(error)
    
    @app.errorhandler(DataValidationError)
    def handle_data_validation(error):
        """Обработчик ошибок валидации - Требование: 5.1"""
        return handle_validation_error(error)
    
    logger.info("Error handlers registered successfully")


def safe_database_operation(operation, *args, **kwargs):
    """
    Безопасное выполнение операции с базой данных с обработкой ошибок
    Требование: 5.4
    
    Args:
        operation: Функция для выполнения
        *args: Позиционные аргументы для функции
        **kwargs: Именованные аргументы для функции
    
    Returns:
        Результат операции или None в случае ошибки
    
    Raises:
        DatabaseConnectionError: При ошибках подключения к БД
    """
    from extensions import db
    
    try:
        result = operation(*args, **kwargs)
        db.session.commit()
        return result
    
    except OperationalError as e:
        db.session.rollback()
        logger.error(f"Database operational error: {str(e)}", exc_info=True)
        raise DatabaseConnectionError(e)
    
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error: {str(e)}", exc_info=True)
        raise
    
    except DatabaseError as e:
        db.session.rollback()
        logger.error(f"Database error: {str(e)}", exc_info=True)
        raise DatabaseConnectionError(e)
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error in database operation: {str(e)}", exc_info=True)
        raise


def validate_masterclass_capacity(masterclass):
    """
    Проверка доступности мест в мастер-классе
    Требование: 1.4, 5.3
    
    Args:
        masterclass: Объект Masterclass
    
    Raises:
        MasterclassFullError: Если мастер-класс заполнен
    """
    if masterclass.is_full:
        raise MasterclassFullError(masterclass.title)


def validate_time_constraint_for_cancellation(masterclass):
    """
    Проверка временных ограничений для отмены регистрации
    Требование: 3.4
    
    Args:
        masterclass: Объект Masterclass
    
    Raises:
        CancellationTooLateError: Если до начала осталось менее 24 часов
    """
    from datetime import datetime
    
    if not masterclass.is_upcoming:
        raise TimeConstraintError(
            f"Мастер-класс '{masterclass.title}' уже прошел. Отмена регистрации невозможна."
        )
    
    time_until_start = masterclass.date_time - datetime.utcnow()
    hours_remaining = time_until_start.total_seconds() / 3600
    
    if hours_remaining < 24:
        raise CancellationTooLateError(masterclass.title, hours_remaining)
