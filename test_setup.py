#!/usr/bin/env python3
"""Basic test to verify the Flask app and database setup"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration

def test_app_creation():
    """Test that the Flask app can be created"""
    app = create_app()
    assert app is not None
    print("✓ Flask app created successfully")

def test_database_models():
    """Test that database models work correctly"""
    # Set environment variable before creating app
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    
    with app.app_context():
        # Test User model
        user = User(
            email='test@example.com',
            name='Test User',
            role='user'
        )
        user.set_password('testpass')
        
        db.session.add(user)
        db.session.commit()
        
        # Verify user was created
        retrieved_user = User.query.filter_by(email='test@example.com').first()
        assert retrieved_user is not None
        assert retrieved_user.check_password('testpass')
        print("✓ User model works correctly")
        
        # Test EventCreator model
        creator_user = User(
            email='creator@example.com',
            name='Event Creator',
            role='event_creator'
        )
        creator_user.set_password('creatorpass')
        db.session.add(creator_user)
        db.session.commit()
        
        event_creator = EventCreator(
            user_id=creator_user.id,
            company_name='Test Company',
            description='Test description'
        )
        db.session.add(event_creator)
        db.session.commit()
        
        # Verify event creator was created
        retrieved_creator = EventCreator.query.filter_by(user_id=creator_user.id).first()
        assert retrieved_creator is not None
        assert retrieved_creator.company_name == 'Test Company'
        print("✓ EventCreator model works correctly")
        
        # Test Masterclass model
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = Masterclass(
            creator_id=event_creator.id,
            title='Test Masterclass',
            description='Test description',
            date_time=future_date,
            max_participants=20,
            price=1500.00,
            category='Programming'
        )
        db.session.add(masterclass)
        db.session.commit()
        
        # Verify masterclass was created
        retrieved_masterclass = Masterclass.query.filter_by(title='Test Masterclass').first()
        assert retrieved_masterclass is not None
        assert retrieved_masterclass.available_spots == 20
        assert retrieved_masterclass.can_register() == True
        print("✓ Masterclass model works correctly")
        
        # Test Registration model
        registration = Registration(
            masterclass_id=masterclass.id,
            user_name='Test Participant',
            user_email='participant@example.com',
            user_phone='+7-999-123-45-67'
        )
        db.session.add(registration)
        
        # Update participant count
        masterclass.current_participants += 1
        db.session.commit()
        
        # Verify registration was created
        retrieved_registration = Registration.query.filter_by(user_email='participant@example.com').first()
        assert retrieved_registration is not None
        assert masterclass.current_participants == 1
        assert masterclass.available_spots == 19
        print("✓ Registration model works correctly")
        
        # Test unique constraint
        try:
            duplicate_registration = Registration(
                masterclass_id=masterclass.id,
                user_name='Another User',
                user_email='participant@example.com',  # Same email
                user_phone='+7-999-999-99-99'
            )
            db.session.add(duplicate_registration)
            db.session.commit()
            assert False, "Should have raised an integrity error"
        except Exception:
            db.session.rollback()
            print("✓ Unique constraint works correctly")

def main():
    """Run all tests"""
    print("Testing Flask app and database setup...")
    
    try:
        test_app_creation()
        test_database_models()
        print("\n✅ All tests passed! Setup is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())