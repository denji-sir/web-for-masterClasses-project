#!/usr/bin/env python3
"""Test public routes implementation"""

import sys
import os
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, EventCreator, Masterclass, Registration

def test_public_routes():
    """Test that public routes work correctly"""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    
    with app.app_context():
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
            max_participants=10,
            price=1000.00,
            category='programming'
        )
        db.session.add(masterclass)
        db.session.commit()
        
        print(f"✓ Created test masterclass with ID: {masterclass.id}")
    
    # Test routes with test client
    with app.test_client() as client:
        # Test index page
        response = client.get('/')
        assert response.status_code == 200
        assert b'Test Masterclass' in response.data
        print("✓ Index page works")
        
        # Test masterclass detail page
        response = client.get(f'/masterclass/{masterclass.id}')
        assert response.status_code == 200
        assert b'Test Masterclass' in response.data
        assert b'Test description' in response.data
        print("✓ Masterclass detail page works")
        
        # Test registration page
        response = client.get(f'/masterclass/{masterclass.id}/register')
        assert response.status_code == 200
        print("✓ Registration page works")
        
        # Test my registrations page
        response = client.get('/my-registrations')
        assert response.status_code == 200
        print("✓ My registrations page works")
        
        # Test search page
        response = client.get('/search')
        assert response.status_code == 200
        print("✓ Search page works")
        
        # Test category filter
        response = client.get('/?category=programming')
        assert response.status_code == 200
        assert b'Test Masterclass' in response.data
        print("✓ Category filter works")

def main():
    """Run all tests"""
    print("Testing public routes...")
    
    try:
        test_public_routes()
        print("\n✅ All route tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
