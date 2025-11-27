from flask import Flask
import os
from extensions import db, csrf, mail

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration - use absolute path for SQLite
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'instance', 'masterclass_portal.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER') or 'localhost'
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 587)
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@masterclass-portal.com'
    
    # Initialize extensions with app
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Import models and services to ensure they are registered with SQLAlchemy
    with app.app_context():
        from models import User, EventCreator, Masterclass, Registration
        from services import (UserService, EventCreatorService, MasterclassService, 
                            RegistrationService, EmailService, AdminService)
        # Create database tables
        db.create_all()
    
    # Register blueprints
    from routes import public_bp
    from routes_creator import creator_bp
    from routes_admin import admin_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(creator_bp)
    app.register_blueprint(admin_bp)
    
    # Register comprehensive error handlers - Требования: 1.4, 2.3, 3.4, 5.4
    from error_handlers import register_error_handlers
    register_error_handlers(app)
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)