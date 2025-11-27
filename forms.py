"""
Формы для веб-портала регистрации на мастер-классы
Требования: 2.1, 4.1, 5.1, 5.2, 6.2
"""
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, TextAreaField, DateTimeField,
    IntegerField, DecimalField, SelectField, BooleanField, SubmitField
)
from wtforms.validators import (
    DataRequired, Email, Length, ValidationError, Optional,
    NumberRange, EqualTo
)
from datetime import datetime
from models import User, Masterclass


class LoginForm(FlaskForm):
    """
    Форма для аутентификации пользователей
    Требования: 2.1, 5.1
    """
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email обязателен'),
            Email(message='Некорректный формат email адреса'),
            Length(max=100, message='Email не должен превышать 100 символов')
        ]
    )
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Пароль обязателен'),
            Length(min=6, message='Пароль должен содержать минимум 6 символов')
        ]
    )
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class UserRegistrationForm(FlaskForm):
    """
    Форма регистрации нового пользователя
    Требования: 5.1, 5.2, 6.2
    """
    name = StringField(
        'Имя',
        validators=[
            DataRequired(message='Имя обязательно'),
            Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email обязателен'),
            Email(message='Некорректный формат email адреса'),
            Length(max=100, message='Email не должен превышать 100 символов')
        ]
    )
    phone = StringField(
        'Телефон',
        validators=[
            Optional(),
            Length(max=20, message='Телефон не должен превышать 20 символов')
        ]
    )
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Пароль обязателен'),
            Length(min=6, message='Пароль должен содержать минимум 6 символов')
        ]
    )
    confirm_password = PasswordField(
        'Подтвердите пароль',
        validators=[
            DataRequired(message='Подтверждение пароля обязательно'),
            EqualTo('password', message='Пароли должны совпадать')
        ]
    )
    submit = SubmitField('Зарегистрироваться')
    
    def validate_email(self, field):
        """
        Валидация уникальности email
        Требования: 5.2, 6.2
        """
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')


class RegistrationForm(FlaskForm):
    """
    Форма регистрации на мастер-класс
    Требования: 2.1, 5.2
    """
    user_name = StringField(
        'Имя',
        validators=[
            DataRequired(message='Имя обязательно'),
            Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
        ]
    )
    user_email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email обязателен'),
            Email(message='Некорректный формат email адреса'),
            Length(max=100, message='Email не должен превышать 100 символов')
        ]
    )
    user_phone = StringField(
        'Телефон',
        validators=[
            Optional(),
            Length(max=20, message='Телефон не должен превышать 20 символов')
        ]
    )
    submit = SubmitField('Зарегистрироваться')


class MasterclassForm(FlaskForm):
    """
    Форма создания и редактирования мастер-класса для создателей ивентов
    Требования: 4.1, 4.2, 4.3, 5.1
    """
    title = StringField(
        'Название',
        validators=[
            DataRequired(message='Название обязательно'),
            Length(min=3, max=200, message='Название должно быть от 3 до 200 символов')
        ]
    )
    description = TextAreaField(
        'Описание',
        validators=[
            Optional(),
            Length(max=5000, message='Описание не должно превышать 5000 символов')
        ]
    )
    date_time = DateTimeField(
        'Дата и время',
        format='%Y-%m-%dT%H:%M',
        validators=[
            DataRequired(message='Дата и время обязательны')
        ]
    )
    max_participants = IntegerField(
        'Максимальное количество участников',
        validators=[
            DataRequired(message='Количество участников обязательно'),
            NumberRange(min=1, max=1000, message='Количество участников должно быть от 1 до 1000')
        ]
    )
    price = DecimalField(
        'Стоимость (₽)',
        places=2,
        validators=[
            Optional(),
            NumberRange(min=0, message='Стоимость не может быть отрицательной')
        ]
    )
    category = SelectField(
        'Категория',
        choices=[
            ('', 'Выберите категорию'),
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
        ],
        validators=[Optional()]
    )
    submit = SubmitField('Сохранить')
    
    def validate_date_time(self, field):
        """
        Валидация даты и времени (должна быть в будущем)
        Требования: 5.1
        """
        if field.data and field.data <= datetime.utcnow():
            raise ValidationError('Дата и время должны быть в будущем')


class SearchForm(FlaskForm):
    """
    Форма поиска регистраций по email
    Требования: 3.1, 5.2
    """
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email обязателен'),
            Email(message='Некорректный формат email адреса'),
            Length(max=100, message='Email не должен превышать 100 символов')
        ]
    )
    submit = SubmitField('Найти регистрации')


class AdminUserForm(FlaskForm):
    """
    Форма управления пользователями для администраторов
    Требования: 5.1, 5.2, 5.5
    """
    name = StringField(
        'Имя',
        validators=[
            DataRequired(message='Имя обязательно'),
            Length(min=2, max=100, message='Имя должно быть от 2 до 100 символов')
        ]
    )
    email = StringField(
        'Email',
        validators=[
            DataRequired(message='Email обязателен'),
            Email(message='Некорректный формат email адреса'),
            Length(max=100, message='Email не должен превышать 100 символов')
        ]
    )
    phone = StringField(
        'Телефон',
        validators=[
            Optional(),
            Length(max=20, message='Телефон не должен превышать 20 символов')
        ]
    )
    role = SelectField(
        'Роль',
        choices=[
            ('user', 'Пользователь'),
            ('event_creator', 'Создатель ивентов'),
            ('admin', 'Администратор')
        ],
        validators=[DataRequired(message='Роль обязательна')]
    )
    is_active = BooleanField('Активен')
    submit = SubmitField('Сохранить')


class AdminCreateUserForm(AdminUserForm):
    """
    Форма создания пользователя администратором
    Требования: 5.1, 5.2
    """
    password = PasswordField(
        'Пароль',
        validators=[
            DataRequired(message='Пароль обязателен'),
            Length(min=6, message='Пароль должен содержать минимум 6 символов')
        ]
    )
    confirm_password = PasswordField(
        'Подтвердите пароль',
        validators=[
            DataRequired(message='Подтверждение пароля обязательно'),
            EqualTo('password', message='Пароли должны совпадать')
        ]
    )
    
    def validate_email(self, field):
        """
        Валидация уникальности email
        Требования: 5.2, 6.2
        """
        user = User.query.filter_by(email=field.data.lower().strip()).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован')


class AdminRoleForm(FlaskForm):
    """
    Форма назначения роли пользователю
    Требования: 5.5
    """
    role = SelectField(
        'Роль',
        choices=[
            ('user', 'Пользователь'),
            ('event_creator', 'Создатель ивентов'),
            ('admin', 'Администратор')
        ],
        validators=[DataRequired(message='Роль обязательна')]
    )
    submit = SubmitField('Назначить роль')


class EventCreatorProfileForm(FlaskForm):
    """
    Форма профиля создателя ивентов
    Требования: 4.1
    """
    company_name = StringField(
        'Название компании',
        validators=[
            Optional(),
            Length(max=200, message='Название компании не должно превышать 200 символов')
        ]
    )
    description = TextAreaField(
        'Описание',
        validators=[
            Optional(),
            Length(max=2000, message='Описание не должно превышать 2000 символов')
        ]
    )
    submit = SubmitField('Сохранить профиль')


class CancelRegistrationForm(FlaskForm):
    """
    Форма отмены регистрации
    Требования: 3.2
    """
    submit = SubmitField('Отменить регистрацию')


class AdvancedSearchForm(FlaskForm):
    """
    Форма расширенного поиска мастер-классов
    Требования: 8.1, 8.2, 8.3, 8.4, 8.5
    """
    query = StringField(
        'Поиск',
        validators=[
            Optional(),
            Length(max=200, message='Поисковый запрос не должен превышать 200 символов')
        ]
    )
    category = SelectField(
        'Категория',
        choices=[
            ('', 'Все категории'),
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
        ],
        validators=[Optional()]
    )
    date_from = DateTimeField(
        'Дата от',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    date_to = DateTimeField(
        'Дата до',
        format='%Y-%m-%d',
        validators=[Optional()]
    )
    price_min = DecimalField(
        'Цена от (₽)',
        places=2,
        validators=[
            Optional(),
            NumberRange(min=0, message='Цена не может быть отрицательной')
        ]
    )
    price_max = DecimalField(
        'Цена до (₽)',
        places=2,
        validators=[
            Optional(),
            NumberRange(min=0, message='Цена не может быть отрицательной')
        ]
    )
    min_rating = SelectField(
        'Минимальный рейтинг',
        choices=[
            ('', 'Любой рейтинг'),
            ('4.5', '⭐ 4.5+'),
            ('4.0', '⭐ 4.0+'),
            ('3.5', '⭐ 3.5+'),
            ('3.0', '⭐ 3.0+')
        ],
        validators=[Optional()]
    )
    sort_by = SelectField(
        'Сортировать по',
        choices=[
            ('date', 'Дате'),
            ('price', 'Цене'),
            ('popularity', 'Популярности'),
            ('rating', 'Рейтингу'),
            ('title', 'Названию')
        ],
        default='date',
        validators=[Optional()]
    )
    sort_order = SelectField(
        'Порядок',
        choices=[
            ('asc', 'По возрастанию'),
            ('desc', 'По убыванию')
        ],
        default='asc',
        validators=[Optional()]
    )
    submit = SubmitField('Искать')
    
    def validate(self, extra_validators=None):
        """
        Валидация диапазонов
        Требования: 5.1
        """
        if not super().validate(extra_validators):
            return False
        
        # Валидация диапазона дат
        if self.date_to.data and self.date_from.data and self.date_to.data < self.date_from.data:
            self.date_to.errors.append('Дата "до" не может быть раньше даты "от"')
            return False
        
        # Валидация диапазона цен
        if self.price_max.data and self.price_min.data and self.price_max.data < self.price_min.data:
            self.price_max.errors.append('Максимальная цена не может быть меньше минимальной')
            return False
        
        return True


class ReviewForm(FlaskForm):
    """
    Форма добавления отзыва о мастер-классе
    Требования: 10.4
    """
    rating = SelectField(
        'Рейтинг',
        choices=[
            ('5', '⭐⭐⭐⭐⭐ Отлично'),
            ('4', '⭐⭐⭐⭐ Хорошо'),
            ('3', '⭐⭐⭐ Нормально'),
            ('2', '⭐⭐ Плохо'),
            ('1', '⭐ Ужасно')
        ],
        validators=[DataRequired(message='Рейтинг обязателен')],
        coerce=int
    )
    comment = TextAreaField(
        'Комментарий',
        validators=[
            Optional(),
            Length(max=2000, message='Комментарий не должен превышать 2000 символов')
        ]
    )
    submit = SubmitField('Отправить отзыв')
