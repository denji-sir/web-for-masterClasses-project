from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    """Базовая модель пользователя с ролевой системой"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='user')  # 'user', 'event_creator', 'admin'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def set_password(self, password):
        """Установить хэш пароля"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверить пароль"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Проверить, является ли пользователь администратором"""
        return self.role == 'admin'
    
    def is_event_creator(self):
        """Проверить, является ли пользователь создателем ивентов"""
        return self.role == 'event_creator'
    
    def __repr__(self):
        return f'<User {self.email}>'

class EventCreator(db.Model):
    """Модель создателя ивентов (расширение пользователя)"""
    __tablename__ = 'event_creator'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(200))
    description = db.Column(db.Text)
    verified = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('event_creator_profile', uselist=False))
    masterclasses = db.relationship('Masterclass', backref='creator', cascade='all, delete-orphan', lazy='dynamic')
    
    def __repr__(self):
        return f'<EventCreator {self.company_name or self.user.name}>'

class Masterclass(db.Model):
    """Модель мастер-класса с привязкой к создателю"""
    __tablename__ = 'masterclass'
    
    id = db.Column(db.Integer, primary_key=True)
    creator_id = db.Column(db.Integer, db.ForeignKey('event_creator.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    date_time = db.Column(db.DateTime, nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)
    current_participants = db.Column(db.Integer, default=0, nullable=False)
    price = db.Column(db.Numeric(10, 2))
    category = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    registrations = db.relationship('Registration', backref='masterclass', cascade='all, delete-orphan', lazy='dynamic')
    
    @property
    def available_spots(self):
        """Количество доступных мест"""
        return self.max_participants - self.current_participants
    
    @property
    def is_full(self):
        """Проверить, заполнен ли мастер-класс"""
        return self.current_participants >= self.max_participants
    
    @property
    def is_upcoming(self):
        """Проверить, предстоящий ли мастер-класс"""
        return self.date_time > datetime.utcnow()
    
    def can_register(self):
        """Можно ли зарегистрироваться на мастер-класс"""
        return self.is_active and not self.is_full and self.is_upcoming
    
    def can_cancel_registration(self):
        """Можно ли отменить регистрацию (более 24 часов до начала)"""
        if not self.is_upcoming:
            return False
        time_until_start = self.date_time - datetime.utcnow()
        return time_until_start.total_seconds() > 24 * 3600  # 24 часа в секундах
    
    def __repr__(self):
        return f'<Masterclass {self.title}>'

class Registration(db.Model):
    """Модель регистрации с ограничениями уникальности"""
    __tablename__ = 'registration'
    
    id = db.Column(db.Integer, primary_key=True)
    masterclass_id = db.Column(db.Integer, db.ForeignKey('masterclass.id'), nullable=False)
    user_name = db.Column(db.String(100), nullable=False)
    user_email = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20))
    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Ограничение уникальности: один email на один мастер-класс
    __table_args__ = (
        db.UniqueConstraint('masterclass_id', 'user_email', name='unique_registration_per_masterclass'),
        db.Index('idx_registration_email', 'user_email'),
        db.Index('idx_registration_masterclass', 'masterclass_id'),
    )
    
    def __repr__(self):
        return f'<Registration {self.user_email} -> {self.masterclass.title}>'

# Дополнительные модели для расширенной функциональности

class UserProfile(db.Model):
    """Расширенный профиль пользователя"""
    __tablename__ = 'user_profile'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    bio = db.Column(db.Text)
    interests = db.Column(db.Text)  # JSON строка с интересами
    avatar_url = db.Column(db.String(255))
    notification_preferences = db.Column(db.Text)  # JSON настройки уведомлений
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('profile', uselist=False))
    
    def __repr__(self):
        return f'<UserProfile {self.user.name}>'

class Favorite(db.Model):
    """Избранные мастер-классы пользователей"""
    __tablename__ = 'favorite'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    masterclass_id = db.Column(db.Integer, db.ForeignKey('masterclass.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Ограничение уникальности
    __table_args__ = (
        db.UniqueConstraint('user_id', 'masterclass_id', name='unique_favorite'),
    )
    
    # Relationships
    user = db.relationship('User', backref='favorites')
    masterclass = db.relationship('Masterclass', backref='favorited_by')
    
    def __repr__(self):
        return f'<Favorite {self.user.name} -> {self.masterclass.title}>'

class Review(db.Model):
    """Отзывы о мастер-классах"""
    __tablename__ = 'review'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    masterclass_id = db.Column(db.Integer, db.ForeignKey('masterclass.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5 звезд
    comment = db.Column(db.Text)
    is_approved = db.Column(db.Boolean, default=True, nullable=False)  # Для модерации
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Ограничение уникальности: один отзыв от пользователя на мастер-класс
    __table_args__ = (
        db.UniqueConstraint('user_id', 'masterclass_id', name='unique_review'),
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='valid_rating'),
    )
    
    # Relationships
    user = db.relationship('User', backref='reviews')
    masterclass = db.relationship('Masterclass', backref='reviews')
    
    def __repr__(self):
        return f'<Review {self.user.name} -> {self.masterclass.title} ({self.rating}★)>'

class Notification(db.Model):
    """Системные уведомления"""
    __tablename__ = 'notification'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'reminder', 'cancellation', 'update', 'registration'
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification {self.type} -> {self.user.name}>'