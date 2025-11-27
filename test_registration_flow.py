#!/usr/bin/env python3
"""Test registration and cancellation flow"""

import sys
import os
import pytest
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration
from services import RegistrationService, MasterclassService

def test_registration_flow():
    """Test complete registration and cancellation flow"""
    app = create_app()
    
    with app.app_context():
        # Clean up existing data
        Registration.query.delete()
        Masterclass.query.delete()
        EventCreator.query.delete()
        User.query.delete()
        db.session.commit()
        
        # Create test data
        creator_user = User(
            email='creator@test.com',
            name='Test Creator',
            role='event_creator'
        )
        creator_user.set_password('password')
        db.session.add(creator_user)
        db.session.commit()
        
        event_creator = EventCreator(
            user_id=creator_user.id,
            company_name='Test Company'
        )
        db.session.add(event_creator)
        db.session.commit()
        
        # Create test masterclass
        future_date = datetime.utcnow() + timedelta(days=7)
        masterclass = Masterclass(
            creator_id=event_creator.id,
            title='Test Masterclass',
            description='Test description',
            date_time=future_date,
            max_participants=5,
            price=1000.00,
            category='programming'
        )
        db.session.add(masterclass)
        db.session.commit()
        
        print(f"✓ Created test masterclass with {masterclass.max_participants} spots")
        
        # Test registration via service
        registration = RegistrationService.register_user(
            masterclass_id=masterclass.id,
            user_name='Test User',
            user_email='test@example.com',
            user_phone='+7-999-123-45-67'
        )
        
        assert registration is not None
        assert masterclass.current_participants == 1
        assert masterclass.available_spots == 4
        print("✓ User registered successfully")
        
        # Test duplicate registration prevention
        from error_handlers import DuplicateRegistrationError
        with pytest.raises(DuplicateRegistrationError):
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='Test User',
                user_email='test@example.com',
                user_phone='+7-999-123-45-67'
            )
        
        assert masterclass.current_participants == 1  # Should not increase
        print("✓ Duplicate registration prevented")
        
        # Test finding registrations by email
        registrations = RegistrationService.get_user_registrations('test@example.com')
        assert len(registrations) == 1
        assert registrations[0].user_email == 'test@example.com'
        print("✓ Found registrations by email")
        
        # Test cancellation
        success = RegistrationService.cancel_registration(
            masterclass_id=masterclass.id,
            user_email='test@example.com'
        )
        
        assert success is True
        assert masterclass.current_participants == 0
        assert masterclass.available_spots == 5
        print("✓ Registration cancelled successfully")
        
        # Test registration on full masterclass
        for i in range(5):
            reg = RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name=f'User {i}',
                user_email=f'user{i}@example.com'
            )
            assert reg is not None
        
        assert masterclass.is_full
        print("✓ Masterclass is now full")
        
        # Try to register on full masterclass
        from error_handlers import MasterclassFullError
        with pytest.raises(MasterclassFullError):
            RegistrationService.register_user(
                masterclass_id=masterclass.id,
                user_name='Late User',
                user_email='late@example.com'
            )
        
        print("✓ Registration on full masterclass prevented")
        
        # Test cancellation time restriction
        past_masterclass = Masterclass(
            creator_id=event_creator.id,
            title='Past Masterclass',
            description='Already happened',
            date_time=datetime.utcnow() - timedelta(hours=1),
            max_participants=10
        )
        db.session.add(past_masterclass)
        db.session.commit()
        
        past_reg = Registration(
            masterclass_id=past_masterclass.id,
            user_name='Past User',
            user_email='past@example.com'
        )
        db.session.add(past_reg)
        past_masterclass.current_participants += 1
        db.session.commit()
        
        from error_handlers import TimeConstraintError
        with pytest.raises(TimeConstraintError):
            RegistrationService.cancel_registration(
                masterclass_id=past_masterclass.id,
                user_email='past@example.com'
            )
        
        print("✓ Cancellation of past masterclass prevented")

def test_routes_with_registration():
    """Test routes with actual registration data"""
    app = create_app()
    app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
    
    with app.app_context():
        # Get existing masterclass
        masterclass = Masterclass.query.first()
        
        if not masterclass:
            print("⚠ No masterclass found, skipping route tests")
            return
    
    with app.test_client() as client:
        # Test registration form submission
        response = client.post(
            f'/masterclass/{masterclass.id}/register',
            data={
                'user_name': 'Form Test User',
                'user_email': 'formtest@example.com',
                'user_phone': '+7-999-999-99-99'
            },
            follow_redirects=True
        )
        
        assert response.status_code == 200
        print(f"✓ Registration form submission works")
        
        # Test search for registrations
        response = client.post(
            '/my-registrations',
            data={
                'email': 'user0@example.com'
            },
            follow_redirects=True
        )
        
        assert response.status_code == 200
        print("✓ Registration search works")

def main():
    """Run all tests"""
    print("Testing registration and cancellation flow...")
    
    try:
        test_registration_flow()
        test_routes_with_registration()
        print("\n✅ All registration flow tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
