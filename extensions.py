"""Flask extensions initialization"""
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

# Initialize extensions
db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()