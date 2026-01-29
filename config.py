import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'license_system.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки безопасности
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Настройки лицензий
    LICENSE_KEY_LENGTH = 25
    INSTALLATION_ID_LENGTH = 32
    MAX_DEVICES_DEFAULT = 5