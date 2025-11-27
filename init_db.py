#!/usr/bin/env python3
"""Database initialization script"""

from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration, Review, UserProfile, Favorite, Notification

def init_database():
    """Initialize the database with tables"""
    app = create_app()
    
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()
        
        print("Database tables created successfully!")
        
        # Create a default admin user
        admin_user = User(
            email='admin@masterclass-portal.com',
            name='Администратор',
            role='admin'
        )
        admin_user.set_password('admin123')
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("Default admin user created:")
        print("Email: admin@masterclass-portal.com")
        print("Password: admin123")

if __name__ == '__main__':
    init_database()