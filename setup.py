#!/usr/bin/env python3
"""Setup script for the masterclass registration portal"""

import subprocess
import sys
import os

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_env_file():
    """Create .env file from example if it doesn't exist"""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            import shutil
            shutil.copy('.env.example', '.env')
            print("✓ Created .env file from .env.example")
        else:
            with open('.env', 'w') as f:
                f.write('SECRET_KEY=dev-secret-key-change-in-production\n')
                f.write('FLASK_ENV=development\n')
                f.write('FLASK_DEBUG=1\n')
            print("✓ Created basic .env file")

def main():
    """Main setup function"""
    print("Setting up Masterclass Registration Portal...")
    
    # Install dependencies
    if not install_dependencies():
        return 1
    
    # Create .env file
    create_env_file()
    
    print("\n✅ Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run 'python3 init_db.py' to initialize the database")
    print("2. Run 'python3 test_setup.py' to test the setup")
    print("3. Run 'python3 app.py' to start the development server")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())